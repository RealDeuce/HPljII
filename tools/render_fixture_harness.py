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


def host_byte_fetch_state(**overrides: object) -> dict[str, object]:
    state: dict[str, object] = {
        "service_needed": False,
        "buffer_flags": 0,
        "force_no_byte": False,
        "lifo1": [],
        "data_chain": [],
        "data_chain_end_marker": False,
        "lifo2": [],
        "ring": [],
        "direct_mode": 0,
        "direct_mode1_status": 0,
        "direct_mode1_ack": 0,
        "direct_mode1_data": [],
        "direct_mode2_status": 0,
        "direct_mode2_data": [],
        "mode1_control_shadow": 0x12,
        "mode2_control_shadow": 0x20,
        "handshake_state": 0,
        "timeout_state": 1,
        "status_error": 0,
        "service_calls": 0,
        "control_1a_reports": 0,
        "data_chain_transitions": 0,
    }
    state.update(overrides)
    return state


def host_byte_fetch_via_a904(initial: dict[str, object]) -> dict[str, object]:
    state = dict(initial)
    events: list[dict[str, object]] = []

    for _ in range(8):
        if bool(state.get("service_needed")):
            state["service_calls"] = int(state.get("service_calls", 0)) + 1
            state["service_needed"] = False
            events.append({"kind": "service-retry", "helper": 0x10CC, "argument": 0x780202})
            continue

        if int(state.get("buffer_flags", 0)) != 0 and bool(state.get("force_no_byte")):
            return {
                "d7": -1,
                "source": "no-byte",
                "events": events,
                "state": state,
            }

        lifo1 = list(state.get("lifo1", []))
        if lifo1:
            value = int(lifo1.pop()) & 0xFF
            state["lifo1"] = lifo1
            return {
                "d7": value,
                "source": "first-lifo",
                "events": events + [{"kind": "first-lifo", "remaining": len(lifo1)}],
                "state": state,
            }

        if bool(state.get("data_chain_end_marker")):
            state["data_chain_end_marker"] = False
            state["data_chain_transitions"] = int(state.get("data_chain_transitions", 0)) + 1
            events.append({"kind": "data-chain-transition", "helper": 0xE22C})
            continue

        data_chain = list(state.get("data_chain", []))
        if data_chain:
            value = int(data_chain.pop(0)) & 0xFF
            state["data_chain"] = data_chain
            return {
                "d7": value,
                "source": "data-chain",
                "events": events + [{"kind": "data-chain-byte", "remaining": len(data_chain)}],
                "state": state,
            }

        lifo2 = list(state.get("lifo2", []))
        if lifo2:
            value = int(lifo2.pop()) & 0xFF
            state["lifo2"] = lifo2
            return {
                "d7": value,
                "source": "second-lifo",
                "events": events + [{"kind": "second-lifo", "remaining": len(lifo2)}],
                "state": state,
            }

        ring = list(state.get("ring", []))
        if int(state.get("direct_mode", 0)) == 0 and ring:
            value = int(ring.pop(0)) & 0xFF
            state["ring"] = ring
            return {
                "d7": value,
                "source": "ring",
                "events": events + [{"kind": "ring-byte", "remaining": len(ring)}],
                "state": state,
            }

        if int(state.get("direct_mode", 0)) == 1:
            if (int(state.get("direct_mode1_status", 0)) & 0x10) == 0:
                state["service_calls"] = int(state.get("service_calls", 0)) + 1
                events.append({"kind": "mode1-timeout-retry", "helper": 0xAA88})
                continue
            direct_data = list(state.get("direct_mode1_data", []))
            if not direct_data:
                return {
                    "d7": -1,
                    "source": "mode1-empty",
                    "events": events,
                    "state": state,
                }
            value = int(direct_data.pop(0)) & 0xFF
            state["direct_mode1_data"] = direct_data
            if value == 0x1A:
                state["control_1a_reports"] = int(state.get("control_1a_reports", 0)) + 1
                events.append({"kind": "control-1a-report", "helper": 0x9EC0})
            state["handshake_state"] = 0
            state["timeout_state"] = 0
            return {
                "d7": value,
                "source": "direct-mode-1",
                "events": events + [{
                    "kind": "mode1-handshake",
                    "status": int(state.get("direct_mode1_status", 0)),
                    "ack": int(state.get("direct_mode1_ack", 0)),
                    "control_shadow": int(state.get("mode1_control_shadow", 0)) & 0xFF,
                }],
                "state": state,
            }

        status = int(state.get("direct_mode2_status", 0))
        if (status & 0x01) == 0:
            if status & 0x80:
                state["status_error"] = int(state.get("status_error", 0)) | 0x80
            if status & 0x40:
                state["status_error"] = int(state.get("status_error", 0)) | 0x40
            state["service_calls"] = int(state.get("service_calls", 0)) + 1
            events.append({"kind": "mode2-status-retry", "status_error": int(state.get("status_error", 0))})
            continue
        direct_data = list(state.get("direct_mode2_data", []))
        if not direct_data:
            return {
                "d7": -1,
                "source": "mode2-empty",
                "events": events,
                "state": state,
            }
        value = int(direct_data.pop(0)) & 0xFF
        state["direct_mode2_data"] = direct_data
        if value == 0x1A:
            state["control_1a_reports"] = int(state.get("control_1a_reports", 0)) + 1
            events.append({"kind": "control-1a-report", "helper": 0x9EC0})
        state["handshake_state"] = 1
        state["timeout_state"] = 0
        state["mode2_control_shadow"] = int(state.get("mode2_control_shadow", 0)) | 0x40
        return {
            "d7": value,
            "source": "direct-mode-2",
            "events": events + [{
                "kind": "mode2-handshake",
                "status": status,
                "control_shadow": int(state.get("mode2_control_shadow", 0)) & 0xFF,
            }],
            "state": state,
        }

    raise AssertionError("host byte fetch model did not converge")


def signed_word_bytes(value: int) -> bytes:
    value &= 0xFFFF
    return value.to_bytes(2, "big")


def parse_pcl_numeric_records_via_daf0(stream: bytes, cursor_base: int = 0x7829A2) -> dict[str, object]:
    pos = 0
    records: list[dict[str, object]] = []
    scratch = bytearray()
    returned_d7: list[int] = []
    lookahead: int | None = None

    def read_byte() -> int:
        nonlocal pos
        if pos >= len(stream):
            return -1
        value = stream[pos]
        pos += 1
        return value

    def unread_byte() -> None:
        nonlocal pos
        if pos > 0:
            pos -= 1

    while True:
        flag = 0
        sign_negative = False
        integer_value = 0
        fraction_value = 0
        value = read_byte()
        while value == 0x20:
            value = read_byte()
        if value in (0x2B, 0x2D):
            scratch.append(value)
            flag = 0x81
            sign_negative = value == 0x2D
            value = read_byte()
            while value == 0x20:
                value = read_byte()
        if value == 0x2E or 0x30 <= value <= 0x39:
            flag |= 0x80
        if value == 0x30:
            while value == 0x30:
                scratch.append(value)
                value = read_byte()

        digit_budget = 6
        while 0x30 <= value <= 0x39:
            if digit_budget > 0:
                scratch.append(value)
                integer_value = integer_value * 10 + (value & 0x0F)
                digit_budget -= 1
            value = read_byte()
        if integer_value > 0x7FFF:
            integer_value = 0x7FFF
        if sign_negative:
            integer_value = -integer_value

        if value == 0x2E:
            scratch.append(value)
            value = read_byte()
            fraction_budget = 4
            while fraction_budget > 0:
                fraction_budget -= 1
                fraction_value *= 10
                if 0x30 <= value <= 0x39:
                    scratch.append(value)
                    fraction_value += value & 0x0F
                    value = read_byte()
            if sign_negative:
                fraction_value = -fraction_value
            while 0x30 <= value <= 0x39:
                value = read_byte()

        if value < 0:
            final = 0
        else:
            final = value & 0xFF
        returned = 0 if final in (0x3A, 0x3B) else final
        record_bytes = bytes([flag & 0xFF, final]) + signed_word_bytes(integer_value) + signed_word_bytes(fraction_value)
        record = {
            "record": record_bytes,
            "flag": flag & 0xFF,
            "final": final,
            "parameter": integer_value,
            "fraction": fraction_value,
            "cursor_before": cursor_base + len(records) * 6,
            "cursor_after": cursor_base + (len(records) + 1) * 6,
            "returned_d7": returned,
        }
        records.append(record)
        returned_d7.append(returned)

        lookahead = read_byte()
        if not (flag & 0x80 and 0x20 <= lookahead <= 0x3F):
            break
        unread_byte()

    return {
        "records": records,
        "record_bytes": b"".join(bytes(record["record"]) for record in records),
        "scratch": bytes(scratch),
        "returned_d7": returned_d7,
        "cursor": cursor_base + len(records) * 6,
        "lookahead": lookahead,
        "stream_pos": pos,
    }


def delay_payload_handler_via_121cc(record: bytes, handler: int) -> dict[str, object]:
    if len(record) != 6:
        raise AssertionError("0x121cc delayed handler snapshot requires one six-byte parsed command record")
    return {
        "pending_flag": 1,
        "handler": handler & 0xFFFFFF,
        "snapshot_record": bytes(record),
        "snapshot_bytes": bytes([1]) + (handler & 0xFFFFFFFF).to_bytes(4, "big") + record,
    }


def restore_delayed_payload_via_12218(pending: dict[str, object], alternate_mode: bool = False, cursor: int = 0x7829A2) -> dict[str, object]:
    if int(pending.get("pending_flag", 0)) != 1:
        return {
            "restored": False,
            "cursor_before": cursor,
            "cursor_after": cursor,
            "dispatch": None,
            "pending_after": pending,
        }
    record = bytes(pending["snapshot_record"])
    dispatch: dict[str, int | str]
    if alternate_mode:
        dispatch = {"kind": "alternate-data-wrapper", "helper": 0x12358, "wrapper": 0x1228A}
    else:
        dispatch = {"kind": "direct-handler", "handler": int(pending["handler"])}
    return {
        "restored": True,
        "record": record,
        "cursor_before": cursor,
        "cursor_after": cursor + 6,
        "dispatch": dispatch,
        "pending_after": {
            "pending_flag": 0,
            "handler": 0,
            "snapshot_record": record,
        },
    }


def data_payload_byte_via_dace(stream: bytes, pos: int) -> dict[str, object]:
    if pos >= len(stream):
        return {"value": -1, "pos": pos, "control_hits": 0}
    value = stream[pos]
    pos += 1
    if value != 0x1A:
        return {"value": value, "pos": pos, "control_hits": 0}
    if pos >= len(stream):
        return {"value": -1, "pos": pos, "control_hits": 0}
    value = stream[pos]
    pos += 1
    if value == 0x58:
        return {"value": 0, "pos": pos, "control_hits": 1}
    return {"value": value, "pos": pos, "control_hits": 0}


def consume_data_payload_count_via_12328(byte_count: int, stream: bytes, pos: int = 0) -> dict[str, object]:
    remaining = int(byte_count)
    values: list[int] = []
    control_hits = 0
    while remaining > 0:
        read = data_payload_byte_via_dace(stream, pos)
        value = int(read["value"])
        pos = int(read["pos"])
        control_hits += int(read["control_hits"])
        if value == -1:
            return {
                "status": -1,
                "values": values,
                "pos": pos,
                "remaining": remaining,
                "control_hits": control_hits,
            }
        values.append(value)
        remaining -= 1
    return {
        "status": 1,
        "values": values,
        "pos": pos,
        "remaining": remaining,
        "control_hits": control_hits,
    }


def alternate_payload_dispatch_via_12358(
    record: bytes,
    stream: bytes,
    callback_matches_wrapper: bool,
    cursor_after_record: int = 0x7829A8,
) -> dict[str, object]:
    if len(record) != 6:
        raise AssertionError("0x12358 alternate payload dispatch requires one six-byte parsed command record")
    cursor_rewound = cursor_after_record - 6
    count = s16(record, 2)
    if callback_matches_wrapper:
        consumed = consume_data_payload_count_via_12328(abs(count), stream)
        return {
            "path": "wrapper-1228a",
            "cursor_before": cursor_after_record,
            "cursor_after": cursor_rewound,
            "byte_count": abs(count),
            "status": consumed["status"],
            "values": consumed["values"],
            "echoed": [],
            "pos": consumed["pos"],
            "remaining": consumed["remaining"],
            "control_hits": consumed["control_hits"],
        }

    if count <= 0:
        return {
            "path": "direct-12358",
            "cursor_before": cursor_after_record,
            "cursor_after": cursor_rewound,
            "byte_count": count,
            "status": 1,
            "values": [],
            "echoed": [],
            "pos": 0,
            "remaining": count,
            "control_hits": 0,
        }

    consumed = consume_data_payload_count_via_12328(count, stream)
    return {
        "path": "direct-12358",
        "cursor_before": cursor_after_record,
        "cursor_after": cursor_rewound,
        "byte_count": count,
        "status": consumed["status"],
        "values": consumed["values"],
        "echoed": list(consumed["values"]),
        "pos": consumed["pos"],
        "remaining": consumed["remaining"],
        "control_hits": consumed["control_hits"],
    }


PAGE_GEOMETRY_TABLES = {
    "height": 0x00A112,
    "width": 0x00A128,
    "landscape_margin": 0x00A13E,
    "portrait_margin": 0x00A154,
}


def page_geometry_lookup_via_9dxx(data: bytes, table: str, page_code: int) -> int:
    index = int(page_code) & 0x7F
    if index >= 0x0B:
        return 0
    return u16(data, PAGE_GEOMETRY_TABLES[table] + index * 2)


def page_center_remainder_via_9e56(height: int) -> int:
    return (0x051F - (int(height) >> 1)) % 0x10


def page_geometry_state(**overrides: int) -> dict[str, int]:
    state = {
        "page_code": 2,
        "orientation": 0,
        "default_page_code": 2,
        "pending_text_flushes": 0,
        "page_finalizations": 0,
        "active_record_waits": 0,
        "page_change_flag": 0,
        "print_engine_status": 1,
        "width": 0,
        "height": 0,
        "margin_reference": 0,
        "active_width": 0,
        "active_height": 0,
        "vertical_offset_source": 0,
        "negative_vertical_offset": 0,
        "secondary_vertical_offset": 0,
        "printable_extent": 0,
        "top_offset": 0,
        "top_offset_fraction": 0,
        "center_remainder": 0,
        "portrait_landscape_threshold_6": 0,
        "portrait_landscape_threshold_2": 0,
        "portrait_landscape_threshold_1": 0,
        "portrait_landscape_threshold_5": 0,
    }
    state.update(overrides)
    return state


def map_page_size_parameter_via_fc74(parameter: int, has_parameter: bool = True, default_page_code: int = 2) -> int | None:
    if not has_parameter:
        return int(default_page_code) if int(default_page_code) != 0 else 2
    value = abs(int(parameter))
    mapping = {
        1: 6,
        2: 2,
        3: 5,
        26: 1,
        80: 0x88,
        81: 0x87,
        90: 0x89,
        91: 0x8A,
    }
    return mapping.get(value)


def apply_page_geometry_tables(data: bytes, state: dict[str, int]) -> dict[str, int]:
    state = dict(state)
    page_code = int(state["page_code"])
    orientation = int(state["orientation"])
    state["width"] = page_geometry_lookup_via_9dxx(data, "width", page_code)
    state["height"] = page_geometry_lookup_via_9dxx(data, "height", page_code)
    margin_table = "landscape_margin" if orientation else "portrait_margin"
    state["margin_reference"] = page_geometry_lookup_via_9dxx(data, margin_table, page_code)
    if orientation:
        state["vertical_offset_source"] = 0x32
        state["active_width"] = state["height"]
        state["active_height"] = state["width"]
    else:
        state["vertical_offset_source"] = 0x3C
        state["active_width"] = state["width"]
        state["active_height"] = state["height"]
    state["negative_vertical_offset"] = -int(state["vertical_offset_source"])
    state["secondary_vertical_offset"] = 0
    state["printable_extent"] = int(state["margin_reference"]) - int(state["vertical_offset_source"])
    state["top_offset"] = 0x96 - int(state["vertical_offset_source"])
    state["top_offset_fraction"] = 0
    state["center_remainder"] = page_center_remainder_via_9e56(int(state["height"]))
    return state


def apply_orientation_thresholds_via_103ea(data: bytes, state: dict[str, int]) -> dict[str, int]:
    state = dict(state)
    table = "landscape_margin" if int(state["orientation"]) else "portrait_margin"
    state["portrait_landscape_threshold_6"] = page_geometry_lookup_via_9dxx(data, table, 6)
    state["portrait_landscape_threshold_2"] = page_geometry_lookup_via_9dxx(data, table, 2)
    state["portrait_landscape_threshold_1"] = page_geometry_lookup_via_9dxx(data, table, 1)
    state["portrait_landscape_threshold_5"] = page_geometry_lookup_via_9dxx(data, table, 5)
    return state


def apply_page_size_via_fc74(data: bytes, state: dict[str, int], parameter: int = 0, has_parameter: bool = True) -> dict[str, int]:
    state = dict(state)
    internal_code = map_page_size_parameter_via_fc74(parameter, has_parameter, state["default_page_code"])
    if internal_code is None:
        state["ignored_page_size_parameter"] = abs(int(parameter))
        return state
    state["pending_text_flushes"] += 1
    state["page_finalizations"] += 1
    if not has_parameter:
        state["active_record_waits"] += 1
    state["page_change_flag"] = 1
    state["print_engine_status"] = 0
    state["page_code"] = internal_code
    return apply_page_geometry_tables(data, state)


def apply_orientation_via_10220(data: bytes, state: dict[str, int], parameter: int) -> dict[str, int]:
    state = dict(state)
    orientation = abs(int(parameter))
    if orientation >= 2 or orientation == int(state["orientation"]):
        state["ignored_orientation_parameter"] = orientation
        return state
    state["pending_text_flushes"] += 1
    state["page_finalizations"] += 1
    state["orientation"] = orientation
    state = apply_page_geometry_tables(data, state)
    state = apply_orientation_thresholds_via_103ea(data, state)
    return state


def macro_record(payload: bytes = b"", macro_id: int = 0, permanent: bool = False) -> dict[str, object]:
    return {
        "id": macro_id & 0xFFFF,
        "payload": bytes(payload),
        "permanent": bool(permanent),
    }


def macro_state(**overrides: object) -> dict[str, object]:
    state: dict[str, object] = {
        "current_macro_id": 0,
        "records": [macro_record() for _ in range(32)],
        "current_record": None,
        "alternate_mode": 0,
        "macro_error": 0,
        "parser_mode": 0,
        "overlay_macro_id": 0,
        "data_chain_frames": [],
        "host_gate_bit1": 0,
        "data_chain_slot": 0,
        "events": [],
    }
    state.update(overrides)
    return state


def assign_macro_id_via_e112(record: bytes, state: dict[str, object] | None = None) -> dict[str, object]:
    if len(record) != 6:
        raise AssertionError("0xe112 macro id assignment requires one six-byte parsed command record")
    updated = macro_state() if state is None else dict(state)
    value = s16(record, 2)
    if value < 0:
        value = -value
    updated["current_macro_id"] = value & 0xFFFF
    return updated


def find_macro_record_via_e0a4(state: dict[str, object], macro_id: int) -> dict[str, object]:
    records = list(state["records"])
    first_free: int | None = None
    for index, record_obj in enumerate(records):
        record = dict(record_obj)
        if int(record.get("id", 0)) == (macro_id & 0xFFFF) and bytes(record.get("payload", b"")):
            return {"status": 1, "index": index, "record": record}
        if first_free is None and int(record.get("id", 0)) == 0 and not bytes(record.get("payload", b"")):
            first_free = index
    if first_free is None:
        return {"status": 2, "index": None, "record": None}
    records[first_free] = macro_record(macro_id=macro_id)
    state["records"] = records
    return {"status": 0, "index": first_free, "record": records[first_free]}


def clear_macro_record_via_dfba(state: dict[str, object], index: int) -> None:
    records = list(state["records"])
    old_id = int(records[index].get("id", 0))
    records[index] = macro_record()
    state["records"] = records
    if int(state.get("overlay_macro_id", 0)) == old_id:
        state["parser_mode"] = 0


def execute_macro_data_chain_via_e418(state: dict[str, object], index: int, mode: int) -> dict[str, object]:
    records = list(state["records"])
    record = dict(records[index])
    payload = bytes(record.get("payload", b""))
    frame = {
        "payload": payload,
        "byte_count": len(payload),
        "byte_8": 4,
        "byte_9": mode,
        "environment": "execute" if mode == 2 else "call",
    }
    frames = list(state.get("data_chain_frames", []))
    frames.append(frame)
    state["data_chain_frames"] = frames
    state["data_chain_slot"] = int(state.get("data_chain_slot", 0)) + 1
    if payload:
        state["host_gate_bit1"] = 1
    events = list(state.get("events", []))
    events.append({"kind": "macro-data-chain", "mode": mode, "payload": payload})
    state["events"] = events
    return frame


def apply_macro_control_via_dd08(state: dict[str, object], parameter: int, final_byte: int = 0x58) -> dict[str, object]:
    updated = dict(state)
    updated["records"] = [dict(record) for record in state["records"]]
    updated["data_chain_frames"] = list(state.get("data_chain_frames", []))
    updated["events"] = list(state.get("events", []))
    selector = abs(int(parameter))
    current_id = int(updated.get("current_macro_id", 0)) & 0xFFFF
    lookup = find_macro_record_via_e0a4(updated, current_id)
    status = int(lookup["status"])
    index = lookup["index"]

    current_chain_active = int(updated.get("current_data_chain_byte_9", 0)) != 0
    if current_chain_active and selector not in (2, 3):
        updated["events"].append({"kind": "macro-control-ignored", "selector": selector, "reason": "active-data-chain"})
        return updated
    if int(updated.get("alternate_mode", 0)) == 1 and selector != 1:
        updated["events"].append({"kind": "macro-control-ignored", "selector": selector, "reason": "alternate-mode"})
        return updated

    if selector == 0:
        if index is None:
            updated["macro_error"] = 1
            updated["alternate_mode"] = 1
            updated["events"].append({"kind": "macro-start-failed", "status": status})
            return updated
        updated["records"][index] = macro_record(
            b"\x1b&f" if final_byte == 0x78 else b"\x00",
            macro_id=current_id,
        )
        updated["current_record"] = index
        updated["alternate_mode"] = 1
        updated["macro_error"] = 0
        updated["events"].append({"kind": "macro-start", "status": status, "index": index, "auto_prefix": final_byte == 0x78})
        return updated

    if selector == 1:
        if int(updated.get("alternate_mode", 0)) != 1:
            return updated
        if int(updated.get("macro_error", 0)) == 0 and index is not None:
            payload = bytes(updated["records"][index].get("payload", b""))
            if len(payload) == 1 or payload == b"\x1b&f":
                updated["records"][index] = macro_record()
                updated["events"].append({"kind": "macro-stop-cleared-empty", "index": index})
            else:
                updated["events"].append({"kind": "macro-stop-kept", "index": index, "payload": payload})
        updated["macro_error"] = 0
        updated["alternate_mode"] = 0
        return updated

    if selector in (2, 3):
        if index is not None and status == 1 and bytes(updated["records"][index].get("payload", b"")):
            execute_macro_data_chain_via_e418(updated, index, selector)
        return updated

    if selector == 4:
        if status == 1:
            updated["parser_mode"] = 1
            updated["overlay_macro_id"] = current_id
            updated["events"].append({"kind": "macro-overlay-enable", "id": current_id})
        else:
            updated["parser_mode"] = 0
        return updated

    if selector == 5:
        updated["parser_mode"] = 0
        updated["events"].append({"kind": "macro-overlay-disable"})
        return updated

    if selector == 6:
        updated["records"] = [macro_record() for _ in range(32)]
        updated["parser_mode"] = 0
        updated["events"].append({"kind": "macro-delete-all"})
        return updated

    if selector == 7:
        updated["records"] = [
            dict(record) if bool(dict(record).get("permanent", False)) else macro_record()
            for record in updated["records"]
        ]
        updated["events"].append({"kind": "macro-delete-temporary"})
        return updated

    if selector == 8:
        if index is not None:
            updated["records"][index] = macro_record()
            updated["events"].append({"kind": "macro-delete-current", "index": index})
        return updated

    if selector == 9:
        if index is not None and status == 1:
            updated["records"][index]["permanent"] = False
            updated["events"].append({"kind": "macro-make-temporary", "index": index})
        return updated

    if selector == 10:
        if index is not None and status == 1:
            updated["records"][index]["permanent"] = True
            updated["events"].append({"kind": "macro-make-permanent", "index": index})
        return updated

    updated["events"].append({"kind": "macro-control-ignored", "selector": selector, "reason": "selector-out-of-range"})
    return updated


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


def resolve_inline_glyph(resources: bytes | bytearray, context: int, glyph_index: int) -> dict[str, int | bytes]:
    base = context & 0x00FFFFFF
    record = base + 0x40 + (glyph_index & 0xFF) * 8
    if record + 8 > len(resources):
        raise AssertionError(f"inline glyph record 0x{record:06x} is outside the fixture resource buffer")
    render_span = resources[record]
    rows = resources[record + 1]
    bitmap = base + u32(resources, record + 4)
    if render_span <= 0:
        raise AssertionError("inline glyph fixture requires a positive byte span")
    if bitmap + rows * render_span > len(resources):
        raise AssertionError(f"inline glyph bitmap 0x{bitmap:06x} is outside the fixture resource buffer")
    return {
        "base": base,
        "entry": record,
        "bitmap": bitmap,
        "delta": u32(resources, record + 4),
        "mode": 1,
        "rows": rows,
        "width": render_span * 8,
        "span": render_span,
        "render_span": render_span,
        "source_kind": "inline",
    }


def resolve_compact_glyph(resources: bytes | bytearray, context: int, glyph_index: int) -> dict[str, int | bytes]:
    if context & 0x40000000:
        glyph = resolve_builtin_glyph(bytes(resources), context, glyph_index)
        glyph["source_kind"] = "builtin"
        return glyph
    return resolve_inline_glyph(resources, context, glyph_index)


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


def metric_long_via_10550(value: int) -> int:
    d7 = (int(value) & 0xFFFFFFFF) >> 2
    low_product = (d7 & 0xFFFF) * 12
    return (d7 & 0xFFFF0000) | ((low_product >> 16) & 0xFFFF)


def builtin_flagged_hmi_from_context(resources: bytes, context: int) -> dict[str, int]:
    if not (context & 0x40000000):
        raise AssertionError(f"context 0x{context:08x} does not select the built-in offset-table form")
    base = (context & 0x00FFFFFF) - 0x80000
    raw = u32(resources, base + 0x24)
    return {
        "base": base,
        "metric_flag": resources[base + 0x21],
        "raw_metric": raw,
        "hmi": metric_long_via_10550(raw),
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


def inline_record_is_valid_via_14eb6(memory: bytes, context: int, glyph: int) -> dict[str, int | bool | bytes]:
    base = context & 0x00FFFFFF
    record = base + 0x40 + (glyph & 0xFFFF) * 8
    if record + 8 > len(memory):
        return {
            "base": base,
            "glyph": glyph & 0xFFFF,
            "record": record,
            "record_bytes": b"",
            "bitmap": 0,
            "valid": False,
            "reason": "record-out-of-range",
        }
    record_bytes = bytes(memory[record:record + 8])
    width = record_bytes[0]
    rows = record_bytes[1]
    bitmap_delta = int.from_bytes(record_bytes[4:8], "big") & 0x00FFFFFF
    bitmap = base + bitmap_delta
    if width == 1 and rows == 2:
        valid = bitmap + 2 <= len(memory) and int.from_bytes(memory[bitmap:bitmap + 2], "big") != 0
        return {
            "base": base,
            "glyph": glyph & 0xFFFF,
            "record": record,
            "record_bytes": record_bytes,
            "bitmap": bitmap,
            "valid": valid,
            "reason": "sentinel-bitmap-word" if valid else "zero-sentinel-bitmap-word",
        }
    valid = width != 0 and rows != 0 and bitmap_delta != 0
    return {
        "base": base,
        "glyph": glyph & 0xFFFF,
        "record": record,
        "record_bytes": record_bytes,
        "bitmap": bitmap,
        "valid": valid,
        "reason": "nonzero-fixed-record" if valid else "empty-fixed-record",
    }


def inline_map_via_14e24(memory: bytes, context: int, extended_half_enabled: bool = False) -> dict[str, object]:
    table = [0] * 0x100
    validity: list[dict[str, int | bool | bytes]] = []
    for host in range(0x20, 0x80):
        glyph = host - 0x20
        probe = inline_record_is_valid_via_14eb6(memory, context, glyph)
        validity.append(probe)
        if bool(probe["valid"]):
            table[host] = glyph
    if extended_half_enabled:
        for host in range(0xA0, 0x100):
            glyph = host - 0x40
            probe = inline_record_is_valid_via_14eb6(memory, context, glyph)
            validity.append(probe)
            if bool(probe["valid"]):
                table[host] = glyph
    return {
        "context": context,
        "base": context & 0x00FFFFFF,
        "extended_half_enabled": extended_half_enabled,
        "table": bytes(table),
        "validity": validity,
    }


def build_inline_text_source_object_from_1393a(memory: bytes, context: int, map_table: bytes, host_char: int, x: int, y: int, context_slot: int = 0) -> dict[str, object]:
    mapped = map_table[host_char & 0xFF]
    base = context & 0x00FFFFFF
    record = base + 0x40 + mapped * 8
    if record + 8 > len(memory):
        raise AssertionError(f"inline/downloaded glyph record 0x{record:x} is outside the synthetic memory image")
    record_bytes = bytes(memory[record:record + 8])
    validity = inline_record_is_valid_via_14eb6(memory, context, mapped)
    return {
        "context": context,
        "host_char": host_char & 0xFF,
        "mapped": mapped,
        "glyph_entry": record,
        "glyph_width": record_bytes[0],
        "glyph_rows": record_bytes[1],
        "flag": 0,
        "x": x,
        "y": y,
        "context_slot": context_slot & 0x0F,
        "inline_record": record_bytes,
        "valid_record": bool(validity["valid"]),
        "bitmap": int(validity["bitmap"]),
    }


def font_payload_linear_copy_via_168dc(stream: bytes, byte_count: int, byte_budget: int) -> dict[str, object]:
    pos = 0
    remaining = int(byte_count)
    budget = int(byte_budget)
    dest = bytearray()
    control_hits = 0
    while remaining > 0:
        if budget <= 0:
            return {
                "status": 2,
                "dest": bytes(dest),
                "stream_pos": pos,
                "remaining": remaining,
                "byte_budget": budget,
                "continuation": {
                    "flag": 1,
                    "remaining": remaining,
                    "dest_offset": len(dest),
                },
                "control_hits": control_hits,
            }
        if pos >= len(stream):
            return {
                "status": 0,
                "dest": bytes(dest),
                "stream_pos": pos,
                "remaining": remaining,
                "byte_budget": budget,
                "continuation": None,
                "control_hits": control_hits,
            }
        value = stream[pos]
        pos += 1
        if value == 0x1A:
            if pos >= len(stream):
                return {
                    "status": 0,
                    "dest": bytes(dest),
                    "stream_pos": pos,
                    "remaining": remaining,
                    "byte_budget": budget,
                    "continuation": None,
                    "control_hits": control_hits,
                }
            value = stream[pos]
            pos += 1
            if value == 0x58:
                control_hits += 1
                value = 0
        dest.append(value)
        budget -= 1
        remaining -= 1
    return {
        "status": 1,
        "dest": bytes(dest),
        "stream_pos": pos,
        "remaining": 0,
        "byte_budget": budget,
        "continuation": None,
        "control_hits": control_hits,
    }


def font_payload_split_plane_copy_via_16942(stream: bytes, rows: int, prefix_span: int, byte_budget: int) -> dict[str, object]:
    pos = 0
    budget = int(byte_budget)
    row_remaining = int(rows)
    prefix_remaining = int(prefix_span)
    prefix = bytearray()
    trailing = bytearray()
    control_hits = 0
    phase = "prefix"
    while row_remaining > 0:
        if prefix_remaining > 0:
            if budget <= 0:
                return {
                    "status": 2,
                    "prefix": bytes(prefix),
                    "trailing": bytes(trailing),
                    "stream_pos": pos,
                    "byte_budget": budget,
                    "continuation": {
                        "flag": 1,
                        "prefix_remaining": prefix_remaining - 1,
                        "row_remaining": row_remaining - 1,
                        "prefix_offset": len(prefix),
                        "trailing_offset": len(trailing),
                    },
                    "control_hits": control_hits,
                    "phase": phase,
                }
            if pos >= len(stream):
                return {
                    "status": 0,
                    "prefix": bytes(prefix),
                    "trailing": bytes(trailing),
                    "stream_pos": pos,
                    "byte_budget": budget,
                    "continuation": None,
                    "control_hits": control_hits,
                    "phase": phase,
                }
            value = stream[pos]
            pos += 1
            if value == 0x1A:
                if pos >= len(stream):
                    return {
                        "status": 0,
                        "prefix": bytes(prefix),
                        "trailing": bytes(trailing),
                        "stream_pos": pos,
                        "byte_budget": budget,
                        "continuation": None,
                        "control_hits": control_hits,
                        "phase": phase,
                    }
                value = stream[pos]
                pos += 1
                if value == 0x58:
                    control_hits += 1
                    value = 0
            prefix.append(value)
            budget -= 1
            prefix_remaining -= 1
            continue

        phase = "trailing"
        if budget <= 0:
            return {
                "status": 2,
                "prefix": bytes(prefix),
                "trailing": bytes(trailing),
                "stream_pos": pos,
                "byte_budget": budget,
                "continuation": {
                    "flag": 1,
                    "prefix_remaining": -1,
                    "row_remaining": row_remaining - 1,
                    "prefix_offset": len(prefix),
                    "trailing_offset": len(trailing),
                },
                "control_hits": control_hits,
                "phase": phase,
            }
        if pos >= len(stream):
            return {
                "status": 0,
                "prefix": bytes(prefix),
                "trailing": bytes(trailing),
                "stream_pos": pos,
                "byte_budget": budget,
                "continuation": None,
                "control_hits": control_hits,
                "phase": phase,
            }
        value = stream[pos]
        pos += 1
        if value == 0x1A:
            if pos >= len(stream):
                return {
                    "status": 0,
                    "prefix": bytes(prefix),
                    "trailing": bytes(trailing),
                    "stream_pos": pos,
                    "byte_budget": budget,
                    "continuation": None,
                    "control_hits": control_hits,
                    "phase": phase,
                }
            value = stream[pos]
            pos += 1
            if value == 0x58:
                control_hits += 1
                value = 0
        trailing.append(value)
        budget -= 1
        row_remaining -= 1
        prefix_remaining = int(prefix_span)
        phase = "prefix"
    return {
        "status": 1,
        "prefix": bytes(prefix),
        "trailing": bytes(trailing),
        "stream_pos": pos,
        "byte_budget": budget,
        "continuation": None,
        "control_hits": control_hits,
        "phase": "done",
    }


FONT_RECORD_BASE = 0x782640
FONT_RECORD_SIZE = 10
FONT_RESOURCE_VALIDATE_TABLE: tuple[tuple[int, int], ...] = (
    (0x159F6, 0x17358),
    (0x1599C, 0x17358),
    (0x1599C, 0x17362),
    (0x159F6, 0x17358),
    (0x159D4, 0x173D0),
    (0x159D4, 0x173FE),
    (0x159D4, 0x17430),
    (0x1599C, 0x1749E),
    (0x1599C, 0x174CC),
    (0x159D4, 0x17502),
    (0x159D4, 0x1751A),
    (0x159D4, 0x1754A),
    (0x159D4, 0x1757A),
    (0x1599C, 0x17358),
    (0x1599C, 0x175C2),
    (0x159B6, 0x175DA),
    (0x1599C, 0x17612),
    (0x1599C, 0x17358),
    (0x1599C, 0x17358),
    (0x1599C, 0x17358),
    (0x1599C, 0x17358),
    (0x159B6, 0x1762A),
    (0x1599C, 0x17358),
    (0x159F6, 0x17358),
    (0x159F6, 0x17358),
    (0x159D4, 0x17642),
    (0x159D4, 0x17358),
    (0x1599C, 0x17690),
    (0x1599C, 0x176C2),
    (0x159D4, 0x17358),
    (0x159D4, 0x17358),
    (0x159D4, 0x17358),
)


def font_resource_record_scan_via_172c0(records: list[dict[str, int]], current_id: int) -> dict[str, object]:
    current_id &= 0xFFFF
    for index, record in enumerate(records):
        if (int(record.get("id", 0)) & 0xFFFF) == current_id and int(record.get("payload", 0)) != 0:
            return {
                "status": 0,
                "index": index,
                "address": FONT_RECORD_BASE + index * FONT_RECORD_SIZE,
                "record": dict(record),
            }
    for index, record in enumerate(records):
        if (int(record.get("id", 0)) & 0xFFFF) == 0 and int(record.get("payload", 0)) == 0:
            return {
                "status": 1,
                "index": index,
                "address": FONT_RECORD_BASE + index * FONT_RECORD_SIZE,
                "record": dict(record),
            }
    return {
        "status": 2,
        "index": None,
        "address": None,
        "record": None,
    }


def font_counter_defaults() -> dict[str, int]:
    return {
        "0x78278e": 0,
        "0x782790": 0,
        "0x782796": 0,
        "0x782798": 0,
        "0x78279e": 0,
        "0x78278a": 0,
        "0x782782": 0,
    }


def font_cursor_defaults() -> dict[str, int]:
    return {
        "0x7827ac": 0,
        "0x7827b0": 0,
        "0x7827b4": 0,
    }


def clear_download_continuation_state(continuation: dict[str, int]) -> dict[str, int]:
    cleared = dict(continuation)
    for key in ("flag", "payload", "word_0x7827c8", "dest", "trailing_dest", "remaining", "d4_counter", "d3_counter"):
        cleared[key] = 0
    return cleared


def downloaded_font_object_add_bookkeeping_via_16c14(
    records: list[dict[str, int]],
    *,
    current_id: int,
    new_payload: int,
    byte20: int,
    byte0c: int,
    counters: dict[str, int] | None = None,
    cursors: dict[str, int] | None = None,
    continuation: dict[str, int] | None = None,
    parser_mode: int = 0,
    initial_candidate_flags: int = 0,
    allocation_ok: bool = True,
) -> dict[str, object]:
    updated_records = [dict(record) for record in records]
    updated_counters = font_counter_defaults()
    if counters:
        updated_counters.update(counters)
    updated_cursors = font_cursor_defaults()
    if cursors:
        updated_cursors.update(cursors)
    updated_continuation = dict(continuation) if continuation else None

    budget_action = "accept"
    scan = font_resource_record_scan_via_172c0(updated_records, current_id)
    if parser_mode == 2:
        budget_action = "skip-parser-mode"
    elif scan["status"] == 2:
        budget_action = "skip-no-record-slot"
    elif int(updated_counters["0x78278e"]) >= 0xC0:
        budget_action = "skip-candidate-limit"
    elif not allocation_ok:
        budget_action = "skip-allocation-failed"

    if budget_action != "accept":
        return {
            "status": int(scan["status"]) if parser_mode != 2 else None,
            "scan": scan,
            "records": updated_records,
            "counters": updated_counters,
            "cursors": updated_cursors,
            "continuation": updated_continuation,
            "budget_action": budget_action,
            "candidate_flags": None,
            "replacement": None,
            "record_index": None,
        }

    record_index = scan["index"]
    assert isinstance(record_index, int)
    replacement = None
    if scan["status"] == 0:
        old_payload = int(updated_records[record_index].get("payload", 0)) & 0x00FFFFFF
        continuation_cleared = bool(
            updated_continuation
            and int(updated_continuation.get("flag", 0)) == 1
            and (int(updated_continuation.get("payload", 0)) & 0x00FFFFFF) == old_payload
        )
        if continuation_cleared and updated_continuation is not None:
            updated_continuation = clear_download_continuation_state(updated_continuation)
        replacement = {
            "record_index": record_index,
            "released_payload": old_payload,
            "release_called": True,
            "continuation_cleared": continuation_cleared,
        }

    candidate_flags = int(initial_candidate_flags) & 0xFFFFFFFF
    candidate_flags &= ~(1 << 3)
    candidate_flags &= 0xCFFFFFFF
    candidate_flags |= 1 << 6
    candidate_flags &= ~(1 << 7)
    if (byte0c & 0xFF) == 2:
        candidate_flags |= 1 << 2
    else:
        candidate_flags &= ~(1 << 2)

    if (byte20 & 0xFF) == 1:
        for key in ("0x7827ac", "0x7827b0", "0x7827b4"):
            updated_cursors[key] = int(updated_cursors[key]) + 4
        updated_counters["0x782790"] = int(updated_counters["0x782790"]) + 1
        updated_counters["0x782796"] = int(updated_counters["0x782796"]) + 1
        counter_branch = "byte20-one"
    else:
        updated_counters["0x78279e"] = int(updated_counters["0x78279e"]) + 1
        updated_counters["0x782798"] = int(updated_counters["0x782798"]) + 1
        counter_branch = "byte20-other"
    updated_counters["0x78278e"] = int(updated_counters["0x78278e"]) + 1
    updated_counters["0x78278a"] = int(updated_counters["0x78278a"]) + 1
    updated_counters["0x782782"] = int(updated_counters["0x782782"]) + 1

    record = updated_records[record_index]
    record["id"] = current_id & 0xFFFF
    record["flags"] = int(record.get("flags", 0)) & ~0xE0
    record["payload"] = new_payload & 0x00FFFFFF

    return {
        "status": int(scan["status"]),
        "scan": scan,
        "records": updated_records,
        "counters": updated_counters,
        "cursors": updated_cursors,
        "continuation": updated_continuation,
        "budget_action": budget_action,
        "candidate_flags": candidate_flags,
        "replacement": replacement,
        "record_index": record_index,
        "counter_branch": counter_branch,
    }


def font_payload_record_lookup_via_170be(records: list[dict[str, int]], payload: int) -> dict[str, object]:
    masked_payload = int(payload) & 0x00FFFFFF
    for index, record in enumerate(records):
        if (int(record.get("payload", 0)) & 0x00FFFFFF) == masked_payload:
            record_id = int(record.get("id", 0)) & 0xFFFF
            if record_id & 0x8000:
                record_id -= 0x10000
            return {
                "status": record_id,
                "index": index,
                "address": FONT_RECORD_BASE + index * FONT_RECORD_SIZE,
                "record": dict(record),
                "masked_payload": masked_payload,
            }
    return {
        "status": -1,
        "index": None,
        "address": None,
        "record": None,
        "masked_payload": masked_payload,
    }


def assign_font_id_via_15a56(parsed_word: int) -> int:
    value = int(parsed_word)
    if value < -0x8000 or value > 0x7FFF:
        value = _signed_word(value & 0xFFFF)
    if value < 0:
        value = -value
    if value == 0x8000:
        value = 0x7FFF
    return value & 0xFFFF


def mark_current_font_record_via_17108(records: list[dict[str, int]], current_id: int, counters: dict[str, int] | None = None) -> dict[str, object]:
    updated_records = [dict(record) for record in records]
    updated_counters = {
        "0x782782": 0,
        "0x782786": 0,
    }
    if counters:
        updated_counters.update(counters)
    scan = font_resource_record_scan_via_172c0(updated_records, current_id)
    changed = False
    if scan["status"] == 0:
        index = scan["index"]
        assert isinstance(index, int)
        flags = int(updated_records[index].get("flags", 0))
        if not (flags & 0x40):
            updated_records[index]["flags"] = flags | 0x40
            updated_counters["0x782782"] = int(updated_counters["0x782782"]) - 1
            updated_counters["0x782786"] = int(updated_counters["0x782786"]) + 1
            changed = True
    return {
        "scan": scan,
        "records": updated_records,
        "counters": updated_counters,
        "changed": changed,
    }


def unmark_current_font_record_via_17150(records: list[dict[str, int]], current_id: int, counters: dict[str, int] | None = None) -> dict[str, object]:
    updated_records = [dict(record) for record in records]
    updated_counters = {
        "0x782782": 0,
        "0x782786": 0,
    }
    if counters:
        updated_counters.update(counters)
    scan = font_resource_record_scan_via_172c0(updated_records, current_id)
    changed = False
    if scan["status"] == 0:
        index = scan["index"]
        assert isinstance(index, int)
        flags = int(updated_records[index].get("flags", 0))
        if flags & 0x40:
            updated_records[index]["flags"] = flags & ~0x40
            updated_counters["0x782782"] = int(updated_counters["0x782782"]) + 1
            updated_counters["0x782786"] = int(updated_counters["0x782786"]) - 1
            changed = True
    return {
        "scan": scan,
        "records": updated_records,
        "counters": updated_counters,
        "changed": changed,
    }


def font_control_dispatch_table_via_16df6(data: bytes) -> dict[int | str, int]:
    table: dict[int | str, int] = {}
    pos = 0x16DB6
    while True:
        target = u32(data, pos)
        value = u32(data, pos + 4)
        pos += 8
        if target == 0:
            table["default"] = value
            break
        table[value] = target
    return table


def font_control_dispatch_via_16df6(
    data: bytes,
    records: list[dict[str, int]],
    *,
    current_id: int,
    value: int,
    parser_mode: int,
    counters: dict[str, int] | None = None,
) -> dict[str, object]:
    table = font_control_dispatch_table_via_16df6(data)
    target = table.get(value, table["default"])
    suppressed = parser_mode == 2 and value in (0, 1, 2, 3, 6)
    if target == 0x16E7E:
        result = unmark_current_font_record_via_17150(records, current_id, counters)
        action = "unmark-current"
    elif target == 0x16E86:
        result = mark_current_font_record_via_17108(records, current_id, counters)
        action = "mark-current"
    elif suppressed:
        result = {
            "records": [dict(record) for record in records],
            "counters": dict(counters) if counters else {"0x782782": 0, "0x782786": 0},
            "changed": False,
        }
        action = "suppressed"
    elif target == table["default"]:
        result = {
            "records": [dict(record) for record in records],
            "counters": dict(counters) if counters else {"0x782782": 0, "0x782786": 0},
            "changed": False,
        }
        action = "noop"
    else:
        result = {
            "records": [dict(record) for record in records],
            "counters": dict(counters) if counters else {"0x782782": 0, "0x782786": 0},
            "changed": False,
        }
        action = "dispatch-only"
    return {
        "value": value,
        "target": target,
        "action": action,
        "suppressed": suppressed,
        "result": result,
    }


def font_resource_validate_via_16fae(validator_statuses: list[int], symbol_stream: bytes, budget: int) -> dict[str, object]:
    table_base = 0x16EAE
    copied = bytearray()
    visited: list[dict[str, int]] = []
    for index in range(32):
        table_address = table_base + index * 8
        d5 = index + 1
        status = int(validator_statuses[index]) if index < len(validator_statuses) else 0
        visited.append({
            "index": index,
            "d5": d5,
            "table_address": table_address,
            "status": status,
        })
        if status != 1:
            return {
                "status": 0,
                "failed_index": index,
                "failed_d5": d5,
                "visited": visited,
                "budget": budget,
                "symbol_count": 0,
                "symbol_bytes": bytes(copied),
            }

    remaining_budget = int(budget)
    stream_index = 0
    while remaining_budget > 0 and len(copied) < 16 and stream_index < len(symbol_stream):
        copied.append(symbol_stream[stream_index])
        stream_index += 1
        remaining_budget -= 1

    return {
        "status": 1,
        "failed_index": None,
        "failed_d5": None,
        "visited": visited,
        "budget": remaining_budget,
        "symbol_count": len(copied),
        "symbol_bytes": bytes(copied),
    }


def _signed_word(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def _signed_byte(value: int) -> int:
    value &= 0xFF
    return value - 0x100 if value & 0x80 else value


def font_resource_validate_table_stream_via_16fae(staging: bytes | bytearray, stream: bytes, budget: int) -> dict[str, object]:
    updated = bytearray(staging)
    if len(updated) < 0x32:
        raise AssertionError("font resource validation staging buffer must include copied byte +0x31")
    cursor = 0
    remaining_budget = int(budget)
    payload_units = 0x100
    visited: list[dict[str, int]] = []

    def read_byte() -> int:
        nonlocal cursor, remaining_budget
        if remaining_budget <= 0:
            return 0
        value = stream[cursor] if cursor < len(stream) else 0
        cursor += 1
        remaining_budget -= 1
        return value

    def read_value(reader: int) -> int:
        if reader == 0x1599C:
            return read_byte()
        if reader == 0x159B6:
            return _signed_byte(read_byte())
        high = read_byte()
        low = read_byte()
        word = (high << 8) | low
        if reader == 0x159D4:
            return word
        if reader == 0x159F6:
            return _signed_word(word)
        raise AssertionError(f"unmodeled 0x16fae reader 0x{reader:06x}")

    def apply_predicate(predicate: int, value: int) -> int:
        nonlocal payload_units
        if predicate == 0x17358:
            return 1
        if predicate == 0x17362:
            setup = font_resource_setup_type_via_17362(updated, value)
            updated[:] = setup["staging"]
            payload_units = int(setup["payload_units"])
            return int(setup["status"])
        if predicate == 0x173D0:
            if value > 0x1067:
                return 0
            updated[0x16:0x18] = (value & 0xFFFF).to_bytes(2, "big")
            return 1
        if predicate == 0x173FE:
            if value <= 0 or value > 0x1068:
                return 0
            updated[0x12:0x14] = (value & 0xFFFF).to_bytes(2, "big")
            return 1
        if predicate == 0x17430:
            if value <= 0 or value > 0x1068:
                return 0
            updated[0x14:0x16] = (value & 0xFFFF).to_bytes(2, "big")
            first_code = u16(updated, 0x16)
            if first_code > value - 1:
                return 0
            updated[0x18:0x1A] = ((value - first_code - 1) & 0xFFFF).to_bytes(2, "big")
            return 1
        if predicate == 0x1749E:
            if value > 1:
                return 0
            updated[0x20] = value & 0xFF
            return 1
        if predicate == 0x174CC:
            updated[0x21] = 0 if value == 0 else 1
            return 1
        if predicate == 0x17502:
            updated[0x22:0x24] = (value & 0xFFFF).to_bytes(2, "big")
            return 1
        if predicate == 0x1751A:
            updated[0x24:0x26] = (min(value, 0x41A0) & 0xFFFF).to_bytes(2, "big")
            return 1
        if predicate == 0x1754A:
            updated[0x28:0x2A] = (min(value, 0x2AAA) & 0xFFFF).to_bytes(2, "big")
            return 1
        if predicate == 0x1757A:
            rounded = (value + 2) >> 2
            height = u16(updated, 0x14)
            if rounded > height:
                rounded = height
            updated[0x2C:0x2E] = ((rounded << 2) & 0xFFFF).to_bytes(2, "big")
            return 1
        if predicate == 0x175C2:
            updated[0x2F] = value & 0xFF
            return 1
        if predicate == 0x175DA:
            clamped = max(-7, min(7, value))
            updated[0x30] = clamped & 0xFF
            return 1
        if predicate == 0x17612:
            updated[0x31] = value & 0xFF
            return 1
        if predicate == 0x1762A:
            updated[0x1A:0x1C] = (value & 0xFFFF).to_bytes(2, "big")
            return 1
        if predicate == 0x17642:
            updated[0x0E:0x10] = b"\x00\x00"
            updated[0x10:0x12] = (0x007F if updated[0x0C] == 0 else 0x00FF).to_bytes(2, "big")
            return 1
        if predicate == 0x17690:
            updated[0x26] = 0 if u16(updated, 0x24) >= 0x41A0 else value & 0xFF
            return 1
        if predicate == 0x176C2:
            clamped = value
            if u16(updated, 0x28) >= 0x2AAA and clamped > 0x80:
                clamped = 0x80
            updated[0x2A] = clamped & 0xFF
            return 1
        raise AssertionError(f"unmodeled 0x16fae predicate 0x{predicate:06x}")

    for index, (reader, predicate) in enumerate(FONT_RESOURCE_VALIDATE_TABLE):
        value = read_value(reader)
        status = apply_predicate(predicate, value)
        visited.append({
            "index": index,
            "reader": reader,
            "predicate": predicate,
            "value": value,
            "status": status,
            "budget": remaining_budget,
        })
        if status != 1:
            return {
                "status": 0,
                "failed_index": index,
                "visited": visited,
                "staging": bytes(updated),
                "payload_units": payload_units,
                "budget": remaining_budget,
                "bytes_consumed": cursor,
                "symbol_count": 0,
                "symbol_bytes": b"",
            }

    symbol_bytes = bytearray()
    while remaining_budget > 0 and len(symbol_bytes) < 16:
        symbol_bytes.append(read_byte())

    return {
        "status": 1,
        "failed_index": None,
        "visited": visited,
        "staging": bytes(updated),
        "payload_units": payload_units,
        "budget": remaining_budget,
        "bytes_consumed": cursor,
        "symbol_count": len(symbol_bytes),
        "symbol_bytes": bytes(symbol_bytes),
    }


def font_resource_setup_type_via_17362(staging: bytes | bytearray, setup_type: int) -> dict[str, object]:
    updated = bytearray(staging)
    if len(updated) < 0x0D:
        raise AssertionError("font resource setup staging buffer must include byte +0x0c")
    if setup_type == 2:
        updated[0x0C] = 2
        payload_units = 0x100
        status = 1
    elif setup_type == 1:
        updated[0x0C] = 1
        payload_units = 0x100
        status = 1
    elif setup_type == 0:
        updated[0x0C] = 0
        payload_units = 0x80
        status = 1
    else:
        payload_units = 0x100
        status = 0
    return {
        "status": status,
        "staging": bytes(updated),
        "payload_units": payload_units,
    }


def font_resource_allocation_size_via_17026(payload_units: int) -> int:
    return (((int(payload_units) << 2) + 0x9B) >> 6)


def font_resource_payload_initializer_via_1719c(staging: bytes | bytearray, payload_units: int, symbol_bytes: bytes = b"") -> dict[str, object]:
    if len(staging) < 0x32:
        raise AssertionError("font resource initializer staging buffer must include copied byte +0x31")
    symbol_count = len(symbol_bytes)
    extra_offset = 0
    if symbol_count:
        extra_offset = 0x4A + (int(payload_units) << 2)
    total_size = max(0x3C, extra_offset + 2 + symbol_count)
    payload = bytearray(total_size)

    payload[0:4] = staging[0:4]
    payload[4:8] = staging[4:8]
    payload[8:10] = (0x004A).to_bytes(2, "big")
    payload[0x0C] = staging[0x0C]
    for offset in (0x0E, 0x10, 0x12, 0x14, 0x16, 0x18, 0x1A):
        payload[offset:offset + 2] = staging[offset:offset + 2]
    payload[0x20] = staging[0x20]
    payload[0x21] = staging[0x21]
    payload[0x22:0x24] = staging[0x22:0x24]
    payload[0x24:0x26] = staging[0x24:0x26]
    payload[0x26] = staging[0x26]
    payload[0x28:0x2A] = staging[0x28:0x2A]
    payload[0x2A] = staging[0x2A]
    payload[0x2C:0x2E] = staging[0x2C:0x2E]
    payload[0x2F] = staging[0x2F]
    payload[0x30] = staging[0x30]
    payload[0x31] = staging[0x31]

    if symbol_count:
        payload[0x38:0x3C] = extra_offset.to_bytes(4, "big")
        payload[extra_offset:extra_offset + 2] = symbol_count.to_bytes(2, "big")
        payload[extra_offset + 2:extra_offset + 2 + symbol_count] = symbol_bytes

    return {
        "payload": bytes(payload),
        "base_header_size": 0x4A,
        "extra_offset": extra_offset,
        "symbol_count": symbol_count,
        "symbol_bytes": symbol_bytes,
    }


def font_resource_find_allocate_via_17026(staging: bytes | bytearray, payload_units: int, valid: bool, symbol_bytes: bytes = b"") -> dict[str, object]:
    if not valid:
        return {
            "status": 0,
            "allocation_size": 0,
            "staging": bytes(staging),
            "payload": None,
        }
    updated = bytearray(staging)
    allocation_size = font_resource_allocation_size_via_17026(payload_units)
    updated[0:4] = (0x15).to_bytes(4, "big")
    updated[4:8] = allocation_size.to_bytes(4, "big")
    initialized = font_resource_payload_initializer_via_1719c(updated, payload_units, symbol_bytes)
    return {
        "status": 1,
        "allocation_size": allocation_size,
        "staging": bytes(updated),
        "payload": initialized,
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


def write_bitmap_bits(dest: bytearray, dest_stride: int, source: bytes, rows: int, span: int, x: int, y: int) -> None:
    for row_index in range(rows):
        row_base = row_index * span
        dest_row = (y + row_index) * dest_stride
        for bit_index in range(span * 8):
            src_byte = source[row_base + bit_index // 8]
            src_mask = 0x80 >> (bit_index & 7)
            pixel = x + bit_index
            dest_offset = dest_row + pixel // 8
            if dest_offset >= len(dest):
                raise AssertionError("shifted bitmap write exceeds destination fixture buffer")
            dest_mask = 0x80 >> (pixel & 7)
            if src_byte & src_mask:
                dest[dest_offset] |= dest_mask
            else:
                dest[dest_offset] &= ~dest_mask


def glyph_source_bytes_for_rows(resources: bytes | bytearray, glyph: dict[str, int | bytes], row_skip: int = 0, rows: int | None = None) -> bytes:
    total_rows = int(glyph["rows"])
    span = int(glyph["render_span"])
    if rows is None:
        rows = total_rows - row_skip
    if row_skip < 0 or rows < 0 or row_skip + rows > total_rows:
        raise AssertionError("glyph source row range is outside the glyph")
    bitmap = int(glyph["bitmap"])
    if span & 1 and span > 1 and glyph.get("source_kind") == "inline":
        prefix_span = span - 1
        a2_base = bitmap
        a3_base = bitmap + prefix_span * total_rows
        out = bytearray()
        for row in range(row_skip, row_skip + rows):
            out.extend(resources[a2_base + row * prefix_span : a2_base + (row + 1) * prefix_span])
            out.extend(resources[a3_base + row : a3_base + row + 1])
        return bytes(out)
    start = bitmap + row_skip * span
    return bytes(resources[start : start + rows * span])


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
        glyph = resolve_compact_glyph(resources, context, glyph_index)
        mode = int(glyph["mode"])
        if mode != 1:
            raise AssertionError(f"compact mode-0 fixture does not implement glyph mode {mode}")
        rows = int(glyph["rows"])
        width = int(glyph["width"])
        render_span = int(glyph["render_span"])
        row_index = (coord >> 12) & 0x0F
        subbyte = (coord >> 8) & 0x0F
        byte_pair_offset = (coord & 0x00FF) * 2
        x = byte_pair_offset * 8 + subbyte
        if row_index + rows > band_rows:
            raise AssertionError("compact mode-0 fixture does not implement band-crossing continuation yet")
        source = resources[int(glyph["bitmap"]) : int(glyph["bitmap"]) + rows * render_span]
        result = simulate_row_copy(data, u32(data, 0x1F08E + render_span * 4), rows, stride=dest_stride)
        for write in result.writes:
            if write.source != "A2":
                raise AssertionError(f"unexpected {write.source} write for compact mode-0 glyph")
            if write.src + write.size > len(source):
                raise AssertionError(f"source read past compact mode-0 glyph bitmap at +0x{write.src:x}")
        write_bitmap_bits(dest, dest_stride, source, rows, render_span, x, row_index)
        decoded = coord_decode(coord, band_base=0, payload_offset=0)
        rendered.append({
            "glyph": glyph_index,
            "coord": coord,
            "dest_base": decoded["a1"],
            "x": x,
            "y": row_index,
            "a001": decoded["a001"],
            "span": render_span,
            "rows": rows,
            "width": width,
            "helper": u32(data, 0x1F08E + render_span * 4),
        })
        max_width = max(max_width, x + width)
        max_bottom = max(max_bottom, row_index + rows)
    return {
        "count": count,
        "rendered": rendered,
        "rows": bitmap_bytes_to_rows(dest, max_bottom, max_width, dest_stride),
    }


def render_compact_wide_payload_via_1f0d2(data: bytes, resources: bytes | bytearray, context: int, payload: bytes, dest_stride: int = 0x20, band_rows: int = 64) -> dict[str, object]:
    count = u16(payload, 0)
    pos = 2
    rendered: list[dict[str, int | str]] = []
    dest = bytearray(band_rows * dest_stride)
    max_width = 0
    max_bottom = 0
    for _ in range(count):
        glyph_index = payload[pos]
        coord = u16(payload, pos + 1)
        pos += 3
        glyph = resolve_compact_glyph(resources, context, glyph_index)
        mode = int(glyph["mode"])
        if mode != 1:
            raise AssertionError(f"compact wide fixture does not implement glyph mode {mode}")
        rows = int(glyph["rows"])
        width = int(glyph["width"])
        render_span = int(glyph["render_span"])
        if render_span <= 0x10:
            raise AssertionError("compact wide fixture expects a span wider than one 16-byte chunk")
        row_index = (coord >> 12) & 0x0F
        subbyte = (coord >> 8) & 0x0F
        byte_pair_offset = (coord & 0x00FF) * 2
        x = byte_pair_offset * 8 + subbyte
        if row_index + rows > band_rows:
            raise AssertionError("compact wide fixture does not implement band-crossing continuation yet")

        full_chunks = render_span >> 4
        remainder = render_span & 0x0F
        full_row_skip = render_span - (0x11 if remainder & 1 else 0x10)
        remainder_row_skip = render_span - remainder if remainder else 0
        trailing_plane = bool(render_span & 1 and render_span > 1 and glyph.get("source_kind") == "inline")
        a2_source_len = (render_span - 1) * rows if trailing_plane else render_span * rows
        a3_source_len = rows if trailing_plane else 0

        for chunk in range(full_chunks):
            result = simulate_row_copy(data, 0x2F27C, rows, stride=dest_stride, phase=chunk * 0x10, source_row_delta=full_row_skip)
            for write in result.writes:
                if write.source != "A2":
                    raise AssertionError(f"unexpected {write.source} write for compact wide full chunk")
                if write.src + write.size > a2_source_len:
                    raise AssertionError(f"source read past compact wide A2 bitmap at +0x{write.src:x}")
        remainder_helper = 0
        if remainder:
            remainder_helper = u32(data, 0x1F1AC + remainder * 4)
            result = simulate_row_copy(data, remainder_helper, rows, stride=dest_stride, phase=full_chunks * 0x10, source_row_delta=remainder_row_skip)
            for write in result.writes:
                source_len = a3_source_len if write.source == "A3" else a2_source_len
                if write.src + write.size > source_len:
                    raise AssertionError(f"source read past compact wide {write.source} bitmap at +0x{write.src:x}")

        source = glyph_source_bytes_for_rows(resources, glyph)
        write_bitmap_bits(dest, dest_stride, source, rows, render_span, x, row_index)
        decoded = coord_decode(coord, band_base=0, payload_offset=0)
        rendered.append({
            "glyph": glyph_index,
            "coord": coord,
            "rows": rows,
            "span": render_span,
            "width": width,
            "full_chunks": full_chunks,
            "remainder": remainder,
            "full_row_skip": full_row_skip,
            "remainder_row_skip": remainder_row_skip,
            "full_chunk_helper": 0x2F27C,
            "remainder_helper": remainder_helper,
            "dest_base": decoded["a1"],
            "x": x,
            "y": row_index,
            "a001": decoded["a001"],
            "source_layout": "inline-trailing-plane" if trailing_plane else "linear",
        })
        max_width = max(max_width, x + width)
        max_bottom = max(max_bottom, row_index + rows)
    return {
        "count": count,
        "rendered": rendered,
        "rows": bitmap_bytes_to_rows(dest, max_bottom, max_width, dest_stride),
    }


def render_compact_segmented_wide_payload_via_1f264(data: bytes, resources: bytes | bytearray, context: int, payload: bytes, dest_stride: int = 0x20, band_rows: int = 16) -> dict[str, object]:
    count = u16(payload, 0)
    pos = 2
    rendered: list[dict[str, int | str]] = []
    dest = bytearray(band_rows * dest_stride)
    max_width = 0
    max_bottom = 0
    for _ in range(count):
        glyph_index = payload[pos]
        segment = payload[pos + 1]
        coord = u16(payload, pos + 2)
        pos += 4
        glyph = resolve_compact_glyph(resources, context, glyph_index)
        mode = int(glyph["mode"])
        if mode != 1:
            raise AssertionError(f"compact segmented-wide fixture does not implement glyph mode {mode}")
        render_span = int(glyph["render_span"])
        if render_span <= 0x10:
            raise AssertionError("compact segmented-wide fixture expects a span wider than one 16-byte chunk")
        rows_total = int(glyph["rows"])
        row_skip = segment << 7
        if row_skip >= rows_total:
            raise AssertionError("compact segmented-wide fixture segment starts beyond glyph rows")
        rows_here = min(rows_total - row_skip, 0x80)
        row_index = (coord >> 12) & 0x0F
        subbyte = (coord >> 8) & 0x0F
        byte_pair_offset = (coord & 0x00FF) * 2
        x = byte_pair_offset * 8 + subbyte
        if row_index + rows_here > band_rows:
            raise AssertionError("compact segmented-wide fixture crosses the synthetic band")

        full_chunks = render_span >> 4
        remainder = render_span & 0x0F
        full_row_skip = render_span - (0x11 if remainder & 1 else 0x10)
        remainder_row_skip = render_span - remainder if remainder else 0
        trailing_plane = bool(render_span & 1 and render_span > 1 and glyph.get("source_kind") == "inline")
        a2_row_span = render_span - 1 if trailing_plane else render_span
        a2_source_offset = row_skip * a2_row_span
        a3_source_offset = row_skip if trailing_plane else 0
        a2_source_len = a2_row_span * rows_here
        a3_source_len = rows_here if trailing_plane else 0

        for chunk in range(full_chunks):
            result = simulate_row_copy(data, 0x2F27C, rows_here, stride=dest_stride, phase=chunk * 0x10, source_row_delta=full_row_skip)
            for write in result.writes:
                if write.source != "A2":
                    raise AssertionError(f"unexpected {write.source} write for compact segmented-wide full chunk")
                if write.src + write.size > a2_source_len:
                    raise AssertionError(f"source read past compact segmented-wide A2 bitmap at +0x{write.src:x}")
        remainder_helper = 0
        if remainder:
            remainder_helper = u32(data, 0x1F1AC + remainder * 4)
            result = simulate_row_copy(data, remainder_helper, rows_here, stride=dest_stride, phase=full_chunks * 0x10, source_row_delta=remainder_row_skip)
            for write in result.writes:
                source_len = a3_source_len if write.source == "A3" else a2_source_len
                if write.src + write.size > source_len:
                    raise AssertionError(f"source read past compact segmented-wide {write.source} bitmap at +0x{write.src:x}")

        source = glyph_source_bytes_for_rows(resources, glyph, row_skip=row_skip, rows=rows_here)
        write_bitmap_bits(dest, dest_stride, source, rows_here, render_span, x, row_index)
        decoded = coord_decode(coord, band_base=0, payload_offset=0)
        rendered.append({
            "glyph": glyph_index,
            "segment": segment,
            "coord": coord,
            "row_skip": row_skip,
            "a2_source_offset": a2_source_offset,
            "a3_source_offset": a3_source_offset,
            "rows": rows_here,
            "span": render_span,
            "width": int(glyph["width"]),
            "full_chunks": full_chunks,
            "remainder": remainder,
            "full_row_skip": full_row_skip,
            "remainder_row_skip": remainder_row_skip,
            "full_chunk_helper": 0x2F27C,
            "remainder_helper": remainder_helper,
            "dest_base": decoded["a1"],
            "x": x,
            "y": row_index,
            "a001": decoded["a001"],
            "source_layout": "inline-trailing-plane" if trailing_plane else "linear",
        })
        max_width = max(max_width, x + int(glyph["width"]))
        max_bottom = max(max_bottom, row_index + rows_here)
    return {
        "count": count,
        "rendered": rendered,
        "rows": bitmap_bytes_to_rows(dest, max_bottom, max_width, dest_stride),
    }


def render_compact_segmented_payload_via_1f1f0(data: bytes, resources: bytes | bytearray, context: int, payload: bytes, dest_stride: int = 0x20, band_rows: int = 16) -> dict[str, object]:
    count = u16(payload, 0)
    pos = 2
    rendered: list[dict[str, int]] = []
    dest = bytearray(band_rows * dest_stride)
    max_width = 0
    max_bottom = 0
    for _ in range(count):
        glyph_index = payload[pos]
        segment = payload[pos + 1]
        coord = u16(payload, pos + 2)
        pos += 4
        glyph = resolve_compact_glyph(resources, context, glyph_index)
        render_span = int(glyph["render_span"])
        if render_span & 1:
            raise AssertionError("segmented compact fixture only models even-span A2 source rows")
        row_skip = segment << 7
        rows_total = int(glyph["rows"])
        if row_skip >= rows_total:
            raise AssertionError("segmented compact fixture segment starts beyond glyph rows")
        rows_here = min(rows_total - row_skip, 0x80)
        row_index = (coord >> 12) & 0x0F
        subbyte = (coord >> 8) & 0x0F
        byte_pair_offset = (coord & 0x00FF) * 2
        x = byte_pair_offset * 8 + subbyte
        if row_index + rows_here > band_rows:
            raise AssertionError("segmented compact fixture crosses the synthetic band")
        bitmap = int(glyph["bitmap"])
        source_offset = row_skip * render_span
        source = resources[bitmap + source_offset : bitmap + source_offset + rows_here * render_span]
        result = simulate_row_copy(data, u32(data, 0x1F08E + render_span * 4), rows_here, stride=dest_stride)
        for write in result.writes:
            if write.source != "A2":
                raise AssertionError(f"unexpected {write.source} write for compact segmented glyph")
            if write.src + write.size > len(source):
                raise AssertionError(f"source read past compact segmented glyph bitmap at +0x{write.src:x}")
        write_bitmap_bits(dest, dest_stride, source, rows_here, render_span, x, row_index)
        decoded = coord_decode(coord, band_base=0, payload_offset=0)
        rendered.append({
            "glyph": glyph_index,
            "segment": segment,
            "coord": coord,
            "row_skip": row_skip,
            "source_offset": source_offset,
            "rows": rows_here,
            "span": render_span,
            "width": int(glyph["width"]),
            "dest_base": decoded["a1"],
            "x": x,
            "y": row_index,
            "a001": decoded["a001"],
            "helper": u32(data, 0x1F08E + render_span * 4),
        })
        max_width = max(max_width, x + int(glyph["width"]))
        max_bottom = max(max_bottom, row_index + rows_here)
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


def cursor_stack_state(**overrides: object) -> dict[str, object]:
    state: dict[str, object] = {
        "cursor_x": pack12(10),
        "cursor_y": pack12(20),
        "vertical_offset_source": 60,
        "active_height": 2025,
        "printable_extent": 3090,
        "right_limit": pack12(80),
        "right_limit_latch": 0,
        "pending_text": 1,
        "pending_span_flush_enable": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "stack": [],
        "max_depth": 20,
        "events": [],
    }
    state.update(overrides)
    return state


def apply_cursor_push_pop_via_f75e(state: dict[str, object], parameter: int) -> dict[str, object]:
    updated = dict(state)
    stack = list(state.get("stack", []))
    events = list(state.get("events", []))
    selector = abs(int(parameter))
    if selector == 0:
        if len(stack) >= int(updated.get("max_depth", 20)):
            events.append({"kind": "cursor-push-ignored", "reason": "stack-full"})
        else:
            entry = {
                "x": int(updated["cursor_x"]),
                "stored_y": add_packed12(int(updated["cursor_y"]), pack12(int(updated["vertical_offset_source"]))),
            }
            stack.append(entry)
            events.append({"kind": "cursor-push", "depth": len(stack), "entry": entry})
    elif selector == 1:
        if not stack:
            events.append({"kind": "cursor-pop-ignored", "reason": "stack-empty"})
        else:
            entry = dict(stack.pop())
            max_x = sub_packed12(pack12(int(updated["active_height"])), subunits_to_packed12(1))
            restored_x = min(int(entry["x"]), max_x)
            updated["cursor_x"] = restored_x
            updated["right_limit_latch"] = 1 if restored_x == int(updated["right_limit"]) else 0
            updated["pending_text"] = 0
            max_y = sub_packed12(pack12(int(updated["printable_extent"])), subunits_to_packed12(1))
            restored_y = sub_packed12(int(entry["stored_y"]), pack12(int(updated["vertical_offset_source"])))
            updated["cursor_y"] = min(restored_y, max_y)
            if int(updated.get("pending_span_flush_enable", 0)):
                updated["span_flushes"] = int(updated.get("span_flushes", 0)) + 1
                updated["post_flushes"] = int(updated.get("post_flushes", 0)) + 1
            events.append({
                "kind": "cursor-pop",
                "depth": len(stack),
                "entry": entry,
                "max_x": max_x,
                "max_y": max_y,
            })
    else:
        events.append({"kind": "cursor-stack-ignored", "selector": selector})
    updated["stack"] = stack
    updated["events"] = events
    updated["stack_depth"] = len(stack)
    return updated


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


def text_source_metrics_via_12f2e(resources: bytes, source: dict[str, object]) -> dict[str, int]:
    if int(source["flag"]):
        glyph_entry = int(source["glyph_entry"])
        return {
            "width": u16(resources, glyph_entry + 8),
            "rows": u16(resources, glyph_entry + 6),
            "wide_threshold": 0x80,
        }

    inline_record = source.get("inline_record")
    if not isinstance(inline_record, bytes) or len(inline_record) < 2:
        raise AssertionError("inline/downloaded text source records need inline_record bytes")
    return {
        "width": inline_record[0],
        "rows": inline_record[1],
        "wide_threshold": 0x10,
    }


def queue_text_source_via_12f2e(resources: bytes, source: dict[str, object]) -> dict[str, object]:
    selector = source["context_slot"] & 0x0F
    metrics = text_source_metrics_via_12f2e(resources, source)
    width = metrics["width"]
    rows = metrics["rows"]
    if width > metrics["wide_threshold"]:
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


def bucket_find_or_alloc_via_1387c(
    bucket_array: dict[int, list[bytearray]],
    bucket_index: int,
    selector: int,
    capacity: int,
    object_size: int,
) -> dict[str, object]:
    chain = bucket_array.setdefault(bucket_index, [])
    for index, obj in enumerate(chain):
        if u16(obj, 4) == (selector & 0xFFFF):
            count = u16(obj, 6)
            if count < capacity:
                return {
                    "object": obj,
                    "allocated": False,
                    "chain_index": index,
                    "count_before": count,
                    "bucket_index": bucket_index,
                    "selector": selector & 0xFFFF,
                    "capacity": capacity,
                    "object_size": object_size,
                }
        elif index == len(chain) - 1:
            break

    obj = bytearray(object_size)
    obj[4:6] = (selector & 0xFFFF).to_bytes(2, "big")
    chain.insert(0, obj)
    return {
        "object": obj,
        "allocated": True,
        "chain_index": 0,
        "count_before": 0,
        "bucket_index": bucket_index,
        "selector": selector & 0xFFFF,
        "capacity": capacity,
        "object_size": object_size,
    }


def queue_text_source_to_page_record_via_12f2e(resources: bytes, page_record: dict[str, object], source: dict[str, object]) -> dict[str, object]:
    bucket_array = page_record.setdefault("bucket_array", {})
    if not isinstance(bucket_array, dict):
        raise AssertionError("page record bucket_array must be a dict")

    selector = source["context_slot"] & 0x0F
    metrics = text_source_metrics_via_12f2e(resources, source)
    width = metrics["width"]
    rows = metrics["rows"]
    coord = compact_text_coord(source["x"], source["y"])
    bucket_index = source["y"] >> 4
    glyph = source["mapped"] & 0xFF

    if width > metrics["wide_threshold"]:
        selector |= 0x1000
    events: list[dict[str, object]] = []
    if rows > 0x80:
        selector |= 0x2000
        segment = (rows - 1) >> 7
        while segment >= 0:
            segment_bucket_index = bucket_index + segment * 8
            alloc = bucket_find_or_alloc_via_1387c(bucket_array, segment_bucket_index, selector, 0x08, 0x28)
            obj = alloc["object"]
            if not isinstance(obj, bytearray):
                raise AssertionError("bucket allocator did not return a mutable object")
            count = int(alloc["count_before"])
            entry = 8 + count * 4
            obj[6:8] = (count + 1).to_bytes(2, "big")
            obj[entry] = glyph
            obj[entry + 1] = segment & 0xFF
            obj[entry + 2 : entry + 4] = coord.to_bytes(2, "big")
            events.append({
                key: alloc[key]
                for key in ("allocated", "chain_index", "count_before", "bucket_index", "selector", "capacity", "object_size")
            } | {
                "count_after": count + 1,
                "segment": segment,
                "object": bytes(obj),
            })
            segment -= 1
        return {
            "path": "segmented-page-record",
            "events": events,
            "selector": selector,
            "coord": coord,
            "glyph": glyph,
            "rows": rows,
            "width": width,
        }

    alloc = bucket_find_or_alloc_via_1387c(bucket_array, bucket_index, selector, 0x0A, 0x26)
    obj = alloc["object"]
    if not isinstance(obj, bytearray):
        raise AssertionError("bucket allocator did not return a mutable object")
    count = int(alloc["count_before"])
    entry = 8 + count * 3
    obj[6:8] = (count + 1).to_bytes(2, "big")
    obj[entry] = glyph
    obj[entry + 1 : entry + 3] = coord.to_bytes(2, "big")
    return {
        "path": "short-page-record",
        "allocated": alloc["allocated"],
        "chain_index": alloc["chain_index"],
        "count_before": count,
        "count_after": count + 1,
        "object": bytes(obj),
        "object_size": 0x26,
        "capacity": 0x0A,
        "entry_size": 3,
        "bucket_index": bucket_index,
        "selector": selector,
        "coord": coord,
        "glyph": glyph,
        "rows": rows,
        "width": width,
    }


def advance_flagged_text_cursor_via_d550(cursor_x: int, default_advance: int) -> dict[str, int]:
    d5 = int(cursor_x) + int(default_advance)
    if (d5 & 0xFFFF) >= 12:
        d5 -= 12
    return {
        "cursor_before": cursor_x,
        "default_advance": default_advance,
        "cursor_after": d5,
    }


def combine_short_text_buckets(buckets: list[dict[str, object]]) -> dict[str, object]:
    if not buckets:
        raise AssertionError("short text bucket combiner needs at least one bucket")
    first = buckets[0]
    selector = int(first["selector"])
    bucket_index = int(first["bucket_index"])
    entries = bytearray()
    glyphs: list[int] = []
    coords: list[int] = []
    for bucket in buckets:
        if bucket["path"] != "short":
            raise AssertionError("multi-printable stream fixture only combines short text buckets")
        if int(bucket["selector"]) != selector or int(bucket["bucket_index"]) != bucket_index:
            raise AssertionError("multi-printable stream fixture only combines same-selector/same-bucket text entries")
        glyph = int(bucket["glyph"]) & 0xFF
        coord = int(bucket["coord"]) & 0xFFFF
        entries.append(glyph)
        entries.extend(coord.to_bytes(2, "big"))
        glyphs.append(glyph)
        coords.append(coord)
    obj = bytearray(8 + len(entries))
    obj[4:6] = selector.to_bytes(2, "big")
    obj[6:8] = len(buckets).to_bytes(2, "big")
    obj[8:] = entries
    return {
        "path": "short-combined",
        "object": bytes(obj),
        "selector": selector,
        "bucket_index": bucket_index,
        "count": len(buckets),
        "glyphs": glyphs,
        "coords": coords,
    }


def render_compact_text_bucket_object(data: bytes, resources: bytes | bytearray, contexts: tuple[int, ...], obj: bytes) -> dict[str, object]:
    selector = u16(obj, 4)
    context_slot = obj[5] & 0x0F
    if context_slot >= len(contexts):
        raise AssertionError(f"context slot {context_slot} is not available")
    payload = obj[6:]
    compact_mode = selector & 0x3000
    if compact_mode == 0x0000:
        rendered = render_compact_mode0_payload(data, resources, contexts[context_slot], payload)
    elif compact_mode == 0x1000:
        rendered = render_compact_wide_payload_via_1f0d2(data, resources, contexts[context_slot], payload)
    elif compact_mode == 0x2000:
        rendered = render_compact_segmented_payload_via_1f1f0(data, resources, contexts[context_slot], payload)
    elif compact_mode == 0x3000:
        rendered = render_compact_segmented_wide_payload_via_1f264(data, resources, contexts[context_slot], payload)
    else:
        raise AssertionError("unknown compact text bucket mode")
    rendered["selector"] = selector
    rendered["context_slot"] = context_slot
    rendered["payload"] = payload
    rendered["compact_mode"] = compact_mode >> 12
    return rendered


def bridge_page_record_via_1edc6(page_record: dict[str, object]) -> dict[str, object]:
    """Model the page/control record to render-record copy at 0x1edc6."""
    context_slots = list(page_record.get("context_slots", []))
    if len(context_slots) > 16:
        raise AssertionError("0x1edc6 copies exactly 16 context slots")
    context_slots += [0] * (16 - len(context_slots))

    compact_bucket_root = page_record.get("bucket_root")
    rule_list = [bytearray(node) for node in page_record.get("rule_list", [])]
    fixed_list = [bytearray(node) for node in page_record.get("fixed_list", [])]

    for node in rule_list:
        if len(node) < 0x0E:
            raise AssertionError("rule/list bridge node must include bytes through +0x0d")
        node[5] |= 0x10
        node[0x0C:0x0E] = node[0x0A:0x0C]

    for node in fixed_list:
        if len(node) < 0x0E:
            raise AssertionError("fixed-width bridge node must include bytes through +0x0d")
        node[5] |= 0x10
        node[0x0A:0x0C] = node[0x08:0x0A]
        node[0x0C] = 1
        node[0x0D] = 8

    return {
        "bucket_root": compact_bucket_root,
        "rule_list": [bytes(node) for node in rule_list],
        "fixed_list": [bytes(node) for node in fixed_list],
        "context_slots": tuple(context_slots),
    }


def rectangle_rule_key_via_134d6(source: dict[str, int], vertical_offset: int = 0) -> dict[str, int]:
    x = (int(source["x"]) + int(vertical_offset)) & 0xFFFF
    y = int(source["y"]) & 0xFFFF
    bucket_index = y >> 4
    key = ((y << 12) & 0xF000) | ((x & 0x0F) << 8) | ((x >> 4) & 0x00FF)
    return {
        "x": x,
        "y": y,
        "bucket_index": bucket_index,
        "key": key,
    }


def queue_rectangle_rule_via_13386(page_record: dict[str, object], source: dict[str, int], *, vertical_offset: int = 0, band_byte: int = 0) -> dict[str, object]:
    rule_list = page_record.setdefault("rule_list", [])
    if not isinstance(rule_list, list):
        raise AssertionError("page record rule_list must be a list")
    computed = rectangle_rule_key_via_134d6(source, vertical_offset)
    obj = bytearray(0x0E)
    obj[4] = band_byte & 0xFF
    obj[5] = int(source.get("flags", 0)) & 0xFF
    obj[6:8] = int(computed["key"]).to_bytes(2, "big")
    obj[8:10] = (int(source["width"]) & 0xFFFF).to_bytes(2, "big")
    obj[10:12] = (int(source["height"]) & 0xFFFF).to_bytes(2, "big")
    rule_list.append(bytes(obj))
    return {
        "path": "rectangle-rule-list",
        "computed": computed,
        "object": bytes(obj),
        "list_length": len(rule_list),
    }


def fixed_rule_key_via_137a2(source: dict[str, int], vertical_offset: int = 0) -> dict[str, int]:
    mode = 6 if (int(source.get("mode", 0)) & 1) else 3
    x = (int(source["x"]) + int(vertical_offset)) & 0xFFFF
    y = int(source["y"]) & 0xFFFF
    bucket_index = y >> 4
    key = ((y << 12) & 0xF000) | ((x & 0x0F) << 8) | ((x >> 4) & 0x00FF)
    return {
        "x": x,
        "y": y,
        "bucket_index": bucket_index,
        "key": key,
        "mode": mode,
        "selector_hi": 0x40,
        "selector_lo": 0x00,
    }


def queue_fixed_rule_via_136d2(page_record: dict[str, object], source: dict[str, int], *, vertical_offset: int = 0, band_byte: int = 0) -> dict[str, object]:
    fixed_list = page_record.setdefault("fixed_list", [])
    if not isinstance(fixed_list, list):
        raise AssertionError("page record fixed_list must be a list")
    computed = fixed_rule_key_via_137a2(source, vertical_offset)
    obj = bytearray(0x0E)
    obj[4] = band_byte & 0xFF
    obj[5] = int(computed["mode"]) & 0xFF
    obj[6:8] = int(computed["key"]).to_bytes(2, "big")
    obj[8:10] = (int(source["extent"]) & 0xFFFF).to_bytes(2, "big")
    fixed_list.append(bytes(obj))
    return {
        "path": "fixed-rule-list",
        "computed": computed,
        "object": bytes(obj),
        "list_length": len(fixed_list),
    }


def render_bridged_compact_bucket_object(data: bytes, resources: bytes, render_record: dict[str, object]) -> dict[str, object]:
    obj = render_record["bucket_root"]
    context_slots = render_record["context_slots"]
    if not isinstance(obj, bytes):
        raise AssertionError("bridged render-record fixture needs one compact bucket object")
    if not isinstance(context_slots, tuple):
        raise AssertionError("bridged render-record fixture needs context slots")
    return render_compact_text_bucket_object(data, resources, context_slots, obj)


def raster_graphics_state(**overrides: int) -> dict[str, int]:
    state = {
        "baseline_word": 0,
        "row_y": 0,
        "mode": 3,
        "origin_long": 0,
        "scale": 4,
        "limit": 0,
        "active": 0,
        "orientation": 0,
        "cursor_axis0": 0,
        "cursor_axis1": 0,
        "page_extent": 255,
    }
    state.update(overrides)
    return state


def recompute_raster_limit_via_3324a(state: dict[str, int]) -> int:
    denominator = int(state["scale"]) << 3
    if denominator <= 0:
        raise AssertionError("raster scale denominator must be positive")
    numerator = int(state["page_extent"]) - int(state["baseline_word"]) + 1
    if numerator <= 0:
        return 0
    return (numerator + denominator - 1) // denominator


def apply_raster_resolution_via_10808(state: dict[str, int], parameter: int) -> dict[str, int]:
    state = dict(state)
    if state["active"]:
        return state
    value = abs(int(parameter))
    if value > 150:
        scale = 1
    elif value > 100:
        scale = 2
    elif value > 75:
        scale = 3
    else:
        scale = 4
    state["scale"] = scale
    state["limit"] = recompute_raster_limit_via_3324a(state)
    state["mode"] = scale - 1
    return state


def start_raster_graphics_via_1075a(state: dict[str, int], parameter: int) -> dict[str, int]:
    state = dict(state)
    if state["active"]:
        return state
    state["active"] = 1
    value = abs(int(parameter))
    if value == 1:
        state["origin_long"] = int(state["cursor_axis1"] if state["orientation"] else state["cursor_axis0"])
    else:
        state["origin_long"] = 0
    state["baseline_word"] = (int(state["origin_long"]) >> 16) & 0xFFFF
    state["limit"] = recompute_raster_limit_via_3324a(state)
    return state


def end_raster_graphics_via_107fa(state: dict[str, int]) -> dict[str, int]:
    state = dict(state)
    state["active"] = 0
    return state


def parse_pcl_decimal_parameter(stream: bytes, pos: int) -> tuple[int, int]:
    sign = 1
    if pos < len(stream) and stream[pos] in (ord("+"), ord("-")):
        sign = -1 if stream[pos] == ord("-") else 1
        pos += 1
    if pos >= len(stream) or not chr(stream[pos]).isdigit():
        raise AssertionError("PCL command fixture requires an integer parameter")
    value = 0
    while pos < len(stream) and chr(stream[pos]).isdigit():
        value = value * 10 + stream[pos] - ord("0")
        pos += 1
    return sign * value, pos


def render_raster_command_data_stream_via_121cc_105d0(data: bytes, stream: bytes, initial_state: dict[str, int]) -> dict[str, object]:
    state = dict(initial_state)
    page_record: dict[str, object] = {"bucket_array": {}}
    events: list[dict[str, object]] = []
    queued: list[dict[str, object]] = []
    pos = 0
    while pos < len(stream):
        if stream[pos] != 0x1B:
            raise AssertionError(f"raster command stream expected ESC at offset {pos}")
        start = pos
        pos += 1
        if pos + 1 >= len(stream) or stream[pos] != ord("*"):
            raise AssertionError(f"raster command stream only models ESC * commands at offset {start}")
        group = stream[pos + 1]
        pos += 2
        while True:
            command_start = start if pos == start + 3 else pos
            if pos < len(stream) and (stream[pos] in (ord("+"), ord("-")) or chr(stream[pos]).isdigit()):
                parameter, pos = parse_pcl_decimal_parameter(stream, pos)
            else:
                parameter = 0
            if pos >= len(stream):
                raise AssertionError("raster command stream missing final byte")
            final = stream[pos]
            pos += 1
            final_upper = final & ~0x20 if ord("a") <= final <= ord("z") else final
            sequence = stream[command_start:pos]

            if group == ord("t") and final_upper == ord("R"):
                before = dict(state)
                state = apply_raster_resolution_via_10808(state, parameter)
                events.append({
                    "kind": "raster-resolution",
                    "sequence": sequence,
                    "parameter": parameter,
                    "mode_before": before["mode"],
                    "mode_after": state["mode"],
                    "scale": state["scale"],
                    "limit": state["limit"],
                    "chained": bool(ord("a") <= final <= ord("z")),
                })
            elif group == ord("r") and final_upper == ord("A"):
                before = dict(state)
                state = start_raster_graphics_via_1075a(state, parameter)
                events.append({
                    "kind": "start-raster",
                    "sequence": sequence,
                    "parameter": parameter,
                    "active_before": before["active"],
                    "active_after": state["active"],
                    "origin_long": state["origin_long"],
                    "baseline_word": state["baseline_word"],
                    "limit": state["limit"],
                    "chained": bool(ord("a") <= final <= ord("z")),
                })
            elif group == ord("r") and final_upper == ord("B"):
                before = dict(state)
                state = end_raster_graphics_via_107fa(state)
                events.append({
                    "kind": "end-raster",
                    "sequence": sequence,
                    "parameter": parameter,
                    "active_before": before["active"],
                    "active_after": state["active"],
                    "mode": state["mode"],
                    "scale": state["scale"],
                    "limit": state["limit"],
                    "row_y": state["row_y"],
                    "chained": bool(ord("a") <= final <= ord("z")),
                })
            elif group == ord("b") and final_upper == ord("W"):
                byte_count = abs(parameter)
                payload_start = pos
                payload_end = pos + byte_count
                if payload_end > len(stream):
                    raise AssertionError("raster command stream payload shorter than ESC *b#W byte count")
                payload = stream[payload_start:payload_end]
                pos = payload_end
                transfer_state = {
                    "x": state["baseline_word"],
                    "y": state["row_y"],
                    "byte_count": byte_count,
                    "mode": state["mode"],
                }
                result = queue_raster_row_to_page_record_via_13070(page_record, transfer_state, payload)
                state["row_y"] += 1
                event = {
                    "kind": "raster-transfer",
                    "sequence": sequence,
                    "parameter": parameter,
                    "delayed_handler": 0x0105D0,
                    "payload_offset": payload_start,
                    "payload": payload,
                    "transfer_state": transfer_state,
                    "result": result,
                    "row_y_after": state["row_y"],
                    "chained": bool(ord("a") <= final <= ord("z")),
                }
                events.append(event)
                queued.append(event)
            else:
                raise AssertionError(f"unsupported raster command ESC *{chr(group)}#{chr(final)} at offset {command_start}")

            if not (ord("a") <= final <= ord("z")):
                break

    bucket_array = page_record["bucket_array"]
    assert isinstance(bucket_array, dict)
    bucket_index = queued[-1]["result"]["bucket_index"] if queued else 0
    chain = bucket_array.get(bucket_index, [])
    chain_objects = [bytes(item) for item in chain]
    obj = chain_objects[0] if chain_objects else b""
    rendered = render_encoded_raster_object_via_1f88e(data, obj) if obj else None
    bridged = bridge_page_record_via_1edc6({"bucket_root": obj}) if obj else None
    bridged_rendered = render_bridged_encoded_raster_object(data, bridged) if bridged else None
    return {
        "stream": stream,
        "events": events,
        "page_record": page_record,
        "bucket_index": bucket_index,
        "chain": chain_objects,
        "object": obj,
        "rendered": rendered,
        "bridged": bridged,
        "bridged_rendered": bridged_rendered,
        "final_state": state,
    }


def queue_raster_row_to_page_record_via_13070(
    page_record: dict[str, object],
    raster_state: dict[str, int],
    payload: bytes,
    horizontal_offset: int = 0,
) -> dict[str, object]:
    bucket_array = page_record.setdefault("bucket_array", {})
    if not isinstance(bucket_array, dict):
        raise AssertionError("page record bucket_array must be a dict")

    x = int(raster_state["x"]) + int(horizontal_offset)
    y = int(raster_state["y"])
    byte_count = int(raster_state["byte_count"])
    mode = int(raster_state["mode"]) & 0xFF
    if byte_count < 0:
        raise AssertionError("raster byte count must be non-negative")
    if len(payload) < byte_count:
        raise AssertionError("raster payload fixture shorter than requested byte count")

    bucket_index = y >> 4
    key = ((y << 12) & 0xF000) | ((x & 0x0F) << 8) | ((x >> 4) & 0x00FF)
    capacity = byte_count + (byte_count & 1)
    object_size = 0x0A + capacity

    chain = bucket_array.setdefault(bucket_index, [])
    obj = bytearray(object_size)
    obj[4] = 0x80
    obj[5] = mode
    chain.insert(0, obj)

    copy_count = min(byte_count, capacity)
    obj[6:8] = capacity.to_bytes(2, "big")
    obj[8:10] = key.to_bytes(2, "big")
    obj[10 : 10 + copy_count] = payload[:copy_count]
    remaining_count = byte_count - copy_count

    return {
        "path": "raster-page-record",
        "allocated": True,
        "bucket_index": bucket_index,
        "key": key,
        "mode": mode,
        "byte_count_before": byte_count,
        "byte_count_after": remaining_count,
        "capacity": capacity,
        "object_size": object_size,
        "payload": payload[:copy_count],
        "object": bytes(obj),
    }


def render_encoded_raster_object_via_1f88e(data: bytes, obj: bytes, dest_stride: int = 0x20, band_rows: int = 16) -> dict[str, object]:
    if len(obj) < 0x0A:
        raise AssertionError("encoded raster object must include header through +0x09")
    if obj[4] & 0xC0 != 0x80:
        raise AssertionError("encoded raster fixture requires object byte +4 high bits 0x80")
    mode = obj[5] & 0x03
    byte_count = u16(obj, 6)
    coord = u16(obj, 8)
    payload = obj[10 : 10 + byte_count]
    if len(payload) < byte_count:
        raise AssertionError("encoded raster payload is shorter than byte count")

    decoded = coord_decode(coord, band_base=0, payload_offset=0)
    row = int(decoded["row_index"])
    x = int(decoded["byte_pair_offset"]) * 8 + ((coord >> 8) & 0x0F)
    if mode not in (0, 2) and decoded["a001"] != 0:
        raise AssertionError("encoded raster fixture currently models byte-aligned rows only")
    if row >= band_rows:
        raise AssertionError("encoded raster row starts outside the synthetic band")

    dest = bytearray(band_rows * dest_stride)
    fallback_dest = bytearray(0)
    dest_offset = row * dest_stride + int(decoded["byte_pair_offset"])
    rows_in_band = 0
    remaining_after_band = 0
    if mode == 0:
        if byte_count & 1:
            raise AssertionError("mode-0 encoded raster fixture expects an even byte count")
        rows = 1
        rows_in_band = min(rows, band_rows - row)
        remaining_after_band = rows - rows_in_band
        if decoded["a001"] == 0:
            dest[dest_offset : dest_offset + byte_count] = payload
        else:
            write_bitmap_bits(dest, dest_stride, payload, 1, byte_count, x, row)
        width = byte_count * 8
    elif mode == 1:
        rows = 2
        if row + rows > band_rows:
            raise AssertionError("mode-1 encoded raster fixture crosses the synthetic band")
        rows_in_band = rows
        for index, byte in enumerate(payload):
            word = u16(data, 0x30914 + byte * 2)
            word_bytes = word.to_bytes(2, "big")
            offset = int(decoded["byte_pair_offset"]) + index * 2
            for row_offset in range(rows):
                start = (row + row_offset) * dest_stride + offset
                dest[start : start + 2] = word_bytes
        width = byte_count * 16
    elif mode == 2:
        rows = 3
        if byte_count & 1:
            raise AssertionError("mode-2 encoded raster fixture expects an even byte count")
        rows_in_band = min(rows, band_rows - row)
        remaining_after_band = rows - rows_in_band
        fallback_dest = bytearray(remaining_after_band * dest_stride)
        expanded_span = (byte_count // 2) * 6
        expanded = bytearray(rows * expanded_span)
        for pass_offset, source_start in ((0, 0), (2, 1)):
            for index, byte in enumerate(payload[source_start::2]):
                long_bytes = u32(data, 0x30B14 + byte * 4).to_bytes(4, "big")
                offset = pass_offset + index * 6
                for row_offset in range(rows):
                    start = row_offset * expanded_span + offset
                    expanded[start : start + 4] = long_bytes
        if decoded["a001"] == 0:
            for row_offset in range(rows_in_band):
                start = (row + row_offset) * dest_stride + int(decoded["byte_pair_offset"])
                source = row_offset * expanded_span
                dest[start : start + expanded_span] = expanded[source : source + expanded_span]
            for fallback_row in range(remaining_after_band):
                source = (rows_in_band + fallback_row) * expanded_span
                start = fallback_row * dest_stride + int(decoded["byte_pair_offset"])
                fallback_dest[start : start + expanded_span] = expanded[source : source + expanded_span]
        else:
            write_bitmap_bits(dest, dest_stride, expanded, rows_in_band, expanded_span, x, row)
            fallback_source = expanded[rows_in_band * expanded_span :]
            write_bitmap_bits(fallback_dest, dest_stride, fallback_source, remaining_after_band, expanded_span, x, 0)
        width = (byte_count // 2) * 48
    elif mode == 3:
        rows = 4
        if row + rows > band_rows:
            raise AssertionError("mode-3 encoded raster fixture crosses the synthetic band")
        rows_in_band = rows
        for index, byte in enumerate(payload):
            first = u16(data, 0x30914 + byte * 2)
            high = u16(data, 0x30914 + ((first >> 8) & 0xFF) * 2)
            low = u16(data, 0x30914 + (first & 0xFF) * 2)
            long_bytes = ((high << 16) | low).to_bytes(4, "big")
            offset = int(decoded["byte_pair_offset"]) + index * 4
            for row_offset in range(rows):
                start = (row + row_offset) * dest_stride + offset
                dest[start : start + 4] = long_bytes
        width = byte_count * 32
    else:
        raise AssertionError("queued encoded raster object fixture currently renders modes 0..3 only")

    return {
        "mode": mode,
        "helper": u32(data, 0x1F8CA + mode * 4),
        "byte_count": byte_count,
        "coord": coord,
        "dest_base": dest_offset,
        "x": x,
        "y": row,
        "rows_in_band": rows_in_band,
        "remaining_after_band": remaining_after_band,
        "payload": payload,
        "rows": bitmap_bytes_to_rows(dest, row + rows_in_band, x + width, dest_stride),
        "fallback_rows": bitmap_bytes_to_rows(fallback_dest, remaining_after_band, x + width, dest_stride),
    }


def render_bridged_encoded_raster_object(data: bytes, render_record: dict[str, object]) -> dict[str, object]:
    obj = render_record["bucket_root"]
    if not isinstance(obj, bytes):
        raise AssertionError("bridged raster render-record fixture needs one encoded raster object")
    return render_encoded_raster_object_via_1f88e(data, obj)


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


def render_multi_printable_stream(
    data: bytes,
    resources: bytes,
    stream: bytes,
    context: int,
    cursor_x: int,
    cursor_y: int,
    default_advance: int,
    context_slot: int = 0,
    render_output: bool = True,
) -> dict[str, object]:
    if not stream or any(byte < 0x20 or byte == 0x7F for byte in stream):
        raise AssertionError("multi-printable stream fixture only models normal printable bytes")
    cursor = int(cursor_x)
    cursor_y_whole = unpack12(cursor_y)[0]
    entries: list[dict[str, object]] = []
    buckets: list[dict[str, object]] = []
    advances: list[dict[str, int]] = []
    for byte in stream:
        source = build_text_source_object_from_1393a(resources, context, byte, x=0, y=0, context_slot=context_slot)
        positioned = position_flagged_text_source_via_d824(resources, source, cursor_x=unpack12(cursor)[0], cursor_y=cursor_y_whole)
        positioned_source = positioned["source"]
        assert isinstance(positioned_source, dict)
        bucket = queue_text_source_via_12f2e(resources, positioned_source)
        bucket_object = bucket["object"]
        if not isinstance(bucket_object, bytes):
            raise AssertionError("multi-printable stream fixture only models short compact text objects")
        buckets.append(bucket)
        entries.append({
            "byte": byte,
            "source": source,
            "positioned": positioned,
            "bucket": bucket,
        })
        advance = advance_flagged_text_cursor_via_d550(cursor, default_advance)
        advances.append(advance)
        cursor = advance["cursor_after"]
    combined = combine_short_text_buckets(buckets)
    rendered = None
    if render_output:
        obj = combined["object"]
        assert isinstance(obj, bytes)
        rendered = render_compact_text_bucket_object(data, resources, (context,), obj)
    return {
        "stream": stream,
        "entries": entries,
        "advances": advances,
        "combined": combined,
        "rendered": rendered,
        "final_cursor_x": cursor,
    }


def render_mixed_printable_control_stream(
    data: bytes,
    resources: bytes,
    stream: bytes,
    context: int,
    state: dict[str, int],
    default_advance: int,
    context_slot: int = 0,
) -> dict[str, object]:
    state = dict(state)
    events: list[dict[str, object]] = []
    buckets: list[dict[str, object]] = []
    pos = 0
    while pos < len(stream):
        byte = stream[pos]
        if byte == 0x1B:
            if pos + 1 < len(stream) and stream[pos + 1] == ord("E"):
                before = dict(state)
                state = apply_esc_e_reset(state)
                events.append({
                    "kind": "reset",
                    "offset": pos,
                    "sequence": stream[pos : pos + 2],
                    "current_page_root_before": before["current_page_root"],
                    "current_page_root_after": state["current_page_root"],
                    "page_publications": state["page_publications"],
                    "page_root_clears": state["page_root_clears"],
                    "span_flushes": state["span_flushes"],
                    "post_flushes": state["post_flushes"],
                    "hmi": state["hmi"],
                    "orientation": state["orientation"],
                    "data_chain_ptr": state["data_chain_ptr"],
                    "reset_status": state["reset_status"],
                })
                pos += 2
                continue
            if pos + 3 >= len(stream) or stream[pos + 1 : pos + 3] != b"&k":
                raise AssertionError(f"mixed printable/control stream only models ESC &k#G and ESC E at offset {pos}")
            start = pos
            pos += 3
            sign = 1
            if pos < len(stream) and stream[pos] in (ord("+"), ord("-")):
                sign = -1 if stream[pos] == ord("-") else 1
                pos += 1
            if pos >= len(stream) or not chr(stream[pos]).isdigit():
                raise AssertionError("mixed printable/control ESC &k#G needs an integer parameter")
            value = 0
            while pos < len(stream) and chr(stream[pos]).isdigit():
                value = value * 10 + stream[pos] - ord("0")
                pos += 1
            if pos >= len(stream) or stream[pos] != ord("G"):
                raise AssertionError("mixed printable/control stream only models ESC &k#G final byte")
            state["line_termination"] = line_termination_mode_bits(sign * value)
            pos += 1
            events.append({
                "kind": "escape",
                "offset": start,
                "sequence": stream[start:pos],
                "line_termination": state["line_termination"],
            })
            continue
        if byte in (0x08, 0x09, 0x0A, 0x0C, 0x0D):
            before = dict(state)
            state = apply_direct_control_code(state, byte)
            events.append({
                "kind": "control",
                "offset": pos,
                "byte": byte,
                "cursor_before": (before["cursor_x"], before["cursor_y"]),
                "cursor_after": (state["cursor_x"], state["cursor_y"]),
                "line_termination": state["line_termination"],
                "page_roots": state["page_roots"],
                "span_flushes": state["span_flushes"],
            })
            pos += 1
            continue
        if byte < 0x20 or byte == 0x7F:
            raise AssertionError(f"unsupported mixed printable/control byte 0x{byte:02x} at offset {pos}")

        source = build_text_source_object_from_1393a(resources, context, byte, x=0, y=0, context_slot=context_slot)
        positioned = position_flagged_text_source_via_d824(
            resources,
            source,
            cursor_x=unpack12(state["cursor_x"])[0],
            cursor_y=unpack12(state["cursor_y"])[0],
        )
        positioned_source = positioned["source"]
        assert isinstance(positioned_source, dict)
        bucket = queue_text_source_via_12f2e(resources, positioned_source)
        bucket_object = bucket["object"]
        if not isinstance(bucket_object, bytes):
            raise AssertionError("mixed printable/control fixture only models short compact text objects")
        buckets.append(bucket)
        advance = advance_flagged_text_cursor_via_d550(state["cursor_x"], default_advance)
        state["cursor_x"] = advance["cursor_after"]
        events.append({
            "kind": "printable",
            "offset": pos,
            "byte": byte,
            "cursor_before": advance["cursor_before"],
            "cursor_after": advance["cursor_after"],
            "source": source,
            "positioned": positioned,
            "bucket": bucket,
        })
        pos += 1

    combined = combine_short_text_buckets(buckets)
    obj = combined["object"]
    assert isinstance(obj, bytes)
    rendered = render_compact_text_bucket_object(data, resources, (context,), obj)
    return {
        "stream": stream,
        "events": events,
        "combined": combined,
        "rendered": rendered,
        "final_state": state,
    }


def render_mixed_printable_control_page_record_stream(
    data: bytes,
    resources: bytes,
    stream: bytes,
    context: int,
    state: dict[str, int],
    default_advance: int,
    context_slot: int = 0,
) -> dict[str, object]:
    state = dict(state)
    page_record: dict[str, object] = {"bucket_array": {}, "context_slots": [context]}
    events: list[dict[str, object]] = []
    pos = 0
    while pos < len(stream):
        byte = stream[pos]
        if byte == 0x1B:
            if pos + 1 < len(stream) and stream[pos + 1] == ord("E"):
                before = dict(state)
                state = apply_esc_e_reset(state)
                events.append({
                    "kind": "reset",
                    "offset": pos,
                    "sequence": stream[pos : pos + 2],
                    "current_page_root_before": before["current_page_root"],
                    "current_page_root_after": state["current_page_root"],
                    "page_publications": state["page_publications"],
                    "page_root_clears": state["page_root_clears"],
                    "span_flushes": state["span_flushes"],
                    "post_flushes": state["post_flushes"],
                    "hmi": state["hmi"],
                    "orientation": state["orientation"],
                    "data_chain_ptr": state["data_chain_ptr"],
                    "reset_status": state["reset_status"],
                })
                pos += 2
                continue
            if pos + 3 >= len(stream) or stream[pos + 1 : pos + 3] != b"&k":
                raise AssertionError(f"page-record mixed stream only models ESC &k#G and ESC E at offset {pos}")
            start = pos
            pos += 3
            sign = 1
            if pos < len(stream) and stream[pos] in (ord("+"), ord("-")):
                sign = -1 if stream[pos] == ord("-") else 1
                pos += 1
            if pos >= len(stream) or not chr(stream[pos]).isdigit():
                raise AssertionError("page-record mixed stream ESC &k#G needs an integer parameter")
            value = 0
            while pos < len(stream) and chr(stream[pos]).isdigit():
                value = value * 10 + stream[pos] - ord("0")
                pos += 1
            if pos >= len(stream) or stream[pos] != ord("G"):
                raise AssertionError("page-record mixed stream only models ESC &k#G final byte")
            state["line_termination"] = line_termination_mode_bits(sign * value)
            pos += 1
            events.append({
                "kind": "escape",
                "offset": start,
                "sequence": stream[start:pos],
                "line_termination": state["line_termination"],
            })
            continue
        if byte in (0x08, 0x09, 0x0A, 0x0C, 0x0D):
            before = dict(state)
            state = apply_direct_control_code(state, byte)
            events.append({
                "kind": "control",
                "offset": pos,
                "byte": byte,
                "cursor_before": (before["cursor_x"], before["cursor_y"]),
                "cursor_after": (state["cursor_x"], state["cursor_y"]),
                "page_roots": state["page_roots"],
                "span_flushes": state["span_flushes"],
            })
            pos += 1
            continue
        if byte < 0x20 or byte == 0x7F:
            raise AssertionError(f"unsupported page-record mixed stream byte 0x{byte:02x} at offset {pos}")

        source = build_text_source_object_from_1393a(resources, context, byte, x=0, y=0, context_slot=context_slot)
        positioned = position_flagged_text_source_via_d824(
            resources,
            source,
            cursor_x=unpack12(state["cursor_x"])[0],
            cursor_y=unpack12(state["cursor_y"])[0],
        )
        positioned_source = positioned["source"]
        assert isinstance(positioned_source, dict)
        page_result = queue_text_source_to_page_record_via_12f2e(resources, page_record, positioned_source)
        advance = advance_flagged_text_cursor_via_d550(state["cursor_x"], default_advance)
        state["cursor_x"] = advance["cursor_after"]
        events.append({
            "kind": "printable",
            "offset": pos,
            "byte": byte,
            "cursor_before": advance["cursor_before"],
            "cursor_after": advance["cursor_after"],
            "source": source,
            "positioned": positioned,
            "page_result": page_result,
        })
        pos += 1

    bucket_array = page_record["bucket_array"]
    assert isinstance(bucket_array, dict)
    nonempty_buckets = sorted(bucket for bucket, chain in bucket_array.items() if chain)
    if len(nonempty_buckets) != 1:
        raise AssertionError("page-record mixed stream fixture expects one short compact bucket")
    chain = bucket_array[nonempty_buckets[0]]
    if len(chain) != 1:
        raise AssertionError("page-record mixed stream fixture expects one compact object in the bucket")
    bucket_object = bytes(chain[0])
    bridged_record = bridge_page_record_via_1edc6({
        "bucket_root": bucket_object,
        "context_slots": [context],
    })
    rendered = render_bridged_compact_bucket_object(data, resources, bridged_record)
    return {
        "stream": stream,
        "events": events,
        "page_record": page_record,
        "bucket_index": nonempty_buckets[0],
        "bucket_object": bucket_object,
        "bridged_record": bridged_record,
        "rendered": rendered,
        "final_state": state,
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

    host_fetch_no_byte = host_byte_fetch_via_a904(host_byte_fetch_state(
        buffer_flags=1,
        force_no_byte=True,
        lifo1=[0x41],
        data_chain=[0x42],
        direct_mode=0,
        ring=[0x43],
    ))
    checks.append(assert_equal("0xa904 no-byte branch returns -1 before buffered sources", {
        "d7": host_fetch_no_byte["d7"],
        "source": host_fetch_no_byte["source"],
        "events": host_fetch_no_byte["events"],
    }, {
        "d7": -1,
        "source": "no-byte",
        "events": [],
    }))

    host_fetch_priority = host_byte_fetch_via_a904(host_byte_fetch_state(
        service_needed=True,
        lifo1=[0x31, 0x42],
        data_chain=[0x43],
        lifo2=[0x44],
        ring=[0x45],
        direct_mode=0,
    ))
    host_fetch_priority_state = host_fetch_priority["state"]
    assert isinstance(host_fetch_priority_state, dict)
    checks.append(assert_equal("0xa904 services pending work then prefers first LIFO source", {
        "d7": host_fetch_priority["d7"],
        "source": host_fetch_priority["source"],
        "events": host_fetch_priority["events"],
        "remaining_lifo1": host_fetch_priority_state["lifo1"],
        "service_calls": host_fetch_priority_state["service_calls"],
    }, {
        "d7": 0x42,
        "source": "first-lifo",
        "events": [
            {"kind": "service-retry", "helper": 0x10CC, "argument": 0x780202},
            {"kind": "first-lifo", "remaining": 1},
        ],
        "remaining_lifo1": [0x31],
        "service_calls": 1,
    }))

    host_fetch_data_chain = host_byte_fetch_via_a904(host_byte_fetch_state(
        data_chain_end_marker=True,
        lifo2=[0x55],
        ring=[0x56],
        direct_mode=0,
    ))
    host_fetch_data_chain_state = host_fetch_data_chain["state"]
    assert isinstance(host_fetch_data_chain_state, dict)
    checks.append(assert_equal("0xa904 data-chain end marker retries before second LIFO source", {
        "d7": host_fetch_data_chain["d7"],
        "source": host_fetch_data_chain["source"],
        "events": host_fetch_data_chain["events"],
        "data_chain_transitions": host_fetch_data_chain_state["data_chain_transitions"],
    }, {
        "d7": 0x55,
        "source": "second-lifo",
        "events": [
            {"kind": "data-chain-transition", "helper": 0xE22C},
            {"kind": "second-lifo", "remaining": 0},
        ],
        "data_chain_transitions": 1,
    }))

    host_fetch_ring = host_byte_fetch_via_a904(host_byte_fetch_state(
        ring=[0x66, 0x67],
        direct_mode=0,
        direct_mode1_status=0x10,
        direct_mode1_data=[0x68],
    ))
    host_fetch_ring_state = host_fetch_ring["state"]
    assert isinstance(host_fetch_ring_state, dict)
    checks.append(assert_equal("0xa904 buffered ring source wins before direct hardware in mode 0", {
        "d7": host_fetch_ring["d7"],
        "source": host_fetch_ring["source"],
        "events": host_fetch_ring["events"],
        "remaining_ring": host_fetch_ring_state["ring"],
    }, {
        "d7": 0x66,
        "source": "ring",
        "events": [{"kind": "ring-byte", "remaining": 1}],
        "remaining_ring": [0x67],
    }))

    host_fetch_mode1 = host_byte_fetch_via_a904(host_byte_fetch_state(
        direct_mode=1,
        direct_mode1_status=0x10,
        direct_mode1_ack=0,
        direct_mode1_data=[0x1A],
        mode1_control_shadow=0x34,
        handshake_state=1,
        timeout_state=1,
    ))
    host_fetch_mode1_state = host_fetch_mode1["state"]
    assert isinstance(host_fetch_mode1_state, dict)
    checks.append(assert_equal("0xa904 direct mode 1 preserves 0x1a and clears handshake state", {
        "d7": host_fetch_mode1["d7"],
        "source": host_fetch_mode1["source"],
        "events": host_fetch_mode1["events"],
        "handshake_state": host_fetch_mode1_state["handshake_state"],
        "timeout_state": host_fetch_mode1_state["timeout_state"],
        "control_1a_reports": host_fetch_mode1_state["control_1a_reports"],
    }, {
        "d7": 0x1A,
        "source": "direct-mode-1",
        "events": [
            {"kind": "control-1a-report", "helper": 0x9EC0},
            {"kind": "mode1-handshake", "status": 0x10, "ack": 0, "control_shadow": 0x34},
        ],
        "handshake_state": 0,
        "timeout_state": 0,
        "control_1a_reports": 1,
    }))

    host_fetch_mode2 = host_byte_fetch_via_a904(host_byte_fetch_state(
        direct_mode=2,
        direct_mode2_status=0x01,
        direct_mode2_data=[0x7E],
        mode2_control_shadow=0x20,
        handshake_state=0,
        timeout_state=1,
    ))
    host_fetch_mode2_state = host_fetch_mode2["state"]
    assert isinstance(host_fetch_mode2_state, dict)
    checks.append(assert_equal("0xa904 direct mode 2 reads ready byte and sets control-shadow bit 6", {
        "d7": host_fetch_mode2["d7"],
        "source": host_fetch_mode2["source"],
        "events": host_fetch_mode2["events"],
        "handshake_state": host_fetch_mode2_state["handshake_state"],
        "timeout_state": host_fetch_mode2_state["timeout_state"],
        "mode2_control_shadow": host_fetch_mode2_state["mode2_control_shadow"],
    }, {
        "d7": 0x7E,
        "source": "direct-mode-2",
        "events": [{"kind": "mode2-handshake", "status": 0x01, "control_shadow": 0x60}],
        "handshake_state": 1,
        "timeout_state": 0,
        "mode2_control_shadow": 0x60,
    }))

    tokenizer_chained_resolution = parse_pcl_numeric_records_via_daf0(b"300r150R\x1b")
    tokenizer_chained_records = tokenizer_chained_resolution["records"]
    assert isinstance(tokenizer_chained_records, list)
    checks.append(assert_equal("0xdaf0 tokenizes lowercase-final numeric chain into two six-byte records", {
        "record_bytes": tokenizer_chained_resolution["record_bytes"],
        "scratch": tokenizer_chained_resolution["scratch"],
        "returned_d7": tokenizer_chained_resolution["returned_d7"],
        "cursor": tokenizer_chained_resolution["cursor"],
        "lookahead": tokenizer_chained_resolution["lookahead"],
    }, {
        "record_bytes": bytes.fromhex("80 72 01 2c 00 00 80 52 00 96 00 00"),
        "scratch": b"300150",
        "returned_d7": [0x72, 0x52],
        "cursor": 0x7829AE,
        "lookahead": 0x1B,
    }))

    tokenizer_signed_fraction = parse_pcl_numeric_records_via_daf0(b" -12.34567W\x1b")
    checks.append(assert_equal("0xdb74 parses sign, capped fraction digits, and final byte", {
        "record_bytes": tokenizer_signed_fraction["record_bytes"],
        "scratch": tokenizer_signed_fraction["scratch"],
        "returned_d7": tokenizer_signed_fraction["returned_d7"],
        "cursor": tokenizer_signed_fraction["cursor"],
        "lookahead": tokenizer_signed_fraction["lookahead"],
    }, {
        "record_bytes": bytes.fromhex("81 57 ff f4 f2 80"),
        "scratch": b"-12.3456",
        "returned_d7": [0x57],
        "cursor": 0x7829A8,
        "lookahead": 0x1B,
    }))

    tokenizer_semicolon = parse_pcl_numeric_records_via_daf0(b"1;2X\x1b")
    checks.append(assert_equal("0xdb74 returns D7 zero for semicolon continuation final", {
        "record_bytes": tokenizer_semicolon["record_bytes"],
        "returned_d7": tokenizer_semicolon["returned_d7"],
        "cursor": tokenizer_semicolon["cursor"],
        "lookahead": tokenizer_semicolon["lookahead"],
    }, {
        "record_bytes": bytes.fromhex("80 3b 00 01 00 00 80 58 00 02 00 00"),
        "returned_d7": [0, 0x58],
        "cursor": 0x7829AE,
        "lookahead": 0x1B,
    }))

    raster_transfer_record = bytes.fromhex("80 57 00 04 00 00")
    delayed_raster_transfer = delay_payload_handler_via_121cc(raster_transfer_record, 0x105D0)
    delayed_raster_restore = restore_delayed_payload_via_12218(delayed_raster_transfer)
    checks.append(assert_equal("0x121cc snapshots delayed payload handler and parsed record", delayed_raster_transfer, {
        "pending_flag": 1,
        "handler": 0x105D0,
        "snapshot_record": raster_transfer_record,
        "snapshot_bytes": bytes.fromhex("01 00 01 05 d0 80 57 00 04 00 00"),
    }))
    checks.append(assert_equal("0x12218 restores delayed parsed record and dispatches saved handler", {
        "restored": delayed_raster_restore["restored"],
        "record": delayed_raster_restore["record"],
        "cursor_before": delayed_raster_restore["cursor_before"],
        "cursor_after": delayed_raster_restore["cursor_after"],
        "dispatch": delayed_raster_restore["dispatch"],
        "pending_after": delayed_raster_restore["pending_after"],
    }, {
        "restored": True,
        "record": raster_transfer_record,
        "cursor_before": 0x7829A2,
        "cursor_after": 0x7829A8,
        "dispatch": {"kind": "direct-handler", "handler": 0x105D0},
        "pending_after": {
            "pending_flag": 0,
            "handler": 0,
            "snapshot_record": raster_transfer_record,
        },
    }))
    alternate_payload_wrapper = alternate_payload_dispatch_via_12358(
        bytes.fromhex("81 57 ff fd 00 00"),
        bytes.fromhex("aa 1a 58 bb"),
        callback_matches_wrapper=True,
    )
    checks.append(assert_equal("0x1228a consumes absolute delayed payload count without echo", alternate_payload_wrapper, {
        "path": "wrapper-1228a",
        "cursor_before": 0x7829A8,
        "cursor_after": 0x7829A2,
        "byte_count": 3,
        "status": 1,
        "values": [0xAA, 0x00, 0xBB],
        "echoed": [],
        "pos": 4,
        "remaining": 0,
        "control_hits": 1,
    }))
    alternate_payload_direct = alternate_payload_dispatch_via_12358(
        bytes.fromhex("80 57 00 03 00 00"),
        bytes.fromhex("aa 1a 58 bb cc"),
        callback_matches_wrapper=False,
    )
    alternate_payload_direct_negative = alternate_payload_dispatch_via_12358(
        bytes.fromhex("81 57 ff fd 00 00"),
        bytes.fromhex("aa bb cc"),
        callback_matches_wrapper=False,
    )
    checks.append(assert_equal("0x12358 direct alternate path echoes positive payload bytes only", {
        "positive": alternate_payload_direct,
        "negative": alternate_payload_direct_negative,
    }, {
        "positive": {
            "path": "direct-12358",
            "cursor_before": 0x7829A8,
            "cursor_after": 0x7829A2,
            "byte_count": 3,
            "status": 1,
            "values": [0xAA, 0x00, 0xBB],
            "echoed": [0xAA, 0x00, 0xBB],
            "pos": 4,
            "remaining": 0,
            "control_hits": 1,
        },
        "negative": {
            "path": "direct-12358",
            "cursor_before": 0x7829A8,
            "cursor_after": 0x7829A2,
            "byte_count": -3,
            "status": 1,
            "values": [],
            "echoed": [],
            "pos": 0,
            "remaining": -3,
            "control_hits": 0,
        },
    }))

    checks.append(assert_equal("0x9d16/0x9d4e/0x9d86/0x9dbe page geometry lookups mask page code", {
        "letter_height": page_geometry_lookup_via_9dxx(data, "height", 6),
        "letter_width": page_geometry_lookup_via_9dxx(data, "width", 6),
        "pcl80_height": page_geometry_lookup_via_9dxx(data, "height", 0x88),
        "pcl80_width": page_geometry_lookup_via_9dxx(data, "width", 0x88),
        "invalid": page_geometry_lookup_via_9dxx(data, "width", 0x7F),
        "letter_portrait_margin": page_geometry_lookup_via_9dxx(data, "portrait_margin", 6),
        "letter_landscape_margin": page_geometry_lookup_via_9dxx(data, "landscape_margin", 6),
        "center_remainder": page_center_remainder_via_9e56(2025),
    }, {
        "letter_height": 2025,
        "letter_width": 3030,
        "pcl80_height": 1012,
        "pcl80_width": 2130,
        "invalid": 0,
        "letter_portrait_margin": 3150,
        "letter_landscape_margin": 2175,
        "center_remainder": 11,
    }))
    letter_page = apply_page_size_via_fc74(data, page_geometry_state(), 1)
    pcl80_page = apply_page_size_via_fc74(data, page_geometry_state(), 80)
    default_page = apply_page_size_via_fc74(data, page_geometry_state(default_page_code=0), has_parameter=False)
    invalid_page = apply_page_size_via_fc74(data, page_geometry_state(page_code=6), 99)
    checks.append(assert_equal("0xfc74 ESC &l#A maps page size and recomputes portrait geometry", {
        "letter": {
            key: letter_page[key]
            for key in (
                "page_code",
                "width",
                "height",
                "margin_reference",
                "active_width",
                "active_height",
                "vertical_offset_source",
                "negative_vertical_offset",
                "printable_extent",
                "top_offset",
                "center_remainder",
                "pending_text_flushes",
                "page_finalizations",
                "page_change_flag",
                "print_engine_status",
            )
        },
        "pcl80": {key: pcl80_page[key] for key in ("page_code", "width", "height", "margin_reference")},
        "default": {key: default_page[key] for key in ("page_code", "active_record_waits")},
        "invalid": {key: invalid_page[key] for key in ("page_code", "ignored_page_size_parameter")},
    }, {
        "letter": {
            "page_code": 6,
            "width": 3030,
            "height": 2025,
            "margin_reference": 3150,
            "active_width": 3030,
            "active_height": 2025,
            "vertical_offset_source": 60,
            "negative_vertical_offset": -60,
            "printable_extent": 3090,
            "top_offset": 90,
            "center_remainder": 11,
            "pending_text_flushes": 1,
            "page_finalizations": 1,
            "page_change_flag": 1,
            "print_engine_status": 0,
        },
        "pcl80": {"page_code": 0x88, "width": 2130, "height": 1012, "margin_reference": 2250},
        "default": {"page_code": 2, "active_record_waits": 1},
        "invalid": {"page_code": 6, "ignored_page_size_parameter": 99},
    }))
    landscape_letter = apply_orientation_via_10220(data, letter_page, 1)
    same_orientation = apply_orientation_via_10220(data, landscape_letter, 1)
    invalid_orientation = apply_orientation_via_10220(data, landscape_letter, 2)
    checks.append(assert_equal("0x10220 ESC &l#O swaps active extents and selects orientation margins", {
        "landscape": {
            key: landscape_letter[key]
            for key in (
                "orientation",
                "width",
                "height",
                "margin_reference",
                "active_width",
                "active_height",
                "vertical_offset_source",
                "negative_vertical_offset",
                "printable_extent",
                "top_offset",
                "portrait_landscape_threshold_6",
                "portrait_landscape_threshold_2",
                "portrait_landscape_threshold_1",
                "portrait_landscape_threshold_5",
                "pending_text_flushes",
                "page_finalizations",
            )
        },
        "same_orientation": same_orientation["ignored_orientation_parameter"],
        "invalid_orientation": invalid_orientation["ignored_orientation_parameter"],
    }, {
        "landscape": {
            "orientation": 1,
            "width": 3030,
            "height": 2025,
            "margin_reference": 2175,
            "active_width": 2025,
            "active_height": 3030,
            "vertical_offset_source": 50,
            "negative_vertical_offset": -50,
            "printable_extent": 2125,
            "top_offset": 100,
            "portrait_landscape_threshold_6": 2175,
            "portrait_landscape_threshold_2": 2550,
            "portrait_landscape_threshold_1": 2480,
            "portrait_landscape_threshold_5": 2550,
            "pending_text_flushes": 2,
            "page_finalizations": 2,
        },
        "same_orientation": 1,
        "invalid_orientation": 2,
    }))

    macro_id_state = assign_macro_id_via_e112(bytes.fromhex("81 59 ff 85 00 00"))
    checks.append(assert_equal("0xe112 stores absolute parsed macro id", {
        "current_macro_id": macro_id_state["current_macro_id"],
    }, {
        "current_macro_id": 123,
    }))
    macro_start = apply_macro_control_via_dd08(macro_id_state, 0, final_byte=0x78)
    macro_stop_empty = apply_macro_control_via_dd08(macro_start, 1)
    macro_start_upper = apply_macro_control_via_dd08(macro_id_state, 0, final_byte=0x58)
    macro_stop_upper_empty = apply_macro_control_via_dd08(macro_start_upper, 1)
    macro_records_after_stop = macro_stop_empty["records"]
    macro_upper_records_after_stop = macro_stop_upper_empty["records"]
    assert isinstance(macro_records_after_stop, list)
    assert isinstance(macro_upper_records_after_stop, list)
    checks.append(assert_equal("0xdd08 starts and stops empty macro definitions", {
        "lowercase_start": {
            "alternate_mode": macro_start["alternate_mode"],
            "payload": macro_start["records"][0]["payload"],
            "events": macro_start["events"],
        },
        "lowercase_stop": {
            "alternate_mode": macro_stop_empty["alternate_mode"],
            "macro_error": macro_stop_empty["macro_error"],
            "record0": macro_records_after_stop[0],
            "last_event": macro_stop_empty["events"][-1],
        },
        "uppercase_stop": {
            "record0": macro_upper_records_after_stop[0],
            "last_event": macro_stop_upper_empty["events"][-1],
        },
    }, {
        "lowercase_start": {
            "alternate_mode": 1,
            "payload": b"\x1b&f",
            "events": [{"kind": "macro-start", "status": 0, "index": 0, "auto_prefix": True}],
        },
        "lowercase_stop": {
            "alternate_mode": 0,
            "macro_error": 0,
            "record0": {"id": 0, "payload": b"", "permanent": False},
            "last_event": {"kind": "macro-stop-cleared-empty", "index": 0},
        },
        "uppercase_stop": {
            "record0": {"id": 0, "payload": b"", "permanent": False},
            "last_event": {"kind": "macro-stop-cleared-empty", "index": 0},
        },
    }))
    macro_with_payload = macro_state(
        current_macro_id=123,
        records=[macro_record(b"!\r", 123)] + [macro_record() for _ in range(31)],
    )
    macro_execute = apply_macro_control_via_dd08(macro_with_payload, 2)
    macro_call = apply_macro_control_via_dd08(macro_with_payload, 3)
    checks.append(assert_equal("0xdd08 execute and call push macro data-chain frames", {
        "execute": {
            "frames": macro_execute["data_chain_frames"],
            "host_gate_bit1": macro_execute["host_gate_bit1"],
            "data_chain_slot": macro_execute["data_chain_slot"],
        },
        "call": {
            "frames": macro_call["data_chain_frames"],
            "host_gate_bit1": macro_call["host_gate_bit1"],
            "data_chain_slot": macro_call["data_chain_slot"],
        },
    }, {
        "execute": {
            "frames": [{"payload": b"!\r", "byte_count": 2, "byte_8": 4, "byte_9": 2, "environment": "execute"}],
            "host_gate_bit1": 1,
            "data_chain_slot": 1,
        },
        "call": {
            "frames": [{"payload": b"!\r", "byte_count": 2, "byte_8": 4, "byte_9": 3, "environment": "call"}],
            "host_gate_bit1": 1,
            "data_chain_slot": 1,
        },
    }))
    macro_overlay = apply_macro_control_via_dd08(macro_with_payload, 4)
    macro_overlay_clear = apply_macro_control_via_dd08(macro_overlay, 5)
    macro_permanent = apply_macro_control_via_dd08(macro_with_payload, 10)
    macro_delete_temporary = apply_macro_control_via_dd08(macro_permanent, 7)
    macro_make_temporary = apply_macro_control_via_dd08(macro_permanent, 9)
    macro_delete_now_temporary = apply_macro_control_via_dd08(macro_make_temporary, 7)
    checks.append(assert_equal("0xdd08 overlay and temporary/permanent macro controls", {
        "overlay": {
            "parser_mode": macro_overlay["parser_mode"],
            "overlay_macro_id": macro_overlay["overlay_macro_id"],
        },
        "overlay_clear": {
            "parser_mode": macro_overlay_clear["parser_mode"],
        },
        "permanent_then_delete_temp": macro_delete_temporary["records"][0],
        "temporary_then_delete_temp": macro_delete_now_temporary["records"][0],
    }, {
        "overlay": {
            "parser_mode": 1,
            "overlay_macro_id": 123,
        },
        "overlay_clear": {
            "parser_mode": 0,
        },
        "permanent_then_delete_temp": {"id": 123, "payload": b"!\r", "permanent": True},
        "temporary_then_delete_temp": {"id": 0, "payload": b"", "permanent": False},
    }))

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
    cursor_stack_pushed = apply_cursor_push_pop_via_f75e(cursor_stack_state(
        cursor_x=pack12(12, 4),
        cursor_y=pack12(34, 5),
        vertical_offset_source=60,
    ), 0)
    checks.append(assert_equal("0xf75e ESC &f0S pushes cursor with vertical offset", {
        "stack_depth": cursor_stack_pushed["stack_depth"],
        "stack": cursor_stack_pushed["stack"],
        "events": cursor_stack_pushed["events"],
    }, {
        "stack_depth": 1,
        "stack": [{"x": pack12(12, 4), "stored_y": pack12(94, 5)}],
        "events": [{"kind": "cursor-push", "depth": 1, "entry": {"x": pack12(12, 4), "stored_y": pack12(94, 5)}}],
    }))
    cursor_stack_popped = apply_cursor_push_pop_via_f75e(cursor_stack_pushed, 1)
    checks.append(assert_equal("0xf75e ESC &f1S pops cursor and clears pending flags", {
        "cursor_x": cursor_stack_popped["cursor_x"],
        "cursor_y": cursor_stack_popped["cursor_y"],
        "stack_depth": cursor_stack_popped["stack_depth"],
        "right_limit_latch": cursor_stack_popped["right_limit_latch"],
        "pending_text": cursor_stack_popped["pending_text"],
        "last_event": cursor_stack_popped["events"][-1],
    }, {
        "cursor_x": pack12(12, 4),
        "cursor_y": pack12(34, 5),
        "stack_depth": 0,
        "right_limit_latch": 0,
        "pending_text": 0,
        "last_event": {
            "kind": "cursor-pop",
            "depth": 0,
            "entry": {"x": pack12(12, 4), "stored_y": pack12(94, 5)},
            "max_x": pack12(2024, 11),
            "max_y": pack12(3089, 11),
        },
    }))
    cursor_stack_clamped = apply_cursor_push_pop_via_f75e(cursor_stack_state(
        active_height=100,
        printable_extent=80,
        right_limit=pack12(80),
        pending_span_flush_enable=1,
        stack=[{"x": pack12(120), "stored_y": pack12(200)}],
    ), 1)
    cursor_stack_ignored = apply_cursor_push_pop_via_f75e(cursor_stack_state(stack=[{"x": pack12(index), "stored_y": pack12(index)} for index in range(20)]), 0)
    cursor_stack_empty_pop = apply_cursor_push_pop_via_f75e(cursor_stack_state(stack=[]), 1)
    checks.append(assert_equal("0xf75e cursor stack bounds and pop clamps to current extents", {
        "clamped": {
            "cursor_x": cursor_stack_clamped["cursor_x"],
            "cursor_y": cursor_stack_clamped["cursor_y"],
            "stack_depth": cursor_stack_clamped["stack_depth"],
            "span_flushes": cursor_stack_clamped["span_flushes"],
            "post_flushes": cursor_stack_clamped["post_flushes"],
            "last_event": cursor_stack_clamped["events"][-1],
        },
        "full_push": {
            "stack_depth": cursor_stack_ignored["stack_depth"],
            "last_event": cursor_stack_ignored["events"][-1],
        },
        "empty_pop": {
            "stack_depth": cursor_stack_empty_pop["stack_depth"],
            "last_event": cursor_stack_empty_pop["events"][-1],
        },
    }, {
        "clamped": {
            "cursor_x": pack12(99, 11),
            "cursor_y": pack12(79, 11),
            "stack_depth": 0,
            "span_flushes": 1,
            "post_flushes": 1,
            "last_event": {
                "kind": "cursor-pop",
                "depth": 0,
                "entry": {"x": pack12(120), "stored_y": pack12(200)},
                "max_x": pack12(99, 11),
                "max_y": pack12(79, 11),
            },
        },
        "full_push": {
            "stack_depth": 20,
            "last_event": {"kind": "cursor-push-ignored", "reason": "stack-full"},
        },
        "empty_pop": {
            "stack_depth": 0,
            "last_event": {"kind": "cursor-pop-ignored", "reason": "stack-empty"},
        },
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
    page_record_bucket_fixture: dict[str, object] = {"bucket_array": {}, "context_slots": [0x440946B4]}
    page_record_first = queue_text_source_to_page_record_via_12f2e(resources, page_record_bucket_fixture, text_source)
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
    page_record_second = queue_text_source_to_page_record_via_12f2e(resources, page_record_bucket_fixture, positioned_source)
    page_record_bucket_array = page_record_bucket_fixture["bucket_array"]
    assert isinstance(page_record_bucket_array, dict)
    page_record_chain = page_record_bucket_array[0]
    checks.append(assert_equal("0x1387c page-record bucket allocator reuses matching short object", {
        "first": {
            key: page_record_first[key]
            for key in ("path", "allocated", "chain_index", "count_before", "count_after", "bucket_index", "selector", "coord", "glyph")
        },
        "second": {
            key: page_record_second[key]
            for key in ("path", "allocated", "chain_index", "count_before", "count_after", "bucket_index", "selector", "coord", "glyph")
        },
        "chain_length": len(page_record_chain),
        "object_prefix": bytes(page_record_chain[0][:14]),
    }, {
        "first": {
            "path": "short-page-record",
            "allocated": True,
            "chain_index": 0,
            "count_before": 0,
            "count_after": 1,
            "bucket_index": 0,
            "selector": 0,
            "coord": 0x0000,
            "glyph": 0x20,
        },
        "second": {
            "path": "short-page-record",
            "allocated": False,
            "chain_index": 0,
            "count_before": 1,
            "count_after": 2,
            "bucket_index": 0,
            "selector": 0,
            "coord": 0x0001,
            "glyph": 0x20,
        },
        "chain_length": 1,
        "object_prefix": bytes.fromhex("00 00 00 00 00 00 00 02 20 00 00 20 00 01"),
    }))
    full_chain_object = bytearray(0x26)
    full_chain_object[4:6] = (0).to_bytes(2, "big")
    full_chain_object[6:8] = (10).to_bytes(2, "big")
    full_page_record: dict[str, object] = {"bucket_array": {0: [full_chain_object]}, "context_slots": [0x440946B4]}
    full_page_result = queue_text_source_to_page_record_via_12f2e(resources, full_page_record, text_source)
    full_bucket_array = full_page_record["bucket_array"]
    assert isinstance(full_bucket_array, dict)
    full_chain = full_bucket_array[0]
    checks.append(assert_equal("0x1387c page-record bucket allocator links new head when full", {
        "result": {
            key: full_page_result[key]
            for key in ("allocated", "chain_index", "count_before", "count_after", "bucket_index", "selector", "coord")
        },
        "chain_length": len(full_chain),
        "head_prefix": bytes(full_chain[0][:11]),
        "old_count": u16(full_chain[1], 6),
    }, {
        "result": {
            "allocated": True,
            "chain_index": 0,
            "count_before": 0,
            "count_after": 1,
            "bucket_index": 0,
            "selector": 0,
            "coord": 0,
        },
        "chain_length": 2,
        "head_prefix": bytes.fromhex("00 00 00 00 00 00 00 01 20 00 00"),
        "old_count": 10,
    }))
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

    selected_inline_context = 0x00000100
    selected_inline_memory = bytearray(0x300)
    selected_inline_record = selected_inline_context + 0x40 + 1 * 8
    selected_inline_bitmap_delta = 0x80
    selected_inline_bitmap = selected_inline_context + selected_inline_bitmap_delta
    selected_inline_memory[selected_inline_record:selected_inline_record + 8] = bytes.fromhex("02 03 04 00 00 00 00 80")
    selected_inline_memory[selected_inline_context + 0x40 + 2 * 8:selected_inline_context + 0x40 + 2 * 8 + 8] = bytes.fromhex("01 02 00 00 00 00 00 90")
    selected_inline_memory[selected_inline_bitmap:selected_inline_bitmap + 6] = bytes.fromhex("aa 55 f0 0f c3 3c")
    selected_inline_map = inline_map_via_14e24(selected_inline_memory, selected_inline_context)
    selected_inline_map_table = selected_inline_map["table"]
    assert isinstance(selected_inline_map_table, bytes)
    selected_inline_validity = selected_inline_map["validity"]
    assert isinstance(selected_inline_validity, list)
    checks.append(assert_equal("0x14e24-modeled inline/downloaded map entries", {
        "context": selected_inline_map["context"],
        "base": selected_inline_map["base"],
        "host_0x20": selected_inline_map_table[0x20],
        "host_0x21": selected_inline_map_table[0x21],
        "host_0x22": selected_inline_map_table[0x22],
        "glyph1_probe": {
            key: selected_inline_validity[1][key]
            for key in ("glyph", "record", "record_bytes", "bitmap", "valid", "reason")
        },
        "glyph2_probe": {
            key: selected_inline_validity[2][key]
            for key in ("glyph", "record", "record_bytes", "bitmap", "valid", "reason")
        },
    }, {
        "context": 0x00000100,
        "base": 0x00000100,
        "host_0x20": 0,
        "host_0x21": 1,
        "host_0x22": 0,
        "glyph1_probe": {
            "glyph": 1,
            "record": 0x00000148,
            "record_bytes": bytes.fromhex("02 03 04 00 00 00 00 80"),
            "bitmap": 0x00000180,
            "valid": True,
            "reason": "nonzero-fixed-record",
        },
        "glyph2_probe": {
            "glyph": 2,
            "record": 0x00000150,
            "record_bytes": bytes.fromhex("01 02 00 00 00 00 00 90"),
            "bitmap": 0x00000190,
            "valid": False,
            "reason": "zero-sentinel-bitmap-word",
        },
    }))
    selected_inline_source = build_inline_text_source_object_from_1393a(
        selected_inline_memory,
        selected_inline_context,
        selected_inline_map_table,
        0x21,
        x=0,
        y=0,
        context_slot=3,
    )
    checks.append(assert_equal("0x1393a-modeled selected inline source object fields", {
        key: selected_inline_source[key]
        for key in ("context", "host_char", "mapped", "glyph_entry", "glyph_width", "glyph_rows", "flag", "x", "y", "context_slot", "inline_record", "valid_record", "bitmap")
    }, {
        "context": 0x00000100,
        "host_char": 0x21,
        "mapped": 0x01,
        "glyph_entry": 0x00000148,
        "glyph_width": 0x02,
        "glyph_rows": 0x03,
        "flag": 0,
        "x": 0,
        "y": 0,
        "context_slot": 3,
        "inline_record": bytes.fromhex("02 03 04 00 00 00 00 80"),
        "valid_record": True,
        "bitmap": 0x00000180,
    }))
    selected_inline_positioned = position_unflagged_text_source_via_d3b2(
        selected_inline_source,
        bytes(selected_inline_source["inline_record"]),
        cursor_x=10,
        cursor_y=20,
        printable_offset=7,
        context_metric_flag=0,
        source_x_offset=5,
    )
    selected_inline_positioned_source = selected_inline_positioned["source"]
    assert isinstance(selected_inline_positioned_source, dict)
    selected_inline_bucket = queue_text_source_via_12f2e(selected_inline_memory, selected_inline_positioned_source)
    selected_inline_page_record: dict[str, object] = {"bucket_array": {}, "context_slots": [0, 0, 0, selected_inline_context]}
    selected_inline_page_result = queue_text_source_to_page_record_via_12f2e(selected_inline_memory, selected_inline_page_record, selected_inline_positioned_source)
    selected_inline_page_bucket_array = selected_inline_page_record["bucket_array"]
    assert isinstance(selected_inline_page_bucket_array, dict)
    selected_inline_page_object = bytes(selected_inline_page_bucket_array[1][0])
    selected_inline_rendered = render_compact_text_bucket_object(
        data,
        selected_inline_memory,
        (0, 0, 0, selected_inline_context),
        selected_inline_bucket["object"],
    )
    checks.append(assert_equal("selected inline source queues and renders through unflagged path", {
        "position": {
            "x": selected_inline_positioned_source["x"],
            "y": selected_inline_positioned_source["y"],
            "record0": selected_inline_positioned["record0"],
            "record1": selected_inline_positioned["record1"],
            "record2_signed": selected_inline_positioned["record2_signed"],
        },
        "bucket": {
            key: selected_inline_bucket[key]
            for key in ("path", "object", "bucket_index", "selector", "coord", "glyph", "rows", "width")
        },
        "page": {
            key: selected_inline_page_result[key]
            for key in ("path", "allocated", "chain_index", "count_before", "count_after", "bucket_index", "selector", "coord", "glyph")
        } | {
            "object_prefix": selected_inline_page_object[:11],
        },
        "render": {
            "selector": selected_inline_rendered["selector"],
            "context_slot": selected_inline_rendered["context_slot"],
            "compact_mode": selected_inline_rendered["compact_mode"],
            "payload": selected_inline_rendered["payload"],
            "rendered": selected_inline_rendered["rendered"],
            "rows": selected_inline_rendered["rows"],
        },
    }, {
        "position": {
            "x": 22,
            "y": 22,
            "record0": 0x02,
            "record1": 0x03,
            "record2_signed": 0x04,
        },
        "bucket": {
            "path": "short",
            "object": bytes.fromhex("00 00 00 00 00 03 00 01 01 66 01"),
            "bucket_index": 1,
            "selector": 0x0003,
            "coord": 0x6601,
            "glyph": 0x01,
            "rows": 3,
            "width": 2,
        },
        "page": {
            "path": "short-page-record",
            "allocated": True,
            "chain_index": 0,
            "count_before": 0,
            "count_after": 1,
            "bucket_index": 1,
            "selector": 0x0003,
            "coord": 0x6601,
            "glyph": 0x01,
            "object_prefix": bytes.fromhex("00 00 00 00 00 03 00 01 01 66 01"),
        },
        "render": {
            "selector": 0x0003,
            "context_slot": 3,
            "compact_mode": 0,
            "payload": bytes.fromhex("00 01 01 66 01"),
            "rendered": [{
                "glyph": 1,
                "coord": 0x6601,
                "dest_base": 0xC2,
                "x": 22,
                "y": 6,
                "a001": 0x16,
                "span": 2,
                "rows": 3,
                "width": 16,
                "helper": u32(data, 0x1F08E + 2 * 4),
            }],
            "rows": [
                "." * 38,
                "." * 38,
                "." * 38,
                "." * 38,
                "." * 38,
                "." * 38,
                "." * 22 + "#.#.#.#..#.#.#.#",
                "." * 22 + "####........####",
                "." * 22 + "##....##..####..",
            ],
        },
    }))

    font_linear_payload = font_payload_linear_copy_via_168dc(bytes.fromhex("aa 1a 58 bb cc"), byte_count=4, byte_budget=4)
    checks.append(assert_equal("0x168dc-modeled font payload linear copy handles 0x1a58", font_linear_payload, {
        "status": 1,
        "dest": bytes.fromhex("aa 00 bb cc"),
        "stream_pos": 5,
        "remaining": 0,
        "byte_budget": 0,
        "continuation": None,
        "control_hits": 1,
    }))
    font_linear_continuation = font_payload_linear_copy_via_168dc(bytes.fromhex("aa bb cc dd"), byte_count=4, byte_budget=2)
    checks.append(assert_equal("0x168dc-modeled font payload linear copy continuation state", font_linear_continuation, {
        "status": 2,
        "dest": bytes.fromhex("aa bb"),
        "stream_pos": 2,
        "remaining": 2,
        "byte_budget": 0,
        "continuation": {
            "flag": 1,
            "remaining": 2,
            "dest_offset": 2,
        },
        "control_hits": 0,
    }))
    font_split_payload = font_payload_split_plane_copy_via_16942(bytes.fromhex("a0 a1 b0 c0 c1 d0"), rows=2, prefix_span=2, byte_budget=6)
    checks.append(assert_equal("0x16942-modeled font payload split-plane copy layout", font_split_payload, {
        "status": 1,
        "prefix": bytes.fromhex("a0 a1 c0 c1"),
        "trailing": bytes.fromhex("b0 d0"),
        "stream_pos": 6,
        "byte_budget": 0,
        "continuation": None,
        "control_hits": 0,
        "phase": "done",
    }))
    font_split_continuation = font_payload_split_plane_copy_via_16942(bytes.fromhex("a0 a1 b0 c0 c1 d0"), rows=2, prefix_span=2, byte_budget=5)
    checks.append(assert_equal("0x16942-modeled font payload split-plane continuation state", font_split_continuation, {
        "status": 2,
        "prefix": bytes.fromhex("a0 a1 c0 c1"),
        "trailing": bytes.fromhex("b0"),
        "stream_pos": 5,
        "byte_budget": 0,
        "continuation": {
            "flag": 1,
            "prefix_remaining": -1,
            "row_remaining": 0,
            "prefix_offset": 4,
            "trailing_offset": 1,
        },
        "control_hits": 0,
        "phase": "trailing",
    }))
    font_split_control = font_payload_split_plane_copy_via_16942(bytes.fromhex("a0 1a 58 b0"), rows=1, prefix_span=2, byte_budget=3)
    checks.append(assert_equal("0x16942-modeled font payload split-plane copy handles 0x1a58", font_split_control, {
        "status": 1,
        "prefix": bytes.fromhex("a0 00"),
        "trailing": bytes.fromhex("b0"),
        "stream_pos": 4,
        "byte_budget": 0,
        "continuation": None,
        "control_hits": 1,
        "phase": "done",
    }))

    font_records = [
        {"id": 0x1234, "flags": 0xE0, "payload": 0x123456},
        {"id": 0x0000, "flags": 0x00, "payload": 0x000000},
        {"id": 0x2222, "flags": 0x00, "payload": 0x333333},
    ]
    font_scan_existing = font_resource_record_scan_via_172c0(font_records, 0x1234)
    font_scan_free = font_resource_record_scan_via_172c0(font_records, 0x7777)
    font_scan_full = font_resource_record_scan_via_172c0([
        {"id": 0x1111, "flags": 0x00, "payload": 0x111111},
        {"id": 0x2222, "flags": 0x00, "payload": 0x222222},
    ], 0x7777)
    checks.append(assert_equal("0x172c0-modeled font resource record scan statuses", {
        "existing": {key: font_scan_existing[key] for key in ("status", "index", "address", "record")},
        "free": {key: font_scan_free[key] for key in ("status", "index", "address", "record")},
        "full": {key: font_scan_full[key] for key in ("status", "index", "address", "record")},
    }, {
        "existing": {
            "status": 0,
            "index": 0,
            "address": 0x782640,
            "record": {"id": 0x1234, "flags": 0xE0, "payload": 0x123456},
        },
        "free": {
            "status": 1,
            "index": 1,
            "address": 0x78264A,
            "record": {"id": 0x0000, "flags": 0x00, "payload": 0x000000},
        },
        "full": {
            "status": 2,
            "index": None,
            "address": None,
            "record": None,
        },
    }))

    font_replace = downloaded_font_object_add_bookkeeping_via_16c14(
        font_records,
        current_id=0x1234,
        new_payload=0x456789,
        byte20=1,
        byte0c=2,
        counters={"0x78278e": 5, "0x78278a": 11, "0x782782": 7},
        cursors={"0x7827ac": 0x20, "0x7827b0": 0x30, "0x7827b4": 0x40},
        continuation={
            "flag": 1,
            "payload": 0x123456,
            "word_0x7827c8": 0x55,
            "dest": 0x111111,
            "trailing_dest": 0x222222,
            "remaining": 3,
            "d4_counter": 4,
            "d3_counter": 5,
        },
        initial_candidate_flags=0x30000088,
    )
    checks.append(assert_equal("0x16c14-modeled downloaded font replacement bookkeeping", {
        "status": font_replace["status"],
        "record_index": font_replace["record_index"],
        "record": font_replace["records"][0],
        "candidate_flags": font_replace["candidate_flags"],
        "counter_branch": font_replace["counter_branch"],
        "counters": font_replace["counters"],
        "cursors": font_replace["cursors"],
        "replacement": font_replace["replacement"],
        "continuation": font_replace["continuation"],
    }, {
        "status": 0,
        "record_index": 0,
        "record": {"id": 0x1234, "flags": 0x00, "payload": 0x456789},
        "candidate_flags": 0x44,
        "counter_branch": "byte20-one",
        "counters": {
            "0x78278e": 6,
            "0x782790": 1,
            "0x782796": 1,
            "0x782798": 0,
            "0x78279e": 0,
            "0x78278a": 12,
            "0x782782": 8,
        },
        "cursors": {
            "0x7827ac": 0x24,
            "0x7827b0": 0x34,
            "0x7827b4": 0x44,
        },
        "replacement": {
            "record_index": 0,
            "released_payload": 0x123456,
            "release_called": True,
            "continuation_cleared": True,
        },
        "continuation": {
            "flag": 0,
            "payload": 0,
            "word_0x7827c8": 0,
            "dest": 0,
            "trailing_dest": 0,
            "remaining": 0,
            "d4_counter": 0,
            "d3_counter": 0,
        },
    }))

    font_insert = downloaded_font_object_add_bookkeeping_via_16c14(
        font_records,
        current_id=0x7777,
        new_payload=0x111111,
        byte20=0,
        byte0c=1,
        initial_candidate_flags=0x3000008C,
    )
    checks.append(assert_equal("0x16c14-modeled downloaded font free-slot bookkeeping", {
        "status": font_insert["status"],
        "record_index": font_insert["record_index"],
        "record": font_insert["records"][1],
        "candidate_flags": font_insert["candidate_flags"],
        "counter_branch": font_insert["counter_branch"],
        "counters": font_insert["counters"],
        "cursors": font_insert["cursors"],
        "replacement": font_insert["replacement"],
    }, {
        "status": 1,
        "record_index": 1,
        "record": {"id": 0x7777, "flags": 0x00, "payload": 0x111111},
        "candidate_flags": 0x40,
        "counter_branch": "byte20-other",
        "counters": {
            "0x78278e": 1,
            "0x782790": 0,
            "0x782796": 0,
            "0x782798": 1,
            "0x78279e": 1,
            "0x78278a": 1,
            "0x782782": 1,
        },
        "cursors": {
            "0x7827ac": 0,
            "0x7827b0": 0,
            "0x7827b4": 0,
        },
        "replacement": None,
    }))

    font_no_slot = downloaded_font_object_add_bookkeeping_via_16c14(
        [
            {"id": 0x1111, "flags": 0xE0, "payload": 0x111111},
            {"id": 0x2222, "flags": 0x00, "payload": 0x222222},
        ],
        current_id=0x7777,
        new_payload=0x333333,
        byte20=1,
        byte0c=2,
    )
    checks.append(assert_equal("0x16c14-modeled downloaded font no-slot budget skip", {
        "status": font_no_slot["status"],
        "budget_action": font_no_slot["budget_action"],
        "record_index": font_no_slot["record_index"],
        "records": font_no_slot["records"],
        "counters": font_no_slot["counters"],
        "candidate_flags": font_no_slot["candidate_flags"],
    }, {
        "status": 2,
        "budget_action": "skip-no-record-slot",
        "record_index": None,
        "records": [
            {"id": 0x1111, "flags": 0xE0, "payload": 0x111111},
            {"id": 0x2222, "flags": 0x00, "payload": 0x222222},
        ],
        "counters": {
            "0x78278e": 0,
            "0x782790": 0,
            "0x782796": 0,
            "0x782798": 0,
            "0x78279e": 0,
            "0x78278a": 0,
            "0x782782": 0,
        },
        "candidate_flags": None,
    }))

    font_payload_lookup_hit = font_payload_record_lookup_via_170be(font_records, 0x99123456)
    font_payload_lookup_miss = font_payload_record_lookup_via_170be(font_records, 0x00AAAAAA)
    checks.append(assert_equal("0x170be-modeled font payload record lookup", {
        "hit": {
            key: font_payload_lookup_hit[key]
            for key in ("status", "index", "address", "record", "masked_payload")
        },
        "miss": {
            key: font_payload_lookup_miss[key]
            for key in ("status", "index", "address", "record", "masked_payload")
        },
    }, {
        "hit": {
            "status": 0x1234,
            "index": 0,
            "address": 0x782640,
            "record": {"id": 0x1234, "flags": 0xE0, "payload": 0x123456},
            "masked_payload": 0x123456,
        },
        "miss": {
            "status": -1,
            "index": None,
            "address": None,
            "record": None,
            "masked_payload": 0xAAAAAA,
        },
    }))

    font_mark = mark_current_font_record_via_17108(
        [
            {"id": 0x1234, "flags": 0x00, "payload": 0x123456},
            {"id": 0x5678, "flags": 0x40, "payload": 0x567890},
        ],
        0x1234,
        {"0x782782": 7, "0x782786": 2},
    )
    font_mark_already = mark_current_font_record_via_17108(
        [
            {"id": 0x1234, "flags": 0x40, "payload": 0x123456},
        ],
        0x1234,
        {"0x782782": 7, "0x782786": 2},
    )
    font_mark_missing = mark_current_font_record_via_17108(
        [
            {"id": 0x1234, "flags": 0x00, "payload": 0x123456},
            {"id": 0x0000, "flags": 0x00, "payload": 0x000000},
        ],
        0x9999,
        {"0x782782": 7, "0x782786": 2},
    )
    checks.append(assert_equal("0x17108-modeled current font record mark/count transfer", {
        "marked": {
            "changed": font_mark["changed"],
            "record": font_mark["records"][0],
            "counters": font_mark["counters"],
        },
        "already": {
            "changed": font_mark_already["changed"],
            "record": font_mark_already["records"][0],
            "counters": font_mark_already["counters"],
        },
        "missing": {
            "changed": font_mark_missing["changed"],
            "counters": font_mark_missing["counters"],
            "scan_status": font_mark_missing["scan"]["status"],
        },
    }, {
        "marked": {
            "changed": True,
            "record": {"id": 0x1234, "flags": 0x40, "payload": 0x123456},
            "counters": {"0x782782": 6, "0x782786": 3},
        },
        "already": {
            "changed": False,
            "record": {"id": 0x1234, "flags": 0x40, "payload": 0x123456},
            "counters": {"0x782782": 7, "0x782786": 2},
        },
        "missing": {
            "changed": False,
            "counters": {"0x782782": 7, "0x782786": 2},
            "scan_status": 1,
        },
    }))

    font_unmark = unmark_current_font_record_via_17150(
        [
            {"id": 0x1234, "flags": 0x40, "payload": 0x123456},
            {"id": 0x5678, "flags": 0x00, "payload": 0x567890},
        ],
        0x1234,
        {"0x782782": 6, "0x782786": 3},
    )
    font_unmark_already = unmark_current_font_record_via_17150(
        [
            {"id": 0x1234, "flags": 0x00, "payload": 0x123456},
        ],
        0x1234,
        {"0x782782": 6, "0x782786": 3},
    )
    checks.append(assert_equal("0x17150-modeled current font record unmark/count transfer", {
        "unmarked": {
            "changed": font_unmark["changed"],
            "record": font_unmark["records"][0],
            "counters": font_unmark["counters"],
        },
        "already": {
            "changed": font_unmark_already["changed"],
            "record": font_unmark_already["records"][0],
            "counters": font_unmark_already["counters"],
        },
    }, {
        "unmarked": {
            "changed": True,
            "record": {"id": 0x1234, "flags": 0x00, "payload": 0x123456},
            "counters": {"0x782782": 7, "0x782786": 2},
        },
        "already": {
            "changed": False,
            "record": {"id": 0x1234, "flags": 0x00, "payload": 0x123456},
            "counters": {"0x782782": 6, "0x782786": 3},
        },
    }))

    font_id_assign = [assign_font_id_via_15a56(value) for value in (0, 17, -17, -0x8000, 0x8001)]
    checks.append(assert_equal("0x15a56-modeled assign font ID normalization", font_id_assign, [
        0,
        17,
        17,
        0x7FFF,
        0x7FFF,
    ]))

    font_control_mark = font_control_dispatch_via_16df6(
        data,
        [{"id": 0x1234, "flags": 0x00, "payload": 0x123456}],
        current_id=0x1234,
        value=5,
        parser_mode=2,
        counters={"0x782782": 7, "0x782786": 2},
    )
    font_control_unmark = font_control_dispatch_via_16df6(
        data,
        [{"id": 0x1234, "flags": 0x40, "payload": 0x123456}],
        current_id=0x1234,
        value=4,
        parser_mode=2,
        counters={"0x782782": 6, "0x782786": 3},
    )
    font_control_suppressed = font_control_dispatch_via_16df6(
        data,
        [{"id": 0x1234, "flags": 0x40, "payload": 0x123456}],
        current_id=0x1234,
        value=2,
        parser_mode=2,
        counters={"0x782782": 6, "0x782786": 3},
    )
    font_control_noop = font_control_dispatch_via_16df6(
        data,
        [{"id": 0x1234, "flags": 0x40, "payload": 0x123456}],
        current_id=0x1234,
        value=99,
        parser_mode=0,
        counters={"0x782782": 6, "0x782786": 3},
    )
    checks.append(assert_equal("0x16df6-modeled font-control dispatch mark/unmark and suppression", {
        "mark": {
            "target": font_control_mark["target"],
            "action": font_control_mark["action"],
            "suppressed": font_control_mark["suppressed"],
            "result": {
                "changed": font_control_mark["result"]["changed"],
                "record": font_control_mark["result"]["records"][0],
                "counters": font_control_mark["result"]["counters"],
            },
        },
        "unmark": {
            "target": font_control_unmark["target"],
            "action": font_control_unmark["action"],
            "suppressed": font_control_unmark["suppressed"],
            "result": {
                "changed": font_control_unmark["result"]["changed"],
                "record": font_control_unmark["result"]["records"][0],
                "counters": font_control_unmark["result"]["counters"],
            },
        },
        "suppressed": {
            "target": font_control_suppressed["target"],
            "action": font_control_suppressed["action"],
            "suppressed": font_control_suppressed["suppressed"],
            "record": font_control_suppressed["result"]["records"][0],
        },
        "noop": {
            "target": font_control_noop["target"],
            "action": font_control_noop["action"],
            "suppressed": font_control_noop["suppressed"],
            "record": font_control_noop["result"]["records"][0],
        },
    }, {
        "mark": {
            "target": 0x16E86,
            "action": "mark-current",
            "suppressed": False,
            "result": {
                "changed": True,
                "record": {"id": 0x1234, "flags": 0x40, "payload": 0x123456},
                "counters": {"0x782782": 6, "0x782786": 3},
            },
        },
        "unmark": {
            "target": 0x16E7E,
            "action": "unmark-current",
            "suppressed": False,
            "result": {
                "changed": True,
                "record": {"id": 0x1234, "flags": 0x00, "payload": 0x123456},
                "counters": {"0x782782": 7, "0x782786": 2},
            },
        },
        "suppressed": {
            "target": 0x16E4C,
            "action": "suppressed",
            "suppressed": True,
            "record": {"id": 0x1234, "flags": 0x40, "payload": 0x123456},
        },
        "noop": {
            "target": 0x16EAA,
            "action": "noop",
            "suppressed": False,
            "record": {"id": 0x1234, "flags": 0x40, "payload": 0x123456},
        },
    }))

    font_validate_ok = font_resource_validate_via_16fae([1] * 32, bytes(range(0x30, 0x50)), 20)
    font_validate_fail = font_resource_validate_via_16fae([1] * 7 + [0] + [1] * 24, bytes(range(0x30, 0x50)), 20)
    font_validate_zero_budget = font_resource_validate_via_16fae([1] * 32, bytes(range(0x30, 0x50)), 0)
    checks.append(assert_equal("0x16fae-modeled font resource validation and symbol-byte staging", {
        "ok": {
            "status": font_validate_ok["status"],
            "visited": len(font_validate_ok["visited"]),
            "first_table_address": font_validate_ok["visited"][0]["table_address"],
            "last_d5": font_validate_ok["visited"][-1]["d5"],
            "symbol_count": font_validate_ok["symbol_count"],
            "symbol_bytes": font_validate_ok["symbol_bytes"],
            "budget": font_validate_ok["budget"],
        },
        "fail": {
            "status": font_validate_fail["status"],
            "failed_index": font_validate_fail["failed_index"],
            "failed_d5": font_validate_fail["failed_d5"],
            "visited": len(font_validate_fail["visited"]),
            "symbol_count": font_validate_fail["symbol_count"],
            "budget": font_validate_fail["budget"],
        },
        "zero_budget": {
            "status": font_validate_zero_budget["status"],
            "visited": len(font_validate_zero_budget["visited"]),
            "symbol_count": font_validate_zero_budget["symbol_count"],
            "symbol_bytes": font_validate_zero_budget["symbol_bytes"],
            "budget": font_validate_zero_budget["budget"],
        },
    }, {
        "ok": {
            "status": 1,
            "visited": 32,
            "first_table_address": 0x16EAE,
            "last_d5": 32,
            "symbol_count": 16,
            "symbol_bytes": bytes(range(0x30, 0x40)),
            "budget": 4,
        },
        "fail": {
            "status": 0,
            "failed_index": 7,
            "failed_d5": 8,
            "visited": 8,
            "symbol_count": 0,
            "budget": 20,
        },
        "zero_budget": {
            "status": 1,
            "visited": 32,
            "symbol_count": 0,
            "symbol_bytes": b"",
            "budget": 0,
        },
    }))

    font_validate_stream = bytes.fromhex(
        "00 01 02 00 ff ff 00 04 00 06 00 09 01 05 12 34"
        " 50 00 30 00 00 20 99 ab f0 cd 01 02 03 04 05 06"
        " 00 07 00 08 00 00 00 09 ee f0 00 0a 00 0b 00 0c"
        " 41 42 43 44 45 46 47 48 49 4a 4b 4c 4d 4e 4f 50"
    )
    font_validate_table = font_resource_validate_table_stream_via_16fae(bytearray(0x40), font_validate_stream, 80)
    font_validate_table_staging = font_validate_table["staging"]
    assert isinstance(font_validate_table_staging, bytes)
    checks.append(assert_equal("0x16fae table-driven validation predicates populate staged header fields", {
        "status": font_validate_table["status"],
        "visited": len(font_validate_table["visited"]),
        "bytes_consumed": font_validate_table["bytes_consumed"],
        "budget": font_validate_table["budget"],
        "payload_units": font_validate_table["payload_units"],
        "staging_fields": {
            "byte0c": font_validate_table_staging[0x0C],
            "word0e": u16(font_validate_table_staging, 0x0E),
            "word10": u16(font_validate_table_staging, 0x10),
            "word12": u16(font_validate_table_staging, 0x12),
            "word14": u16(font_validate_table_staging, 0x14),
            "word16": u16(font_validate_table_staging, 0x16),
            "word18": u16(font_validate_table_staging, 0x18),
            "word1a": u16(font_validate_table_staging, 0x1A),
            "byte20": font_validate_table_staging[0x20],
            "byte21": font_validate_table_staging[0x21],
            "word22": u16(font_validate_table_staging, 0x22),
            "word24": u16(font_validate_table_staging, 0x24),
            "byte26": font_validate_table_staging[0x26],
            "word28": u16(font_validate_table_staging, 0x28),
            "byte2a": font_validate_table_staging[0x2A],
            "word2c": u16(font_validate_table_staging, 0x2C),
            "byte2f": font_validate_table_staging[0x2F],
            "byte30": font_validate_table_staging[0x30],
            "byte31": font_validate_table_staging[0x31],
        },
        "symbols": font_validate_table["symbol_bytes"],
    }, {
        "status": 1,
        "visited": 32,
        "bytes_consumed": 64,
        "budget": 16,
        "payload_units": 0x80,
        "staging_fields": {
            "byte0c": 0,
            "word0e": 0,
            "word10": 0x007F,
            "word12": 0x0006,
            "word14": 0x0009,
            "word16": 0x0004,
            "word18": 0x0004,
            "word1a": 0x0005,
            "byte20": 1,
            "byte21": 1,
            "word22": 0x1234,
            "word24": 0x41A0,
            "byte26": 0,
            "word28": 0x2AAA,
            "byte2a": 0x80,
            "word2c": 0x0020,
            "byte2f": 0xAB,
            "byte30": 0xF9,
            "byte31": 0xCD,
        },
        "symbols": bytes.fromhex("41 42 43 44 45 46 47 48 49 4a 4b 4c 4d 4e 4f 50"),
    }))

    font_staging = bytearray(0x40)
    font_staging[0:4] = (0xDEADBEEF).to_bytes(4, "big")
    font_staging[4:8] = (0x01020304).to_bytes(4, "big")
    font_staging[0x0C] = 0x99
    for offset, value in (
        (0x0E, 0x1111),
        (0x10, 0x2222),
        (0x12, 0x3333),
        (0x14, 0x4444),
        (0x16, 0x5555),
        (0x18, 0x6666),
        (0x1A, 0x7777),
        (0x22, 0x8888),
        (0x24, 0x9999),
        (0x28, 0xAAAA),
        (0x2C, 0xBBBB),
    ):
        font_staging[offset:offset + 2] = value.to_bytes(2, "big")
    for offset, value in ((0x20, 0xC0), (0x21, 0xC1), (0x26, 0xC6), (0x2A, 0xCA), (0x2F, 0xCF), (0x30, 0xD0), (0x31, 0xD1)):
        font_staging[offset] = value
    font_setup_type_0 = font_resource_setup_type_via_17362(font_staging, 0)
    font_setup_type_2 = font_resource_setup_type_via_17362(font_staging, 2)
    font_setup_type_bad = font_resource_setup_type_via_17362(font_staging, 3)
    checks.append(assert_equal("0x17362-modeled font resource setup type", {
        "type0": {
            "status": font_setup_type_0["status"],
            "byte0c": font_setup_type_0["staging"][0x0C],
            "payload_units": font_setup_type_0["payload_units"],
        },
        "type2": {
            "status": font_setup_type_2["status"],
            "byte0c": font_setup_type_2["staging"][0x0C],
            "payload_units": font_setup_type_2["payload_units"],
        },
        "bad": {
            "status": font_setup_type_bad["status"],
            "byte0c": font_setup_type_bad["staging"][0x0C],
            "payload_units": font_setup_type_bad["payload_units"],
        },
    }, {
        "type0": {
            "status": 1,
            "byte0c": 0,
            "payload_units": 0x80,
        },
        "type2": {
            "status": 1,
            "byte0c": 2,
            "payload_units": 0x100,
        },
        "bad": {
            "status": 0,
            "byte0c": 0x99,
            "payload_units": 0x100,
        },
    }))

    font_allocated = font_resource_find_allocate_via_17026(font_setup_type_0["staging"], int(font_setup_type_0["payload_units"]), True, bytes.fromhex("41 42 43"))
    font_payload_info = font_allocated["payload"]
    assert isinstance(font_payload_info, dict)
    font_payload_bytes = font_payload_info["payload"]
    assert isinstance(font_payload_bytes, bytes)
    font_alloc_failed = font_resource_find_allocate_via_17026(font_setup_type_0["staging"], int(font_setup_type_0["payload_units"]), False)
    checks.append(assert_equal("0x17026/0x1719c-modeled font resource allocation and header initialization", {
        "allocation": {
            "status": font_allocated["status"],
            "allocation_size": font_allocated["allocation_size"],
            "staging_type": int.from_bytes(font_allocated["staging"][0:4], "big"),
            "staging_size": int.from_bytes(font_allocated["staging"][4:8], "big"),
        },
        "payload_fields": {
            "long0": int.from_bytes(font_payload_bytes[0:4], "big"),
            "long4": int.from_bytes(font_payload_bytes[4:8], "big"),
            "word8": u16(font_payload_bytes, 8),
            "byte0c": font_payload_bytes[0x0C],
            "word0e": u16(font_payload_bytes, 0x0E),
            "word10": u16(font_payload_bytes, 0x10),
            "byte20": font_payload_bytes[0x20],
            "byte21": font_payload_bytes[0x21],
            "word22": u16(font_payload_bytes, 0x22),
            "byte2f": font_payload_bytes[0x2F],
            "byte30": font_payload_bytes[0x30],
            "byte31": font_payload_bytes[0x31],
            "extra_offset": int.from_bytes(font_payload_bytes[0x38:0x3C], "big"),
            "extra_count": u16(font_payload_bytes, int(font_payload_info["extra_offset"])),
            "extra_bytes": font_payload_bytes[int(font_payload_info["extra_offset"]) + 2:int(font_payload_info["extra_offset"]) + 5],
        },
        "invalid": font_alloc_failed,
    }, {
        "allocation": {
            "status": 1,
            "allocation_size": 10,
            "staging_type": 0x15,
            "staging_size": 10,
        },
        "payload_fields": {
            "long0": 0x15,
            "long4": 10,
            "word8": 0x004A,
            "byte0c": 0,
            "word0e": 0x1111,
            "word10": 0x2222,
            "byte20": 0xC0,
            "byte21": 0xC1,
            "word22": 0x8888,
            "byte2f": 0xCF,
            "byte30": 0xD0,
            "byte31": 0xD1,
            "extra_offset": 0x024A,
            "extra_count": 3,
            "extra_bytes": bytes.fromhex("41 42 43"),
        },
        "invalid": {
            "status": 0,
            "allocation_size": 0,
            "staging": bytes(font_setup_type_0["staging"]),
            "payload": None,
        },
    }))

    table_payload_allocated = font_resource_find_allocate_via_17026(
        font_validate_table_staging,
        int(font_validate_table["payload_units"]),
        True,
        font_validate_table["symbol_bytes"],
    )
    table_payload_info = table_payload_allocated["payload"]
    assert isinstance(table_payload_info, dict)
    table_payload_bytes = table_payload_info["payload"]
    assert isinstance(table_payload_bytes, bytes)
    table_payload_memory = bytearray(table_payload_bytes)
    table_payload_record = 0x40 + 1 * 8
    table_payload_bitmap = 0x00A0
    table_payload_memory[table_payload_record:table_payload_record + 8] = bytes.fromhex("02 03 04 00 00 00 00 a0")
    table_payload_memory[table_payload_bitmap:table_payload_bitmap + 6] = bytes.fromhex("aa 55 f0 0f c3 3c")
    table_payload_map = inline_map_via_14e24(table_payload_memory, 0)
    table_payload_map_table = table_payload_map["table"]
    assert isinstance(table_payload_map_table, bytes)
    table_payload_source = build_inline_text_source_object_from_1393a(
        table_payload_memory,
        0,
        table_payload_map_table,
        0x21,
        x=0,
        y=0,
        context_slot=3,
    )
    table_payload_positioned = position_unflagged_text_source_via_d3b2(
        table_payload_source,
        bytes(table_payload_source["inline_record"]),
        cursor_x=10,
        cursor_y=20,
        printable_offset=7,
        context_metric_flag=0,
        source_x_offset=5,
    )
    table_payload_positioned_source = table_payload_positioned["source"]
    assert isinstance(table_payload_positioned_source, dict)
    table_payload_bucket = queue_text_source_via_12f2e(table_payload_memory, table_payload_positioned_source)
    table_payload_rendered = render_compact_text_bucket_object(
        data,
        table_payload_memory,
        (0, 0, 0, 0),
        table_payload_bucket["object"],
    )
    checks.append(assert_equal("0x16fae/0x1719c-backed inline payload maps, queues, and renders one fixed record", {
        "allocation": {
            "status": table_payload_allocated["status"],
            "allocation_size": table_payload_allocated["allocation_size"],
            "payload_units": font_validate_table["payload_units"],
            "header_word8": u16(table_payload_memory, 8),
            "byte0c": table_payload_memory[0x0C],
            "word10": u16(table_payload_memory, 0x10),
            "word12": u16(table_payload_memory, 0x12),
            "word14": u16(table_payload_memory, 0x14),
            "word16": u16(table_payload_memory, 0x16),
            "word18": u16(table_payload_memory, 0x18),
            "extra_offset": int.from_bytes(table_payload_memory[0x38:0x3C], "big"),
            "extra_count": u16(table_payload_memory, int(table_payload_info["extra_offset"])),
        },
        "map_source": {
            "host_0x21": table_payload_map_table[0x21],
            "glyph_entry": table_payload_source["glyph_entry"],
            "inline_record": table_payload_source["inline_record"],
            "valid_record": table_payload_source["valid_record"],
            "bitmap": table_payload_source["bitmap"],
        },
        "bucket": {
            key: table_payload_bucket[key]
            for key in ("path", "object", "bucket_index", "selector", "coord", "glyph", "rows", "width")
        },
        "render": {
            "selector": table_payload_rendered["selector"],
            "context_slot": table_payload_rendered["context_slot"],
            "payload": table_payload_rendered["payload"],
            "rows": table_payload_rendered["rows"],
        },
    }, {
        "allocation": {
            "status": 1,
            "allocation_size": 10,
            "payload_units": 0x80,
            "header_word8": 0x004A,
            "byte0c": 0,
            "word10": 0x007F,
            "word12": 0x0006,
            "word14": 0x0009,
            "word16": 0x0004,
            "word18": 0x0004,
            "extra_offset": 0x024A,
            "extra_count": 16,
        },
        "map_source": {
            "host_0x21": 1,
            "glyph_entry": 0x00000048,
            "inline_record": bytes.fromhex("02 03 04 00 00 00 00 a0"),
            "valid_record": True,
            "bitmap": 0x000000A0,
        },
        "bucket": {
            "path": "short",
            "object": bytes.fromhex("00 00 00 00 00 03 00 01 01 66 01"),
            "bucket_index": 1,
            "selector": 0x0003,
            "coord": 0x6601,
            "glyph": 0x01,
            "rows": 3,
            "width": 2,
        },
        "render": {
            "selector": 0x0003,
            "context_slot": 3,
            "payload": bytes.fromhex("00 01 01 66 01"),
            "rows": [
                "." * 38,
                "." * 38,
                "." * 38,
                "." * 38,
                "." * 38,
                "." * 38,
                "." * 22 + "#.#.#.#..#.#.#.#",
                "." * 22 + "####........####",
                "." * 22 + "##....##..####..",
            ],
        },
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
    unflagged_positioned_source = unflagged_fixture["source"]
    assert isinstance(unflagged_positioned_source, dict)
    unflagged_short_source = dict(unflagged_positioned_source)
    unflagged_short_source["inline_record"] = inline_record
    unflagged_short_bucket = queue_text_source_via_12f2e(resources, unflagged_short_source)
    checks.append(assert_equal("0x12f2e-modeled unflagged short bucket object fields", {key: unflagged_short_bucket[key] for key in ("path", "object", "bucket_index", "selector", "coord", "glyph", "rows", "width")}, {
        "path": "short",
        "object": bytes.fromhex("00 00 00 00 00 03 00 01 01 66 01"),
        "bucket_index": 1,
        "selector": 0x0003,
        "coord": 0x6601,
        "glyph": 0x01,
        "rows": 3,
        "width": 2,
    }))
    unflagged_page_record: dict[str, object] = {"bucket_array": {}, "context_slots": [0, 0, 0, 0]}
    unflagged_page_result = queue_text_source_to_page_record_via_12f2e(resources, unflagged_page_record, unflagged_short_source)
    unflagged_page_bucket_array = unflagged_page_record["bucket_array"]
    assert isinstance(unflagged_page_bucket_array, dict)
    unflagged_page_object = bytes(unflagged_page_bucket_array[1][0])
    checks.append(assert_equal("0x1387c page-record unflagged short bucket object", {
        key: unflagged_page_result[key]
        for key in ("path", "allocated", "chain_index", "count_before", "count_after", "bucket_index", "selector", "coord", "glyph", "rows", "width", "capacity", "object_size")
    } | {
        "object_prefix": unflagged_page_object[:11],
    }, {
        "path": "short-page-record",
        "allocated": True,
        "chain_index": 0,
        "count_before": 0,
        "count_after": 1,
        "bucket_index": 1,
        "selector": 0x0003,
        "coord": 0x6601,
        "glyph": 0x01,
        "rows": 3,
        "width": 2,
        "capacity": 0x0A,
        "object_size": 0x26,
        "object_prefix": bytes.fromhex("00 00 00 00 00 03 00 01 01 66 01"),
    }))
    unflagged_wide_source = dict(unflagged_positioned_source)
    unflagged_wide_source["inline_record"] = bytes.fromhex("11 03 04")
    unflagged_wide_bucket = queue_text_source_via_12f2e(resources, unflagged_wide_source)
    checks.append(assert_equal("0x12f2e-modeled unflagged width byte selects compact mode bit", {key: unflagged_wide_bucket[key] for key in ("path", "object", "bucket_index", "selector", "coord", "glyph", "rows", "width")}, {
        "path": "short",
        "object": bytes.fromhex("00 00 00 00 10 03 00 01 01 66 01"),
        "bucket_index": 1,
        "selector": 0x1003,
        "coord": 0x6601,
        "glyph": 0x01,
        "rows": 3,
        "width": 0x11,
    }))
    wide_inline_render_resources = bytearray(0x300)
    wide_inline_context = 0x00000100
    wide_inline_record_offset = wide_inline_context + 0x40 + 1 * 8
    wide_inline_bitmap_delta = 0x80
    wide_inline_bitmap = wide_inline_context + wide_inline_bitmap_delta
    wide_inline_render_resources[wide_inline_record_offset] = 0x11
    wide_inline_render_resources[wide_inline_record_offset + 1] = 0x03
    wide_inline_render_resources[wide_inline_record_offset + 4:wide_inline_record_offset + 8] = wide_inline_bitmap_delta.to_bytes(4, "big")
    wide_inline_render_resources[wide_inline_bitmap:wide_inline_bitmap + 0x30] = (b"\xff" * 0x10) + (b"\x00" * 0x10) + (b"\xaa" * 0x10)
    wide_inline_render_resources[wide_inline_bitmap + 0x30:wide_inline_bitmap + 0x33] = bytes.fromhex("ff 00 55")
    unflagged_wide_rendered = render_compact_text_bucket_object(
        data,
        wide_inline_render_resources,
        (0, 0, 0, wide_inline_context),
        unflagged_wide_bucket["object"],
    )
    checks.append(assert_equal("0x1f0d2 renders wide inline compact payload row", {
        "selector": unflagged_wide_rendered["selector"],
        "context_slot": unflagged_wide_rendered["context_slot"],
        "compact_mode": unflagged_wide_rendered["compact_mode"],
        "payload": unflagged_wide_rendered["payload"],
        "count": unflagged_wide_rendered["count"],
        "rendered": unflagged_wide_rendered["rendered"],
        "rows": unflagged_wide_rendered["rows"],
    }, {
        "selector": 0x1003,
        "context_slot": 3,
        "compact_mode": 1,
        "payload": bytes.fromhex("00 01 01 66 01"),
        "count": 1,
        "rendered": [{
            "glyph": 1,
            "coord": 0x6601,
            "rows": 3,
            "span": 0x11,
            "width": 0x88,
            "full_chunks": 1,
            "remainder": 1,
            "full_row_skip": 0,
            "remainder_row_skip": 0x10,
            "full_chunk_helper": 0x2F27C,
            "remainder_helper": u32(data, 0x1F1AC + 1 * 4),
            "dest_base": 0xC2,
            "x": 22,
            "y": 6,
            "a001": 0x16,
            "source_layout": "inline-trailing-plane",
        }],
        "rows": [
            "." * 158,
            "." * 158,
            "." * 158,
            "." * 158,
            "." * 158,
            "." * 158,
            "." * 22 + "#" * 136,
            "." * 158,
            "." * 22 + "#." * 64 + ".#.#.#.#",
        ],
    }))
    unflagged_tall_source = dict(unflagged_positioned_source)
    unflagged_tall_source["inline_record"] = bytes.fromhex("02 81 04")
    unflagged_tall_bucket = queue_text_source_via_12f2e(resources, unflagged_tall_source)
    checks.append(assert_equal("0x12f2e-modeled unflagged tall inline bucket objects", {
        key: unflagged_tall_bucket[key]
        for key in ("path", "object_size", "capacity", "entry_size", "selector", "coord", "glyph", "rows", "width", "objects")
    }, {
        "path": "segmented",
        "object_size": 0x28,
        "capacity": 0x08,
        "entry_size": 4,
        "selector": 0x2003,
        "coord": 0x6601,
        "glyph": 0x01,
        "rows": 0x81,
        "width": 0x02,
        "objects": [
            {"bucket_index": 9, "segment": 1, "object": bytes.fromhex("00 00 00 00 20 03 00 01 01 01 66 01")},
            {"bucket_index": 1, "segment": 0, "object": bytes.fromhex("00 00 00 00 20 03 00 01 01 00 66 01")},
        ],
    }))
    unflagged_wide_tall_source = dict(unflagged_positioned_source)
    unflagged_wide_tall_source["inline_record"] = bytes.fromhex("11 81 04")
    unflagged_wide_tall_bucket = queue_text_source_via_12f2e(resources, unflagged_wide_tall_source)
    checks.append(assert_equal("0x12f2e-modeled unflagged wide tall inline bucket objects", {
        key: unflagged_wide_tall_bucket[key]
        for key in ("path", "object_size", "capacity", "entry_size", "selector", "coord", "glyph", "rows", "width", "objects")
    }, {
        "path": "segmented",
        "object_size": 0x28,
        "capacity": 0x08,
        "entry_size": 4,
        "selector": 0x3003,
        "coord": 0x6601,
        "glyph": 0x01,
        "rows": 0x81,
        "width": 0x11,
        "objects": [
            {"bucket_index": 9, "segment": 1, "object": bytes.fromhex("00 00 00 00 30 03 00 01 01 01 66 01")},
            {"bucket_index": 1, "segment": 0, "object": bytes.fromhex("00 00 00 00 30 03 00 01 01 00 66 01")},
        ],
    }))
    segmented_wide_inline_render_resources = bytearray(0x1000)
    segmented_wide_inline_context = 0x00000100
    segmented_wide_record_offset = segmented_wide_inline_context + 0x40 + 1 * 8
    segmented_wide_bitmap_delta = 0x100
    segmented_wide_bitmap = segmented_wide_inline_context + segmented_wide_bitmap_delta
    segmented_wide_inline_render_resources[segmented_wide_record_offset] = 0x11
    segmented_wide_inline_render_resources[segmented_wide_record_offset + 1] = 0x81
    segmented_wide_inline_render_resources[segmented_wide_record_offset + 4:segmented_wide_record_offset + 8] = segmented_wide_bitmap_delta.to_bytes(4, "big")
    segmented_wide_inline_render_resources[segmented_wide_bitmap + 0x80 * 0x10:segmented_wide_bitmap + 0x81 * 0x10] = b"\xaa" * 0x10
    segmented_wide_inline_render_resources[segmented_wide_bitmap + 0x81 * 0x10 + 0x80] = 0x55
    unflagged_segmented_wide_object = unflagged_wide_tall_bucket["objects"][0]["object"]
    unflagged_segmented_wide_rendered = render_compact_text_bucket_object(
        data,
        segmented_wide_inline_render_resources,
        (0, 0, 0, segmented_wide_inline_context),
        unflagged_segmented_wide_object,
    )
    checks.append(assert_equal("0x1f264 renders segmented wide inline compact payload row", {
        "selector": unflagged_segmented_wide_rendered["selector"],
        "context_slot": unflagged_segmented_wide_rendered["context_slot"],
        "compact_mode": unflagged_segmented_wide_rendered["compact_mode"],
        "payload": unflagged_segmented_wide_rendered["payload"],
        "count": unflagged_segmented_wide_rendered["count"],
        "rendered": unflagged_segmented_wide_rendered["rendered"],
        "rows": unflagged_segmented_wide_rendered["rows"],
    }, {
        "selector": 0x3003,
        "context_slot": 3,
        "compact_mode": 3,
        "payload": bytes.fromhex("00 01 01 01 66 01"),
        "count": 1,
        "rendered": [{
            "glyph": 1,
            "segment": 1,
            "coord": 0x6601,
            "row_skip": 0x80,
            "a2_source_offset": 0x800,
            "a3_source_offset": 0x80,
            "rows": 1,
            "span": 0x11,
            "width": 0x88,
            "full_chunks": 1,
            "remainder": 1,
            "full_row_skip": 0,
            "remainder_row_skip": 0x10,
            "full_chunk_helper": 0x2F27C,
            "remainder_helper": u32(data, 0x1F1AC + 1 * 4),
            "dest_base": 0xC2,
            "x": 22,
            "y": 6,
            "a001": 0x16,
            "source_layout": "inline-trailing-plane",
        }],
        "rows": [
            "." * 158,
            "." * 158,
            "." * 158,
            "." * 158,
            "." * 158,
            "." * 158,
            "." * 22 + "#." * 64 + ".#.#.#.#",
        ],
    }))
    inline_render_resources = bytearray(0x300)
    inline_context = 0x00000100
    inline_record_offset = inline_context + 0x40 + 1 * 8
    inline_bitmap_delta = 0x80
    inline_bitmap = inline_context + inline_bitmap_delta
    inline_render_resources[inline_record_offset] = 0x02
    inline_render_resources[inline_record_offset + 1] = 0x81
    inline_render_resources[inline_record_offset + 4:inline_record_offset + 8] = inline_bitmap_delta.to_bytes(4, "big")
    inline_render_resources[inline_bitmap + 0x100:inline_bitmap + 0x102] = bytes.fromhex("aa 55")
    unflagged_segmented_object = unflagged_tall_bucket["objects"][0]["object"]
    unflagged_segmented_rendered = render_compact_text_bucket_object(
        data,
        inline_render_resources,
        (0, 0, 0, inline_context),
        unflagged_segmented_object,
    )
    checks.append(assert_equal("0x1f1f0 renders segmented inline compact payload row", {
        "selector": unflagged_segmented_rendered["selector"],
        "context_slot": unflagged_segmented_rendered["context_slot"],
        "compact_mode": unflagged_segmented_rendered["compact_mode"],
        "payload": unflagged_segmented_rendered["payload"],
        "count": unflagged_segmented_rendered["count"],
        "rendered": unflagged_segmented_rendered["rendered"],
        "rows": unflagged_segmented_rendered["rows"],
    }, {
        "selector": 0x2003,
        "context_slot": 3,
        "compact_mode": 2,
        "payload": bytes.fromhex("00 01 01 01 66 01"),
        "count": 1,
        "rendered": [{
            "glyph": 1,
            "segment": 1,
            "coord": 0x6601,
            "row_skip": 0x80,
            "source_offset": 0x100,
            "rows": 1,
            "span": 2,
            "width": 16,
            "dest_base": 0xC2,
            "x": 22,
            "y": 6,
            "a001": 0x16,
            "helper": u32(data, 0x1F08E + 2 * 4),
        }],
        "rows": [
            "." * 38,
            "." * 38,
            "." * 38,
            "." * 38,
            "." * 38,
            "." * 38,
            "." * 22 + "#.#.#.#..#.#.#.#",
        ],
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
    tall_page_record: dict[str, object] = {"bucket_array": {}, "context_slots": [0x440946B4]}
    tall_page_first = queue_text_source_to_page_record_via_12f2e(resources, tall_page_record, tall_text_source)
    tall_page_bucket_array = tall_page_record["bucket_array"]
    assert isinstance(tall_page_bucket_array, dict)
    expected_tall_segment_pairs = [
        {"bucket_index": 64, "segment": 8},
        {"bucket_index": 56, "segment": 7},
        {"bucket_index": 48, "segment": 6},
        {"bucket_index": 40, "segment": 5},
        {"bucket_index": 32, "segment": 4},
        {"bucket_index": 24, "segment": 3},
        {"bucket_index": 16, "segment": 2},
        {"bucket_index": 8, "segment": 1},
        {"bucket_index": 0, "segment": 0},
    ]
    tall_page_first_prefixes = [
        bytes(tall_page_bucket_array[pair["bucket_index"]][0][:12])
        for pair in expected_tall_segment_pairs
    ]
    tall_page_second = queue_text_source_to_page_record_via_12f2e(resources, tall_page_record, tall_text_source)
    tall_page_first_events = tall_page_first["events"]
    tall_page_second_events = tall_page_second["events"]
    assert isinstance(tall_page_first_events, list)
    assert isinstance(tall_page_second_events, list)
    checks.append(assert_equal("0x1387c page-record segmented allocator places tall glyph buckets", {
        "metadata": {
            key: tall_page_first[key]
            for key in ("path", "selector", "coord", "glyph", "rows", "width")
        },
        "events": [
            {
                key: event[key]
                for key in ("bucket_index", "segment", "allocated", "chain_index", "count_before", "count_after", "capacity", "object_size", "selector")
            }
            for event in tall_page_first_events
        ],
        "prefixes": tall_page_first_prefixes,
    }, {
        "metadata": {
            "path": "segmented-page-record",
            "selector": 0x2000,
            "coord": 0,
            "glyph": 0x1F,
            "rows": 1108,
            "width": 74,
        },
        "events": [
            pair | {
                "allocated": True,
                "chain_index": 0,
                "count_before": 0,
                "count_after": 1,
                "capacity": 8,
                "object_size": 0x28,
                "selector": 0x2000,
            }
            for pair in expected_tall_segment_pairs
        ],
        "prefixes": [
            bytes.fromhex("00 00 00 00 20 00 00 01 1f 08 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 01 1f 07 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 01 1f 06 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 01 1f 05 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 01 1f 04 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 01 1f 03 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 01 1f 02 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 01 1f 01 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 01 1f 00 00 00"),
        ],
    }))
    checks.append(assert_equal("0x1387c page-record segmented allocator reuses tall glyph buckets", {
        "events": [
            {
                key: event[key]
                for key in ("bucket_index", "segment", "allocated", "chain_index", "count_before", "count_after", "capacity", "object_size", "selector")
            }
            for event in tall_page_second_events
        ],
        "prefixes": [
            bytes(tall_page_bucket_array[pair["bucket_index"]][0][:16])
            for pair in expected_tall_segment_pairs
        ],
    }, {
        "events": [
            pair | {
                "allocated": False,
                "chain_index": 0,
                "count_before": 1,
                "count_after": 2,
                "capacity": 8,
                "object_size": 0x28,
                "selector": 0x2000,
            }
            for pair in expected_tall_segment_pairs
        ],
        "prefixes": [
            bytes.fromhex("00 00 00 00 20 00 00 02 1f 08 00 00 1f 08 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 02 1f 07 00 00 1f 07 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 02 1f 06 00 00 1f 06 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 02 1f 05 00 00 1f 05 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 02 1f 04 00 00 1f 04 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 02 1f 03 00 00 1f 03 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 02 1f 02 00 00 1f 02 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 02 1f 01 00 00 1f 01 00 00"),
            bytes.fromhex("00 00 00 00 20 00 00 02 1f 00 00 00 1f 00 00 00"),
        ],
    }))
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
            "x": 0,
            "y": 0,
            "a001": 0,
            "span": 1,
            "rows": 22,
            "width": 4,
            "helper": 0x01FA5C,
        }],
        "payload": bytes.fromhex("00 01 20 00 00"),
    }))
    checks.append(assert_equal("compact text bucket object fixture rendered rows", compact_mode0["rows"], line_printer_glyph32_rows))
    page_record_short_rendered = render_compact_text_bucket_object(data, resources, (0x440946B4,), bytes(page_record_chain[0]))
    checks.append(assert_equal("0x1387c page-record queued short object renders reused entries", {
        "rendered": {key: page_record_short_rendered[key] for key in ("selector", "context_slot", "count", "rendered", "payload")},
        "rows": page_record_short_rendered["rows"],
    }, {
        "rendered": {
            "selector": 0,
            "context_slot": 0,
            "count": 2,
            "rendered": [
                {
                    "glyph": 0x20,
                    "coord": 0x0000,
                    "dest_base": 0x00,
                    "x": 0,
                    "y": 0,
                    "a001": 0x00,
                    "span": 1,
                    "rows": 22,
                    "width": 4,
                    "helper": 0x01FA5C,
                },
                {
                    "glyph": 0x20,
                    "coord": 0x0001,
                    "dest_base": 0x02,
                    "x": 16,
                    "y": 0,
                    "a001": 0x00,
                    "span": 1,
                    "rows": 22,
                    "width": 4,
                    "helper": 0x01FA5C,
                },
            ],
            "payload": bytes.fromhex("00 02 20 00 00 20 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"),
        },
        "rows": [
            "####............####" if row == "####" else "." * 20
            for row in line_printer_glyph32_rows
        ],
    }))
    bridged_page_record = bridge_page_record_via_1edc6({
        "bucket_root": bytes(page_record_chain[0]),
        "rule_list": [
            bytes.fromhex("00 00 00 00 00 03 00 00 00 00 12 34 00 00"),
        ],
        "fixed_list": [
            bytes.fromhex("00 00 00 00 00 04 00 00 ab cd 00 00 00 00"),
        ],
        "context_slots": [0x440946B4],
    })
    bridged_rendered = render_bridged_compact_bucket_object(data, resources, bridged_page_record)
    checks.append(assert_equal("0x1edc6 page-record bridge copies compact bucket and context slots", {
        "bucket_root": bridged_page_record["bucket_root"],
        "context_slots": bridged_page_record["context_slots"][:2],
        "rendered": {key: bridged_rendered[key] for key in ("selector", "context_slot", "count", "rendered", "payload")},
    }, {
        "bucket_root": bytes(page_record_chain[0]),
        "context_slots": (0x440946B4, 0),
        "rendered": {key: page_record_short_rendered[key] for key in ("selector", "context_slot", "count", "rendered", "payload")},
    }))
    checks.append(assert_equal("0x1edc6 page-record bridge normalizes rule and fixed lists", {
        "rule_list": bridged_page_record["rule_list"],
        "fixed_list": bridged_page_record["fixed_list"],
        "rows": bridged_rendered["rows"],
    }, {
        "rule_list": [bytes.fromhex("00 00 00 00 00 13 00 00 00 00 12 34 12 34")],
        "fixed_list": [bytes.fromhex("00 00 00 00 00 14 00 00 ab cd ab cd 01 08")],
        "rows": page_record_short_rendered["rows"],
    }))
    rule_page_record: dict[str, object] = {}
    rule_result = queue_rectangle_rule_via_13386(
        rule_page_record,
        {"x": 0x0023, "y": 0x0045, "width": 0x0012, "height": 0x0034, "flags": 0x07},
        vertical_offset=0x0010,
        band_byte=0x04,
    )
    rule_bridged = bridge_page_record_via_1edc6(rule_page_record)
    checks.append(assert_equal("0x13386/0x133aa-modeled rectangle/rule list object and bridge normalization", {
        "computed": rule_result["computed"],
        "object": rule_result["object"],
        "bridged": rule_bridged["rule_list"],
    }, {
        "computed": {
            "x": 0x0033,
            "y": 0x0045,
            "bucket_index": 0x0004,
            "key": 0x5303,
        },
        "object": bytes.fromhex("00 00 00 00 04 07 53 03 00 12 00 34 00 00"),
        "bridged": [bytes.fromhex("00 00 00 00 04 17 53 03 00 12 00 34 00 34")],
    }))
    fixed_rule_page_record: dict[str, object] = {}
    fixed_rule_result = queue_fixed_rule_via_136d2(
        fixed_rule_page_record,
        {"x": 0x0017, "y": 0x0021, "mode": 1, "extent": 0x0044},
        vertical_offset=0x0009,
        band_byte=0x02,
    )
    fixed_rule_bridged = bridge_page_record_via_1edc6(fixed_rule_page_record)
    checks.append(assert_equal("0x137a2/0x136d2-modeled fixed-rule list object and bridge normalization", {
        "computed": fixed_rule_result["computed"],
        "object": fixed_rule_result["object"],
        "bridged": fixed_rule_bridged["fixed_list"],
    }, {
        "computed": {
            "x": 0x0020,
            "y": 0x0021,
            "bucket_index": 0x0002,
            "key": 0x1002,
            "mode": 6,
            "selector_hi": 0x40,
            "selector_lo": 0x00,
        },
        "object": bytes.fromhex("00 00 00 00 02 06 10 02 00 44 00 00 00 00"),
        "bridged": [bytes.fromhex("00 00 00 00 02 16 10 02 00 44 00 44 01 08")],
    }))
    parser_raster_resolution_cases = [
        (300, {"mode": 0, "scale": 1, "limit": 32}),
        (150, {"mode": 1, "scale": 2, "limit": 16}),
        (100, {"mode": 2, "scale": 3, "limit": 11}),
        (75, {"mode": 3, "scale": 4, "limit": 8}),
    ]
    checks.append(assert_equal("0x10808 ESC *t#R selects raster mode and scale thresholds", [
        {
            "parameter": parameter,
            "mode": apply_raster_resolution_via_10808(raster_graphics_state(page_extent=255), parameter)["mode"],
            "scale": apply_raster_resolution_via_10808(raster_graphics_state(page_extent=255), parameter)["scale"],
            "limit": apply_raster_resolution_via_10808(raster_graphics_state(page_extent=255), parameter)["limit"],
        }
        for parameter, _expected in parser_raster_resolution_cases
    ], [
        {"parameter": parameter, **expected}
        for parameter, expected in parser_raster_resolution_cases
    ]))
    parser_raster_start_base = apply_raster_resolution_via_10808(
        raster_graphics_state(page_extent=255, cursor_axis0=0x00100000, cursor_axis1=0x00200000),
        300,
    )
    parser_raster_start = start_raster_graphics_via_1075a(parser_raster_start_base, 1)
    parser_raster_start_left = start_raster_graphics_via_1075a(parser_raster_start_base, 0)
    checks.append(assert_equal("0x1075a ESC *r#A seeds raster baseline from cursor or left edge", {
        "current_cursor": {key: parser_raster_start[key] for key in ("active", "origin_long", "baseline_word", "mode", "scale", "limit")},
        "left_edge": {key: parser_raster_start_left[key] for key in ("active", "origin_long", "baseline_word", "mode", "scale", "limit")},
    }, {
        "current_cursor": {
            "active": 1,
            "origin_long": 0x00100000,
            "baseline_word": 16,
            "mode": 0,
            "scale": 1,
            "limit": 30,
        },
        "left_edge": {
            "active": 1,
            "origin_long": 0,
            "baseline_word": 0,
            "mode": 0,
            "scale": 1,
            "limit": 32,
        },
    }))
    parser_raster_end = end_raster_graphics_via_107fa(parser_raster_start)
    checks.append(assert_equal("0x107fa ESC *r#B clears raster active flag only", {
        key: parser_raster_end[key]
        for key in ("active", "origin_long", "baseline_word", "mode", "scale", "limit", "row_y")
    }, {
        "active": 0,
        "origin_long": 0x00100000,
        "baseline_word": 16,
        "mode": 0,
        "scale": 1,
        "limit": 30,
        "row_y": 0,
    }))
    parser_raster_page_record: dict[str, object] = {"bucket_array": {}}
    parser_raster_page_result = queue_raster_row_to_page_record_via_13070(
        parser_raster_page_record,
        {
            "x": parser_raster_start["baseline_word"],
            "y": parser_raster_start["row_y"],
            "byte_count": 4,
            "mode": parser_raster_start["mode"],
        },
        bytes.fromhex("f0 0f aa 55"),
    )
    parser_raster_bucket_array = parser_raster_page_record["bucket_array"]
    assert isinstance(parser_raster_bucket_array, dict)
    parser_raster_object = bytes(parser_raster_bucket_array[0][0])
    parser_raster_rendered = render_encoded_raster_object_via_1f88e(data, parser_raster_object)
    checks.append(assert_equal("parser-derived ESC *t300R / ESC *r1A state queues mode-0 raster row", {
        "state": {key: parser_raster_start[key] for key in ("active", "baseline_word", "mode", "scale", "limit")},
        "result": {
            key: parser_raster_page_result[key]
            for key in ("path", "allocated", "bucket_index", "key", "mode", "byte_count_before", "byte_count_after", "capacity", "object_size")
        },
        "object": parser_raster_object,
        "rows": parser_raster_rendered["rows"],
    }, {
        "state": {
            "active": 1,
            "baseline_word": 16,
            "mode": 0,
            "scale": 1,
            "limit": 30,
        },
        "result": {
            "path": "raster-page-record",
            "allocated": True,
            "bucket_index": 0,
            "key": 0x0001,
            "mode": 0,
            "byte_count_before": 4,
            "byte_count_after": 0,
            "capacity": 4,
            "object_size": 0x0E,
        },
        "object": bytes.fromhex("00 00 00 00 80 00 00 04 00 01 f0 0f aa 55"),
        "rows": ["................####........#####.#.#.#..#.#.#.#"],
    }))
    raster_command_stream = b"\x1b*t300R\x1b*r1A\x1b*b4W" + bytes.fromhex("f0 0f aa 55")
    raster_stream_result = render_raster_command_data_stream_via_121cc_105d0(
        data,
        raster_command_stream,
        raster_graphics_state(page_extent=255, cursor_axis0=0x00100000, cursor_axis1=0x00200000),
    )
    raster_stream_rendered = raster_stream_result["rendered"]
    assert isinstance(raster_stream_rendered, dict)
    checks.append(assert_equal("modeled raster command stream parses ESC *t300R / ESC *r1A / ESC *b4W payload boundary", {
        "events": [
            {
                key: event[key]
                for key in (
                    ("kind", "parameter", "mode_after", "scale", "limit")
                    if event["kind"] == "raster-resolution"
                    else ("kind", "parameter", "active_after", "origin_long", "baseline_word", "limit")
                    if event["kind"] == "start-raster"
                    else ("kind", "parameter", "delayed_handler", "payload_offset", "payload", "transfer_state", "row_y_after")
                )
            }
            for event in raster_stream_result["events"]
        ],
        "final_state": {
            key: raster_stream_result["final_state"][key]
            for key in ("active", "baseline_word", "mode", "scale", "limit", "row_y")
        },
    }, {
        "events": [
            {"kind": "raster-resolution", "parameter": 300, "mode_after": 0, "scale": 1, "limit": 32},
            {"kind": "start-raster", "parameter": 1, "active_after": 1, "origin_long": 0x00100000, "baseline_word": 16, "limit": 30},
            {
                "kind": "raster-transfer",
                "parameter": 4,
                "delayed_handler": 0x0105D0,
                "payload_offset": 17,
                "payload": bytes.fromhex("f0 0f aa 55"),
                "transfer_state": {"x": 16, "y": 0, "byte_count": 4, "mode": 0},
                "row_y_after": 1,
            },
        ],
        "final_state": {
            "active": 1,
            "baseline_word": 16,
            "mode": 0,
            "scale": 1,
            "limit": 30,
            "row_y": 1,
        },
    }))
    checks.append(assert_equal("modeled raster command stream queues and renders ESC *b4W payload", {
        "bucket_index": raster_stream_result["bucket_index"],
        "chain": raster_stream_result["chain"],
        "object": raster_stream_result["object"],
        "rows": raster_stream_rendered["rows"],
    }, {
        "bucket_index": 0,
        "chain": [bytes.fromhex("00 00 00 00 80 00 00 04 00 01 f0 0f aa 55")],
        "object": bytes.fromhex("00 00 00 00 80 00 00 04 00 01 f0 0f aa 55"),
        "rows": ["................####........#####.#.#.#..#.#.#.#"],
    }))
    raster_stream_bridged = raster_stream_result["bridged"]
    raster_stream_bridged_rendered = raster_stream_result["bridged_rendered"]
    assert isinstance(raster_stream_bridged, dict)
    assert isinstance(raster_stream_bridged_rendered, dict)
    checks.append(assert_equal("modeled raster command stream bridges queued ESC *b4W page object", {
        "bucket_root": raster_stream_bridged["bucket_root"],
        "rows": raster_stream_bridged_rendered["rows"],
    }, {
        "bucket_root": bytes.fromhex("00 00 00 00 80 00 00 04 00 01 f0 0f aa 55"),
        "rows": raster_stream_rendered["rows"],
    }))
    raster_mode1_command_stream = b"\x1b*t150R\x1b*r0A\x1b*b2W" + bytes.fromhex("f0 0f")
    raster_mode1_stream_result = render_raster_command_data_stream_via_121cc_105d0(
        data,
        raster_mode1_command_stream,
        raster_graphics_state(page_extent=255, cursor_axis0=0x00100000, cursor_axis1=0x00200000),
    )
    raster_mode1_stream_rendered = raster_mode1_stream_result["rendered"]
    assert isinstance(raster_mode1_stream_rendered, dict)
    checks.append(assert_equal("modeled raster command stream selects 150-dpi mode-1 state", {
        "events": [
            {
                key: event[key]
                for key in (
                    ("kind", "parameter", "mode_after", "scale", "limit")
                    if event["kind"] == "raster-resolution"
                    else ("kind", "parameter", "active_after", "origin_long", "baseline_word", "limit")
                    if event["kind"] == "start-raster"
                    else ("kind", "parameter", "delayed_handler", "payload_offset", "payload", "transfer_state", "row_y_after")
                )
            }
            for event in raster_mode1_stream_result["events"]
        ],
        "final_state": {
            key: raster_mode1_stream_result["final_state"][key]
            for key in ("active", "baseline_word", "mode", "scale", "limit", "row_y")
        },
    }, {
        "events": [
            {"kind": "raster-resolution", "parameter": 150, "mode_after": 1, "scale": 2, "limit": 16},
            {"kind": "start-raster", "parameter": 0, "active_after": 1, "origin_long": 0, "baseline_word": 0, "limit": 16},
            {
                "kind": "raster-transfer",
                "parameter": 2,
                "delayed_handler": 0x0105D0,
                "payload_offset": 17,
                "payload": bytes.fromhex("f0 0f"),
                "transfer_state": {"x": 0, "y": 0, "byte_count": 2, "mode": 1},
                "row_y_after": 1,
            },
        ],
        "final_state": {
            "active": 1,
            "baseline_word": 0,
            "mode": 1,
            "scale": 2,
            "limit": 16,
            "row_y": 1,
        },
    }))
    checks.append(assert_equal("modeled raster command stream queues and renders 150-dpi mode-1 payload", {
        "object": raster_mode1_stream_result["object"],
        "rows": raster_mode1_stream_rendered["rows"],
    }, {
        "object": bytes.fromhex("00 00 00 00 80 01 00 02 00 00 f0 0f"),
        "rows": [
            "########................########",
            "########................########",
        ],
    }))
    raster_mode2_command_stream = b"\x1b*t100R\x1b*r0A\x1b*b2W" + bytes.fromhex("f0 0f")
    raster_mode2_stream_result = render_raster_command_data_stream_via_121cc_105d0(
        data,
        raster_mode2_command_stream,
        raster_graphics_state(page_extent=255, cursor_axis0=0x00100000, cursor_axis1=0x00200000),
    )
    raster_mode2_stream_rendered = raster_mode2_stream_result["rendered"]
    assert isinstance(raster_mode2_stream_rendered, dict)
    checks.append(assert_equal("modeled raster command stream selects 100-dpi mode-2 state", {
        "events": [
            {
                key: event[key]
                for key in (
                    ("kind", "parameter", "mode_after", "scale", "limit")
                    if event["kind"] == "raster-resolution"
                    else ("kind", "parameter", "active_after", "origin_long", "baseline_word", "limit")
                    if event["kind"] == "start-raster"
                    else ("kind", "parameter", "delayed_handler", "payload_offset", "payload", "transfer_state", "row_y_after")
                )
            }
            for event in raster_mode2_stream_result["events"]
        ],
        "final_state": {
            key: raster_mode2_stream_result["final_state"][key]
            for key in ("active", "baseline_word", "mode", "scale", "limit", "row_y")
        },
    }, {
        "events": [
            {"kind": "raster-resolution", "parameter": 100, "mode_after": 2, "scale": 3, "limit": 11},
            {"kind": "start-raster", "parameter": 0, "active_after": 1, "origin_long": 0, "baseline_word": 0, "limit": 11},
            {
                "kind": "raster-transfer",
                "parameter": 2,
                "delayed_handler": 0x0105D0,
                "payload_offset": 17,
                "payload": bytes.fromhex("f0 0f"),
                "transfer_state": {"x": 0, "y": 0, "byte_count": 2, "mode": 2},
                "row_y_after": 1,
            },
        ],
        "final_state": {
            "active": 1,
            "baseline_word": 0,
            "mode": 2,
            "scale": 3,
            "limit": 11,
            "row_y": 1,
        },
    }))
    checks.append(assert_equal("modeled raster command stream queues and renders 100-dpi mode-2 payload", {
        "object": raster_mode2_stream_result["object"],
        "rows": raster_mode2_stream_rendered["rows"],
    }, {
        "object": bytes.fromhex("00 00 00 00 80 02 00 02 00 00 f0 0f"),
        "rows": [
            "############................############........",
            "############................############........",
            "############................############........",
        ],
    }))
    raster_mode3_command_stream = b"\x1b*t75R\x1b*r0A\x1b*b2W" + bytes.fromhex("f0 0f")
    raster_mode3_stream_result = render_raster_command_data_stream_via_121cc_105d0(
        data,
        raster_mode3_command_stream,
        raster_graphics_state(page_extent=255, cursor_axis0=0x00100000, cursor_axis1=0x00200000),
    )
    raster_mode3_stream_rendered = raster_mode3_stream_result["rendered"]
    assert isinstance(raster_mode3_stream_rendered, dict)
    checks.append(assert_equal("modeled raster command stream selects 75-dpi mode-3 state", {
        "events": [
            {
                key: event[key]
                for key in (
                    ("kind", "parameter", "mode_after", "scale", "limit")
                    if event["kind"] == "raster-resolution"
                    else ("kind", "parameter", "active_after", "origin_long", "baseline_word", "limit")
                    if event["kind"] == "start-raster"
                    else ("kind", "parameter", "delayed_handler", "payload_offset", "payload", "transfer_state", "row_y_after")
                )
            }
            for event in raster_mode3_stream_result["events"]
        ],
        "final_state": {
            key: raster_mode3_stream_result["final_state"][key]
            for key in ("active", "baseline_word", "mode", "scale", "limit", "row_y")
        },
    }, {
        "events": [
            {"kind": "raster-resolution", "parameter": 75, "mode_after": 3, "scale": 4, "limit": 8},
            {"kind": "start-raster", "parameter": 0, "active_after": 1, "origin_long": 0, "baseline_word": 0, "limit": 8},
            {
                "kind": "raster-transfer",
                "parameter": 2,
                "delayed_handler": 0x0105D0,
                "payload_offset": 16,
                "payload": bytes.fromhex("f0 0f"),
                "transfer_state": {"x": 0, "y": 0, "byte_count": 2, "mode": 3},
                "row_y_after": 1,
            },
        ],
        "final_state": {
            "active": 1,
            "baseline_word": 0,
            "mode": 3,
            "scale": 4,
            "limit": 8,
            "row_y": 1,
        },
    }))
    checks.append(assert_equal("modeled raster command stream queues and renders 75-dpi mode-3 payload", {
        "object": raster_mode3_stream_result["object"],
        "rows": raster_mode3_stream_rendered["rows"],
    }, {
        "object": bytes.fromhex("00 00 00 00 80 03 00 02 00 00 f0 0f"),
        "rows": [
            "################................................################",
            "################................................################",
            "################................................################",
            "################................................################",
        ],
    }))
    raster_multirow_command_stream = b"\x1b*t300R\x1b*r0A\x1b*b2W" + bytes.fromhex("f0 0f") + b"\x1b*b2W" + bytes.fromhex("0f f0")
    raster_multirow_stream_result = render_raster_command_data_stream_via_121cc_105d0(
        data,
        raster_multirow_command_stream,
        raster_graphics_state(page_extent=255, cursor_axis0=0x00100000, cursor_axis1=0x00200000),
    )
    raster_multirow_page_record = raster_multirow_stream_result["page_record"]
    assert isinstance(raster_multirow_page_record, dict)
    raster_multirow_bucket_array = raster_multirow_page_record["bucket_array"]
    assert isinstance(raster_multirow_bucket_array, dict)
    raster_multirow_chain = [bytes(obj) for obj in raster_multirow_bucket_array[0]]
    raster_multirow_rendered = [render_encoded_raster_object_via_1f88e(data, obj) for obj in reversed(raster_multirow_chain)]
    checks.append(assert_equal("modeled raster command stream queues consecutive ESC *b#W rows", {
        "transfer_events": [
            {
                key: event[key]
                for key in ("parameter", "payload_offset", "payload", "transfer_state", "row_y_after")
            }
            for event in raster_multirow_stream_result["events"]
            if event["kind"] == "raster-transfer"
        ],
        "final_state": {
            key: raster_multirow_stream_result["final_state"][key]
            for key in ("active", "baseline_word", "mode", "scale", "limit", "row_y")
        },
        "chain": raster_multirow_chain,
    }, {
        "transfer_events": [
            {
                "parameter": 2,
                "payload_offset": 17,
                "payload": bytes.fromhex("f0 0f"),
                "transfer_state": {"x": 0, "y": 0, "byte_count": 2, "mode": 0},
                "row_y_after": 1,
            },
            {
                "parameter": 2,
                "payload_offset": 24,
                "payload": bytes.fromhex("0f f0"),
                "transfer_state": {"x": 0, "y": 1, "byte_count": 2, "mode": 0},
                "row_y_after": 2,
            },
        ],
        "final_state": {
            "active": 1,
            "baseline_word": 0,
            "mode": 0,
            "scale": 1,
            "limit": 32,
            "row_y": 2,
        },
        "chain": [
            bytes.fromhex("00 00 00 00 80 00 00 02 10 00 0f f0"),
            bytes.fromhex("00 00 00 00 80 00 00 02 00 00 f0 0f"),
        ],
    }))
    checks.append(assert_equal("modeled raster command stream renders consecutive queued rows", {
        "rendered": [
            {
                key: rendered[key]
                for key in ("coord", "x", "y", "payload", "rows")
            }
            for rendered in raster_multirow_rendered
        ],
    }, {
        "rendered": [
            {
                "coord": 0x0000,
                "x": 0,
                "y": 0,
                "payload": bytes.fromhex("f0 0f"),
                "rows": ["####........####"],
            },
            {
                "coord": 0x1000,
                "x": 0,
                "y": 1,
                "payload": bytes.fromhex("0f f0"),
                "rows": ["................", "....########...."],
            },
        ],
    }))
    raster_end_command_stream = b"\x1b*t300R\x1b*r0A\x1b*b2W" + bytes.fromhex("f0 0f") + b"\x1b*rB\x1b*t150R"
    raster_end_stream_result = render_raster_command_data_stream_via_121cc_105d0(
        data,
        raster_end_command_stream,
        raster_graphics_state(page_extent=255, cursor_axis0=0x00100000, cursor_axis1=0x00200000),
    )
    raster_end_event_summary: list[dict[str, object]] = []
    for event in raster_end_stream_result["events"]:
        if event["kind"] == "raster-resolution":
            raster_end_event_summary.append({
                key: event[key]
                for key in ("kind", "parameter", "mode_before", "mode_after", "scale", "limit")
            })
        elif event["kind"] == "start-raster":
            raster_end_event_summary.append({
                key: event[key]
                for key in ("kind", "parameter", "active_before", "active_after", "origin_long", "baseline_word", "limit")
            })
        elif event["kind"] == "raster-transfer":
            raster_end_event_summary.append({
                key: event[key]
                for key in ("kind", "parameter", "payload_offset", "payload", "transfer_state", "row_y_after")
            })
        elif event["kind"] == "end-raster":
            raster_end_event_summary.append({
                key: event[key]
                for key in ("kind", "parameter", "active_before", "active_after", "mode", "scale", "limit", "row_y")
            })
        else:
            raise AssertionError(f"unexpected raster end stream event {event['kind']}")
    checks.append(assert_equal("modeled raster command stream parses ESC *rB and re-enables resolution changes", {
        "events": raster_end_event_summary,
        "final_state": {
            key: raster_end_stream_result["final_state"][key]
            for key in ("active", "baseline_word", "mode", "scale", "limit", "row_y")
        },
        "object": raster_end_stream_result["object"],
    }, {
        "events": [
            {"kind": "raster-resolution", "parameter": 300, "mode_before": 3, "mode_after": 0, "scale": 1, "limit": 32},
            {"kind": "start-raster", "parameter": 0, "active_before": 0, "active_after": 1, "origin_long": 0, "baseline_word": 0, "limit": 32},
            {
                "kind": "raster-transfer",
                "parameter": 2,
                "payload_offset": 17,
                "payload": bytes.fromhex("f0 0f"),
                "transfer_state": {"x": 0, "y": 0, "byte_count": 2, "mode": 0},
                "row_y_after": 1,
            },
            {"kind": "end-raster", "parameter": 0, "active_before": 1, "active_after": 0, "mode": 0, "scale": 1, "limit": 32, "row_y": 1},
            {"kind": "raster-resolution", "parameter": 150, "mode_before": 0, "mode_after": 1, "scale": 2, "limit": 16},
        ],
        "final_state": {
            "active": 0,
            "baseline_word": 0,
            "mode": 1,
            "scale": 2,
            "limit": 16,
            "row_y": 1,
        },
        "object": bytes.fromhex("00 00 00 00 80 00 00 02 00 00 f0 0f"),
    }))
    raster_chained_resolution_stream = b"\x1b*t300r150R"
    raster_chained_resolution_result = render_raster_command_data_stream_via_121cc_105d0(
        data,
        raster_chained_resolution_stream,
        raster_graphics_state(page_extent=255),
    )
    checks.append(assert_equal("modeled raster command stream accepts lowercase same-group resolution chaining", {
        "events": [
            {
                key: event[key]
                for key in ("kind", "sequence", "parameter", "mode_before", "mode_after", "scale", "limit", "chained")
            }
            for event in raster_chained_resolution_result["events"]
        ],
        "final_state": {
            key: raster_chained_resolution_result["final_state"][key]
            for key in ("active", "baseline_word", "mode", "scale", "limit", "row_y")
        },
    }, {
        "events": [
            {"kind": "raster-resolution", "sequence": b"\x1b*t300r", "parameter": 300, "mode_before": 3, "mode_after": 0, "scale": 1, "limit": 32, "chained": True},
            {"kind": "raster-resolution", "sequence": b"150R", "parameter": 150, "mode_before": 0, "mode_after": 1, "scale": 2, "limit": 16, "chained": False},
        ],
        "final_state": {
            "active": 0,
            "baseline_word": 0,
            "mode": 1,
            "scale": 2,
            "limit": 16,
            "row_y": 0,
        },
    }))
    raster_chained_transfer_stream = b"\x1b*t300R\x1b*r0A\x1b*b2w" + bytes.fromhex("f0 0f") + b"2W" + bytes.fromhex("0f f0")
    raster_chained_transfer_result = render_raster_command_data_stream_via_121cc_105d0(
        data,
        raster_chained_transfer_stream,
        raster_graphics_state(page_extent=255, cursor_axis0=0x00100000, cursor_axis1=0x00200000),
    )
    raster_chained_transfer_page_record = raster_chained_transfer_result["page_record"]
    assert isinstance(raster_chained_transfer_page_record, dict)
    raster_chained_transfer_bucket_array = raster_chained_transfer_page_record["bucket_array"]
    assert isinstance(raster_chained_transfer_bucket_array, dict)
    raster_chained_transfer_chain = [bytes(obj) for obj in raster_chained_transfer_bucket_array[0]]
    raster_chained_transfer_rendered = [render_encoded_raster_object_via_1f88e(data, obj) for obj in reversed(raster_chained_transfer_chain)]
    checks.append(assert_equal("modeled raster command stream keeps ESC *b group open across lowercase w payload", {
        "transfer_events": [
            {
                key: event[key]
                for key in ("sequence", "parameter", "payload_offset", "payload", "transfer_state", "row_y_after", "chained")
            }
            for event in raster_chained_transfer_result["events"]
            if event["kind"] == "raster-transfer"
        ],
        "chain": raster_chained_transfer_chain,
        "rendered": [
            {
                key: rendered[key]
                for key in ("coord", "x", "y", "payload", "rows")
            }
            for rendered in raster_chained_transfer_rendered
        ],
    }, {
        "transfer_events": [
            {
                "sequence": b"\x1b*b2w",
                "parameter": 2,
                "payload_offset": 17,
                "payload": bytes.fromhex("f0 0f"),
                "transfer_state": {"x": 0, "y": 0, "byte_count": 2, "mode": 0},
                "row_y_after": 1,
                "chained": True,
            },
            {
                "sequence": b"2W",
                "parameter": 2,
                "payload_offset": 21,
                "payload": bytes.fromhex("0f f0"),
                "transfer_state": {"x": 0, "y": 1, "byte_count": 2, "mode": 0},
                "row_y_after": 2,
                "chained": False,
            },
        ],
        "chain": [
            bytes.fromhex("00 00 00 00 80 00 00 02 10 00 0f f0"),
            bytes.fromhex("00 00 00 00 80 00 00 02 00 00 f0 0f"),
        ],
        "rendered": [
            {
                "coord": 0x0000,
                "x": 0,
                "y": 0,
                "payload": bytes.fromhex("f0 0f"),
                "rows": ["####........####"],
            },
            {
                "coord": 0x1000,
                "x": 0,
                "y": 1,
                "payload": bytes.fromhex("0f f0"),
                "rows": ["................", "....########...."],
            },
        ],
    }))
    raster_page_record: dict[str, object] = {"bucket_array": {}}
    raster_page_result = queue_raster_row_to_page_record_via_13070(
        raster_page_record,
        {"x": 16, "y": 0, "byte_count": 4, "mode": 0},
        bytes.fromhex("f0 0f aa 55"),
    )
    raster_bucket_array = raster_page_record["bucket_array"]
    assert isinstance(raster_bucket_array, dict)
    raster_chain = raster_bucket_array[0]
    raster_object = bytes(raster_chain[0])
    raster_rendered = render_encoded_raster_object_via_1f88e(data, raster_object)
    checks.append(assert_equal("0x13070/0x13250 raster row queues encoded-span object", {
        "result": {
            key: raster_page_result[key]
            for key in ("path", "allocated", "bucket_index", "key", "mode", "byte_count_before", "byte_count_after", "capacity", "object_size")
        },
        "chain_length": len(raster_chain),
        "object": raster_object,
    }, {
        "result": {
            "path": "raster-page-record",
            "allocated": True,
            "bucket_index": 0,
            "key": 0x0001,
            "mode": 0,
            "byte_count_before": 4,
            "byte_count_after": 0,
            "capacity": 4,
            "object_size": 0x0E,
        },
        "chain_length": 1,
        "object": bytes.fromhex("00 00 00 00 80 00 00 04 00 01 f0 0f aa 55"),
    }))
    checks.append(assert_equal("0x1f88e mode-0 raster object renders queued literal row", {
        key: raster_rendered[key]
        for key in ("mode", "helper", "byte_count", "coord", "dest_base", "x", "y", "payload", "rows")
    }, {
        "mode": 0,
        "helper": 0x01F8DA,
        "byte_count": 4,
        "coord": 0x0001,
        "dest_base": 0x02,
        "x": 16,
        "y": 0,
        "payload": bytes.fromhex("f0 0f aa 55"),
        "rows": ["................####........#####.#.#.#..#.#.#.#"],
    }))
    bridged_raster_record = bridge_page_record_via_1edc6({"bucket_root": raster_object})
    bridged_raster_rendered = render_bridged_encoded_raster_object(data, bridged_raster_record)
    checks.append(assert_equal("0x1edc6 page-record bridge preserves queued raster object", {
        "bucket_root": bridged_raster_record["bucket_root"],
        "rows": bridged_raster_rendered["rows"],
    }, {
        "bucket_root": raster_object,
        "rows": raster_rendered["rows"],
    }))
    raster_shifted_page_record: dict[str, object] = {"bucket_array": {}}
    raster_shifted_page_result = queue_raster_row_to_page_record_via_13070(
        raster_shifted_page_record,
        {"x": 20, "y": 0, "byte_count": 2, "mode": 0},
        bytes.fromhex("c3 3c"),
    )
    raster_shifted_bucket_array = raster_shifted_page_record["bucket_array"]
    assert isinstance(raster_shifted_bucket_array, dict)
    raster_shifted_object = bytes(raster_shifted_bucket_array[0][0])
    raster_shifted_rendered = render_encoded_raster_object_via_1f88e(data, raster_shifted_object)
    checks.append(assert_equal("0x13070/0x13250 raster row queues non-byte-aligned encoded-span object", {
        "result": {
            key: raster_shifted_page_result[key]
            for key in ("path", "allocated", "bucket_index", "key", "mode", "byte_count_before", "byte_count_after", "capacity", "object_size")
        },
        "object": raster_shifted_object,
    }, {
        "result": {
            "path": "raster-page-record",
            "allocated": True,
            "bucket_index": 0,
            "key": 0x0401,
            "mode": 0,
            "byte_count_before": 2,
            "byte_count_after": 0,
            "capacity": 2,
            "object_size": 0x0C,
        },
        "object": bytes.fromhex("00 00 00 00 80 00 00 02 04 01 c3 3c"),
    }))
    checks.append(assert_equal("0x1f88e mode-0 raster object renders sub-byte shifted literal row", {
        key: raster_shifted_rendered[key]
        for key in ("mode", "helper", "byte_count", "coord", "dest_base", "x", "y", "payload", "rows")
    }, {
        "mode": 0,
        "helper": 0x01F8DA,
        "byte_count": 2,
        "coord": 0x0401,
        "dest_base": 0x02,
        "x": 20,
        "y": 0,
        "payload": bytes.fromhex("c3 3c"),
        "rows": ["....................##....##..####.."],
    }))
    raster_mode1_page_record: dict[str, object] = {"bucket_array": {}}
    raster_mode1_page_result = queue_raster_row_to_page_record_via_13070(
        raster_mode1_page_record,
        {"x": 16, "y": 0, "byte_count": 2, "mode": 1},
        bytes.fromhex("f0 0f"),
    )
    raster_mode1_bucket_array = raster_mode1_page_record["bucket_array"]
    assert isinstance(raster_mode1_bucket_array, dict)
    raster_mode1_object = bytes(raster_mode1_bucket_array[0][0])
    raster_mode1_rendered = render_encoded_raster_object_via_1f88e(data, raster_mode1_object)
    checks.append(assert_equal("0x13070/0x13250 raster mode-1 row queues encoded-span object", {
        "result": {
            key: raster_mode1_page_result[key]
            for key in ("path", "allocated", "bucket_index", "key", "mode", "byte_count_before", "byte_count_after", "capacity", "object_size")
        },
        "object": raster_mode1_object,
    }, {
        "result": {
            "path": "raster-page-record",
            "allocated": True,
            "bucket_index": 0,
            "key": 0x0001,
            "mode": 1,
            "byte_count_before": 2,
            "byte_count_after": 0,
            "capacity": 2,
            "object_size": 0x0C,
        },
        "object": bytes.fromhex("00 00 00 00 80 01 00 02 00 01 f0 0f"),
    }))
    checks.append(assert_equal("0x1f88e mode-1 raster object expands queued bytes into two rows", {
        key: raster_mode1_rendered[key]
        for key in ("mode", "helper", "byte_count", "coord", "dest_base", "x", "y", "payload", "rows")
    }, {
        "mode": 1,
        "helper": 0x01F8E6,
        "byte_count": 2,
        "coord": 0x0001,
        "dest_base": 0x02,
        "x": 16,
        "y": 0,
        "payload": bytes.fromhex("f0 0f"),
        "rows": [
            "................########................########",
            "................########................########",
        ],
    }))
    raster_mode2_page_record: dict[str, object] = {"bucket_array": {}}
    raster_mode2_page_result = queue_raster_row_to_page_record_via_13070(
        raster_mode2_page_record,
        {"x": 16, "y": 0, "byte_count": 2, "mode": 2},
        bytes.fromhex("f0 0f"),
    )
    raster_mode2_bucket_array = raster_mode2_page_record["bucket_array"]
    assert isinstance(raster_mode2_bucket_array, dict)
    raster_mode2_object = bytes(raster_mode2_bucket_array[0][0])
    raster_mode2_rendered = render_encoded_raster_object_via_1f88e(data, raster_mode2_object)
    checks.append(assert_equal("0x13070/0x13250 raster mode-2 row queues encoded-span object", {
        "result": {
            key: raster_mode2_page_result[key]
            for key in ("path", "allocated", "bucket_index", "key", "mode", "byte_count_before", "byte_count_after", "capacity", "object_size")
        },
        "object": raster_mode2_object,
    }, {
        "result": {
            "path": "raster-page-record",
            "allocated": True,
            "bucket_index": 0,
            "key": 0x0001,
            "mode": 2,
            "byte_count_before": 2,
            "byte_count_after": 0,
            "capacity": 2,
            "object_size": 0x0C,
        },
        "object": bytes.fromhex("00 00 00 00 80 02 00 02 00 01 f0 0f"),
    }))
    checks.append(assert_equal("0x1f88e mode-2 raster object expands queued byte pair into three rows", {
        key: raster_mode2_rendered[key]
        for key in ("mode", "helper", "byte_count", "coord", "dest_base", "x", "y", "payload", "rows")
    }, {
        "mode": 2,
        "helper": 0x01F920,
        "byte_count": 2,
        "coord": 0x0001,
        "dest_base": 0x02,
        "x": 16,
        "y": 0,
        "payload": bytes.fromhex("f0 0f"),
        "rows": [
            "................############................############........",
            "................############................############........",
            "................############................############........",
        ],
    }))
    raster_mode2_shifted_page_record: dict[str, object] = {"bucket_array": {}}
    raster_mode2_shifted_page_result = queue_raster_row_to_page_record_via_13070(
        raster_mode2_shifted_page_record,
        {"x": 20, "y": 0, "byte_count": 2, "mode": 2},
        bytes.fromhex("f0 0f"),
    )
    raster_mode2_shifted_bucket_array = raster_mode2_shifted_page_record["bucket_array"]
    assert isinstance(raster_mode2_shifted_bucket_array, dict)
    raster_mode2_shifted_object = bytes(raster_mode2_shifted_bucket_array[0][0])
    raster_mode2_shifted_rendered = render_encoded_raster_object_via_1f88e(data, raster_mode2_shifted_object)
    checks.append(assert_equal("0x13070/0x13250 raster mode-2 row queues non-byte-aligned encoded-span object", {
        "result": {
            key: raster_mode2_shifted_page_result[key]
            for key in ("path", "allocated", "bucket_index", "key", "mode", "byte_count_before", "byte_count_after", "capacity", "object_size")
        },
        "object": raster_mode2_shifted_object,
    }, {
        "result": {
            "path": "raster-page-record",
            "allocated": True,
            "bucket_index": 0,
            "key": 0x0401,
            "mode": 2,
            "byte_count_before": 2,
            "byte_count_after": 0,
            "capacity": 2,
            "object_size": 0x0C,
        },
        "object": bytes.fromhex("00 00 00 00 80 02 00 02 04 01 f0 0f"),
    }))
    checks.append(assert_equal("0x1f88e mode-2 raster object renders sub-byte shifted expanded rows", {
        key: raster_mode2_shifted_rendered[key]
        for key in ("mode", "helper", "byte_count", "coord", "dest_base", "x", "y", "rows_in_band", "remaining_after_band", "payload", "rows")
    }, {
        "mode": 2,
        "helper": 0x01F920,
        "byte_count": 2,
        "coord": 0x0401,
        "dest_base": 0x02,
        "x": 20,
        "y": 0,
        "rows_in_band": 3,
        "remaining_after_band": 0,
        "payload": bytes.fromhex("f0 0f"),
        "rows": [
            "....................############................############........",
            "....................############................############........",
            "....................############................############........",
        ],
    }))
    raster_mode2_clipped_page_record: dict[str, object] = {"bucket_array": {}}
    raster_mode2_clipped_page_result = queue_raster_row_to_page_record_via_13070(
        raster_mode2_clipped_page_record,
        {"x": 16, "y": 15, "byte_count": 2, "mode": 2},
        bytes.fromhex("f0 0f"),
    )
    raster_mode2_clipped_bucket_array = raster_mode2_clipped_page_record["bucket_array"]
    assert isinstance(raster_mode2_clipped_bucket_array, dict)
    raster_mode2_clipped_object = bytes(raster_mode2_clipped_bucket_array[0][0])
    raster_mode2_clipped_rendered = render_encoded_raster_object_via_1f88e(data, raster_mode2_clipped_object, band_rows=16)
    checks.append(assert_equal("0x13070/0x13250 raster mode-2 row queues band-clipped encoded-span object", {
        "result": {
            key: raster_mode2_clipped_page_result[key]
            for key in ("path", "allocated", "bucket_index", "key", "mode", "byte_count_before", "byte_count_after", "capacity", "object_size")
        },
        "object": raster_mode2_clipped_object,
    }, {
        "result": {
            "path": "raster-page-record",
            "allocated": True,
            "bucket_index": 0,
            "key": 0xF001,
            "mode": 2,
            "byte_count_before": 2,
            "byte_count_after": 0,
            "capacity": 2,
            "object_size": 0x0C,
        },
        "object": bytes.fromhex("00 00 00 00 80 02 00 02 f0 01 f0 0f"),
    }))
    checks.append(assert_equal("0x1f88e mode-2 raster object clips current-band rows and continues in fallback buffer", {
        key: raster_mode2_clipped_rendered[key]
        for key in ("mode", "helper", "byte_count", "coord", "dest_base", "x", "y", "rows_in_band", "remaining_after_band", "payload", "rows", "fallback_rows")
    }, {
        "mode": 2,
        "helper": 0x01F920,
        "byte_count": 2,
        "coord": 0xF001,
        "dest_base": 0x1E2,
        "x": 16,
        "y": 15,
        "rows_in_band": 1,
        "remaining_after_band": 2,
        "payload": bytes.fromhex("f0 0f"),
        "rows": ["." * 64] * 15 + [
            "................############................############........",
        ],
        "fallback_rows": [
            "................############................############........",
            "................############................############........",
        ],
    }))
    raster_mode3_page_record: dict[str, object] = {"bucket_array": {}}
    raster_mode3_page_result = queue_raster_row_to_page_record_via_13070(
        raster_mode3_page_record,
        {"x": 16, "y": 0, "byte_count": 2, "mode": 3},
        bytes.fromhex("f0 0f"),
    )
    raster_mode3_bucket_array = raster_mode3_page_record["bucket_array"]
    assert isinstance(raster_mode3_bucket_array, dict)
    raster_mode3_object = bytes(raster_mode3_bucket_array[0][0])
    raster_mode3_rendered = render_encoded_raster_object_via_1f88e(data, raster_mode3_object)
    checks.append(assert_equal("0x13070/0x13250 raster mode-3 row queues encoded-span object", {
        "result": {
            key: raster_mode3_page_result[key]
            for key in ("path", "allocated", "bucket_index", "key", "mode", "byte_count_before", "byte_count_after", "capacity", "object_size")
        },
        "object": raster_mode3_object,
    }, {
        "result": {
            "path": "raster-page-record",
            "allocated": True,
            "bucket_index": 0,
            "key": 0x0001,
            "mode": 3,
            "byte_count_before": 2,
            "byte_count_after": 0,
            "capacity": 2,
            "object_size": 0x0C,
        },
        "object": bytes.fromhex("00 00 00 00 80 03 00 02 00 01 f0 0f"),
    }))
    checks.append(assert_equal("0x1f88e mode-3 raster object expands queued bytes into four rows", {
        key: raster_mode3_rendered[key]
        for key in ("mode", "helper", "byte_count", "coord", "dest_base", "x", "y", "payload", "rows")
    }, {
        "mode": 3,
        "helper": 0x01F9C6,
        "byte_count": 2,
        "coord": 0x0001,
        "dest_base": 0x02,
        "x": 16,
        "y": 0,
        "payload": bytes.fromhex("f0 0f"),
        "rows": [
            "................################................................################",
            "................################................................################",
            "................################................................################",
            "................################................................################",
        ],
    }))
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
    multi_printable_stream = render_multi_printable_stream(
        data,
        resources,
        b"!!",
        0x440946B4,
        cursor_x=pack12(10),
        cursor_y=pack12(21),
        default_advance=pack12(16),
    )
    multi_printable_combined = multi_printable_stream["combined"]
    multi_printable_rendered = multi_printable_stream["rendered"]
    assert isinstance(multi_printable_combined, dict)
    assert isinstance(multi_printable_rendered, dict)
    checks.append(assert_equal("two printable byte stream combines compact text entries", {
        "stream": multi_printable_stream["stream"],
        "advances": multi_printable_stream["advances"],
        "combined": {
            key: multi_printable_combined[key]
            for key in ("object", "selector", "bucket_index", "count", "glyphs", "coords")
        },
        "rendered": {key: multi_printable_rendered[key] for key in ("selector", "context_slot", "count", "payload")},
        "final_cursor_x": multi_printable_stream["final_cursor_x"],
    }, {
        "stream": b"!!",
        "advances": [
            {"cursor_before": pack12(10), "default_advance": pack12(16), "cursor_after": pack12(26)},
            {"cursor_before": pack12(26), "default_advance": pack12(16), "cursor_after": pack12(42)},
        ],
        "combined": {
            "object": bytes.fromhex("00 00 00 00 00 00 00 02 20 00 01 20 00 02"),
            "selector": 0,
            "bucket_index": 0,
            "count": 2,
            "glyphs": [0x20, 0x20],
            "coords": [0x0001, 0x0002],
        },
        "rendered": {
            "selector": 0,
            "context_slot": 0,
            "count": 2,
            "payload": bytes.fromhex("00 02 20 00 01 20 00 02"),
        },
        "final_cursor_x": pack12(42),
    }))
    checks.append(assert_equal("two printable byte stream renders advanced glyph rows", multi_printable_rendered["rows"], [
        "................####............####" if row == "####" else "." * 36
        for row in line_printer_glyph32_rows
    ]))
    line_printer_hmi = builtin_flagged_hmi_from_context(resources, 0x440946B4)
    checks.append(assert_equal("line-printer flagged HMI metric via 0x10550", line_printer_hmi, {
        "base": 0x0146B4,
        "metric_flag": 0,
        "raw_metric": 0x00480000,
        "hmi": pack12(18),
    }))
    metric_printable_stream = render_multi_printable_stream(
        data,
        resources,
        b"!!",
        0x440946B4,
        cursor_x=pack12(10),
        cursor_y=pack12(21),
        default_advance=line_printer_hmi["hmi"],
    )
    metric_printable_combined = metric_printable_stream["combined"]
    metric_printable_rendered = metric_printable_stream["rendered"]
    assert isinstance(metric_printable_combined, dict)
    assert isinstance(metric_printable_rendered, dict)
    checks.append(assert_equal("two printable byte stream with line-printer HMI renders subbyte entry", {
        "stream": metric_printable_stream["stream"],
        "advances": metric_printable_stream["advances"],
        "combined": {
            key: metric_printable_combined[key]
            for key in ("object", "selector", "bucket_index", "count", "glyphs", "coords")
        },
        "rendered": {
            key: metric_printable_rendered[key]
            for key in ("selector", "context_slot", "count", "rendered", "payload")
        },
        "final_cursor_x": metric_printable_stream["final_cursor_x"],
    }, {
        "stream": b"!!",
        "advances": [
            {"cursor_before": pack12(10), "default_advance": pack12(18), "cursor_after": pack12(28)},
            {"cursor_before": pack12(28), "default_advance": pack12(18), "cursor_after": pack12(46)},
        ],
        "combined": {
            "object": bytes.fromhex("00 00 00 00 00 00 00 02 20 00 01 20 02 02"),
            "selector": 0,
            "bucket_index": 0,
            "count": 2,
            "glyphs": [0x20, 0x20],
            "coords": [0x0001, 0x0202],
        },
        "rendered": {
            "selector": 0,
            "context_slot": 0,
            "count": 2,
            "rendered": [
                {
                    "glyph": 0x20,
                    "coord": 0x0001,
                    "dest_base": 0x02,
                    "x": 16,
                    "y": 0,
                    "a001": 0x00,
                    "span": 1,
                    "rows": 22,
                    "width": 4,
                    "helper": 0x01FA5C,
                },
                {
                    "glyph": 0x20,
                    "coord": 0x0202,
                    "dest_base": 0x04,
                    "x": 34,
                    "y": 0,
                    "a001": 0x12,
                    "span": 1,
                    "rows": 22,
                    "width": 4,
                    "helper": 0x01FA5C,
                },
            ],
            "payload": bytes.fromhex("00 02 20 00 01 20 02 02"),
        },
        "final_cursor_x": pack12(46),
    }))
    checks.append(assert_equal("two printable byte stream with line-printer HMI renders subbyte rows", metric_printable_rendered["rows"], [
        "................####..............####" if row == "####" else "." * 38
        for row in line_printer_glyph32_rows
    ]))
    mixed_stream = render_mixed_printable_control_stream(
        data,
        resources,
        b"\x1b&k1G!\r!",
        0x440946B4,
        control_fixture_state(
            cursor_x=pack12(10),
            cursor_y=pack12(21),
            left_margin=pack12(5),
            vmi=pack12(3),
            hmi=line_printer_hmi["hmi"],
            pending_width=1,
            pending_text=0,
            span_flush_enable=1,
        ),
        default_advance=line_printer_hmi["hmi"],
    )
    mixed_combined = mixed_stream["combined"]
    mixed_rendered = mixed_stream["rendered"]
    mixed_final_state = mixed_stream["final_state"]
    assert isinstance(mixed_combined, dict)
    assert isinstance(mixed_rendered, dict)
    assert isinstance(mixed_final_state, dict)
    mixed_events = mixed_stream["events"]
    assert isinstance(mixed_events, list)
    mixed_event_summary: list[dict[str, object]] = []
    for event in mixed_events:
        assert isinstance(event, dict)
        if event["kind"] == "escape":
            mixed_event_summary.append({
                "kind": "escape",
                "sequence": event["sequence"],
                "line_termination": event["line_termination"],
            })
        elif event["kind"] == "control":
            mixed_event_summary.append({
                "kind": "control",
                "byte": event["byte"],
                "cursor_before": event["cursor_before"],
                "cursor_after": event["cursor_after"],
                "page_roots": event["page_roots"],
                "span_flushes": event["span_flushes"],
            })
        else:
            bucket = event["bucket"]
            positioned = event["positioned"]
            assert isinstance(bucket, dict)
            assert isinstance(positioned, dict)
            positioned_source = positioned["source"]
            assert isinstance(positioned_source, dict)
            mixed_event_summary.append({
                "kind": "printable",
                "byte": event["byte"],
                "cursor_before": event["cursor_before"],
                "cursor_after": event["cursor_after"],
                "positioned_xy": (positioned_source["x"], positioned_source["y"]),
                "coord": bucket["coord"],
            })
    checks.append(assert_equal("mixed printable/control stream applies CR+LF before second glyph", {
        "stream": mixed_stream["stream"],
        "events": mixed_event_summary,
        "combined": {
            key: mixed_combined[key]
            for key in ("object", "selector", "bucket_index", "count", "glyphs", "coords")
        },
        "rendered": {
            key: mixed_rendered[key]
            for key in ("selector", "context_slot", "count", "rendered", "payload")
        },
        "final_state": select_keys(mixed_final_state, ("cursor_x", "cursor_y", "line_termination", "page_roots", "span_flushes", "post_flushes")),
    }, {
        "stream": b"\x1b&k1G!\r!",
        "events": [
            {"kind": "escape", "sequence": b"\x1b&k1G", "line_termination": 0x80},
            {
                "kind": "printable",
                "byte": 0x21,
                "cursor_before": pack12(10),
                "cursor_after": pack12(28),
                "positioned_xy": (16, 0),
                "coord": 0x0001,
            },
            {
                "kind": "control",
                "byte": 0x0D,
                "cursor_before": (pack12(28), pack12(21)),
                "cursor_after": (pack12(5), pack12(24)),
                "page_roots": 1,
                "span_flushes": 1,
            },
            {
                "kind": "printable",
                "byte": 0x21,
                "cursor_before": pack12(5),
                "cursor_after": pack12(23),
                "positioned_xy": (11, 3),
                "coord": 0x3B00,
            },
        ],
        "combined": {
            "object": bytes.fromhex("00 00 00 00 00 00 00 02 20 00 01 20 3b 00"),
            "selector": 0,
            "bucket_index": 0,
            "count": 2,
            "glyphs": [0x20, 0x20],
            "coords": [0x0001, 0x3B00],
        },
        "rendered": {
            "selector": 0,
            "context_slot": 0,
            "count": 2,
            "rendered": [
                {
                    "glyph": 0x20,
                    "coord": 0x0001,
                    "dest_base": 0x02,
                    "x": 16,
                    "y": 0,
                    "a001": 0x00,
                    "span": 1,
                    "rows": 22,
                    "width": 4,
                    "helper": 0x01FA5C,
                },
                {
                    "glyph": 0x20,
                    "coord": 0x3B00,
                    "dest_base": 0x60,
                    "x": 11,
                    "y": 3,
                    "a001": 0x1B,
                    "span": 1,
                    "rows": 22,
                    "width": 4,
                    "helper": 0x01FA5C,
                },
            ],
            "payload": bytes.fromhex("00 02 20 00 01 20 3b 00"),
        },
        "final_state": {
            "cursor_x": pack12(23),
            "cursor_y": pack12(24),
            "line_termination": 0x80,
            "page_roots": 1,
            "span_flushes": 1,
            "post_flushes": 1,
        },
    }))
    expected_mixed_rows: list[str] = []
    for row_index in range(25):
        row_bits = [False] * 20
        if row_index < len(line_printer_glyph32_rows) and line_printer_glyph32_rows[row_index] == "####":
            for bit in range(4):
                row_bits[16 + bit] = True
        shifted_index = row_index - 3
        if 0 <= shifted_index < len(line_printer_glyph32_rows):
            shifted_bits = [line_printer_glyph32_rows[shifted_index] == "####" and bit < 4 for bit in range(8)]
            for bit, value in enumerate(shifted_bits):
                if 11 + bit < len(row_bits):
                    row_bits[11 + bit] = value
        expected_mixed_rows.append("".join("#" if bit else "." for bit in row_bits))
    checks.append(assert_equal("mixed printable/control stream renders post-CR glyph rows", mixed_rendered["rows"], expected_mixed_rows))
    mixed_page_record_stream = render_mixed_printable_control_page_record_stream(
        data,
        resources,
        b"\x1b&k1G!\r!",
        0x440946B4,
        control_fixture_state(
            cursor_x=pack12(10),
            cursor_y=pack12(21),
            left_margin=pack12(5),
            vmi=pack12(3),
            hmi=line_printer_hmi["hmi"],
            pending_width=1,
            pending_text=0,
            span_flush_enable=1,
        ),
        default_advance=line_printer_hmi["hmi"],
    )
    mixed_page_record_object = mixed_page_record_stream["bucket_object"]
    mixed_page_record_rendered = mixed_page_record_stream["rendered"]
    mixed_page_record_bridged = mixed_page_record_stream["bridged_record"]
    assert isinstance(mixed_page_record_object, bytes)
    assert isinstance(mixed_page_record_rendered, dict)
    assert isinstance(mixed_page_record_bridged, dict)
    mixed_page_record_event_summary: list[dict[str, object]] = []
    mixed_page_record_events = mixed_page_record_stream["events"]
    assert isinstance(mixed_page_record_events, list)
    for event in mixed_page_record_events:
        assert isinstance(event, dict)
        if event["kind"] == "escape":
            mixed_page_record_event_summary.append({
                "kind": "escape",
                "sequence": event["sequence"],
                "line_termination": event["line_termination"],
            })
        elif event["kind"] == "control":
            mixed_page_record_event_summary.append({
                "kind": "control",
                "byte": event["byte"],
                "cursor_before": event["cursor_before"],
                "cursor_after": event["cursor_after"],
                "page_roots": event["page_roots"],
                "span_flushes": event["span_flushes"],
            })
        else:
            page_result = event["page_result"]
            positioned = event["positioned"]
            assert isinstance(page_result, dict)
            assert isinstance(positioned, dict)
            positioned_source = positioned["source"]
            assert isinstance(positioned_source, dict)
            mixed_page_record_event_summary.append({
                "kind": "printable",
                "byte": event["byte"],
                "cursor_before": event["cursor_before"],
                "cursor_after": event["cursor_after"],
                "positioned_xy": (positioned_source["x"], positioned_source["y"]),
                "coord": page_result["coord"],
                "allocated": page_result["allocated"],
                "count_before": page_result["count_before"],
                "count_after": page_result["count_after"],
                "bucket_index": page_result["bucket_index"],
            })
    checks.append(assert_equal("mixed printable/control page-record stream queues through 0x1387c", {
        "stream": mixed_page_record_stream["stream"],
        "events": mixed_page_record_event_summary,
        "bucket_index": mixed_page_record_stream["bucket_index"],
        "object_prefix": mixed_page_record_object[:14],
        "object_size": len(mixed_page_record_object),
        "final_state": select_keys(mixed_page_record_stream["final_state"], ("cursor_x", "cursor_y", "line_termination", "page_roots", "span_flushes", "post_flushes")),
    }, {
        "stream": b"\x1b&k1G!\r!",
        "events": [
            {"kind": "escape", "sequence": b"\x1b&k1G", "line_termination": 0x80},
            {
                "kind": "printable",
                "byte": 0x21,
                "cursor_before": pack12(10),
                "cursor_after": pack12(28),
                "positioned_xy": (16, 0),
                "coord": 0x0001,
                "allocated": True,
                "count_before": 0,
                "count_after": 1,
                "bucket_index": 0,
            },
            {
                "kind": "control",
                "byte": 0x0D,
                "cursor_before": (pack12(28), pack12(21)),
                "cursor_after": (pack12(5), pack12(24)),
                "page_roots": 1,
                "span_flushes": 1,
            },
            {
                "kind": "printable",
                "byte": 0x21,
                "cursor_before": pack12(5),
                "cursor_after": pack12(23),
                "positioned_xy": (11, 3),
                "coord": 0x3B00,
                "allocated": False,
                "count_before": 1,
                "count_after": 2,
                "bucket_index": 0,
            },
        ],
        "bucket_index": 0,
        "object_prefix": bytes.fromhex("00 00 00 00 00 00 00 02 20 00 01 20 3b 00"),
        "object_size": 0x26,
        "final_state": {
            "cursor_x": pack12(23),
            "cursor_y": pack12(24),
            "line_termination": 0x80,
            "page_roots": 1,
            "span_flushes": 1,
            "post_flushes": 1,
        },
    }))
    checks.append(assert_equal("mixed printable/control page-record bridge renders post-CR glyph rows", {
        "bucket_root": mixed_page_record_bridged["bucket_root"],
        "context_slots": mixed_page_record_bridged["context_slots"][:2],
        "rendered": {
            key: mixed_page_record_rendered[key]
            for key in ("selector", "context_slot", "count", "rendered", "payload")
        },
        "rows": mixed_page_record_rendered["rows"],
    }, {
        "bucket_root": mixed_page_record_object,
        "context_slots": (0x440946B4, 0),
        "rendered": {
            "selector": 0,
            "context_slot": 0,
            "count": 2,
            "rendered": mixed_rendered["rendered"],
            "payload": bytes.fromhex("00 02 20 00 01 20 3b 00") + bytes(0x18),
        },
        "rows": expected_mixed_rows,
    }))
    mixed_reset_stream = render_mixed_printable_control_stream(
        data,
        resources,
        b"!\x1bE",
        0x440946B4,
        reset_fixture_state(
            cursor_x=pack12(10),
            cursor_y=pack12(21),
            font_hmi_clear=line_printer_hmi["hmi"],
        ),
        default_advance=line_printer_hmi["hmi"],
    )
    mixed_reset_combined = mixed_reset_stream["combined"]
    mixed_reset_rendered = mixed_reset_stream["rendered"]
    mixed_reset_final_state = mixed_reset_stream["final_state"]
    assert isinstance(mixed_reset_combined, dict)
    assert isinstance(mixed_reset_rendered, dict)
    assert isinstance(mixed_reset_final_state, dict)
    mixed_reset_events = mixed_reset_stream["events"]
    assert isinstance(mixed_reset_events, list)
    mixed_reset_event_summary: list[dict[str, object]] = []
    for event in mixed_reset_events:
        assert isinstance(event, dict)
        if event["kind"] == "printable":
            bucket = event["bucket"]
            positioned = event["positioned"]
            assert isinstance(bucket, dict)
            assert isinstance(positioned, dict)
            positioned_source = positioned["source"]
            assert isinstance(positioned_source, dict)
            mixed_reset_event_summary.append({
                "kind": "printable",
                "byte": event["byte"],
                "cursor_before": event["cursor_before"],
                "cursor_after": event["cursor_after"],
                "positioned_xy": (positioned_source["x"], positioned_source["y"]),
                "coord": bucket["coord"],
            })
        else:
            mixed_reset_event_summary.append({
                "kind": "reset",
                "sequence": event["sequence"],
                "current_page_root_before": event["current_page_root_before"],
                "current_page_root_after": event["current_page_root_after"],
                "page_publications": event["page_publications"],
                "page_root_clears": event["page_root_clears"],
                "span_flushes": event["span_flushes"],
                "post_flushes": event["post_flushes"],
                "hmi": event["hmi"],
                "orientation": event["orientation"],
                "data_chain_ptr": event["data_chain_ptr"],
                "reset_status": event["reset_status"],
            })
    checks.append(assert_equal("mixed printable/reset stream publishes page root after text", {
        "stream": mixed_reset_stream["stream"],
        "events": mixed_reset_event_summary,
        "combined": {
            key: mixed_reset_combined[key]
            for key in ("object", "selector", "bucket_index", "count", "glyphs", "coords")
        },
        "rendered": {
            key: mixed_reset_rendered[key]
            for key in ("selector", "context_slot", "count", "rendered", "payload")
        },
        "final_state": select_keys(mixed_reset_final_state, (
            "cursor_x",
            "cursor_y",
            "current_page_root",
            "page_publications",
            "page_root_clears",
            "span_flushes",
            "post_flushes",
            "pending_width",
            "hmi",
            "orientation",
            "data_chain_ptr",
            "reset_status",
        )),
    }, {
        "stream": b"!\x1bE",
        "events": [
            {
                "kind": "printable",
                "byte": 0x21,
                "cursor_before": pack12(10),
                "cursor_after": pack12(28),
                "positioned_xy": (16, 0),
                "coord": 0x0001,
            },
            {
                "kind": "reset",
                "sequence": b"\x1bE",
                "current_page_root_before": 1,
                "current_page_root_after": 0,
                "page_publications": 1,
                "page_root_clears": 1,
                "span_flushes": 1,
                "post_flushes": 1,
                "hmi": line_printer_hmi["hmi"],
                "orientation": 0,
                "data_chain_ptr": 0x782D3E,
                "reset_status": 0,
            },
        ],
        "combined": {
            "object": bytes.fromhex("00 00 00 00 00 00 00 01 20 00 01"),
            "selector": 0,
            "bucket_index": 0,
            "count": 1,
            "glyphs": [0x20],
            "coords": [0x0001],
        },
        "rendered": {
            "selector": 0,
            "context_slot": 0,
            "count": 1,
            "rendered": [
                {
                    "glyph": 0x20,
                    "coord": 0x0001,
                    "dest_base": 0x02,
                    "x": 16,
                    "y": 0,
                    "a001": 0x00,
                    "span": 1,
                    "rows": 22,
                    "width": 4,
                    "helper": 0x01FA5C,
                },
            ],
            "payload": bytes.fromhex("00 01 20 00 01"),
        },
        "final_state": {
            "cursor_x": pack12(28),
            "cursor_y": pack12(21),
            "current_page_root": 0,
            "page_publications": 1,
            "page_root_clears": 1,
            "span_flushes": 1,
            "post_flushes": 1,
            "pending_width": 0,
            "hmi": line_printer_hmi["hmi"],
            "orientation": 0,
            "data_chain_ptr": 0x782D3E,
            "reset_status": 0,
        },
    }))
    checks.append(assert_equal("mixed printable/reset stream keeps pre-reset text rows renderable", mixed_reset_rendered["rows"], positioned_mode0["rows"]))
    mixed_reset_page_record_stream = render_mixed_printable_control_page_record_stream(
        data,
        resources,
        b"!\x1bE",
        0x440946B4,
        reset_fixture_state(
            cursor_x=pack12(10),
            cursor_y=pack12(21),
            font_hmi_clear=line_printer_hmi["hmi"],
        ),
        default_advance=line_printer_hmi["hmi"],
    )
    mixed_reset_page_record_object = mixed_reset_page_record_stream["bucket_object"]
    mixed_reset_page_record_rendered = mixed_reset_page_record_stream["rendered"]
    mixed_reset_page_record_bridged = mixed_reset_page_record_stream["bridged_record"]
    assert isinstance(mixed_reset_page_record_object, bytes)
    assert isinstance(mixed_reset_page_record_rendered, dict)
    assert isinstance(mixed_reset_page_record_bridged, dict)
    mixed_reset_page_record_event_summary: list[dict[str, object]] = []
    mixed_reset_page_record_events = mixed_reset_page_record_stream["events"]
    assert isinstance(mixed_reset_page_record_events, list)
    for event in mixed_reset_page_record_events:
        assert isinstance(event, dict)
        if event["kind"] == "printable":
            page_result = event["page_result"]
            positioned = event["positioned"]
            assert isinstance(page_result, dict)
            assert isinstance(positioned, dict)
            positioned_source = positioned["source"]
            assert isinstance(positioned_source, dict)
            mixed_reset_page_record_event_summary.append({
                "kind": "printable",
                "byte": event["byte"],
                "cursor_before": event["cursor_before"],
                "cursor_after": event["cursor_after"],
                "positioned_xy": (positioned_source["x"], positioned_source["y"]),
                "coord": page_result["coord"],
                "allocated": page_result["allocated"],
                "count_before": page_result["count_before"],
                "count_after": page_result["count_after"],
                "bucket_index": page_result["bucket_index"],
            })
        else:
            mixed_reset_page_record_event_summary.append({
                "kind": "reset",
                "sequence": event["sequence"],
                "current_page_root_before": event["current_page_root_before"],
                "current_page_root_after": event["current_page_root_after"],
                "page_publications": event["page_publications"],
                "page_root_clears": event["page_root_clears"],
                "span_flushes": event["span_flushes"],
                "post_flushes": event["post_flushes"],
                "hmi": event["hmi"],
                "orientation": event["orientation"],
                "data_chain_ptr": event["data_chain_ptr"],
                "reset_status": event["reset_status"],
            })
    checks.append(assert_equal("mixed printable/reset page-record stream queues through 0x1387c before reset", {
        "stream": mixed_reset_page_record_stream["stream"],
        "events": mixed_reset_page_record_event_summary,
        "bucket_index": mixed_reset_page_record_stream["bucket_index"],
        "object_prefix": mixed_reset_page_record_object[:11],
        "object_size": len(mixed_reset_page_record_object),
        "final_state": select_keys(mixed_reset_page_record_stream["final_state"], (
            "cursor_x",
            "cursor_y",
            "current_page_root",
            "page_publications",
            "page_root_clears",
            "span_flushes",
            "post_flushes",
            "pending_width",
            "hmi",
            "orientation",
            "data_chain_ptr",
            "reset_status",
        )),
    }, {
        "stream": b"!\x1bE",
        "events": [
            {
                "kind": "printable",
                "byte": 0x21,
                "cursor_before": pack12(10),
                "cursor_after": pack12(28),
                "positioned_xy": (16, 0),
                "coord": 0x0001,
                "allocated": True,
                "count_before": 0,
                "count_after": 1,
                "bucket_index": 0,
            },
            {
                "kind": "reset",
                "sequence": b"\x1bE",
                "current_page_root_before": 1,
                "current_page_root_after": 0,
                "page_publications": 1,
                "page_root_clears": 1,
                "span_flushes": 1,
                "post_flushes": 1,
                "hmi": line_printer_hmi["hmi"],
                "orientation": 0,
                "data_chain_ptr": 0x782D3E,
                "reset_status": 0,
            },
        ],
        "bucket_index": 0,
        "object_prefix": bytes.fromhex("00 00 00 00 00 00 00 01 20 00 01"),
        "object_size": 0x26,
        "final_state": {
            "cursor_x": pack12(28),
            "cursor_y": pack12(21),
            "current_page_root": 0,
            "page_publications": 1,
            "page_root_clears": 1,
            "span_flushes": 1,
            "post_flushes": 1,
            "pending_width": 0,
            "hmi": line_printer_hmi["hmi"],
            "orientation": 0,
            "data_chain_ptr": 0x782D3E,
            "reset_status": 0,
        },
    }))
    checks.append(assert_equal("mixed printable/reset page-record bridge keeps pre-reset rows renderable", {
        "bucket_root": mixed_reset_page_record_bridged["bucket_root"],
        "context_slots": mixed_reset_page_record_bridged["context_slots"][:2],
        "rendered": {
            key: mixed_reset_page_record_rendered[key]
            for key in ("selector", "context_slot", "count", "rendered", "payload")
        },
        "rows": mixed_reset_page_record_rendered["rows"],
    }, {
        "bucket_root": mixed_reset_page_record_object,
        "context_slots": (0x440946B4, 0),
        "rendered": {
            "selector": 0,
            "context_slot": 0,
            "count": 1,
            "rendered": mixed_reset_rendered["rendered"],
            "payload": bytes.fromhex("00 01 20 00 01") + bytes(0x1B),
        },
        "rows": positioned_mode0["rows"],
    }))

    lines.append("## Host Byte Fetch Fixtures")
    lines.append("")
    lines.append("These fixtures model the normalized byte-source priority of routine `0xa904` before the main parser or payload readers see `D7`. They are not electrical interface emulation, but they pin the order and state side effects needed by a byte-stream reproduction harness.")
    lines.append("")
    lines.append("- `0x780e66 != 0` plus `0x780e3b != 0` returns `D7 = -1` before buffered or direct sources are consumed.")
    lines.append("- A pending `0x7821cd` service flag runs helper `0x10cc(0x780202)` and retries before the first LIFO source is consumed.")
    lines.append("- A current data-chain end marker runs helper `0xe22c` and retries, then the second LIFO source can provide the byte.")
    lines.append("- In buffered mode `0x780e40 == 0`, the ring source wins before direct hardware fallback.")
    lines.append("- Direct mode `1` returns the `0x8801` byte after `0x8e01.4` is ready, preserves `0x1a` while reporting it through `0x9ec0`, and clears the handshake/timeout state.")
    lines.append("- Direct mode `2` returns the `0xfffee001` byte when `0xfffee005.0` is ready, sets `0x7828ec`, clears the timeout state, and sets bit 6 in the `0x7828fb` control shadow.")
    lines.append("")
    lines.append("| Fixture | Source | D7 | Events |")
    lines.append("| --- | --- | ---: | --- |")
    for title, result in (
        ("no-byte branch", host_fetch_no_byte),
        ("service + first LIFO", host_fetch_priority),
        ("data-chain transition + second LIFO", host_fetch_data_chain),
        ("ring source", host_fetch_ring),
        ("direct mode 1", host_fetch_mode1),
        ("direct mode 2", host_fetch_mode2),
    ):
        lines.append(f"| {title} | `{result['source']}` | `{int(result['d7']):d}` | `{result['events']}` |")
    lines.append("")

    lines.append("## PCL Tokenizer and Delayed Payload Fixtures")
    lines.append("")
    lines.append("These fixtures model the six-byte parsed command records built by `0xdaf0` / `0xdb74` and the delayed payload snapshot used by `0x121cc` before handlers such as raster transfer `0x105d0` consume following data bytes.")
    lines.append("")
    lines.append("- `300r150R` produces two records because the first numeric record has flag bit 7 set and the next byte is still in the parameter/intermediate range; the lowercase final stays in the same parser family until the uppercase final.")
    lines.append("- Signed numeric parsing sets flag byte `0x81`, caps fractional storage to four digits, skips excess fractional digits, and stores signed word fields.")
    lines.append("- A semicolon final is stored in the record but returns `D7 = 0`, matching the command-combining continuation path.")
    lines.append("- `0x121cc` snapshots pending flag `1`, the saved handler longword, and the current six-byte parsed command record; `0x12218` restores that record at `0x78299e` and dispatches the saved handler when alternate/data mode is clear.")
    lines.append("- In alternate/data mode, `0x12358` either calls wrapper `0x1228a`, which consumes the absolute parsed byte count through `0x12328` without echo, or consumes only positive counts itself while echoing each normalized byte through `0xe002`; both paths use `0xdace`, where payload control `1a 58` calls `0xd99a` and contributes byte `00`.")
    lines.append("")
    lines.append(f"- chained resolution record bytes: `{' '.join(f'{byte:02x}' for byte in tokenizer_chained_resolution['record_bytes'])}`")
    lines.append(f"- signed/fraction record bytes: `{' '.join(f'{byte:02x}' for byte in tokenizer_signed_fraction['record_bytes'])}`, scratch `{tokenizer_signed_fraction['scratch']!r}`")
    lines.append(f"- semicolon continuation record bytes: `{' '.join(f'{byte:02x}' for byte in tokenizer_semicolon['record_bytes'])}`, returned D7 `{tokenizer_semicolon['returned_d7']}`")
    lines.append(f"- delayed raster transfer snapshot: `{' '.join(f'{byte:02x}' for byte in delayed_raster_transfer['snapshot_bytes'])}`")
    lines.append(f"- alternate wrapper consume values: `{alternate_payload_wrapper['values']}`, echoed `{alternate_payload_wrapper['echoed']}`, control hits `{alternate_payload_wrapper['control_hits']}`")
    lines.append(f"- alternate direct consume values: `{alternate_payload_direct['values']}`, echoed `{alternate_payload_direct['echoed']}`, negative-count values `{alternate_payload_direct_negative['values']}`")
    lines.append("")

    lines.append("## Page Geometry Command Fixtures")
    lines.append("")
    lines.append("These fixtures model the ROM table lookups at `0x9d16`/`0x9d4e`/`0x9d86`/`0x9dbe`, the `ESC &l#A` page-size handler at `0xfc74`, and the `ESC &l#O` orientation handler at `0x10220`.")
    lines.append("")
    lines.append("- Page-code lookup masks the internal code with `0x7f`; PCL `80` stores internal code `0x88`, which reads table index `8`.")
    lines.append("- `ESC &l#A` maps PCL values `1`, `2`, `3`, `26`, `80`, `81`, `90`, and `91` to internal page codes, finalizes pending page state, updates width/height words, then recomputes portrait or landscape extents.")
    lines.append("- `ESC &l#O` accepts only values `0` and `1`; changing orientation finalizes pending page state, swaps active width/height in landscape, changes the vertical offset source from `60` to `50`, and reloads the orientation margin thresholds through `0x103ea`.")
    lines.append("")
    lines.append(f"- Letter portrait from `ESC &l1A`: code `{letter_page['page_code']}`, width `{letter_page['width']}`, height `{letter_page['height']}`, margin `{letter_page['margin_reference']}`, top offset `{letter_page['top_offset']}`")
    lines.append(f"- PCL 80 envelope lookup: code `0x{pcl80_page['page_code']:02x}`, width `{pcl80_page['width']}`, height `{pcl80_page['height']}`, margin `{pcl80_page['margin_reference']}`")
    lines.append(f"- Letter landscape from `ESC &l1O`: active `{landscape_letter['active_width']}x{landscape_letter['active_height']}`, margin `{landscape_letter['margin_reference']}`, printable extent `{landscape_letter['printable_extent']}`, top offset `{landscape_letter['top_offset']}`")
    lines.append(f"- Landscape thresholds loaded by `0x103ea`: `{[landscape_letter[key] for key in ('portrait_landscape_threshold_6', 'portrait_landscape_threshold_2', 'portrait_landscape_threshold_1', 'portrait_landscape_threshold_5')]}`")
    lines.append("")

    lines.append("## Macro Command and Data-Chain Fixtures")
    lines.append("")
    lines.append("These fixtures model the `ESC &f#Y` macro-id handler at `0xe112`, the `ESC &f#X` macro-control dispatch at `0xdd08`, and the macro replay data-chain frame built by `0xe418` for execute/call.")
    lines.append("")
    lines.append("- `0xe112` stores the absolute parsed macro id word in `0x783164`.")
    lines.append("- Selector `0` starts macro definition, clears/reuses the selected 12-byte record, sets alternate/data mode, and for lowercase `x` seeds the stored byte stream with `ESC &f`; selector `1` stops definition and clears empty/auto-prefix-only records.")
    lines.append("- Selectors `2` and `3` replay an existing macro by pushing a data-chain frame whose byte `+8` is `4` and byte `+9` is the execute/call selector.")
    lines.append("- Selectors `4`/`5` enable/disable overlay state, `6`/`7`/`8` delete all/temporary/current macros, and `9`/`10` toggle the temporary/permanent byte at record `+0x0a`.")
    lines.append("")
    lines.append(f"- assigned macro id: `{macro_id_state['current_macro_id']}`")
    lines.append(f"- lowercase start payload: `{macro_start['records'][0]['payload']!r}`, stop event `{macro_stop_empty['events'][-1]}`")
    lines.append(f"- execute frame: `{macro_execute['data_chain_frames'][0]}`")
    lines.append(f"- call frame: `{macro_call['data_chain_frames'][0]}`")
    lines.append(f"- permanent survives delete-temporary: `{macro_delete_temporary['records'][0]}`")
    lines.append("")

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
    lines.append("- `ESC &f0S` pushes the horizontal cursor and the vertical cursor plus `0x782dbe` onto the cursor stack; `ESC &f1S` pops, restores horizontal position clamped to active extent minus `1/12`, restores vertical position after subtracting `0x782dbe` and clamps to printable extent minus `1/12`, then clears pending/right-limit flags.")
    lines.append("- The direct-control fixture parser intentionally recognizes only `ESC &k#G`, `ESC E`, and direct control bytes; mixed printable/control/reset coverage is added separately for narrow normal-mode streams, while combined escape sequences and real page-object allocation still need fuller parser-driven fixtures.")
    lines.append("")
    lines.append(f"- cursor stack push entry: `{cursor_stack_pushed['stack'][0]}`")
    lines.append(f"- cursor stack pop cursor: x `0x{int(cursor_stack_popped['cursor_x']):08x}`, y `0x{int(cursor_stack_popped['cursor_y']):08x}`")
    lines.append(f"- cursor stack clamped pop: x `0x{int(cursor_stack_clamped['cursor_x']):08x}`, y `0x{int(cursor_stack_clamped['cursor_y']):08x}`")
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

    lines.append("## `0x1387c` Page-Record Compact Bucket Allocator Fixture")
    lines.append("")
    lines.append("This fixture moves the short text bucket one step closer to the real page-root shape. It models `0x1387c`, which indexes the page-root `+0x1c` bucket array by `0x782a7c`, walks the bucket chain looking for the same selector word at object `+4`, reuses that object when count `+6` is below the caller-supplied capacity, or allocates and links a new object at the bucket head when the matching object is full or missing.")
    lines.append("")
    lines.append("- first allocation: allocated `%s`, bucket `%d`, selector `0x%04x`, count `%d -> %d`, coord `0x%04x`" % (
        page_record_first["allocated"],
        page_record_first["bucket_index"],
        page_record_first["selector"],
        page_record_first["count_before"],
        page_record_first["count_after"],
        page_record_first["coord"],
    ))
    lines.append("- second same-selector insertion: allocated `%s`, chain index `%d`, count `%d -> %d`, coord `0x%04x`" % (
        page_record_second["allocated"],
        page_record_second["chain_index"],
        page_record_second["count_before"],
        page_record_second["count_after"],
        page_record_second["coord"],
    ))
    lines.append(f"- reused object bytes: `{' '.join(f'{byte:02x}' for byte in page_record_chain[0])}`")
    lines.append("- full-object case: a prefilled count-10 object causes `0x1387c` to allocate a new head object while leaving the old object second in the chain.")
    lines.append("- page-record queued rows:")
    lines.extend(f"`{row}`" for row in page_record_short_rendered["rows"])
    lines.append("")

    lines.append("## `0x1edc6` Page-Record Bridge Fixture")
    lines.append("")
    lines.append("This fixture models the render-record bridge at `0x1edc6` after a compact text bucket has been queued under a page/control record through the `0x1387c` model above. The firmware copies page-root `+0x1c` to render-record `+0x18`, page-root `+0x24` to render-record `+0x1c`, page-root `+0x28` to render-record `+0x20`, and the 16 font/context slots from page-root `+0x2c..+0x68` to render-record `+0x24..+0x60`. It then normalizes the two rule/list chains in-place before band rendering.")
    lines.append("")
    lines.append(f"- bridged compact bucket root: `{' '.join(f'{byte:02x}' for byte in bridged_page_record['bucket_root'])}`")
    lines.append("- bridged context slots `[0..1]`: `0x%08x`, `0x%08x`" % (
        bridged_page_record["context_slots"][0],
        bridged_page_record["context_slots"][1],
    ))
    lines.append(f"- normalized `+0x24`/render `+0x1c` rule-list node: `{' '.join(f'{byte:02x}' for byte in bridged_page_record['rule_list'][0])}`")
    lines.append(f"- normalized `+0x28`/render `+0x20` fixed-list node: `{' '.join(f'{byte:02x}' for byte in bridged_page_record['fixed_list'][0])}`")
    lines.append("- producer-shaped rectangle/rule fixtures: `0x13386`/`0x133aa` stores key `0x%04x`, width `0x%04x`, and height `0x%04x` before bridge byte `+5` becomes `0x%02x`; `0x137a2`/`0x136d2` stores key `0x%04x` and extent `0x%04x` before bridge byte `+5` becomes `0x%02x`." % (
        rule_result["computed"]["key"],
        0x0012,
        0x0034,
        rule_bridged["rule_list"][0][5],
        fixed_rule_result["computed"]["key"],
        0x0044,
        fixed_rule_bridged["fixed_list"][0][5],
    ))
    lines.append("- bridged compact rows match the page-record queued rows above.")
    lines.append("- remaining gap: replace this synthetic page/control record with a parser-produced page root and compare the finalized record published by `0xff1e`.")
    lines.append("")

    lines.append("## Parser-Derived Raster State Fixture")
    lines.append("")
    lines.append("This fixture models the raster state fields written by `ESC *t#R` handler `0x10808` and `ESC *r#A` handler `0x1075a` before the existing `0x13070` row-object queue path. It is still a state model rather than a full parser run through `0x121cc` / `0x105d0`, but the encoded raster mode comes from the resolution command threshold instead of being hand-picked.")
    lines.append("")
    lines.append("| Parameter | Encoded mode | Scale word | Limit for extent 255 |")
    lines.append("| ---: | ---: | ---: | ---: |")
    for parameter, expected in parser_raster_resolution_cases:
        lines.append(f"| `{parameter}` | `{expected['mode']}` | `{expected['scale']}` | `{expected['limit']}` |")
    lines.append("")
    lines.append("- `ESC *r1A` with orientation `0` seeds raster origin from cursor-axis longword `0x00100000`, giving baseline word `16`, mode `0`, scale `1`, and limit `30` for extent `255`.")
    lines.append("- `ESC *r0A` starts at the left edge, giving origin `0`, baseline word `0`, mode `0`, scale `1`, and limit `32` for extent `255`.")
    lines.append("- `ESC *rB` handler `0x107fa` clears only the raster active byte, leaving origin/baseline/mode/scale/limit/row counters untouched in this state fixture.")
    lines.append(f"- parser-derived transfer object bytes: `{' '.join(f'{byte:02x}' for byte in parser_raster_object)}`")
    lines.append("- parser-derived rendered row:")
    lines.extend(f"`{row}`" for row in parser_raster_rendered["rows"])
    lines.append("- remaining gap: replace the modeled command/data stream fixture below with a full live parser run through `0x121cc` / `0x105d0`.")
    lines.append("")

    lines.append("## Modeled Raster Command/Data Stream Fixture")
    lines.append("")
    lines.append("This fixture starts from actual PCL command bytes, then models the delayed payload boundary that `0x121cc` records for handler `0x105d0`. It is still not a full firmware parser run, but it proves the byte stream selects parser-derived raster state before queueing and rendering the `ESC *b#W` payload. The 300/150/100/75-dpi streams pin byte-stream-selected modes 0..3, and same-group lowercase-final sequences now stay in the firmware parser mode until the final uppercase command byte.")
    lines.append("")
    lines.append(f"- stream bytes: `{' '.join(f'{byte:02x}' for byte in raster_command_stream)}`")
    lines.append("- parsed events:")
    for event in raster_stream_result["events"]:
        if event["kind"] == "raster-resolution":
            lines.append("- `ESC *t%dR`: mode `%d`, scale `%d`, limit `%d`" % (
                event["parameter"],
                event["mode_after"],
                event["scale"],
                event["limit"],
            ))
        elif event["kind"] == "start-raster":
            lines.append("- `ESC *r%dA`: origin `0x%08x`, baseline word `%d`, limit `%d`" % (
                event["parameter"],
                event["origin_long"],
                event["baseline_word"],
                event["limit"],
            ))
        elif event["kind"] == "raster-transfer":
            lines.append("- `ESC *b%dW`: delayed handler `0x%06x`, payload offset `%d`, payload `%s`, transfer state `%s`" % (
                event["parameter"],
                event["delayed_handler"],
                event["payload_offset"],
                " ".join(f"{byte:02x}" for byte in event["payload"]),
                event["transfer_state"],
            ))
    lines.append(f"- queued object bytes: `{' '.join(f'{byte:02x}' for byte in raster_stream_result['object'])}`")
    lines.append("- rendered stream row:")
    lines.extend(f"`{row}`" for row in raster_stream_rendered["rows"])
    lines.append("- bridged command-stream page object survives `0x1edc6` and renders the same row.")
    lines.append("")
    lines.append(f"- mode-1 stream bytes: `{' '.join(f'{byte:02x}' for byte in raster_mode1_command_stream)}`")
    lines.append("- mode-1 parsed events:")
    for event in raster_mode1_stream_result["events"]:
        if event["kind"] == "raster-resolution":
            lines.append("- `ESC *t%dR`: mode `%d`, scale `%d`, limit `%d`" % (
                event["parameter"],
                event["mode_after"],
                event["scale"],
                event["limit"],
            ))
        elif event["kind"] == "start-raster":
            lines.append("- `ESC *r%dA`: origin `0x%08x`, baseline word `%d`, limit `%d`" % (
                event["parameter"],
                event["origin_long"],
                event["baseline_word"],
                event["limit"],
            ))
        elif event["kind"] == "raster-transfer":
            lines.append("- `ESC *b%dW`: delayed handler `0x%06x`, payload offset `%d`, payload `%s`, transfer state `%s`" % (
                event["parameter"],
                event["delayed_handler"],
                event["payload_offset"],
                " ".join(f"{byte:02x}" for byte in event["payload"]),
                event["transfer_state"],
            ))
    lines.append(f"- mode-1 queued object bytes: `{' '.join(f'{byte:02x}' for byte in raster_mode1_stream_result['object'])}`")
    lines.append("- mode-1 rendered stream rows:")
    lines.extend(f"`{row}`" for row in raster_mode1_stream_rendered["rows"])
    lines.append("")
    lines.append(f"- mode-2 stream bytes: `{' '.join(f'{byte:02x}' for byte in raster_mode2_command_stream)}`")
    lines.append("- mode-2 parsed events:")
    for event in raster_mode2_stream_result["events"]:
        if event["kind"] == "raster-resolution":
            lines.append("- `ESC *t%dR`: mode `%d`, scale `%d`, limit `%d`" % (
                event["parameter"],
                event["mode_after"],
                event["scale"],
                event["limit"],
            ))
        elif event["kind"] == "start-raster":
            lines.append("- `ESC *r%dA`: origin `0x%08x`, baseline word `%d`, limit `%d`" % (
                event["parameter"],
                event["origin_long"],
                event["baseline_word"],
                event["limit"],
            ))
        elif event["kind"] == "raster-transfer":
            lines.append("- `ESC *b%dW`: delayed handler `0x%06x`, payload offset `%d`, payload `%s`, transfer state `%s`" % (
                event["parameter"],
                event["delayed_handler"],
                event["payload_offset"],
                " ".join(f"{byte:02x}" for byte in event["payload"]),
                event["transfer_state"],
            ))
    lines.append(f"- mode-2 queued object bytes: `{' '.join(f'{byte:02x}' for byte in raster_mode2_stream_result['object'])}`")
    lines.append("- mode-2 rendered stream rows:")
    lines.extend(f"`{row}`" for row in raster_mode2_stream_rendered["rows"])
    lines.append("")
    lines.append(f"- mode-3 stream bytes: `{' '.join(f'{byte:02x}' for byte in raster_mode3_command_stream)}`")
    lines.append("- mode-3 parsed events:")
    for event in raster_mode3_stream_result["events"]:
        if event["kind"] == "raster-resolution":
            lines.append("- `ESC *t%dR`: mode `%d`, scale `%d`, limit `%d`" % (
                event["parameter"],
                event["mode_after"],
                event["scale"],
                event["limit"],
            ))
        elif event["kind"] == "start-raster":
            lines.append("- `ESC *r%dA`: origin `0x%08x`, baseline word `%d`, limit `%d`" % (
                event["parameter"],
                event["origin_long"],
                event["baseline_word"],
                event["limit"],
            ))
        elif event["kind"] == "raster-transfer":
            lines.append("- `ESC *b%dW`: delayed handler `0x%06x`, payload offset `%d`, payload `%s`, transfer state `%s`" % (
                event["parameter"],
                event["delayed_handler"],
                event["payload_offset"],
                " ".join(f"{byte:02x}" for byte in event["payload"]),
                event["transfer_state"],
            ))
    lines.append(f"- mode-3 queued object bytes: `{' '.join(f'{byte:02x}' for byte in raster_mode3_stream_result['object'])}`")
    lines.append("- mode-3 rendered stream rows:")
    lines.extend(f"`{row}`" for row in raster_mode3_stream_rendered["rows"])
    lines.append("")
    lines.append(f"- multi-row stream bytes: `{' '.join(f'{byte:02x}' for byte in raster_multirow_command_stream)}`")
    lines.append("- multi-row transfer events:")
    for event in raster_multirow_stream_result["events"]:
        if event["kind"] == "raster-transfer":
            lines.append("- payload offset `%d`, payload `%s`, transfer state `%s`, row_y after `%d`" % (
                event["payload_offset"],
                " ".join(f"{byte:02x}" for byte in event["payload"]),
                event["transfer_state"],
                event["row_y_after"],
            ))
    lines.append("- multi-row queued chain, newest first:")
    lines.extend(f"`{' '.join(f'{byte:02x}' for byte in obj)}`" for obj in raster_multirow_chain)
    lines.append("- multi-row rendered rows, source order:")
    for rendered in raster_multirow_rendered:
        lines.append("- coord `0x%04x`, y `%d`, payload `%s`" % (
            rendered["coord"],
            rendered["y"],
            " ".join(f"{byte:02x}" for byte in rendered["payload"]),
        ))
        lines.extend(f"`{row}`" for row in rendered["rows"])
    lines.append("")
    lines.append(f"- raster-end stream bytes: `{' '.join(f'{byte:02x}' for byte in raster_end_command_stream)}`")
    lines.append("- raster-end parsed events:")
    for event in raster_end_stream_result["events"]:
        if event["kind"] == "raster-resolution":
            lines.append("- `ESC *t%dR`: mode `%d -> %d`, scale `%d`, limit `%d`" % (
                event["parameter"],
                event["mode_before"],
                event["mode_after"],
                event["scale"],
                event["limit"],
            ))
        elif event["kind"] == "start-raster":
            lines.append("- `ESC *r%dA`: active `%d -> %d`, origin `0x%08x`, baseline word `%d`, limit `%d`" % (
                event["parameter"],
                event["active_before"],
                event["active_after"],
                event["origin_long"],
                event["baseline_word"],
                event["limit"],
            ))
        elif event["kind"] == "raster-transfer":
            lines.append("- `ESC *b%dW`: payload offset `%d`, payload `%s`, transfer state `%s`, row_y after `%d`" % (
                event["parameter"],
                event["payload_offset"],
                " ".join(f"{byte:02x}" for byte in event["payload"]),
                event["transfer_state"],
                event["row_y_after"],
            ))
        elif event["kind"] == "end-raster":
            lines.append("- `ESC *rB`: active `%d -> %d`, mode `%d`, scale `%d`, limit `%d`, row_y `%d`" % (
                event["active_before"],
                event["active_after"],
                event["mode"],
                event["scale"],
                event["limit"],
                event["row_y"],
            ))
    lines.append("- raster-end final state: active `%d`, mode `%d`, scale `%d`, limit `%d`, row_y `%d`" % (
        raster_end_stream_result["final_state"]["active"],
        raster_end_stream_result["final_state"]["mode"],
        raster_end_stream_result["final_state"]["scale"],
        raster_end_stream_result["final_state"]["limit"],
        raster_end_stream_result["final_state"]["row_y"],
    ))
    lines.append(f"- chained resolution stream bytes: `{' '.join(f'{byte:02x}' for byte in raster_chained_resolution_stream)}`")
    lines.append("- chained resolution events: `%s` then `%s`, leaving mode `%d` / scale `%d`." % (
        raster_chained_resolution_result["events"][0]["sequence"],
        raster_chained_resolution_result["events"][1]["sequence"],
        raster_chained_resolution_result["final_state"]["mode"],
        raster_chained_resolution_result["final_state"]["scale"],
    ))
    lines.append(f"- chained `ESC *b` stream bytes: `{' '.join(f'{byte:02x}' for byte in raster_chained_transfer_stream)}`")
    lines.append("- chained `ESC *b` transfer events:")
    for event in raster_chained_transfer_result["events"]:
        if event["kind"] == "raster-transfer":
            lines.append("- sequence `%s`, payload offset `%d`, payload `%s`, row_y after `%d`, chained `%s`" % (
                event["sequence"],
                event["payload_offset"],
                " ".join(f"{byte:02x}" for byte in event["payload"]),
                event["row_y_after"],
                event["chained"],
            ))
    lines.append("- chained `ESC *b` queued chain, newest first:")
    lines.extend(f"`{' '.join(f'{byte:02x}' for byte in obj)}`" for obj in raster_chained_transfer_chain)
    lines.append("- remaining gap: run the same byte stream through the live parser/data-chain machinery instead of this modeled command recognizer.")
    lines.append("")

    lines.append("## Raster Row Page-Record Fixture")
    lines.append("")
    lines.append("This fixture models one byte-aligned raster row through the page-object path used by `0x105d0`: `0x13070` computes the bucket/key fields from the raster state, `0x13250` allocates and links an encoded-span object under page-root `+0x1c`, `0x138de` copies host payload bytes into object `+0x0a`, and `0x1f88e` mode 0 renders the literal row after the `0x1edc6` bridge copies the bucket root into render-record `+0x18`.")
    lines.append("")
    lines.append(f"- raster state: x `16`, y `0`, byte count `4`, mode `0`, payload `{' '.join(f'{byte:02x}' for byte in raster_page_result['payload'])}`")
    lines.append(f"- queued raster object bytes: `{' '.join(f'{byte:02x}' for byte in raster_object)}`")
    lines.append("- object fields: class `0x80`, mode byte `0x%02x`, byte count `%d`, coord `0x%04x`, bucket `%d`, key `0x%04x`" % (
        raster_page_result["mode"],
        raster_page_result["capacity"],
        raster_page_result["key"],
        raster_page_result["bucket_index"],
        raster_page_result["key"],
    ))
    lines.append("- rendered mode-0 literal row:")
    lines.extend(f"`{row}`" for row in raster_rendered["rows"])
    lines.append("- bridged raster rows match the queued raster object render.")
    lines.append(f"- non-byte-aligned mode-0 queued raster object bytes: `{' '.join(f'{byte:02x}' for byte in raster_shifted_object)}`")
    lines.append("- rendered sub-byte shifted mode-0 row:")
    lines.extend(f"`{row}`" for row in raster_shifted_rendered["rows"])
    lines.append(f"- mode-1 queued raster object bytes: `{' '.join(f'{byte:02x}' for byte in raster_mode1_object)}`")
    lines.append("- rendered mode-1 expanded rows:")
    lines.extend(f"`{row}`" for row in raster_mode1_rendered["rows"])
    lines.append(f"- mode-2 queued raster object bytes: `{' '.join(f'{byte:02x}' for byte in raster_mode2_object)}`")
    lines.append("- rendered mode-2 expanded rows:")
    lines.extend(f"`{row}`" for row in raster_mode2_rendered["rows"])
    lines.append(f"- non-byte-aligned mode-2 queued raster object bytes: `{' '.join(f'{byte:02x}' for byte in raster_mode2_shifted_object)}`")
    lines.append("- rendered sub-byte shifted mode-2 rows:")
    lines.extend(f"`{row}`" for row in raster_mode2_shifted_rendered["rows"])
    lines.append(f"- band-clipped mode-2 queued raster object bytes: `{' '.join(f'{byte:02x}' for byte in raster_mode2_clipped_object)}`")
    lines.append("- band-clipped mode-2 current-band rows: `%d`, remaining after band: `%d`" % (
        raster_mode2_clipped_rendered["rows_in_band"],
        raster_mode2_clipped_rendered["remaining_after_band"],
    ))
    lines.append("- band-clipped mode-2 visible row:")
    lines.extend(f"`{row}`" for row in raster_mode2_clipped_rendered["rows"][-int(raster_mode2_clipped_rendered["rows_in_band"]):])
    lines.append("- band-clipped mode-2 fallback rows:")
    lines.extend(f"`{row}`" for row in raster_mode2_clipped_rendered["fallback_rows"])
    lines.append(f"- mode-3 queued raster object bytes: `{' '.join(f'{byte:02x}' for byte in raster_mode3_object)}`")
    lines.append("- rendered mode-3 expanded rows:")
    lines.extend(f"`{row}`" for row in raster_mode3_rendered["rows"])
    lines.append("- remaining gap: replace the modeled raster command/data stream with a full live parser/data-chain run through `0x121cc` / `0x105d0`.")
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
    lines.append("- remaining gap: broaden this from fixture-only source/bucket state into full parser-produced page objects.")
    lines.append("")

    lines.append("## Two Printable Byte Stream Fixture")
    lines.append("")
    lines.append("This fixture keeps the same normal printable path but repeats it for stream bytes `21 21` (`!!`). Between bytes it models the simple `0xd550` default-advance branch: alternate metrics and previous-width centering are disabled, the drawable source is present, precheck succeeds, and the packed cursor is advanced by `0x00100000` so both compact coordinates stay byte-aligned for the current renderer fixture.")
    lines.append("")
    lines.append("- stream bytes: `21 21`")
    lines.append(f"- cursor advances: `0x{pack12(10):08x}` -> `0x{pack12(26):08x}` -> `0x{pack12(42):08x}`")
    lines.append(f"- combined compact object bytes: `{' '.join(f'{byte:02x}' for byte in multi_printable_combined['object'])}`")
    lines.append("- compact entries: glyph `0x20` at coords `0x0001` and `0x0002`")
    lines.append("- rendered rows:")
    lines.extend(f"`{row}`" for row in multi_printable_rendered["rows"])
    lines.append("- this byte-aligned advance is a renderer control fixture; it is not the initialized `LINE_PRINTER` HMI.")
    lines.append("")
    lines.append("The initialized `LINE_PRINTER` built-in metric path follows the `0x10550` conversion branch used by current-font refresh code: resource longword `0x00480000` at context offset `+0x24` becomes HMI/default advance `0x00120000`. Reusing the same `!!` stream with that advance queues the second glyph at compact coord `0x0202`; renderer helper `0x1f3d4` decodes that as byte base `+0x04` plus `$a001 = 0x12`, so the fixture draws the second glyph at pixel x `34`.")
    lines.append("")
    lines.append(f"- metric source: context `0x{0x440946B4:08x}`, resource base `0x{line_printer_hmi['base']:06x}`, byte `+0x21 = 0x{line_printer_hmi['metric_flag']:02x}`, long `+0x24 = 0x{line_printer_hmi['raw_metric']:08x}`")
    lines.append(f"- `0x10550` result: `0x{line_printer_hmi['hmi']:08x}`")
    lines.append(f"- real-HMI compact object bytes: `{' '.join(f'{byte:02x}' for byte in metric_printable_combined['object'])}`")
    lines.append("- real-HMI compact entries: glyph `0x20` at coords `0x0001` and `0x0202`")
    lines.append("- real-HMI rendered rows:")
    lines.extend(f"`{row}`" for row in metric_printable_rendered["rows"])
    lines.append("")
    lines.append("A first mixed printable/control stream fixture now drives `ESC &k1G`, printable `!`, CR, then printable `!` through one pass. The `ESC &k1G` byte stream stores line-termination mode `0x80`; CR therefore resets x to the left margin and also applies LF/VMI before the second printable byte is positioned. With left margin `5`, VMI `3`, and initialized `LINE_PRINTER` HMI `0x00120000`, the second glyph queues at source `(11,3)` / compact coord `0x3b00`, decoded by `0x1f3d4` as `$a001 = 0x1b`.")
    lines.append("")
    lines.append("- mixed stream bytes: `1b 26 6b 31 47 21 0d 21`")
    lines.append(f"- mixed compact object bytes: `{' '.join(f'{byte:02x}' for byte in mixed_combined['object'])}`")
    lines.append("- mixed compact entries: glyph `0x20` at coords `0x0001` and `0x3b00`")
    lines.append("- mixed final cursor: x `0x%08x`, y `0x%08x`, page roots `%d`, span flushes `%d`" % (
        mixed_final_state["cursor_x"],
        mixed_final_state["cursor_y"],
        mixed_final_state["page_roots"],
        mixed_final_state["span_flushes"],
    ))
    lines.append("- mixed rendered rows:")
    lines.extend(f"`{row}`" for row in mixed_rendered["rows"])
    lines.append("- note: the shifted second glyph writes a full one-byte span, so its blank rows clear pixels `x=11..18` and can erase part of an earlier glyph in the same bucket.")
    lines.append("")
    lines.append("The same mixed stream is now also queued through the page-record allocator shape as the stream is processed, rather than being combined after the fact. The first printable byte allocates bucket `0` through `0x1387c`; after CR+LF, the second printable byte reuses that object and increments the count to `2`. Bridging the resulting full `0x26` object through `0x1edc6` renders the same post-CR rows.")
    lines.append("")
    lines.append(f"- page-record stream object bytes: `{' '.join(f'{byte:02x}' for byte in mixed_page_record_object)}`")
    lines.append(f"- page-record bridged context slots `[0..1]`: `0x{mixed_page_record_bridged['context_slots'][0]:08x}`, `0x{mixed_page_record_bridged['context_slots'][1]:08x}`")
    lines.append("")
    lines.append("A mixed printable/reset stream fixture drives printable `!` followed by `ESC E`. It keeps the pre-reset compact text object renderable, then applies the reset publication path from the same byte stream: pending text is flushed, the valid current page root is published and cleared, the environment is rebuilt, and HMI is refreshed from the selected current-font metric.")
    lines.append("")
    lines.append("- mixed reset stream bytes: `21 1b 45`")
    lines.append(f"- mixed reset compact object bytes: `{' '.join(f'{byte:02x}' for byte in mixed_reset_combined['object'])}`")
    lines.append("- mixed reset compact entry: glyph `0x20` at coord `0x0001`")
    lines.append("- mixed reset final state: current page root `%d`, publications `%d`, root clears `%d`, span flushes `%d`, HMI `0x%08x`, data-chain pointer `0x%06x`, reset status `%d`" % (
        mixed_reset_final_state["current_page_root"],
        mixed_reset_final_state["page_publications"],
        mixed_reset_final_state["page_root_clears"],
        mixed_reset_final_state["span_flushes"],
        mixed_reset_final_state["hmi"],
        mixed_reset_final_state["data_chain_ptr"],
        mixed_reset_final_state["reset_status"],
    ))
    lines.append(f"- page-record reset object bytes: `{' '.join(f'{byte:02x}' for byte in mixed_reset_page_record_object)}`")
    lines.append("- page-record reset bridged rows match the pre-reset compact text rows.")
    lines.append("- remaining gap: replace these fixture-only source/bucket/page-root states with parser-produced page objects and compare the finalized page/control records.")
    lines.append("")

    lines.append("## `0xd3b2` Unflagged Positioning Fixture")
    lines.append("")
    lines.append("This fixture pins the unflagged/inline positioning arithmetic at `0xd3b2`, then continues through the unflagged branch of `0x12f2e`. The first inline case now starts from a selected inline/downloaded context model: `0x14e24` calls `0x14eb6`-equivalent fixed-record probes, maps host byte `0x21` to glyph `1`, and `0x1393a` builds the source object with record pointer `context_base + 0x40 + 8*glyph`. The later wide/segmented cases still reuse synthetic records to isolate renderer modes. For unflagged sources, record byte `+0` is the width threshold byte, byte `+1` is the row count used for short/segmented selection, and byte `+2` feeds the signed positioning arithmetic.")
    lines.append("")
    selected_inline_source_report = selected_inline_source
    selected_inline_render = selected_inline_rendered["rendered"][0]
    assert isinstance(selected_inline_render, dict)
    lines.append("- selected inline map: context `0x%08x`, host `0x21 -> glyph %d`, invalid sentinel host `0x22 -> glyph %d`, glyph-1 record `%s`, bitmap `0x%06x`." % (
        selected_inline_context,
        selected_inline_map_table[0x21],
        selected_inline_map_table[0x22],
        " ".join(f"{byte:02x}" for byte in selected_inline_source_report["inline_record"]),
        selected_inline_source_report["bitmap"],
    ))
    lines.append("- selected inline source object from `0x1393a`: glyph entry `0x%06x`, flag `%d`, x `%d`, y `%d`, context slot `%d`, valid `%s`." % (
        selected_inline_source_report["glyph_entry"],
        selected_inline_source_report["flag"],
        selected_inline_source_report["x"],
        selected_inline_source_report["y"],
        selected_inline_source_report["context_slot"],
        selected_inline_source_report["valid_record"],
    ))
    lines.append("- selected inline positioned object bytes through `0xd3b2`/`0x12f2e`: `%s`; page-record prefix `%s`." % (
        " ".join(f"{byte:02x}" for byte in selected_inline_bucket["object"]),
        " ".join(f"{byte:02x}" for byte in selected_inline_page_object[:11]),
    ))
    lines.append("- selected inline mode-0 rendered rows from fixed-record bitmap bytes:")
    selected_inline_rows = selected_inline_rendered["rows"]
    assert isinstance(selected_inline_rows, list)
    for row in selected_inline_rows:
        lines.append(f"`{row}`")
    lines.append("")
    lines.append("The font payload reader fixtures model the byte-copy loops immediately before these fixed records are usable. Linear reader `0x168dc` copies host bytes into one destination, treats `0x1a 0x58` as a control escape by calling `0xd99a` and storing a zero payload byte, and records continuation state when byte budget `0x783140` expires. Split-plane reader `0x16942` writes `rows * prefix_span` bytes at `A4`, then one trailing byte per row at `A3 = A4 + rows * prefix_span`; this is the same A2/A3 layout used by odd-width inline render fixtures.")
    lines.append("")
    lines.append(f"- linear copy with `1a 58`: `{' '.join(f'{byte:02x}' for byte in font_linear_payload['dest'])}`, status `{font_linear_payload['status']}`, budget `{font_linear_payload['byte_budget']}`, control hits `{font_linear_payload['control_hits']}`")
    lines.append(f"- linear continuation after two payload bytes: status `{font_linear_continuation['status']}`, remaining `{font_linear_continuation['remaining']}`, state `{font_linear_continuation['continuation']}`")
    lines.append(f"- split-plane copy: prefix `{' '.join(f'{byte:02x}' for byte in font_split_payload['prefix'])}`, trailing `{' '.join(f'{byte:02x}' for byte in font_split_payload['trailing'])}`")
    lines.append(f"- split-plane continuation before trailing byte: status `{font_split_continuation['status']}`, state `{font_split_continuation['continuation']}`")
    lines.append(f"- split-plane copy with `1a 58`: prefix `{' '.join(f'{byte:02x}' for byte in font_split_control['prefix'])}`, trailing `{' '.join(f'{byte:02x}' for byte in font_split_control['trailing'])}`, control hits `{font_split_control['control_hits']}`")
    lines.append("")
    lines.append("The next modeled step is the current downloaded-font record bookkeeping at `0x172c0` and `0x16c14`. The record scan treats each `0x782640..0x782776` slot as a 10-byte entry: word `+0` is the current font/resource id, byte/word area `+2` carries flags that `0x16c14` clears at bits 5..7, and long `+6` points at the allocated payload. Status `0` means an existing id with nonzero payload was found, status `1` means a free zero-id/zero-payload slot was found, and status `2` makes `0x16c14` consume/skip the byte budget instead of installing a payload.")
    lines.append("")
    lines.append("- `0x172c0` scan fixtures: existing id `0x1234` -> status `%d` at slot `%s`; missing id with free slot -> status `%d` at slot `%s`; missing id with no free slot -> status `%d`." % (
        font_scan_existing["status"],
        font_scan_existing["index"],
        font_scan_free["status"],
        font_scan_free["index"],
        font_scan_full["status"],
    ))
    font_replace_record = font_replace["records"][0]
    assert isinstance(font_replace_record, dict)
    lines.append("- replacement path: existing slot `%s` releases payload `0x%06x`, clears matching continuation state `%s`, installs payload `0x%06x`, clears record flag bits 5..7 to `0x%02x`, and writes candidate flags `0x%08x` with downloaded bit 6 set and byte `+0x0c == 2` bit 2 set." % (
        font_replace["record_index"],
        font_replace["replacement"]["released_payload"],
        font_replace["replacement"]["continuation_cleared"],
        font_replace_record["payload"],
        font_replace_record["flags"],
        font_replace["candidate_flags"],
    ))
    lines.append("- byte `+0x20 == 1` counter branch after replacement: counters `%s`, cursors `%s`." % (
        font_replace["counters"],
        font_replace["cursors"],
    ))
    font_insert_record = font_insert["records"][1]
    assert isinstance(font_insert_record, dict)
    lines.append("- free-slot path: slot `%s` receives id `0x%04x` and payload `0x%06x`; byte `+0x20 != 1` increments counters `%s` with candidate flags `0x%08x`." % (
        font_insert["record_index"],
        font_insert_record["id"],
        font_insert_record["payload"],
        font_insert["counters"],
        font_insert["candidate_flags"],
    ))
    lines.append("- no-slot path: status `%s` leaves records unchanged and reports budget action `%s`." % (
        font_no_slot["status"],
        font_no_slot["budget_action"],
    ))
    lines.append("")
    lines.append("The adjacent current-record helpers and the host command edge are now modeled as well. `0x170be` masks the candidate payload pointer to 24 bits, scans the same 10-byte current-record table by payload long `+6`, returns the matching signed id word, and stores the record pointer for callers. `0x17108` reuses `0x172c0`; when the current id already has a payload and flag bit 6 at record byte `+2` is clear, it sets that bit, decrements `0x782782`, and increments `0x782786`. `0x17150` is the inverse count-transfer helper. `0x15a56` normalizes the parsed `ESC *c#D` font id, and the `0x16df6` dispatch table routes `ESC *c#F` values to the mark/unmark helpers while suppressing values `0`, `1`, `2`, `3`, and `6` when mode byte `0x782a92 == 2`.")
    lines.append("")
    lines.append("- payload lookup: payload `0x99123456` masks to `0x%06x`, finds slot `%s`, and returns id `0x%04x`; missing payload returns `%d`." % (
        font_payload_lookup_hit["masked_payload"],
        font_payload_lookup_hit["index"],
        font_payload_lookup_hit["status"],
        font_payload_lookup_miss["status"],
    ))
    marked_record = font_mark["records"][0]
    assert isinstance(marked_record, dict)
    lines.append("- current-record mark: id `0x1234` changes flag byte from `0x00` to `0x%02x`, with counters `%s`; already-marked and missing/free-slot cases leave counters unchanged." % (
        marked_record["flags"],
        font_mark["counters"],
    ))
    unmarked_record = font_unmark["records"][0]
    assert isinstance(unmarked_record, dict)
    lines.append("- current-record unmark: id `0x1234` changes flag byte from `0x40` to `0x%02x`, with counters `%s`; already-unmarked cases leave counters unchanged." % (
        unmarked_record["flags"],
        font_unmark["counters"],
    ))
    lines.append("- command-edge fixtures: `0x15a56` maps parsed ids `[0, 17, -17, -32768, 0x8001]` to `%s`; `0x16df6` value `5` targets `0x%06x` and marks, value `4` targets `0x%06x` and unmarks, value `2` targets `0x%06x` but is suppressed in parser mode `2`, and unknown value `99` targets no-op `0x%06x`." % (
        font_id_assign,
        font_control_mark["target"],
        font_control_unmark["target"],
        font_control_suppressed["target"],
        font_control_noop["target"],
    ))
    lines.append("")
    lines.append("The allocation/header side of that path is now pinned through `0x16fae`, `0x17362`, `0x17026`, and `0x1719c`. Validator `0x16fae` walks the 32-entry validation table at `0x16eae` in 8-byte steps, fails immediately if a predicate returns anything other than `1`, and on success copies up to 16 symbol bytes from `0x1599c` into `0x782842` while byte budget `0x783140` remains positive, storing the count in `0x782856`. Setup helper `0x17362` writes staged byte `+0x0c` from the requested type and sets `0x7827ba` to `0x80` for type `0` or `0x100` for types `1`/`2`. `0x17026` then computes the allocation size as `((0x7827ba << 2) + 0x9b) >> 6`, writes staged long `+0 = 0x15` and long `+4 = size`, calls the allocator with class `1` and alignment `0x40`, and initializes the allocated record through `0x1719c`.")
    lines.append("")
    lines.append("- validation fixtures: all 32 table entries passing copy `%d` symbol bytes `%s` and leave budget `%d`; a failed entry at index `%d` returns status `%d` after `%d` visits; zero budget still validates but copies `%d` bytes." % (
        font_validate_ok["symbol_count"],
        " ".join(f"{byte:02x}" for byte in font_validate_ok["symbol_bytes"]),
        font_validate_ok["budget"],
        font_validate_fail["failed_index"],
        font_validate_fail["status"],
        len(font_validate_fail["visited"]),
        font_validate_zero_budget["symbol_count"],
    ))
    lines.append("- table-driven validation stream: `%d` decoded table entries consume `%d` bytes before the symbol tail, leave budget `%d`, set type byte `+0x0c = %d`, range words `+0x12/+0x14/+0x16/+0x18 = 0x%04x/0x%04x/0x%04x/0x%04x`, clamp spacing words `+0x24/+0x28 = 0x%04x/0x%04x`, clamp bytes `+0x26/+0x2a/+0x30 = %02x/%02x/%02x`, and copy symbols `%s`." % (
        len(font_validate_table["visited"]),
        font_validate_table["bytes_consumed"] - font_validate_table["symbol_count"],
        font_validate_table["budget"],
        font_validate_table_staging[0x0C],
        u16(font_validate_table_staging, 0x12),
        u16(font_validate_table_staging, 0x14),
        u16(font_validate_table_staging, 0x16),
        u16(font_validate_table_staging, 0x18),
        u16(font_validate_table_staging, 0x24),
        u16(font_validate_table_staging, 0x28),
        font_validate_table_staging[0x26],
        font_validate_table_staging[0x2A],
        font_validate_table_staging[0x30],
        " ".join(f"{byte:02x}" for byte in font_validate_table["symbol_bytes"]),
    ))
    lines.append("- setup type fixtures: type `0` -> byte `+0x0c = %d`, units `0x%03x`; type `2` -> byte `+0x0c = %d`, units `0x%03x`; unsupported type returns status `%d` without changing byte `+0x0c`." % (
        font_setup_type_0["staging"][0x0C],
        font_setup_type_0["payload_units"],
        font_setup_type_2["staging"][0x0C],
        font_setup_type_2["payload_units"],
        font_setup_type_bad["status"],
    ))
    lines.append("- allocation fixture: units `0x%03x` produce allocation size `%d`, staged long `+0 = 0x%08x`, staged long `+4 = %d`; invalid validation returns status `%d` and no payload." % (
        font_setup_type_0["payload_units"],
        font_allocated["allocation_size"],
        int.from_bytes(font_allocated["staging"][0:4], "big"),
        int.from_bytes(font_allocated["staging"][4:8], "big"),
        font_alloc_failed["status"],
    ))
    lines.append("- `0x1719c` sparse header copy fixture: payload long `+0 = 0x%08x`, long `+4 = %d`, word `+8 = 0x%04x`, byte `+0x0c = %d`, word `+0x0e = 0x%04x`, byte `+0x20 = 0x%02x`, byte `+0x21 = 0x%02x`, word `+0x22 = 0x%04x`, bytes `+0x2f..+0x31 = %02x %02x %02x`." % (
        int.from_bytes(font_payload_bytes[0:4], "big"),
        int.from_bytes(font_payload_bytes[4:8], "big"),
        u16(font_payload_bytes, 8),
        font_payload_bytes[0x0C],
        u16(font_payload_bytes, 0x0E),
        font_payload_bytes[0x20],
        font_payload_bytes[0x21],
        u16(font_payload_bytes, 0x22),
        font_payload_bytes[0x2F],
        font_payload_bytes[0x30],
        font_payload_bytes[0x31],
    ))
    lines.append("- optional symbol bytes: `0x1719c` writes long `+0x38 = 0x%04x`, then count `%d` and bytes `%s` at `payload + 0x%04x`." % (
        int.from_bytes(font_payload_bytes[0x38:0x3C], "big"),
        u16(font_payload_bytes, int(font_payload_info["extra_offset"])),
        " ".join(f"{byte:02x}" for byte in font_payload_bytes[int(font_payload_info["extra_offset"]) + 2:int(font_payload_info["extra_offset"]) + 2 + int(font_payload_info["symbol_count"])]),
        int(font_payload_info["extra_offset"]),
    ))
    lines.append("- payload-backed inline fixture: the table-driven `0x16fae` staging allocates a `0x1719c` payload with header word `+8 = 0x%04x`, type byte `+0x0c = %d`, extra symbol count `%d`, then a fixed record placed at the `0x14eb6` scanned offset `+0x40 + 8*1 = 0x%04x` maps host `0x21` to glyph `1`, queues object `%s`, and renders the same mode-0 rows from bitmap `0x%04x`." % (
        u16(table_payload_memory, 8),
        table_payload_memory[0x0C],
        u16(table_payload_memory, int(table_payload_info["extra_offset"])),
        table_payload_record,
        " ".join(f"{byte:02x}" for byte in table_payload_bucket["object"]),
        table_payload_source["bitmap"],
    ))
    lines.append("")
    unflagged_source_report = unflagged_fixture["source"]
    assert isinstance(unflagged_source_report, dict)
    lines.append(f"- context metric flag clear: cursor `(10,20)`, printable offset `7`, source x-offset `5` -> x `{unflagged_source_report['x']}`, y `{unflagged_source_report['y']}`, context slot `{unflagged_source_report['context_slot']}`, overflow correction `{unflagged_fixture['overflow_correction']}`")
    lines.append(f"- unflagged short object bytes from record `02 03 04`: `{' '.join(f'{byte:02x}' for byte in unflagged_short_bucket['object'])}`")
    lines.append(f"- unflagged page-record short object prefix: `{' '.join(f'{byte:02x}' for byte in unflagged_page_object[:11])}`")
    lines.append("- record byte `+0 = 0x11` sets selector bit `0x1000`, producing object bytes: `%s`" % (
        " ".join(f"{byte:02x}" for byte in unflagged_wide_bucket["object"]),
    ))
    wide_rendered = unflagged_wide_rendered["rendered"]
    assert isinstance(wide_rendered, list)
    wide_render_entry = wide_rendered[0]
    assert isinstance(wide_render_entry, dict)
    lines.append("- synthetic wide inline render record at context `0x%08x` maps glyph `1` to span `0x11`, rows `3`, and split A2/A3 bitmap planes; the selector-`0x1000` object renders through `0x1f0d2` as `%d` full 16-byte chunk plus `%d` trailing byte using helpers `0x%06x` and `0x%06x`." % (
        wide_inline_context,
        wide_render_entry["full_chunks"],
        wide_render_entry["remainder"],
        wide_render_entry["full_chunk_helper"],
        wide_render_entry["remainder_helper"],
    ))
    lines.append("- record byte `+1 = 0x81` selects segmented entries with selector `0x%04x`:" % (
        unflagged_tall_bucket["selector"],
    ))
    for obj in unflagged_tall_bucket["objects"]:
        assert isinstance(obj, dict)
        lines.append("- bucket `%d`, segment `%d`: `%s`" % (
            obj["bucket_index"],
            obj["segment"],
            " ".join(f"{byte:02x}" for byte in obj["object"]),
        ))
    lines.append("- synthetic inline render record at context `0x%08x` maps glyph `1` to span `2`, rows `0x81`, bitmap delta `0x%02x`; the segment-1 object renders row `128` from bytes `aa 55` through `0x1f1f0`:" % (
        inline_context,
        inline_bitmap_delta,
    ))
    segmented_rows = unflagged_segmented_rendered["rows"]
    assert isinstance(segmented_rows, list)
    for row in segmented_rows:
        lines.append(f"`{row}`")
    segmented_wide_rendered = unflagged_segmented_wide_rendered["rendered"]
    assert isinstance(segmented_wide_rendered, list)
    segmented_wide_entry = segmented_wide_rendered[0]
    assert isinstance(segmented_wide_entry, dict)
    lines.append("- record bytes `+0 = 0x11`, `+1 = 0x81` select combined selector `0x%04x`; the segment-1 object renders row `128` through `0x1f264` with split A2/A3 planes, helpers `0x%06x` and `0x%06x`, and object bytes `%s`." % (
        unflagged_wide_tall_bucket["selector"],
        segmented_wide_entry["full_chunk_helper"],
        segmented_wide_entry["remainder_helper"],
        " ".join(f"{byte:02x}" for byte in unflagged_segmented_wide_object),
    ))
    unflagged_overflow_source_report = unflagged_overflow_fixture["source"]
    assert isinstance(unflagged_overflow_source_report, dict)
    lines.append(f"- context metric flag set plus left overflow: cursor `(10,20)`, printable offset `20`, source x-offset `-15` -> x `{unflagged_overflow_source_report['x']}`, y `{unflagged_overflow_source_report['y']}`, context slot `{unflagged_overflow_source_report['context_slot']}`, overflow correction `0x{int(unflagged_overflow_fixture['overflow_correction']):08x}`")
    lines.append("- remaining gap: replace the synthetic inline fixed-record memory with records populated by the real font-download parser, then carry those parser-produced page objects into the bridge/render path.")
    lines.append("")

    lines.append("## Segmented Text Bucket Producer Fixture")
    lines.append("")
    lines.append("The same producer model also covers the `0x12f2e` segmented path where the glyph height word exceeds `0x80`. For `LINE_PRINTER`, host byte `0x20` maps to glyph byte `0x1f`; the resolved table target is the record base `0x0146b4`, whose height word is `0x0454` and width word is `0x004a`. `0x12f2e` therefore sets selector bit `0x2000`, computes segment index `(rows - 1) >> 7 = 8`, and emits one four-byte entry per segment while stepping the bucket index down by eight.")
    lines.append("")
    lines.append(f"- source fields: context `0x{tall_text_source['context']:08x}`, host `0x{tall_text_source['host_char']:02x}`, glyph `0x{tall_text_source['mapped']:02x}`, glyph entry `0x{tall_text_source['glyph_entry']:06x}`, width `{tall_text_source['glyph_width']}`, rows `{tall_text_source['glyph_rows']}`")
    lines.append(f"- producer path: `{tall_bucket['path']}`, selector `0x{int(tall_bucket['selector']):04x}`, object size `0x{int(tall_bucket['object_size']):02x}`, capacity `{tall_bucket['capacity']}`, entry size `{tall_bucket['entry_size']}`")
    first_segment_event = tall_page_first_events[0]
    second_segment_event = tall_page_second_events[0]
    assert isinstance(first_segment_event, dict)
    assert isinstance(second_segment_event, dict)
    lines.append("- page-record allocator first pass: `%d` segment objects allocated through `0x1387c`; first bucket `%d`/segment `%d` count `%d -> %d`" % (
        len(tall_page_first_events),
        first_segment_event["bucket_index"],
        first_segment_event["segment"],
        first_segment_event["count_before"],
        first_segment_event["count_after"],
    ))
    lines.append("- page-record allocator second pass: same selector `0x%04x` reuses all segment buckets; first bucket count `%d -> %d` and prefix `%s`" % (
        tall_page_second["selector"],
        second_segment_event["count_before"],
        second_segment_event["count_after"],
        " ".join(f"{byte:02x}" for byte in tall_page_bucket_array[64][0][:16]),
    ))
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
