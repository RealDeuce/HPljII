# IC30/IC13 Parser Anchor Cross-References

Linear scan over even offsets for selected 68000 absolute calls, jumps, LEAs,
BRA, and BSR forms. This is a lead generator, not a full disassembler; confirm
each reference in local disassembly before naming behavior.

## byte_fetch (`0x00a904`)

| Source | Kind |
| --- | --- |
| `0x00a97c` | `bra_w` |
| `0x00aaa2` | `bra_w` |
| `0x00ab8a` | `bra_w` |
| `0x00da9a` | `jsr_abs` |
| `0x00daa6` | `jsr_abs` |
| `0x00dab2` | `jsr_abs` |
| `0x00dace` | `jsr_abs` |
| `0x00dada` | `jsr_abs` |
| `0x012142` | `jsr_abs` |
| `0x012152` | `jsr_abs` |
| `0x0124bc` | `jsr_abs` |
| `0x0124cc` | `jsr_abs` |
| `0x012582` | `jsr_abs` |
| `0x012592` | `jsr_abs` |
| `0x0138fa` | `jsr_abs` |
| `0x013904` | `jsr_abs` |
| `0x0168dc` | `jsr_abs` |
| `0x0168fe` | `jsr_abs` |
| `0x016960` | `jsr_abs` |
| `0x01697a` | `jsr_abs` |
| `0x0169ca` | `jsr_abs` |
| `0x0169e0` | `jsr_abs` |

## esc_byte_fetch_wrapper (`0x00da9a`)

| Source | Kind |
| --- | --- |
| `0x00dabe` | `bra_b` |
| `0x00daf4` | `lea_abs_a3` |
| `0x00db96` | `lea_abs_a5` |
| `0x0117d2` | `jsr_abs` |
| `0x011bc2` | `jsr_abs` |
| `0x011be2` | `jsr_abs` |
| `0x011c8e` | `jsr_abs` |
| `0x0122da` | `jsr_abs` |
| `0x012630` | `jsr_abs` |

## control_1a_58_probe (`0x00dace`)

| Source | Kind |
| --- | --- |
| `0x010660` | `jsr_abs` |
| `0x0106ba` | `jsr_abs` |
| `0x012338` | `jsr_abs` |
| `0x01238a` | `jsr_abs` |
| `0x012dd0` | `jsr_abs` |
| `0x012df6` | `jsr_abs` |
| `0x012e1a` | `jsr_abs` |
| `0x012ef8` | `jsr_abs` |
| `0x0159a4` | `jsr_abs` |
| `0x0159be` | `jsr_abs` |

## escape_tokenizer (`0x00daf0`)

| Source | Kind |
| --- | --- |
| `0x011b28` | `jsr_abs` |
| `0x011bdc` | `jsr_abs` |
| `0x011c88` | `jsr_abs` |
| `0x011d64` | `jsr_abs` |
| `0x011e2a` | `jsr_abs` |
| `0x011fda` | `jsr_abs` |
| `0x011fec` | `jsr_abs` |
| `0x012014` | `jsr_abs` |
| `0x01202a` | `jsr_abs` |
| `0x01262a` | `jsr_abs` |

## angle_bracket_helper (`0x00db46`)

| Source | Kind |
| --- | --- |
| `0x00db0a` | `bsr_b` |
| `0x00db2a` | `bsr_b` |
| `0x00db70` | `bra_b` |

## parameter_parser (`0x00db74`)

| Source | Kind |
| --- | --- |
| `0x00db00` | `bsr_b` |

## parsed_command_dispatch (`0x00dd08`)

(no direct references found)

## clear_command_record (`0x00dfba`)

| Source | Kind |
| --- | --- |
| `0x00dd9e` | `jsr_abs` |
| `0x00de2a` | `jsr_abs` |
| `0x00de74` | `jsr_abs` |
| `0x00df1a` | `jsr_abs` |
| `0x00df68` | `jsr_abs` |
| `0x00dfa0` | `jsr_abs` |

## append_command_byte (`0x00e002`)

