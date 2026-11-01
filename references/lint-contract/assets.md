# lint 检查合同 · assets 阶段

> 由 build_lint_contract.py 从实际 STAGE_CHECKS 与共享调用图生成；禁止手改。
> 只证明结构、来源、算术、依赖与技术合同；内容须按观看顺序独立审校。

运行：`python scripts/drama_lint.py <skill-root> --project-root <project> --stage assets`。

轻量走同一内核和单任务预检适配，不要求伪造完整模式上游。

| 检查码 | 级别 | 查什么 | 来源 |
|---|---|---|---|
| `asset_entity_scope_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_entity_scope_not_character` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_file_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_id_missing` | error | 资产缺少 asset_id。 | `drama_lint.check_assets` |
| `asset_id_prefix_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_status_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_usage_duplicate` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_usage_shared_not_approved` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_usage_shared_version_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_usage_unknown_shared_asset` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_usage_unknown_shared_version` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_version_duplicate` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `assets_invalid` | error | asset_registry.assets 必须是数组。 | `drama_lint.check_assets` |
| `character_entity_scope_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_collective_profiles` |
| `character_state_asset_requires_image_edit` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `collective_asset_data_card_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `collective_asset_ref_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_collective_profiles` |
| `collective_asset_scope_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `collective_character_id_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_collective_profiles` |
| `collective_count_range_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_collective_profiles` |
| `collective_count_range_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_collective_profiles` |
| `collective_group_type_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_collective_profiles` |
| `collective_individual_voice_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_collective_profiles` |
| `collective_profile_field_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_collective_profiles` |
| `collective_profile_field_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_collective_profiles` |
| `collective_profile_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_collective_profiles` |
| `collective_usage_scope_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `collective_voice_mode_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_collective_profiles` |
| `combined_story_outline_reference_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_stage_artifacts` |
| `combined_story_outline_section_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_stage_artifacts` |
| `combined_story_outline_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_stage_artifacts` |
| `content_review_open_issue` | error | 有未解决的内容设计问题 | `content_first.check_review` |
| `content_review_open_issue` | error | 缺内容审校记录；字段存在不证明摄影成立 | `content_first.check_review` |
| `content_review_stale` | error | 内容审校不对应当前设计/源/时间输入 | `content_first.check_review` |
| `episode_asset_duplicate` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_asset_file_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_asset_status_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_character_state_asset_requires_image_edit` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_id_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_episode_manifest_ids` |
| `episode_image_edit_reference_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_image_edit_visual_reference_decision_conflict` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_image_gen_should_not_have_visual_inputs` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_image_gen_visual_reference_available` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_image_gen_visual_reference_decision_conflict` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_project_visual_mode_missing_or_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_visual_reference_decision_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `file_missing` | error | 缺少流程所需文件。 | `drama_lint.load_json` |
| `generation_prompt_file_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_generation_prompt_file` |
| `generation_prompt_path_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_generation_prompt_file` |
| `generation_prompt_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_generation_prompt_file` |
| `highlight_ledger_invalid` | error | 完整模式 script_contract.highlight_ledger 必须是数组。 | `drama_lint.check_stage_artifacts` |
| `image_edit_reference_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `image_edit_visual_reference_decision_conflict` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `image_gen_should_not_have_visual_inputs` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `image_gen_visual_reference_available` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `image_gen_visual_reference_decision_conflict` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `json_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_json` |
| `lightweight_style_unresolved` | error | 轻量唯一生成确认前需确定具体画风 | `content_first.check_lightweight` |
| `pack_drift` | error | beat_groups 必须为数组 | `timeline_core.validate_timeline_shape` |
| `pack_drift` | error | group_id 必须唯一且非空 | `timeline_core.compute_groups` |
| `pack_drift` | error | segment_id 必须为非空字符串 | `timeline_core.compute_groups` |
| `pack_drift` | error | segment_id 重复 | `timeline_core.compute_groups` |
| `pack_drift` | error | 动态消息；按当前对象及源码核对 | `timeline_core.compute_groups` |
| `pack_drift` | error | 组必须按正式顺序恰好覆盖所有镜头，无重漏 | `timeline_core.compute_groups` |
| `pack_drift` | error | 镜头组字段非法 | `timeline_core.compute_groups` |
| `pack_drift` | error | 需要导演声明的合法镜头组，不自动制造切点 | `timeline_core.compute_groups` |
| `project_visual_mode_missing_or_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `required_artifact_missing` | error | 缺少当前阶段所需产物。 | `drama_lint.check_stage_artifacts` |
| `reused_episode_asset_duplicate` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `reused_episode_asset_file_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `reused_episode_asset_files_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `reused_episode_asset_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `reused_episode_asset_not_approved` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `reused_episode_asset_ref_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `reused_episode_asset_source_not_found` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `reused_episode_assets_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `reused_episode_source_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `reused_episode_source_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `source_event_uncovered` | error | 事件索引必须是对象 | `content_first.source_index_from_contract` |
| `source_event_uncovered` | error | 动态消息；按当前对象及源码核对 | `content_first.source_index_from_contract` |
| `source_line_uncovered` | error | speech_lines 必须是数组，可空 | `content_first.source_index_from_contract` |
| `source_line_uncovered` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `source_line_uncovered` | error | 台词索引必须是对象 | `content_first.source_index_from_contract` |
| `source_line_uncovered` | error | 轻量人声未完整承接 | `content_first.check_lightweight` |
| `source_revision_mismatch` | error | script contract 缺 scenes | `content_first.source_index_from_contract` |
| `source_revision_mismatch` | error | source_script 需 file/revision/sha256 | `timeline_core.validate_timeline_shape` |
| `source_revision_mismatch` | error | 动态消息；按当前对象及源码核对 | `content_first.source_index_from_contract` |
| `source_revision_mismatch` | error | 源剧本正文 SHA 不符。 | `drama_lint.check_stage_artifacts` |
| `source_revision_mismatch` | error | 源场次 ID 必须唯一且非空 | `content_first.source_index_from_contract` |
| `speech_span_discontinuous` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `speech_span_incomplete` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `speech_timing_basis_invalid` | error | timing_basis 字段无效 | `timeline_core.validate_timeline_shape` |
| `speech_timing_basis_invalid` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `storyboard_fifteen_columns_missing` | error | 完整分镜表必须包含一个十五列表格。 | `drama_lint.check_stage_artifacts` |
| `storyboard_source_markdown_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_stage_artifacts` |
| `style_adopt_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_style_anchor_contract` |
| `style_anchor_requires_image_edit` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_style_anchor_contract` |
| `style_anchor_visual_reference_decision_conflict` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_style_anchor_contract` |
| `style_asset_type_invalid` | error | STYLE001 必须登记为 global_visual_language_moodboard。 | `drama_lint.check_assets` |
| `style_asset_type_missing` | error | STYLE001 approved 前必须登记 style_asset_type=global_visual_language_moodboard。 | `drama_lint.check_assets` |
| `style_exclude_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_style_anchor_contract` |
| `style_moodboard_contains_characters_unknown` | error | STYLE001 全局风格 moodboard 必须明确 contains_story_characters=false。 | `drama_lint.check_assets` |
| `style_moodboard_contains_props_unknown` | error | STYLE001 全局风格 moodboard 必须明确 contains_story_props=false。 | `drama_lint.check_assets` |
| `style_prompt_file_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_style_anchor_contract` |
| `style_prompt_path_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_style_anchor_contract` |
| `style_prompt_terms_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_style_anchor_contract` |
| `style_scene_atmosphere_links_missing` | error | STYLE001 approved 时 style_scene_atmosphere_links 必须是非空数组。 | `drama_lint.check_assets` |
| `style_visual_language_missing` | error | STYLE001 必须登记色彩、光线、构图、材质或空间氛围等视觉语言。 | `drama_lint.check_assets` |
| `style_visual_language_missing` | error | STYLE001 需记录本项目实际采用的视觉语言；字段数量不证明风格质量。 | `drama_lint.check_assets` |
| `technical_handle_unresolved` | error | 动态消息；按当前对象及源码核对 | `timeline_core.compute_groups` |
| `timeline_dependency_conflict` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `timeline_dependency_cycle` | error | after 中存在自依赖或循环 | `timeline_core.reconcile_timeline` |
| `timeline_field_unknown` | error | speech 文本只回指 utterance，不另建权威 | `timeline_core.validate_timeline_shape` |
| `timeline_field_unknown` | error | 非 speech 不能携带 utterance | `timeline_core.validate_timeline_shape` |
| `timeline_id_duplicate` | error | 动态消息；按当前对象及源码核对 | `content_first.source_index_from_contract` |
| `timeline_id_duplicate` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `timeline_number_invalid` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `timeline_ref_unknown` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `timeline_shape_invalid` | error | episode_id 必须为 ep_N | `timeline_core.validate_timeline_shape` |
| `timeline_shape_invalid` | error | scene_id 必须非空字符串 | `timeline_core.validate_timeline_shape` |
| `timeline_shape_invalid` | error | scenes 必须是非空数组 | `timeline_core.validate_timeline_shape` |
| `timeline_shape_invalid` | error | shot_id 必须非空字符串 | `timeline_core.validate_timeline_shape` |
| `timeline_shape_invalid` | error | speech 需 utterance_id/utterance_offset_s | `timeline_core.validate_timeline_shape` |
| `timeline_shape_invalid` | error | utterance/line/speaker 需非空 ID | `timeline_core.validate_timeline_shape` |
| `timeline_shape_invalid` | error | utterances 必须为数组，可空 | `timeline_core.validate_timeline_shape` |
| `timeline_shape_invalid` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `timeline_shape_invalid` | error | 动态消息；按当前对象及源码核对 | `timeline_core.validate_timeline_shape` |
| `timeline_shape_invalid` | error | 场次必须有 shots | `timeline_core.validate_timeline_shape` |
| `timeline_shape_invalid` | error | 必须是对象 | `timeline_core._unknown` |
| `timeline_shape_invalid` | error | 未知过程 kind | `timeline_core.validate_timeline_shape` |
| `timeline_shape_invalid` | error | 每镜至少一个时间过程 | `timeline_core.validate_timeline_shape` |
| `timeline_shape_invalid` | error | 非 speech 需非空 process | `timeline_core.validate_timeline_shape` |
| `timeline_shot_set_mismatch` | error | 十五列阅读稿的镜头集合/顺序需与同源时间输入一致 | `content_first.check_reading_times` |
| `timing_input_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_stage_artifacts` |
| `timing_output_drift` | error | 动态消息；按当前对象及源码核对 | `content_first.check_reading_times` |
| `tool_capabilities_invalid` | error | 动态消息；按当前对象及源码核对 | `timeline_core.compute_groups` |
| `tool_duration_unrepresentable` | error | 动态消息；按当前对象及源码核对 | `timeline_core.compute_groups` |
| `tool_duration_unrepresentable` | error | 轻量只允许一个真实生成任务；不自动扩范围 | `content_first.check_lightweight` |
| `visual_reference_decision_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
