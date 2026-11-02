# lint 检查合同 · assets 阶段

> 由 build_lint_contract.py 从实际 STAGE_CHECKS 与共享调用图生成；按需读取。
> 只证明结构、来源、算术、依赖与技术合同；内容须按观看顺序独立审校。

运行：`python scripts/drama_lint.py <skill-root> --project-root <project> --stage assets`。

| 检查码 | 级别 | 查什么 | 来源 |
|---|---|---|---|
| `asset_entity_scope_invalid` | error | {asset_id or '角色资产'} entity_scope 必须为 individual 或 collective。 | `lint_checks.assets.check_assets`（182–471，触发 201） |
| `asset_entity_scope_not_character` | error | {asset_id or '资产'} 只有 character 类资产可填写 entity_scope。 | `lint_checks.assets.check_assets`（182–471，触发 207） |
| `asset_file_missing` | error | 资产缺本地文件或有效 HTTP(S) 引用：{file_value} | `lint_checks.assets.check_assets`（182–471，触发 228） |
| `asset_id_missing` | error | 资产缺少 asset_id。 | `lint_checks.assets.check_assets`（182–471，触发 218） |
| `asset_id_prefix_mismatch` | error | {asset_id} 与 category={category} 的前缀不一致。 | `lint_checks.assets.check_assets`（182–471，触发 216） |
| `asset_status_invalid` | error | 资产状态无效：{status} | `lint_checks.assets.check_assets`（182–471，触发 222） |
| `asset_usage_duplicate` | error | {episode_id} 共享资产重复：{asset_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 342） |
| `asset_usage_shared_not_approved` | error | {episode_id} 只能引用 registry 中 approved 的共享资产版本：{asset_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 339） |
| `asset_usage_shared_version_missing` | error | {episode_id} 共享资产必须填写 version：{asset_id} | `lint_checks.assets.check_assets`（182–471，触发 333） |
| `asset_usage_unknown_shared_asset` | error | {episode_id} 引用了 registry 中不存在的共享资产：{asset_id} | `lint_checks.assets.check_assets`（182–471，触发 331） |
| `asset_usage_unknown_shared_version` | error | {episode_id} 引用了 registry 中不存在的共享资产版本：{asset_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 337） |
| `asset_version_duplicate` | error | asset_id + version 重复：{asset_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 212） |
| `assets_invalid` | error | asset_registry.assets 必须是数组。 | `lint_checks.assets.check_assets`（182–471，触发 303） |
| `character_entity_scope_invalid` | error | characters[{index}].entity_scope 必须为 individual 或 collective。 | `lint_checks.causal.validate_collective_profiles`（90–140，触发 102） |
| `character_state_asset_requires_image_edit` | error | {asset_id or '角色状态资产'} 是人物状态资产时必须基于已批准人物图使用 image_edit；除非用户明确要求重做并记录 explicit_user_override。 | `lint_checks.assets.check_assets`（182–471，触发 262） |
| `collective_asset_data_card_missing` | error | {asset_id or '群像资产'} 登记为 collective，但项目数据卡没有对应群像角色记录。 | `lint_checks.assets.check_assets`（182–471，触发 205） |
| `collective_asset_ref_mismatch` | error | {asset_id} asset_refs.collective_profile 必须指向该群像 CHR。 | `lint_checks.causal.validate_collective_profiles`（90–140，触发 136） |
| `collective_asset_scope_mismatch` | error | {asset_id} 在项目数据卡中是群像，registry 必须登记 entity_scope=collective。 | `lint_checks.assets.check_assets`（182–471，触发 203） |
| `collective_character_id_invalid` | error | characters[{index}] 群像必须使用 CHR ID。 | `lint_checks.causal.validate_collective_profiles`（90–140，触发 108） |
| `collective_count_range_invalid` | error | {asset_id} collective_profile.count_range 必须满足 1 <= min <= max。 | `lint_checks.causal.validate_collective_profiles`（90–140，触发 124） |
| `collective_count_range_missing` | error | {asset_id} collective_profile.count_range 必须包含 min/max。 | `lint_checks.causal.validate_collective_profiles`（90–140，触发 119） |
| `collective_group_type_missing` | error | {asset_id} collective_profile.group_type 不能为空。 | `lint_checks.causal.validate_collective_profiles`（90–140，触发 116） |
| `collective_individual_voice_invalid` | error | {asset_id} 群像不能绑定单人 identity_locked.voice_id。 | `lint_checks.causal.validate_collective_profiles`（90–140，触发 139） |
| `collective_profile_field_invalid` | error | {asset_id} collective_profile.{field} 必须是数组；无内容时填空数组。 | `lint_checks.causal.validate_collective_profiles`（90–140，触发 131） |
| `collective_profile_field_missing` | error | {asset_id} collective_profile.{field} 必须是非空数组。 | `lint_checks.causal.validate_collective_profiles`（90–140，触发 128） |
| `collective_profile_missing` | error | {asset_id or f'characters[{index}]'} 必须填写 collective_profile。 | `lint_checks.causal.validate_collective_profiles`（90–140，触发 113） |
| `collective_usage_scope_mismatch` | error | {episode_id} 的 {asset_id} 必须以 entity_scope=collective 登记。 | `lint_checks.assets.check_assets`（182–471，触发 321） |
| `collective_voice_mode_invalid` | error | {asset_id} collective_profile.voice_mode 必须为 none 或 collective_ambience。 | `lint_checks.causal.validate_collective_profiles`（90–140，触发 133） |
| `combined_story_outline_reference_invalid` | error | project_script_manifest.global_story_and_episode_outline 必须指向 01_剧本/剧本_全局设定与分集总纲.md。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 149） |
| `combined_story_outline_section_missing` | error | 合并剧本文档缺少“{heading}”章节。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 143） |
| `combined_story_outline_unreadable` | error | 合并剧本文档无法读取：{exc} | `lint_checks.stages.check_stage_artifacts`（64–173，触发 139） |
| `episode_asset_duplicate` | error | {episode_id} 分集资产重复：{asset_id} {state_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 426） |
| `episode_asset_file_missing` | error | 分集资产缺本地文件或有效 HTTP(S) 引用：{file_value} | `lint_checks.assets.check_assets`（182–471，触发 470） |
| `episode_asset_status_invalid` | error | 分集资产状态无效：{item.get('status')} | `lint_checks.assets.check_assets`（182–471，触发 430） |
| `episode_character_state_asset_requires_image_edit` | error | {asset_id or '角色状态资产'} 是人物状态资产时必须基于已批准人物图使用 image_edit；除非用户明确要求重做并记录 explicit_user_override。 | `lint_checks.assets.check_assets`（182–471，触发 466） |
| `episode_id_mismatch` | error | {stage} episode_id 必须等于目录 ID：{episode_id} | `lint_checks.stages.check_episode_manifest_ids`（28–35，触发 35） |
| `episode_image_edit_reference_missing` | error | {asset_id or '分集资产'} 使用 image_edit 时必须登记实际参考来源。 | `lint_checks.assets.check_assets`（182–471，触发 461） |
| `episode_image_edit_visual_reference_decision_conflict` | error | {asset_id or '分集资产'} 使用 image_edit 时 visual_reference_decision 不能写 none_available。 | `lint_checks.assets.check_assets`（182–471，触发 463） |
| `episode_image_gen_should_not_have_visual_inputs` | error | {asset_id or '分集资产'} 使用 image_gen 时不应登记图片参考输入。 | `lint_checks.assets.check_assets`（182–471，触发 455） |
| `episode_image_gen_visual_reference_available` | error | {asset_id or '分集资产'} 已登记可用视觉参考，必须使用 image_edit；除非用户明确要求不参考并记录 explicit_user_override。 | `lint_checks.assets.check_assets`（182–471，触发 457） |
| `episode_image_gen_visual_reference_decision_conflict` | error | {asset_id or '分集资产'} visual_reference_decision=used 时不能使用 image_gen。 | `lint_checks.assets.check_assets`（182–471，触发 459） |
| `episode_project_visual_mode_missing_or_invalid` | error | {asset_id or '分集资产'} approved 图片资产必须登记有效 project_visual_mode。 | `lint_checks.assets.check_assets`（182–471，触发 453） |
| `episode_visual_reference_decision_invalid` | error | {asset_id or '分集资产'} visual_reference_decision 无效：{visual_reference_decision} | `lint_checks.assets.check_assets`（182–471，触发 441） |
| `file_missing` | error | 缺少流程所需文件。 | `lint_checks.common.load_json`（22–30，触发 27） |
| `generation_prompt_file_missing` | error | {owner_label} 生成图片 Prompt 文件不存在。 | `lint_checks.common.check_generation_prompt_file`（135–154，触发 149） |
| `generation_prompt_path_missing` | error | {owner_label} 使用 {tool} 生成图片时必须登记项目相对 prompt_path。 | `lint_checks.common.check_generation_prompt_file`（135–154，触发 147） |
| `generation_prompt_unreadable` | error | {owner_label} 生成图片 Prompt 无法读取：{exc} | `lint_checks.common.check_generation_prompt_file`（135–154，触发 154） |
| `highlight_ledger_invalid` | error | script_contract.highlight_ledger 必须是数组。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 165） |
| `image_edit_reference_missing` | error | {asset_id} 使用 image_edit 时必须登记实际参考来源。 | `lint_checks.assets.check_assets`（182–471，触发 258） |
| `image_edit_visual_reference_decision_conflict` | error | {asset_id} 使用 image_edit 时 visual_reference_decision 不能写 none_available。 | `lint_checks.assets.check_assets`（182–471，触发 260） |
| `image_gen_should_not_have_visual_inputs` | error | {asset_id} 使用 image_gen 时不应登记图片参考输入。 | `lint_checks.assets.check_assets`（182–471，触发 252） |
| `image_gen_visual_reference_available` | error | {asset_id} 已登记可用视觉参考，必须使用 image_edit；除非用户明确要求不参考并记录 explicit_user_override。 | `lint_checks.assets.check_assets`（182–471，触发 254） |
| `image_gen_visual_reference_decision_conflict` | error | {asset_id} visual_reference_decision=used 时不能使用 image_gen。 | `lint_checks.assets.check_assets`（182–471，触发 256） |
| `json_invalid` | error | JSON 无法读取或解析，后续关系无法确认：{exc} | `lint_checks.common.load_json`（22–30，触发 29） |
| `project_visual_mode_missing_or_invalid` | error | {asset_id or '资产'} approved 图片资产必须登记有效 project_visual_mode。 | `lint_checks.assets.check_assets`（182–471，触发 250） |
| `required_artifact_missing` | error | 缺少当前阶段所需产物。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 132） |
| `reused_episode_asset_duplicate` | error | {episode_id} 复用分集资产重复：{source_episode_id} {asset_id} {state_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 407） |
| `reused_episode_asset_file_missing` | error | 复用分集资产缺本地文件或有效 HTTP(S) 引用：{file_value} | `lint_checks.assets.check_assets`（182–471，触发 411） |
| `reused_episode_asset_files_mismatch` | error | {episode_id} 复用资产文件必须与 {source_episode_id} 来源记录一致：{asset_id} {state_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 397） |
| `reused_episode_asset_invalid` | error | {episode_id} reused_episode_assets 每项必须是对象。 | `lint_checks.assets.check_assets`（182–471，触发 350） |
| `reused_episode_asset_not_approved` | error | {episode_id} 只能复用 approved 分集资产：{asset_id} {state_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 368） |
| `reused_episode_asset_ref_missing` | error | {episode_id} 复用分集资产必须填写 asset_id 和 version。 | `lint_checks.assets.check_assets`（182–471，触发 365） |
| `reused_episode_asset_source_not_found` | error | {episode_id} 复用资产在 {source_episode_id} 中找不到一致的 approved 来源：{asset_id} {state_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 394） |
| `reused_episode_assets_invalid` | error | {episode_id} reused_episode_assets 必须是数组。 | `lint_checks.assets.check_assets`（182–471，触发 345） |
| `reused_episode_source_invalid` | error | {episode_id} 只能复用更早分集的 approved 资产：{source_episode_id} | `lint_checks.assets.check_assets`（182–471，触发 362） |
| `reused_episode_source_missing` | error | {episode_id} 复用分集资产必须填写 source_episode_id。 | `lint_checks.assets.check_assets`（182–471，触发 359） |
| `source_event_uncovered` | error | {eid} 缺必要事实摘要 | `content_first.source_index_from_contract`（33–91，触发 73） |
| `source_event_uncovered` | error | {scene.get('scene_id')} 需 events 源索引（不设数量） | `content_first.source_index_from_contract`（33–91，触发 59） |
| `source_event_uncovered` | error | 事件索引必须是对象 | `content_first.source_index_from_contract`（33–91，触发 63） |
| `source_line_uncovered` | error | speech_lines 必须是数组，可空 | `content_first.source_index_from_contract`（33–91，触发 77） |
| `source_line_uncovered` | error | 台词索引必须是对象 | `content_first.source_index_from_contract`（33–91，触发 81） |
| `source_revision_mismatch` | error | script contract 缺 scenes | `content_first.source_index_from_contract`（33–91，触发 37） |
| `source_revision_mismatch` | error | {eid} source_excerpt 不在对应场次原文 | `content_first.source_index_from_contract`（33–91，触发 71） |
| `source_revision_mismatch` | error | {lid} 台词不在对应源场次 | `content_first.source_index_from_contract`（33–91，触发 89） |
| `source_revision_mismatch` | error | {sid} 需唯一场次标题以定位源原文 | `content_first.source_index_from_contract`（33–91，触发 49） |
| `source_revision_mismatch` | error | 源剧本正文 SHA 不符。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 169） |
| `source_revision_mismatch` | error | 源场次 ID 必须唯一且非空 | `content_first.source_index_from_contract`（33–91，触发 44） |
| `style_adopt_missing` | error | {owner_label} 使用 style_anchor_reference 时 style_adopt 必须是非空字符串数组。 | `lint_checks.common.check_style_anchor_contract`（103–132，触发 125） |
| `style_anchor_requires_image_edit` | error | {owner_label} 使用 style_anchor_reference 时必须走 image_edit。 | `lint_checks.common.check_style_anchor_contract`（103–132，触发 119） |
| `style_anchor_visual_reference_decision_conflict` | error | {owner_label} 使用 style_anchor_reference 时 visual_reference_decision 不能写 none_available。 | `lint_checks.common.check_style_anchor_contract`（103–132，触发 121） |
| `style_asset_type_invalid` | error | STYLE001 必须登记为 global_visual_language_moodboard。 | `lint_checks.assets.check_assets`（182–471，触发 282） |
| `style_asset_type_missing` | error | STYLE001 approved 前必须登记 style_asset_type=global_visual_language_moodboard。 | `lint_checks.assets.check_assets`（182–471，触发 280） |
| `style_exclude_missing` | error | {owner_label} 使用 style_anchor_reference 时 style_exclude 必须是非空字符串数组。 | `lint_checks.common.check_style_anchor_contract`（103–132，触发 127） |
| `style_moodboard_contains_characters_unknown` | error | STYLE001 全局风格 moodboard 必须明确 contains_story_characters=false。 | `lint_checks.assets.check_assets`（182–471，触发 299） |
| `style_moodboard_contains_props_unknown` | error | STYLE001 全局风格 moodboard 必须明确 contains_story_props=false。 | `lint_checks.assets.check_assets`（182–471，触发 301） |
| `style_prompt_file_missing` | error | {owner_label} style_anchor_reference 对应 Prompt 文件不存在。 | `lint_checks.common.check_style_anchor_contract`（103–132，触发 132） |
| `style_prompt_path_missing` | error | {owner_label} 使用 style_anchor_reference 时必须登记项目相对 prompt_path。 | `lint_checks.common.check_style_anchor_contract`（103–132，触发 130） |
| `style_prompt_terms_missing` | error | {owner_label} 使用 style_anchor_reference 时 style_prompt_terms 必须是非空字符串数组。 | `lint_checks.common.check_style_anchor_contract`（103–132，触发 123） |
| `style_scene_atmosphere_links_missing` | error | STYLE001 approved 时 style_scene_atmosphere_links 必须是非空数组。 | `lint_checks.assets.check_assets`（182–471，触发 285） |
| `style_visual_language_missing` | error | STYLE001 必须登记色彩、光线、构图、材质或空间氛围等视觉语言。 | `lint_checks.assets.check_assets`（182–471，触发 289） |
| `style_visual_language_missing` | error | STYLE001 需记录本项目实际采用的视觉语言；字段数量不证明风格质量。 | `lint_checks.assets.check_assets`（182–471，触发 297） |
| `timeline_id_duplicate` | error | 无效/重复 line_id {lid} | `content_first.source_index_from_contract`（33–91，触发 87） |
| `timeline_id_duplicate` | error | 无效/重复源事件 {eid} | `content_first.source_index_from_contract`（33–91，触发 69） |
| `visual_reference_decision_invalid` | error | {asset_id} visual_reference_decision 无效：{visual_reference_decision} | `lint_checks.assets.check_assets`（182–471，触发 239） |
| `voice_sample_duration_invalid` | error | {label} 音色 {duration}s 不满足能力档案的音频参考范围 {ranges}；资产阶段处理后试听，不自动补静音或批准。 | `lint_checks.assets.check_voice_sample`（96–141，触发 134） |
| `voice_sample_duration_mismatch` | error | {label} 登记时长与本地音频实测不同。 | `lint_checks.assets.check_voice_sample`（96–141，触发 139） |
| `voice_sample_invalid` | error | {label} 音色技术核验失败：{exc} | `lint_checks.assets.check_voice_sample`（96–141，触发 141） |
| `voice_sample_source_invalid` | error | {asset_id} 原批准记录未登记为 voice。 | `lint_checks.assets.check_reused_voice_sample`（144–179，触发 177） |
| `voice_sample_source_invalid` | error | {asset_id} 音色复用来源必须指向更早分集。 | `lint_checks.assets.check_reused_voice_sample`（144–179，触发 156） |
| `voice_sample_source_invalid` | error | {asset_id} 音色复用链缺唯一、文件一致的 approved 来源。 | `lint_checks.assets.check_reused_voice_sample`（144–179，触发 172） |