| Source | Kind |
| --- | --- |
| `0x00ddca` | `jsr_abs` |
| `0x00ddd6` | `jsr_abs` |
| `0x00dde2` | `jsr_abs` |
| `0x00ddf4` | `jsr_abs` |
| `0x011874` | `jsr_abs` |
| `0x011a82` | `jsr_abs` |
| `0x011ac0` | `jsr_abs` |
| `0x011adc` | `jsr_abs` |
| `0x011b84` | `jsr_abs` |
| `0x011dae` | `jsr_abs` |
| `0x011dc0` | `jsr_abs` |
| `0x011dca` | `jsr_abs` |
| `0x011e80` | `jsr_abs` |
| `0x011e92` | `jsr_abs` |
| `0x011e9c` | `jsr_abs` |
| `0x012114` | `jsr_abs` |
| `0x01212e` | `jsr_abs` |
| `0x01213a` | `jsr_abs` |
| `0x012174` | `jsr_abs` |
| `0x0121c0` | `jsr_abs` |
| `0x0123a4` | `jsr_abs` |
| `0x0123ce` | `jsr_abs` |
| `0x0123fa` | `jsr_abs` |

## find_or_alloc_command_record (`0x00e0a4`)

| Source | Kind |
| --- | --- |
| `0x00dd38` | `jsr_abs` |
| `0x00ff6e` | `jsr_abs` |

## page_root_finalize_or_reset (`0x00ff1e`)

| Source | Kind |
| --- | --- |
| `0x00cc92` | `jsr_abs` |
| `0x00d494` | `jsr_abs` |
| `0x00d8e4` | `jsr_abs` |
| `0x00da30` | `jsr_abs` |
| `0x00da86` | `jsr_abs` |
| `0x00ef96` | `jsr_abs` |
| `0x00f128` | `jsr_abs` |
| `0x00fa68` | `jsr_abs` |
| `0x00fb10` | `jsr_abs` |
| `0x00fcaa` | `jsr_abs` |
| `0x00fd6e` | `jsr_abs` |
| `0x0106e6` | `jsr_abs` |
| `0x010d32` | `jsr_abs` |
| `0x0127be` | `jsr_abs` |
| `0x01ba76` | `jsr_abs` |

## ensure_page_object_root (`0x010084`)

| Source | Kind |
| --- | --- |
| `0x00d20a` | `jsr_abs` |
| `0x00d49a` | `jsr_abs` |
| `0x00d63c` | `jsr_abs` |
| `0x00d8ea` | `jsr_abs` |
| `0x00d9ec` | `jsr_abs` |
| `0x00da4c` | `jsr_abs` |
| `0x00f0b6` | `jsr_abs` |
| `0x00f10c` | `jsr_abs` |
| `0x00f17a` | `jsr_abs` |
| `0x00f2b0` | `jsr_abs` |
| `0x00f576` | `jsr_abs` |
| `0x00f6ee` | `jsr_abs` |
| `0x00ff9a` | `jsr_abs` |
| `0x0106a4` | `jsr_abs` |
| `0x0106ec` | `jsr_abs` |
| `0x010d0a` | `jsr_abs` |
| `0x010d38` | `jsr_abs` |
| `0x012788` | `jsr_abs` |
| `0x0127c4` | `jsr_abs` |
| `0x012912` | `jsr_abs` |
| `0x01c2d2` | `jsr_abs` |
| `0x01ca08` | `jsr_abs` |
| `0x01e0ee` | `jsr_abs` |
| `0x01e922` | `jsr_abs` |
| `0x030f4e` | `jsr_abs` |

## text_span_flush_to_page_objects (`0x012714`)

| Source | Kind |
| --- | --- |
| `0x00d530` | `jsr_abs` |
| `0x00d97a` | `jsr_abs` |
| `0x00ebd8` | `jsr_abs` |
| `0x00f35c` | `jsr_abs` |
| `0x00f748` | `jsr_abs` |
| `0x00f86e` | `jsr_abs` |
| `0x01269a` | `jsr_abs` |
| `0x01caa0` | `jsr_abs` |

## text_object_queue_builder (`0x012f2e`)

| Source | Kind |
| --- | --- |
| `0x00d47a` | `jsr_abs` |
| `0x00d8ca` | `jsr_abs` |

## raster_row_object_builder (`0x013070`)

| Source | Kind |
| --- | --- |
| `0x0106cc` | `jsr_abs` |

## bucket_object_alloc_and_link (`0x013250`)

