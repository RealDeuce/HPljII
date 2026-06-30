#!/usr/bin/env python3
"""Verify LaserJet II ROM dumps and regenerate local derived artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "rom_manifest.json"
GENERATED = ROOT / "generated"
UNIDASM = ROOT.parent / "mame" / "unidasm"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_if_changed(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_bytes() if path.exists() else None
    new = data.encode("utf-8") if isinstance(data, str) else data
    if old != new:
        path.write_bytes(new)


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def verify_raw_roms(manifest: dict) -> dict[str, Path]:
    by_location: dict[str, Path] = {}
    for rom in manifest["raw_roms"]:
        path = ROOT / rom["filename"]
        if not path.exists():
            raise FileNotFoundError(path)
        actual_size = path.stat().st_size
        if actual_size != rom["size_bytes"]:
            raise RuntimeError(f"{path.name}: size {actual_size}, expected {rom['size_bytes']}")
        actual_hash = sha256(path)
        if actual_hash != rom["sha256"]:
            raise RuntimeError(f"{path.name}: sha256 {actual_hash}, expected {rom['sha256']}")
        by_location[rom["board_location"]] = path
    return by_location


def interleave(first: Path, second: Path) -> bytes:
    a = first.read_bytes()
    b = second.read_bytes()
    if len(a) != len(b):
        raise RuntimeError(f"Cannot interleave unequal ROMs: {first.name}, {second.name}")
    out = bytearray(len(a) * 2)
    out[0::2] = a
    out[1::2] = b
    return bytes(out)


def generate_interleaves(manifest: dict, by_location: dict[str, Path]) -> dict[str, Path]:
    generated: dict[str, Path] = {}
    for entry in manifest["interleaves"]:
        first_loc, second_loc = entry["byte_order"]
        data = interleave(by_location[first_loc], by_location[second_loc])
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != entry["sha256"]:
            raise RuntimeError(f"{entry['name']}: sha256 {actual_hash}, expected {entry['sha256']}")
        out_path = ROOT / entry["generated_file"]
        write_if_changed(out_path, data)
        generated[entry["name"]] = out_path
    return generated


def generate_vector_notes(firmware: Path) -> None:
    data = firmware.read_bytes()
    names = {
        0: "initial_ssp",
        1: "reset_pc",
        2: "bus_error",
        3: "address_error",
        4: "illegal_instruction",
        5: "zero_divide",
        6: "chk",
        7: "trapv",
        8: "privilege_violation",
        9: "trace",
        10: "line_1010",
        11: "line_1111",
    }
    lines = [
        "# IC30/IC13 68000 Vector Table",
        "",
        "Values are decoded as big-endian 68000 longwords from generated/roms/ic30_ic13.bin.",
        "",
    ]
    for vector in range(0x40):
        offset = vector * 4
        value = int.from_bytes(data[offset : offset + 4], "big")
        label = names.get(vector, f"vector_{vector:02d}")
        lines.append(f"{vector:02d}  @{offset:06x}  {value:08x}  {label}")
    lines.append("")
    write_if_changed(GENERATED / "analysis" / "ic30_ic13_vectors.txt", "\n".join(lines))


def generate_resource_header_notes(resources: Path) -> None:
    data = resources.read_bytes()
    text = "".join(chr(b) if 32 <= b < 127 else "." for b in data[:0x180])
    lines = [
        "# IC32/IC15 Resource Header Probe",
        "",
        "Printable ASCII projection of the first 0x180 bytes from generated/roms/ic32_ic15.bin.",
        "",
    ]
    for offset in range(0, len(text), 64):
        lines.append(f"{offset:06x}: {text[offset:offset + 64]}")
    lines.append("")
    write_if_changed(GENERATED / "analysis" / "ic32_ic15_header.txt", "\n".join(lines))


def generate_disassembly(firmware: Path) -> None:
    if not UNIDASM.exists():
        write_if_changed(
            GENERATED / "disasm" / "README.txt",
            f"unidasm was not found at {UNIDASM}; disassembly was not generated.\n",
        )
        return
    windows = [
        ("ic30_ic13_reset_000110.lst", "0x110", "0x110", "0x500"),
        ("ic30_ic13_cart_resource_scan_0003e8.lst", "0x3e8", "0x3e8", "0x260"),
        ("ic30_ic13_trampoline_handlers_000c7e.lst", "0xc7e", "0xc7e", "0x280"),
        ("ic30_ic13_timer_status_trampoline_000d52.lst", "0xd52", "0xd52", "0x22c"),
        ("ic30_ic13_scan_status_interrupt_000f84.lst", "0xf84", "0xf84", "0x170"),
        ("ic30_ic13_scheduler_trap_handlers_00110c.lst", "0x110c", "0x110c", "0x180"),
        ("ic30_ic13_scheduler_dispatch_00123a.lst", "0x123a", "0x123a", "0x50"),
        ("ic30_ic13_error_report_entry_001284.lst", "0x1284", "0x1284", "0x130"),
        ("ic30_ic13_error_report_00128c.lst", "0x128c", "0x128c", "0x120"),
        ("ic30_ic13_startup_config_probe_0005ba.lst", "0x5ba", "0x5ba", "0x180"),
        ("ic30_ic13_startup_config_init_00071c.lst", "0x71c", "0x71c", "0x80"),
        ("ic30_ic13_startup_memory_probe_00073a.lst", "0x73a", "0x73a", "0x47c"),
        ("ic30_ic13_startup_memory_tests_0008a2.lst", "0x8a2", "0x8a2", "0xd4"),
        ("ic30_ic13_startup_heap_window_000b18.lst", "0xb18", "0xb18", "0x10c"),
        ("ic30_ic13_startup_scheduler_bootstrap_000c24.lst", "0xc24", "0xc24", "0x60"),
        ("ic30_ic13_startup_retained_load_000266.lst", "0x266", "0x266", "0x36"),
        ("ic30_ic13_startup_render_work_init_02feb6.lst", "0x2feb6", "0x2feb6", "0x48"),
        ("ic30_ic13_startup_byte_source_init_003178.lst", "0x3178", "0x3178", "0x5e"),
        ("ic30_ic13_startup_status_ring_init_0031d6.lst", "0x31d6", "0x31d6", "0x22"),
        ("ic30_ic13_interface_status_aggregate_0036e4.lst", "0x36e4", "0x36e4", "0x120"),
        ("ic30_ic13_panel_service_dispatch_003dae.lst", "0x3d66", "0x3d66", "0x210"),
        ("ic30_ic13_page_pool_init_003100.lst", "0x3100", "0x3100", "0x80"),
        ("ic30_ic13_host_input_quiesce_004200.lst", "0x4200", "0x4200", "0x2d4"),
        ("ic30_ic13_host_scheduler_caller_004700.lst", "0x4700", "0x4700", "0x230"),
        ("ic30_ic13_host_input_quiesce_0061e4.lst", "0x61e4", "0x61e4", "0x180"),
        ("ic30_ic13_host_byte_fetch_00a904.lst", "0xa904", "0xa904", "0x2f0"),
        ("ic30_ic13_interface_output_mmio_00a1b0.lst", "0xa1b0", "0xa1b0", "0x90"),
        ("ic30_ic13_panel_service_byte_source_00a39a.lst", "0xa39a", "0xa39a", "0xe0"),
        ("ic30_ic13_8a01_a801_status_bits_00a42c.lst", "0xa42c", "0xa42c", "0x1e0"),
        ("ic30_ic13_a801_a601_io_00a4e8.lst", "0xa4e8", "0xa4e8", "0x420"),
        ("ic30_ic13_host_output_worker_00ae2c.lst", "0xae2c", "0xae2c", "0x150"),
        ("ic30_ic13_host_output_retry_00af7c.lst", "0xaf7c", "0xaf7c", "0xb0"),
        ("ic30_ic13_host_output_fifo_00b022.lst", "0xb022", "0xb022", "0x10a"),
        ("ic30_ic13_font_context_install_00c428.lst", "0xc428", "0xc428", "0x160"),
        ("ic30_ic13_active_pool_cycle_001958.lst", "0x1958", "0x1958", "0x2e6"),
        ("ic30_ic13_page_environment_status_002888.lst", "0x2888", "0x2888", "0x1f8"),
        ("ic30_ic13_page_status_cleanup_002c00.lst", "0x2c00", "0x2c00", "0x80"),
        ("ic30_ic13_service_default_reset_entry_002c84.lst", "0x2c84", "0x2c84", "0xc0"),
        ("ic30_ic13_page_pool_candidate_insert_001c04.lst", "0x1c04", "0x1c04", "0x414"),
        ("ic30_ic13_active_pool_engine_gate_002038.lst", "0x2038", "0x2038", "0x206"),
        ("ic30_ic13_engine_copy_pass_0022f4.lst", "0x22f4", "0x22f4", "0x190"),
        ("ic30_ic13_page_pool_cursor_007612.lst", "0x7612", "0x7612", "0x210"),
        ("ic30_ic13_page_service_messages_008656.lst", "0x8656", "0x8656", "0x400"),
        ("ic30_ic13_status_message_selection_008430.lst", "0x8430", "0x8430", "0x200"),
        ("ic30_ic13_page_environment_message_008a48.lst", "0x8a48", "0x8a48", "0xf8"),
        ("ic30_ic13_message_dispatch_wrappers_008c7a.lst", "0x8c7a", "0x8c7a", "0x60"),
        ("ic30_ic13_panel_menu_commit_004922.lst", "0x4922", "0x4922", "0x160"),
        ("ic30_ic13_nvram_default_record_commit_0096c4.lst", "0x96c4", "0x96c4", "0x1a0"),
        ("ic30_ic13_nvram_serial_bit_helpers_009860.lst", "0x9860", "0x9860", "0x260"),
        ("ic30_ic13_status_bit_helpers_009ba2.lst", "0x9ba2", "0x9ba2", "0x8a"),
        ("ic30_ic13_retained_record_bulk_load_005a16.lst", "0x5a16", "0x5a16", "0x50"),
        ("ic30_ic13_external_ready_service_loop_00ba48.lst", "0xba48", "0xba48", "0x290"),
        ("ic30_ic13_nvram_service_poll_00bbb2.lst", "0xbbb2", "0xbbb2", "0x126"),
        ("ic30_ic13_external_service_io_00bcd8.lst", "0xbcd8", "0xbcd8", "0x430"),
        ("ic30_ic13_external_service_reset_00c06e.lst", "0xc06e", "0xc06e", "0x302"),
        ("ic30_ic13_default_env_menu_update_004fb0.lst", "0x4fb0", "0x4fb0", "0x430"),
        ("ic30_ic13_default_env_record_maintenance_0056c2.lst", "0x56c2", "0x56c2", "0x670"),
        ("ic30_ic13_default_env_load_005e80.lst", "0x5e80", "0x5e80", "0x1e0"),
        ("ic30_ic13_page_pool_candidate_select_007ec6.lst", "0x7ec6", "0x7ec6", "0xd2"),
        ("ic30_ic13_startup_config_code_019a78.lst", "0x19a78", "0x19a78", "0x180"),
        ("ic30_ic13_font_update_common_00c580.lst", "0xc580", "0xc580", "0x160"),
        ("ic30_ic13_pitch_mode_handler_00c390.lst", "0xc390", "0xc390", "0x98"),
        ("ic30_ic13_font_selection_update_handlers_00c6ec.lst", "0xc6ec", "0xc6ec", "0x340"),
        ("ic30_ic13_hmi_vmi_handlers_00ca8c.lst", "0xca8c", "0xca8c", "0x140"),
        ("ic30_ic13_esc_e_metric_refresh_00cbd4.lst", "0xcbd4", "0xcbd4", "0x80"),
        ("ic30_ic13_esc_e_reset_00cc52.lst", "0xcc52", "0xcc52", "0x170"),
        ("ic30_ic13_esc_e_environment_reset_00cda2.lst", "0xcda2", "0xcda2", "0x2b0"),
        ("ic30_ic13_esc_e_parser_state_reset_00e146.lst", "0xe146", "0xe146", "0x160"),
        ("ic30_ic13_heap_allocator_init_00164a.lst", "0x164a", "0x164a", "0x290"),
        ("ic30_ic13_macro_record_chain_helpers_00dfba.lst", "0xdfba", "0xdfba", "0x6a0"),
        ("ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst", "0xe65c", "0xe65c", "0x390"),
        ("ic30_ic13_printable_text_path_00d04a.lst", "0xd04a", "0xd04a", "0xa40"),
        ("ic30_ic13_control_code_handlers_00f02c.lst", "0xf02c", "0xf02c", "0x540"),
        ("ic30_ic13_wrap_mode_handler_00edb0.lst", "0xedb0", "0xedb0", "0x70"),
        ("ic30_ic13_perforation_skip_handler_00ee64.lst", "0xee40", "0xee40", "0x70"),
        ("ic30_ic13_copies_handler_00eef0.lst", "0xeec0", "0xeec0", "0x80"),
        ("ic30_ic13_paper_source_handler_00ef62.lst", "0xef40", "0xef40", "0xf0"),
        ("ic30_ic13_dot_position_handlers_00f48c.lst", "0xf48c", "0xf48c", "0x280"),
        ("ic30_ic13_page_root_finalize_00ff1e.lst", "0xff1e", "0xff1e", "0x170"),
        ("ic30_ic13_page_geometry_tables_009d16.lst", "0x9d16", "0x9d16", "0x190"),
        ("ic30_ic13_page_length_handler_00f9e8.lst", "0xf9e8", "0xf9e8", "0x290"),
        ("ic30_ic13_page_size_handler_00fc74.lst", "0xfc74", "0xfc74", "0x260"),
        ("ic30_ic13_orientation_handler_010220.lst", "0x10220", "0x10220", "0x270"),
        ("ic30_ic13_page_root_allocate_010084.lst", "0x10084", "0x10084", "0x1c0"),
        ("ic30_ic13_coordinate_math_0104d8.lst", "0x104d8", "0x104d8", "0xb0"),
        ("ic30_ic13_raster_handlers_0105d0.lst", "0x105d0", "0x105d0", "0x300"),
        ("ic30_ic13_rectangle_graphics_010898.lst", "0x10898", "0x10898", "0x520"),
        ("ic30_ic13_main_parser_loop_011774.lst", "0x11774", "0x11774", "0x430"),
        ("ic30_ic13_tokenizer_stateful_helpers_011ba6.lst", "0x11ba6", "0x11ba6", "0x300"),
        ("ic30_ic13_parser_setup_handlers_011ea4.lst", "0x11ea4", "0x11ea4", "0xd0"),
        ("ic30_ic13_control_z_handlers_0120d2.lst", "0x120d2", "0x120d2", "0xf8"),
        ("ic30_ic13_font_selector_setup_helpers_011ec8.lst", "0x11ec8", "0x11ec8", "0xa0"),
        ("ic30_ic13_transparent_data_handler_011f5a.lst", "0x11f5a", "0x11f5a", "0x70"),
        ("ic30_ic13_payload_dispatch_011f82.lst", "0x11f82", "0x11f82", "0x470"),
        ("ic30_ic13_text_payload_repeat_readers_012120.lst", "0x12120", "0x12120", "0x650"),
        ("ic30_ic13_text_span_state_0126e2.lst", "0x126e2", "0x126e2", "0x132"),
        ("ic30_ic13_text_span_flush_012714.lst", "0x12714", "0x12714", "0x100"),
        ("ic30_ic13_vertical_forms_control_01280a.lst", "0x1280a", "0x1280a", "0x730"),
        ("ic30_ic13_text_object_queue_012f2e.lst", "0x12f2e", "0x12f2e", "0x150"),
        ("ic30_ic13_raster_object_queue_013070.lst", "0x13070", "0x13070", "0x330"),
        ("ic30_ic13_display_list_helpers_013386.lst", "0x13386", "0x13386", "0x610"),
        ("ic30_ic13_object_compare_013a48.lst", "0x13a48", "0x13a48", "0x4c0"),
        ("ic30_ic13_active_object_scan_014398.lst", "0x14398", "0x14398", "0x300"),
        ("ic30_ic13_active_object_dispatch_014ba4.lst", "0x14ba4", "0x14ba4", "0x580"),
        ("ic30_ic13_page_root_font_slot_scan_0196c4.lst", "0x196c4", "0x196c4", "0x70"),
        ("ic30_ic13_page_scheduler_019dd2.lst", "0x19dd2", "0x19dd2", "0x510"),
        ("ic30_ic13_font_sample_page_01c170.lst", "0x1c170", "0x1c170", "0x1200"),
        ("ic30_ic13_font_sample_row_helpers_01d198.lst", "0x1d198", "0x1d198", "0x1000"),
        ("ic30_ic13_font_candidate_filters_01519a.lst", "0x1519a", "0x1519a", "0x6b0"),
        ("ic30_ic13_font_candidate_activate_01569c.lst", "0x1569c", "0x1569c", "0x1b0"),
        ("ic30_ic13_inline_symbol_helpers_015850.lst", "0x15850", "0x15850", "0xd0"),
        ("ic30_ic13_assign_font_id_015a56.lst", "0x15a56", "0x15a56", "0x50"),
        ("ic30_ic13_font_stream_byte_helpers_01599c.lst", "0x1599c", "0x1599c", "0xc0"),
        ("ic30_ic13_font_payload_setup_015b80.lst", "0x15b80", "0x15b80", "0x4d0"),
        ("ic30_ic13_font_payload_object_path_016040.lst", "0x16040", "0x16040", "0x860"),
        ("ic30_ic13_font_payload_readers_016874.lst", "0x16874", "0x16874", "0x1a0"),
        ("ic30_ic13_font_payload_descriptor_helpers_016a10.lst", "0x16a10", "0x16a10", "0x204"),
        ("ic30_ic13_font_resource_object_add_016c14.lst", "0x16c14", "0x16c14", "0x1a0"),
        ("ic30_ic13_font_control_dispatch_016df6.lst", "0x16df6", "0x16df6", "0xb8"),
        ("ic30_ic13_font_resource_validate_016fae.lst", "0x16fae", "0x16fae", "0x80"),
        ("ic30_ic13_font_resource_find_017026.lst", "0x17026", "0x17026", "0x120"),
        ("ic30_ic13_font_resource_payload_record_lookup_0170be.lst", "0x170be", "0x170be", "0x90"),
        ("ic30_ic13_font_resource_payload_initializer_01719c.lst", "0x1719c", "0x1719c", "0x130"),
        ("ic30_ic13_font_resource_classify_0172c0.lst", "0x172c0", "0x172c0", "0x100"),
        ("ic30_ic13_font_resource_setup_type_017362.lst", "0x17362", "0x17362", "0x80"),
        ("ic30_ic13_font_resource_validate_predicates_017358.lst", "0x17358", "0x17358", "0x3b0"),
        ("ic30_ic13_font_id_select_017708.lst", "0x17708", "0x17708", "0x130"),
        ("ic30_ic13_font_resource_refresh_helpers_0178fa.lst", "0x178fa", "0x178fa", "0x130"),
        ("ic30_ic13_font_fixed_record_release_017a24.lst", "0x17a24", "0x17a24", "0x580"),
        ("ic30_ic13_font_resource_payload_link_01887a.lst", "0x1887a", "0x1887a", "0x320"),
        ("ic30_ic13_font_resource_release_018b92.lst", "0x18b92", "0x18b92", "0xe0"),
        ("ic30_ic13_font_resource_release_alt_018bf2.lst", "0x18bf2", "0x18bf2", "0xe0"),
        ("ic30_ic13_font_scheduler_commit_01a4fa.lst", "0x1a4fa", "0x1a4fa", "0x4c0"),
        ("ic30_ic13_font_resource_object_lookup_01b4c0.lst", "0x1b4c0", "0x1b4c0", "0x720"),
        ("ic30_ic13_font_candidate_window_prune_01ba92.lst", "0x1ba92", "0x1ba92", "0x170"),
        ("ic30_ic13_font_default_update_01ba40.lst", "0x1ba40", "0x1ba40", "0x80"),
        ("ic30_ic13_font_candidate_object_alloc_01bc38.lst", "0x1bc38", "0x1bc38", "0x150"),
        ("ic30_ic13_default_font_tables_01ab84.lst", "0x1ab84", "0x1ab84", "0x4d0"),
        ("ic30_ic13_symbol_set_handler_01be22.lst", "0x1bde2", "0x1bde2", "0x2d0"),
        ("ic30_ic13_font_resource_scan_01a2e4.lst", "0x1a2e4", "0x1a2e4", "0x380"),
        ("ic30_ic13_font_candidate_classify_01a9be.lst", "0x1a9be", "0x1a9be", "0x1d0"),
        ("ic30_ic13_font_page_setup_01e0b2.lst", "0x1e0b2", "0x1e0b2", "0xf0"),
        ("ic30_ic13_font_page_setup_alt_01e8e6.lst", "0x1e8e6", "0x1e8e6", "0x1c0"),
        ("ic30_ic13_active_render_scheduler_01eb2a.lst", "0x1eb2a", "0x1eb2a", "0x260"),
        ("ic30_ic13_page_record_to_render_record_01ed84.lst", "0x1ed84", "0x1ed84", "0x120"),
        ("ic30_ic13_bitmap_state_setup_01ee9e.lst", "0x1ee9e", "0x1ee9e", "0x160"),
        ("ic30_ic13_bitmap_bucket_walk_01ef6a.lst", "0x1ef6a", "0x1ef6a", "0x190"),
        ("ic30_ic13_bitmap_compact_object_renderers_01f024.lst", "0x1f024", "0x1f024", "0x3b0"),
        ("ic30_ic13_bitmap_draw_core_01f3d4.lst", "0x1f3d4", "0x1f3d4", "0x690"),
        ("ic30_ic13_bitmap_encoded_span_modes_01f88e.lst", "0x1f88e", "0x1f88e", "0x1d0"),
        ("ic30_ic13_bitmap_row_copy_tables_01fa5c.lst", "0x1fa5c", "0x1fa5c", "0x4c0"),
        ("ic30_ic13_glyph_row_copy_helper_02f27c.lst", "0x2f27c", "0x2f27c", "0x250"),
        ("ic30_ic13_pcl_escape_parser_00da9a.lst", "0xda9a", "0xda9a", "0x520"),
    ]
    for out_name, basepc, skip, count in windows:
        result = subprocess.run(
            [
                str(UNIDASM),
                str(firmware),
                "-arch",
                "m68000",
                "-basepc",
                basepc,
                "-skip",
                skip,
                "-count",
                count,
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        write_if_changed(GENERATED / "disasm" / out_name, result.stdout)


def main() -> None:
    manifest = load_manifest()
    by_location = verify_raw_roms(manifest)
    generated = generate_interleaves(manifest, by_location)
    generate_vector_notes(generated["firmware_68000"])
    generate_resource_header_notes(generated["resources_data"])
    generate_disassembly(generated["firmware_68000"])
    for name, path in generated.items():
        print(f"{name}: {path.relative_to(ROOT)} {sha256(path)}")


if __name__ == "__main__":
    main()
