#!/usr/bin/env python3
"""Verify local evidence for the transparent segment-57 resource window."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "rom_manifest.json"

RESOURCE_BASE = 0x080000
SEGMENT_SOURCE_OFFSET = 0x03FE22
SEGMENT_READ_LENGTH = 0x0500
CONTINUATION_LENGTH = (SEGMENT_SOURCE_OFFSET + SEGMENT_READ_LENGTH) - 0x040000

EXPECTED = {
    "resource_sha256": "dd4ca68e1790dc81dfdb4c364a0bc5e449f4c53e1bfc39a1536c26369eab935c",
    "firmware_sha256": "feeaf8d651b593af72b65d76fe6b85ee7d191278570438caeac49e0b74dbd079",
    "verified_suffix_sha256": "e0a0fd34ce7a39f79ecd27c0ee288631554a0ff78359b72e27ea6087651bcf1f",
    "mirror_continuation_sha256": "e435e3b9d033e491b57282a88b0f321aa5fecae8128fa060844cc01379349563",
    "code_pair_continuation_sha256": "90934acf59d9e8519c9149dc5df228f8fec2bff8451427be265489be967cdd16",
    "zero_fill_continuation_sha256": "359f38eef400e2fa3924a3258652e74ee19cd46cb92e47bce91f1194fce25e9e",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def u32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 4], "big")


def interleave(first: bytes, second: bytes) -> bytes:
    if len(first) != len(second):
        raise RuntimeError("cannot interleave ROM images of different sizes")
    out = bytearray(len(first) * 2)
    out[0::2] = first
    out[1::2] = second
    return bytes(out)


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def verified_raw_roms(manifest: dict[str, Any]) -> dict[str, bytes]:
    by_location: dict[str, bytes] = {}
    for rom in manifest["raw_roms"]:
        path = ROOT / rom["filename"]
        if not path.exists():
            raise FileNotFoundError(path)
        actual_size = path.stat().st_size
        if actual_size != int(rom["size_bytes"]):
            raise RuntimeError(
                f"{path.name}: size {actual_size}, expected {rom['size_bytes']}"
            )
        actual_hash = file_sha256(path)
        if actual_hash != rom["sha256"]:
            raise RuntimeError(
                f"{path.name}: sha256 {actual_hash}, expected {rom['sha256']}"
            )
        by_location[str(rom["board_location"])] = path.read_bytes()
    return by_location


def generated_interleaves(
    manifest: dict[str, Any],
    raw: dict[str, bytes],
) -> dict[str, bytes]:
    generated: dict[str, bytes] = {}
    for entry in manifest["interleaves"]:
        first_loc, second_loc = entry["byte_order"]
        data = interleave(raw[first_loc], raw[second_loc])
        actual_hash = sha256(data)
        if actual_hash != entry["sha256"]:
            raise RuntimeError(
                f"{entry['name']}: sha256 {actual_hash}, expected {entry['sha256']}"
            )
        generated[str(entry["name"])] = data
    return generated


def resource_head_scan(
    memory: bytes | bytearray,
    *,
    scan_span: int | None = None,
) -> dict[str, Any]:
    span = len(memory) if scan_span is None else int(scan_span)
    probe = 0
    heads: list[int] = []
    records: list[dict[str, int]] = []
    boundary_crossings = 0

    for _ in range(512):
        if probe >= span:
            return {
                "status": "end",
                "head_offsets": heads,
                "walked_records": records,
                "boundary_crossings": boundary_crossings,
                "final_probe": probe,
            }
        if probe + 4 > len(memory):
            return {
                "status": "source-exhausted",
                "head_offsets": heads,
                "walked_records": records,
                "boundary_crossings": boundary_crossings,
                "final_probe": probe,
            }
        marker = u32(memory, probe)
        if marker != 0x48454144:
            probe += 0x40000
            continue

        heads.append(probe)
        record = probe
        cumulative = 0
        next_probe_units = 1
        while True:
            if record + 8 > len(memory):
                return {
                    "status": "source-exhausted",
                    "head_offsets": heads,
                    "walked_records": records,
                    "boundary_crossings": boundary_crossings,
                    "final_probe": record,
                }
            length = u32(memory, record + 4)
            cumulative += length
            record += length
            if record >= span:
                return {
                    "status": "end",
                    "head_offsets": heads,
                    "walked_records": records,
                    "boundary_crossings": boundary_crossings,
                    "final_probe": record,
                }
            if cumulative > 0x3FFFA:
                next_probe_units += 1
                cumulative -= 0x40000
                boundary_crossings += 1
            if record + 4 > len(memory):
                return {
                    "status": "source-exhausted",
                    "head_offsets": heads,
                    "walked_records": records,
                    "boundary_crossings": boundary_crossings,
                    "final_probe": record,
                }
            marker = u32(memory, record)
            if marker in (0, 0xFFFFFFFF):
                probe += next_probe_units * 0x40000
                break
            if marker == 0x000000BE:
                return {
                    "status": "jump-or-error",
                    "head_offsets": heads,
                    "walked_records": records,
                    "boundary_crossings": boundary_crossings,
                    "final_probe": probe,
                }
            records.append({
                "offset": record,
                "marker": marker,
                "length": u32(memory, record + 4),
            })

    raise RuntimeError("HEAD scanner exceeded iteration limit")


def candidate_scan(memory: bytes, *, scan_span: int | None = None) -> dict[str, Any]:
    head_scan = resource_head_scan(memory, scan_span=scan_span)
    counters = {
        "0x78278e": 0,
        "0x782790": 0,
        "0x782792": 0,
        "0x782798": 0,
        "0x78279a": 0,
    }
    for record in head_scan["walked_records"]:
        marker = int(record["marker"])
        offset = int(record["offset"])
        if marker not in (0x14, 0x15) or offset + 0x21 > len(memory):
            continue
        address = RESOURCE_BASE + offset
        class_byte = memory[offset + 0x20]
        is_low_builtin = 0x080000 <= address <= 0x0FFFFE
        counters["0x78278e"] += 1
        if class_byte == 1:
            counters["0x782790"] += 1
            if is_low_builtin:
                counters["0x782792"] += 1
        elif class_byte == 0:
            counters["0x782798"] += 1
            if is_low_builtin:
                counters["0x78279a"] += 1
    return {
        "status": head_scan["status"],
        "head_offsets": head_scan["head_offsets"],
        "candidate_count": counters["0x78278e"],
        "counters": counters,
    }


def build_report() -> dict[str, Any]:
    manifest = load_manifest()
    raw = verified_raw_roms(manifest)
    interleaves = generated_interleaves(manifest, raw)
    resources = interleaves["resources_data"]
    firmware = interleaves["firmware_68000"]

    suffix = resources[SEGMENT_SOURCE_OFFSET:0x040000]
    continuations = {
        "mirror": resources[:CONTINUATION_LENGTH],
        "code_pair": firmware[:CONTINUATION_LENGTH],
        "zero_fill": b"\x00" * CONTINUATION_LENGTH,
    }
    variants = {
        "mirror": resources + resources,
        "code_pair": resources + firmware,
        "zero_fill": resources + (b"\x00" * len(resources)),
    }

    return {
        "resource_sha256": sha256(resources),
        "firmware_sha256": sha256(firmware),
        "segment_source_offset": SEGMENT_SOURCE_OFFSET,
        "segment_firmware_start": RESOURCE_BASE + SEGMENT_SOURCE_OFFSET,
        "segment_firmware_end_exclusive": (
            RESOURCE_BASE + SEGMENT_SOURCE_OFFSET + SEGMENT_READ_LENGTH
        ),
        "segment_read_length": SEGMENT_READ_LENGTH,
        "verified_suffix_length": len(suffix),
        "verified_suffix_sha256": sha256(suffix),
        "continuation_length": CONTINUATION_LENGTH,
        "continuations": {
            name: {
                "first_long": u32(data, 0) if len(data) >= 4 else None,
                "sha256": sha256(data),
            }
            for name, data in continuations.items()
        },
        "head_scans": {
            name: resource_head_scan(data, scan_span=len(data))
            for name, data in variants.items()
        },
        "candidate_scans": {
            name: candidate_scan(data, scan_span=len(data))
            for name, data in variants.items()
        },
    }


def assert_expected(report: dict[str, Any]) -> None:
    checks = {
        "resource_sha256": report["resource_sha256"],
        "firmware_sha256": report["firmware_sha256"],
        "verified_suffix_sha256": report["verified_suffix_sha256"],
        "mirror_continuation_sha256": report["continuations"]["mirror"]["sha256"],
        "code_pair_continuation_sha256": (
            report["continuations"]["code_pair"]["sha256"]
        ),
        "zero_fill_continuation_sha256": report["continuations"]["zero_fill"]["sha256"],
    }
    for key, actual in checks.items():
        if actual != EXPECTED[key]:
            raise AssertionError(f"{key}: {actual}, expected {EXPECTED[key]}")

    expected_scans = {
        "mirror": {
            "heads": [0, 0x40000],
            "candidate_count": 48,
            "low_class_one": 24,
            "low_class_zero": 24,
        },
        "code_pair": {
            "heads": [0],
            "candidate_count": 24,
            "low_class_one": 12,
            "low_class_zero": 12,
        },
        "zero_fill": {
            "heads": [0],
            "candidate_count": 24,
            "low_class_one": 12,
            "low_class_zero": 12,
        },
    }
    for name, expected in expected_scans.items():
        head_scan = report["head_scans"][name]
        candidate = report["candidate_scans"][name]
        counters = candidate["counters"]
        if head_scan["head_offsets"] != expected["heads"]:
            raise AssertionError(
                f"{name}: heads {head_scan['head_offsets']}, expected {expected['heads']}"
            )
        if candidate["candidate_count"] != expected["candidate_count"]:
            raise AssertionError(
                f"{name}: candidate_count {candidate['candidate_count']}, "
                f"expected {expected['candidate_count']}"
            )
        if counters["0x782792"] != expected["low_class_one"]:
            raise AssertionError(
                f"{name}: low class-one count {counters['0x782792']}, "
                f"expected {expected['low_class_one']}"
            )
        if counters["0x78279a"] != expected["low_class_zero"]:
            raise AssertionError(
                f"{name}: low class-zero count {counters['0x78279a']}, "
                f"expected {expected['low_class_zero']}"
            )


def print_report(report: dict[str, Any]) -> None:
    print("resource-window probe")
    print(f"  resource sha256: {report['resource_sha256']}")
    print(f"  firmware sha256: {report['firmware_sha256']}")
    print(
        "  segment-57 read: "
        f"0x{report['segment_firmware_start']:06x}.."
        f"0x{report['segment_firmware_end_exclusive'] - 1:06x} "
        f"({report['segment_read_length']} bytes)"
    )
    print(
        "  verified suffix: "
        f"{report['verified_suffix_length']} bytes, "
        f"sha256 {report['verified_suffix_sha256']}"
    )
    print(f"  continuation length: {report['continuation_length']} bytes")
    for name, info in report["continuations"].items():
        print(
            f"  {name:9s}: first_long 0x{info['first_long']:08x}, "
            f"sha256 {info['sha256']}"
        )
    for name, scan in report["head_scans"].items():
        candidate = report["candidate_scans"][name]
        counters = candidate["counters"]
        heads = ", ".join(f"0x{offset:05x}" for offset in scan["head_offsets"])
        print(
            f"  {name:9s}: heads [{heads}], "
            f"candidates {candidate['candidate_count']}, "
            f"low class1/class0 {counters['0x782792']}/{counters['0x78279a']}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe the local ROM evidence for the 0x0c0000 resource window.",
    )
    parser.add_argument("--quiet", action="store_true", help="print nothing on success")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report()
    assert_expected(report)
    if not args.quiet:
        print_report(report)


if __name__ == "__main__":
    main()