| Source | Kind |
| --- | --- |
| `0x013136` | `jsr_abs` |

## display_list_stream_allocator (`0x0132b6`)

| Source | Kind |
| --- | --- |
| `0x01325c` | `jsr_abs` |

## rectangle_object_queue_entry (`0x013386`)

| Source | Kind |
| --- | --- |
| `0x010d16` | `jsr_abs` |

## rectangle_object_insert (`0x0133aa`)

| Source | Kind |
| --- | --- |
| `0x01339c` | `jsr_abs` |

## display_list_storage_alloc (`0x01381c`)

| Source | Kind |
| --- | --- |
| `0x0133ba` | `jsr_abs` |
| `0x0136f0` | `jsr_abs` |
| `0x01371e` | `jsr_abs` |

## bucket_find_or_alloc (`0x01387c`)

| Source | Kind |
| --- | --- |
| `0x012fe0` | `jsr_abs` |
| `0x012ffe` | `jsr_abs` |
| `0x01361a` | `jsr_abs` |

## raster_payload_copy_from_host (`0x0138de`)

| Source | Kind |
| --- | --- |
| `0x01320c` | `jsr_abs` |

## font_candidate_overlap_or_order_check (`0x013a48`)

| Source | Kind |
| --- | --- |
| `0x014c66` | `jsr_abs` |

## font_candidate_select (`0x014398`)

| Source | Kind |
| --- | --- |
| `0x013f7c` | `jsr_abs` |

## snapshot_selected_font_candidate (`0x01440c`)

| Source | Kind |
| --- | --- |
| `0x014d92` | `jsr_abs` |

## font_candidate_dispatch (`0x014c64`)

| Source | Kind |
| --- | --- |
| `0x00e798` | `jsr_abs` |
| `0x013fbc` | `jsr_abs` |
| `0x0167ac` | `jsr_abs` |
| `0x01686a` | `jsr_abs` |
| `0x0177fa` | `jsr_abs` |
| `0x017830` | `jsr_abs` |
| `0x017ac2` | `jsr_abs` |
| `0x017afe` | `jsr_abs` |
| `0x017f08` | `jsr_abs` |
| `0x017f44` | `jsr_abs` |
| `0x01b364` | `jsr_abs` |
| `0x01c66a` | `jsr_abs` |
| `0x01cf16` | `jsr_abs` |
| `0x01ea2e` | `jsr_abs` |
| `0x031724` | `jsr_abs` |
| `0x031822` | `jsr_abs` |

## font_candidate_pitch_filter (`0x01519a`)

| Source | Kind |
| --- | --- |
| `0x013f34` | `jsr_abs` |

## font_candidate_style_filter (`0x0153c6`)

| Source | Kind |
| --- | --- |
| `0x013f1e` | `jsr_abs` |

## font_candidate_activate_primary_list (`0x01569c`)

| Source | Kind |
| --- | --- |
| `0x013eea` | `jsr_abs` |

## font_candidate_filter_current_selection (`0x0156de`)

| Source | Kind |
| --- | --- |
| `0x013f08` | `jsr_abs` |

## font_resource_download_or_object_add (`0x016c14`)

(no direct references found)

## page_root_font_slot_scan (`0x0196c4`)

| Source | Kind |
| --- | --- |
| `0x017a62` | `jsr_abs` |
| `0x017e00` | `jsr_abs` |
| `0x018218` | `jsr_abs` |
| `0x018266` | `jsr_abs` |
| `0x0188aa` | `jsr_abs` |

## font_resource_scheduler_handoff (`0x019dd2`)

| Source | Kind |
| --- | --- |
| `0x00447a` | `jsr_abs` |
| `0x004760` | `jsr_abs` |
| `0x007164` | `jsr_abs` |
| `0x00bb16` | `jsr_abs` |
| `0x01a3c2` | `jsr_abs` |

## font_resource_candidate_scan (`0x01a2e4`)

| Source | Kind |
| --- | --- |
| `0x002f1c` | `jsr_abs` |

## font_resource_region_scan (`0x01a616`)

| Source | Kind |
| --- | --- |
| `0x01a39a` | `jsr_abs` |
| `0x01a58a` | `jsr_abs` |

## font_candidate_classify_and_count (`0x01a9be`)

| Source | Kind |
| --- | --- |
| `0x01a6f8` | `jsr_abs` |
| `0x01a7b4` | `jsr_abs` |

## copy_active_page_record_to_render_record (`0x01ed84`)

| Source | Kind |
| --- | --- |
| `0x01ed76` | `jsr_abs` |

## page_record_queue_bridge (`0x01edc6`)

| Source | Kind |
| --- | --- |
| `0x01edb6` | `jsr_abs` |

## bitmap_render_state_setup (`0x01ee9e`)

| Source | Kind |
| --- | --- |
| `0x01ed6e` | `jsr_abs` |

## bitmap_band_render_entry (`0x01ef6a`)

| Source | Kind |
| --- | --- |
| `0x01ec9e` | `jsr_abs` |

## bitmap_band_destination_base_setup (`0x01ef86`)

| Source | Kind |
| --- | --- |
| `0x01ef72` | `bsr_b` |

## bitmap_bucket_chain_dispatch (`0x01efc2`)

| Source | Kind |
| --- | --- |
| `0x01ef74` | `bsr_b` |

## bitmap_object_coordinate_decode (`0x01f3d4`)

| Source | Kind |
| --- | --- |
| `0x01f050` | `bsr_w` |
| `0x01f0f0` | `bsr_w` |
| `0x01f22a` | `bsr_w` |
| `0x01f29a` | `bsr_w` |
| `0x01f83a` | `jsr_abs` |
| `0x01f8a4` | `jsr_abs` |

## bitmap_object_span_setup (`0x01f414`)

| Source | Kind |
| --- | --- |
| `0x01f054` | `bsr_w` |
| `0x01f0f4` | `bsr_w` |
| `0x01f22e` | `bsr_w` |
| `0x01f29e` | `bsr_w` |
| `0x01f8ac` | `jsr_abs` |

## bitmap_special_object_dispatch (`0x01f446`)

| Source | Kind |
| --- | --- |
| `0x01ef76` | `jsr_abs` |

## bitmap_word_mask_writer (`0x01f4e0`)

(no direct references found)

## bitmap_solid_mask_writer (`0x01f596`)

(no direct references found)

## bitmap_destination_pointer_setup (`0x01f626`)

| Source | Kind |
| --- | --- |
| `0x01f514` | `jsr_abs` |
| `0x01f5ca` | `jsr_abs` |

## bitmap_fixed_width_rule_writer (`0x01f756`)

| Source | Kind |
| --- | --- |
| `0x01ef7c` | `jsr_abs` |

## bitmap_segment_list_writer (`0x01f812`)

| Source | Kind |
| --- | --- |
| `0x01efea` | `jsr_abs` |

## bitmap_segment_writer (`0x01f862`)

| Source | Kind |
| --- | --- |
| `0x01f82a` | `bsr_b` |

## bitmap_encoded_span_writer (`0x01f88e`)

| Source | Kind |
| --- | --- |
| `0x01eff2` | `jsr_abs` |

## common_dispatch_helper (`0x033298`)

| Source | Kind |
| --- | --- |
| `0x002e00` | `jmp_abs` |
| `0x003df0` | `jmp_abs` |
| `0x004cc4` | `jmp_abs` |
| `0x007630` | `jmp_abs` |
| `0x0086a6` | `jmp_abs` |
| `0x008d96` | `jmp_abs` |
| `0x00c3b4` | `jmp_abs` |
| `0x00dd80` | `jmp_abs` |
| `0x00efa8` | `jmp_abs` |
| `0x016e10` | `jmp_abs` |
| `0x01bec2` | `jmp_abs` |
| `0x01bece` | `jmp_abs` |

## References Into Parser Region 0x00d900..0x00e500

| Destination | Source | Kind |
| --- | --- | --- |
| `0x00d922` | `0x00d998` | `bra_b` |
| `0x00d954` | `0x00d950` | `bra_b` |
| `0x00d99a` | `0x00d066` | `jsr_abs` |
| `0x00d99a` | `0x00dae6` | `jsr_abs` |
| `0x00d99a` | `0x012162` | `jsr_abs` |
| `0x00d99a` | `0x0121b6` | `jsr_abs` |
| `0x00d99a` | `0x0124dc` | `jsr_abs` |
| `0x00d99a` | `0x0125a2` | `jsr_abs` |
| `0x00d99a` | `0x013910` | `jsr_abs` |
| `0x00d99a` | `0x01690a` | `jsr_abs` |
| `0x00d99a` | `0x0169d6` | `jsr_abs` |
| `0x00d99a` | `0x0169ec` | `jsr_abs` |
| `0x00da38` | `0x00d9ea` | `bra_b` |
| `0x00da38` | `0x00da42` | `bra_b` |
| `0x00da92` | `0x00da8e` | `bra_b` |
| `0x00da9a` | `0x00dabe` | `bra_b` |
| `0x00da9a` | `0x00daf4` | `lea_abs_a3` |
| `0x00da9a` | `0x00db96` | `lea_abs_a5` |
| `0x00da9a` | `0x0117d2` | `jsr_abs` |
| `0x00da9a` | `0x011bc2` | `jsr_abs` |
| `0x00da9a` | `0x011be2` | `jsr_abs` |
| `0x00da9a` | `0x011c8e` | `jsr_abs` |
| `0x00da9a` | `0x0122da` | `jsr_abs` |
| `0x00da9a` | `0x012630` | `jsr_abs` |
| `0x00dace` | `0x010660` | `jsr_abs` |
| `0x00dace` | `0x0106ba` | `jsr_abs` |
| `0x00dace` | `0x012338` | `jsr_abs` |
| `0x00dace` | `0x01238a` | `jsr_abs` |
| `0x00dace` | `0x012dd0` | `jsr_abs` |
| `0x00dace` | `0x012df6` | `jsr_abs` |
| `0x00dace` | `0x012e1a` | `jsr_abs` |
| `0x00dace` | `0x012ef8` | `jsr_abs` |
| `0x00dace` | `0x0159a4` | `jsr_abs` |
| `0x00dace` | `0x0159be` | `jsr_abs` |
| `0x00daf0` | `0x011b28` | `jsr_abs` |
| `0x00daf0` | `0x011bdc` | `jsr_abs` |
| `0x00daf0` | `0x011c88` | `jsr_abs` |
| `0x00daf0` | `0x011d64` | `jsr_abs` |
| `0x00daf0` | `0x011e2a` | `jsr_abs` |
| `0x00daf0` | `0x011fda` | `jsr_abs` |
| `0x00daf0` | `0x011fec` | `jsr_abs` |
| `0x00daf0` | `0x012014` | `jsr_abs` |
| `0x00daf0` | `0x01202a` | `jsr_abs` |
| `0x00daf0` | `0x01262a` | `jsr_abs` |
| `0x00db1c` | `0x00db2c` | `bra_b` |
| `0x00db46` | `0x00db0a` | `bsr_b` |
| `0x00db46` | `0x00db2a` | `bsr_b` |
| `0x00db46` | `0x00db70` | `bra_b` |
| `0x00db4c` | `0x00db66` | `bra_b` |
| `0x00db74` | `0x00db00` | `bsr_b` |
| `0x00dbde` | `0x00dbe6` | `bra_b` |
| `0x00dbec` | `0x00dc12` | `bra_b` |
| `0x00dc3a` | `0x00dc60` | `bra_b` |
| `0x00dc68` | `0x00dc7a` | `bra_b` |
| `0x00ddea` | `0x00dd78` | `bra_b` |
| `0x00ddea` | `0x00dd9a` | `bra_b` |
| `0x00ddea` | `0x00ddfa` | `bra_b` |
| `0x00ddea` | `0x00de3c` | `bra_b` |
| `0x00ddea` | `0x00de9e` | `bra_w` |
| `0x00ddea` | `0x00dec4` | `bra_w` |
| `0x00ddea` | `0x00ded6` | `bra_w` |
| `0x00ddea` | `0x00def0` | `bra_w` |
| `0x00ddea` | `0x00defa` | `bra_w` |
| `0x00ddea` | `0x00df04` | `bra_w` |
| `0x00ddea` | `0x00df0e` | `bra_w` |
| `0x00ddea` | `0x00df20` | `bra_w` |
| `0x00ddea` | `0x00df32` | `bra_w` |
| `0x00ddea` | `0x00df46` | `bra_w` |
| `0x00ddea` | `0x00df4a` | `bra_w` |
| `0x00de30` | `0x00de7a` | `bra_b` |
| `0x00df4e` | `0x00defe` | `jsr_abs` |
| `0x00df5e` | `0x00df76` | `bra_b` |
| `0x00df80` | `0x00df08` | `jsr_abs` |
| `0x00df90` | `0x00dfb8` | `bra_b` |
| `0x00dfb0` | `0x00dfa6` | `bra_b` |
| `0x00dfba` | `0x00dd9e` | `jsr_abs` |
| `0x00dfba` | `0x00de2a` | `jsr_abs` |
| `0x00dfba` | `0x00de74` | `jsr_abs` |
| `0x00dfba` | `0x00df1a` | `jsr_abs` |
| `0x00dfba` | `0x00df68` | `jsr_abs` |
| `0x00dfba` | `0x00dfa0` | `jsr_abs` |
| `0x00e002` | `0x00ddca` | `jsr_abs` |
| `0x00e002` | `0x00ddd6` | `jsr_abs` |
| `0x00e002` | `0x00dde2` | `jsr_abs` |
| `0x00e002` | `0x00ddf4` | `jsr_abs` |
| `0x00e002` | `0x011874` | `jsr_abs` |
| `0x00e002` | `0x011a82` | `jsr_abs` |
| `0x00e002` | `0x011ac0` | `jsr_abs` |
| `0x00e002` | `0x011adc` | `jsr_abs` |
| `0x00e002` | `0x011b84` | `jsr_abs` |
| `0x00e002` | `0x011dae` | `jsr_abs` |
| `0x00e002` | `0x011dc0` | `jsr_abs` |
| `0x00e002` | `0x011dca` | `jsr_abs` |
| `0x00e002` | `0x011e80` | `jsr_abs` |
| `0x00e002` | `0x011e92` | `jsr_abs` |
| `0x00e002` | `0x011e9c` | `jsr_abs` |
| `0x00e002` | `0x012114` | `jsr_abs` |
| `0x00e002` | `0x01212e` | `jsr_abs` |
| `0x00e002` | `0x01213a` | `jsr_abs` |
| `0x00e002` | `0x012174` | `jsr_abs` |
| `0x00e002` | `0x0121c0` | `jsr_abs` |
| `0x00e002` | `0x0123a4` | `jsr_abs` |
| `0x00e002` | `0x0123ce` | `jsr_abs` |
| `0x00e002` | `0x0123fa` | `jsr_abs` |
| `0x00e074` | `0x00e07c` | `bra_b` |
| `0x00e07c` | `0x00e08a` | `bra_b` |
| `0x00e080` | `0x00e0a2` | `bra_b` |
| `0x00e096` | `0x00e092` | `bra_b` |
| `0x00e0a4` | `0x00dd38` | `jsr_abs` |
| `0x00e0a4` | `0x00ff6e` | `jsr_abs` |
| `0x00e0ba` | `0x00e0fa` | `bra_b` |
| `0x00e0ea` | `0x00e0d8` | `bra_b` |
| `0x00e0ea` | `0x00e110` | `bra_b` |
| `0x00e0f2` | `0x00e106` | `bra_b` |
| `0x00e146` | `0x00cc60` | `jsr_abs` |
| `0x00e1a2` | `0x00e1bc` | `bra_b` |
| `0x00e1e4` | `0x00e158` | `jsr_abs` |
| `0x00e1f2` | `0x00e222` | `bra_b` |
| `0x00e22c` | `0x00a976` | `jsr_abs` |
| `0x00e350` | `0x00e292` | `bra_w` |
| `0x00e384` | `0x00e34e` | `bra_b` |
| `0x00e3e8` | `0x00e382` | `bra_b` |
| `0x00e408` | `0x00e356` | `bra_w` |
| `0x00e408` | `0x00e3e6` | `bra_b` |
| `0x00e418` | `0x00de96` | `jsr_abs` |
| `0x00e418` | `0x00debc` | `jsr_abs` |
| `0x00e496` | `0x00e47c` | `bra_b` |
| `0x00e4e6` | `0x00e4b0` | `bra_b` |
| `0x00e4f4` | `0x00ff8e` | `jsr_abs` |
