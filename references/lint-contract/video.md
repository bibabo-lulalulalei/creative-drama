# lint 检查合同 · video 阶段

> 本卡片由 `scripts/build_lint_contract.py` 从 `drama_lint.py` 机读生成，禁止手改。
> 用途：开工前读这张卡知道本阶段 lint 会查什么；报错后按码查修复方向。
> 与源码不一致时以源码为准，并重跑 `python scripts/build_lint_contract.py --check`。

本阶段新增检查项：144。运行命令：`python scripts/drama_lint.py --stage video`（skill 阶段在 skill 根目录运行）。

本阶段同时全量复核以下上游检查（报错时先读对应上游卡）：
- planning 阶段卡 · `check_stage_artifacts` —— video 阶段产物存在性
- planning 阶段卡 · `check_episode_manifest_ids` —— episode_manifest 与 stage 绑定
- assets 阶段卡 · `check_assets` —— 资产索引
- assets 阶段卡 · `validate_collective_profiles` —— 群像画像一致性
- storyboard 阶段卡 · `check_beat_library_desync` —— 节拍库漂移
- storyboard 阶段卡 · `check_rhythm_reconciliation` —— 引擎对账
- storyboard 阶段卡 · `check_rhythm_diversity` —— 节奏健康度
- storyboard 阶段卡 · `check_storyboards` —— 分镜全链（video 阶段也复核）
- keyframes 阶段卡 · `check_keyframes` —— KF 清单对账（video 阶段也复核）

| 检查码 | 级别 | 查什么（源码原文消息） |
|---|---|---|
| `episode_id_mismatch` | error | video_manifest episode_id 与目录不一致。 |
| `video_segments_invalid` | error | video_manifest.segments 必须是数组。 |
| `lightweight_video_count_invalid` | error | 轻量模式必须只生成一个最终视频；多个独立视频必须拆为独立任务。 |
| `lightweight_confirmation_call_mismatch` | error | 轻量模式 planning 与首次视频生成记录必须复用同一个 interaction.ask 调用 ID。 |
| `video_segment_missing` | error | <动态生成，见源码> |
| `video_segment_unplanned` | error | <动态生成，见源码> |
| `video_duration_mismatch` | error | video_manifest.duration_s 必须等于 segments.duration_s 之和。 |
| `video_segment_duration_not_integer` | error | <动态生成，见源码> |
| `video_segment_invalid` | error | segments 每项必须是对象。 |
| `video_unknown_segment` | error | <动态生成，见源码> |
| `video_tool_mode_invalid` | error | <动态生成，见源码> |
| `delivery_package_file_missing` | error | <动态生成，见源码> |
| `generated_segment_prompt_missing` | error | <动态生成，见源码> |
| `generated_segment_prompt_sha256_missing` | error | <动态生成，见源码> |
| `video_status_invalid` | error | <动态生成，见源码> |
| `video_segment_output_missing` | error | <动态生成，见源码> |
| `video_segment_duration_mismatch` | error | <动态生成，见源码> |
| `text_to_video_input_invalid` | error | text_to_video 只能用于没有图片、视频、音频或 voice_inputs 的片段。 |
| `media_to_video_media_missing` | error | media_to_video 必须至少登记一个真实视频或音频输入。 |
| `storyboard_required_role_not_inherited` | error | <动态生成，见源码> |
| `storyboard_required_role_not_passed` | error | <动态生成，见源码> |
| `image_to_video_reference_missing` | error | image_to_video 必须登记实际传入参考图。 |
| `image_to_video_input_invalid` | error | image_to_video 不支持上传视频、音频或 voice_inputs；本路由只能传参考图。 |
| `required_reference_roles_missing` | error | image_to_video 必须声明 required_reference_roles。 |
| `video_edit_input_invalid` | error | video_edit 只登记源视频，不登记图片、音频或 voice_inputs。 |
| `video_edit_source_invalid` | error | video_edit 必须且只能登记一个 source_video_for_edit 源视频。 |
| `previous_tail_source_type_invalid` | error | <动态生成，见源码> |
| `video_reference_unknown_keyframe` | error | <动态生成，见源码> |
| `prompt_path_invalid` | error | compiled_prompt_file 必须是项目相对路径。 |
| `video_segment_not_accepted` | error | <动态生成，见源码> |
| `accepted_segment_output_missing` | error | <动态生成，见源码> |
| `accepted_segment_prompt_missing` | error | <动态生成，见源码> |
| `video_quality_gate_invalid` | error | <动态生成，见源码> |
| `required_reference_roles_missing` | error | media_to_video 使用图片或分镜声明图片职责时必须填写 required_reference_roles。 |
| `required_reference_roles_unexpected` | error | media_to_video 没有图片输入时 required_reference_roles 应为空或省略。 |
| `required_reference_role_invalid` | error | required_reference_roles 含无效职责。 |
| `video_segment_not_ready_for_confirmation` | error | <动态生成，见源码> |
| `video_quality_gate_blockers_invalid` | error | <动态生成，见源码> |
| `video_quality_gate_blocked_claim` | error | <动态生成，见源码> |
| `accepted_without_quality_gate` | error | <动态生成，见源码> |
| `quality_deviation_acceptance_missing` | error | <动态生成，见源码> |
| `required_reference_role_not_passed` | error | <动态生成，见源码> |
| `prompt_sha256_unreadable` | error | <动态生成，见源码> |
| `prompt_sha256_mismatch` | error | <动态生成，见源码> |
| `prompt_missing` | error | Prompt 文件不存在。 |
| `prompt_marker_language_mixed` | error | 同一 Prompt 不要混用中文和英文多媒体标记。 |
| `prompt_subtitle_bracket_invalid` | error | 未启用字幕时，最终视频 Prompt 不允许出现【】字幕源标识。 |
| `prompt_unreadable` | error | <动态生成，见源码> |
| `<动态码，见源码>` | error | <动态生成，见源码> |
| `prompt_subject_marker_label_missing` | error | <动态生成，见源码> |
| `prompt_speech_line_extra` | error | <动态生成，见源码> |
| `speech_line_invalid` | error | <动态生成，见源码> |
| `speech_line_spoken_text_missing` | error | <动态生成，见源码> |
| `prompt_speech_line_missing` | error | <动态生成，见源码> |
| `prompt_preflight_missing` | error | <动态生成，见源码> |
| `prompt_preflight_review_count_invalid` | error | <动态生成，见源码> |
| `prompt_preflight_revision_count_invalid` | error | <动态生成，见源码> |
| `prompt_final_validation_count_invalid` | error | <动态生成，见源码> |
| `prompt_five_sections_not_verified` | error | <动态生成，见源码> |
| `prompt_shot_preflight_mismatch` | error | <动态生成，见源码> |
| `prompt_preflight_not_passed` | error | <动态生成，见源码> |
| `h3_prompt_path_invalid` | error | <动态生成，见源码> |
| `h3_prompt_missing` | error | <动态生成，见源码> |
| `generated_segment_h3_prompt_missing` | error | <动态生成，见源码> |
| `generated_segment_h3_prompt_sha256_missing` | error | <动态生成，见源码> |
| `h3_prompt_empty` | error | <动态生成，见源码> |
| `h3_prompt_unreadable` | error | <动态生成，见源码> |
| `h3_prompt_sha256_unreadable` | error | <动态生成，见源码> |
| `h3_prompt_sha256_mismatch` | error | <动态生成，见源码> |
| `episode_segment_index_not_contiguous` | error | episode_segment_index 必须唯一并按 1..N 连续编号。 |
| `video_generation_confirmations_missing` | error | 视频阶段每轮生成都必须记录用户参数确认；每轮最多 2 个视频。 |
| `lightweight_planning_confirmation_missing` | error | 轻量模式首次生成确认必须来源于规划参数与五列预览。 |
| `episode_segment_index_invalid` | error | 每个视频片段必须填写从 1 开始的正整数 episode_segment_index。 |
| `episode_segment_index_duplicate` | error | <动态生成，见源码> |
| `video_generation_confirmation_invalid` | error | generation_confirmations 每项必须是对象。 |
| `video_generation_confirmation_attempt_invalid` | error | generation_confirmations.attempt 必须是从 1 开始的正整数。 |
| `video_generation_confirmation_id_duplicate` | error | <动态生成，见源码> |
| `video_generation_confirmation_range_invalid` | error | generation_confirmations 必须填写整数 batch_start_segment_index 和 batch_end_segment_index。 |
| `video_generation_confirmation_too_large` | error | 一次用户确认只能覆盖连续的 1-2 个视频，且索引必须从 1 开始。 |
| `video_generation_confirmation_unknown_segment` | error | 视频生成参数确认范围必须对应 video_manifest 中真实存在的连续 SEG。 |
| `video_generation_supersedes_invalid` | error | supersedes_confirmation_ids 必须是确认 ID 字符串数组。 |
| `video_generation_confirmation_overlap` | error | 重生或返修覆盖既有 SEG 时，必须通过 supersedes_confirmation_ids 显式替代所有重叠的旧确认。 |
| `video_generation_supersedes_unknown` | error | <动态生成，见源码> |
| `video_generation_supersedes_unrelated` | error | <动态生成，见源码> |
| `video_generation_count_invalid` | error | planned_video_count 必须是 1 或 2。 |
| `lightweight_generation_scope_invalid` | error | 轻量模式规划确认只能授权唯一一个视频。 |
| `video_generation_segment_durations_invalid` | error | segment_durations 必须逐 SEG 记录，项数等于本批次数量。 |
| `video_generation_confirmation_tables_invalid` | error | 视频生成确认展示结构与当前模式不一致。 |
| `video_generation_confirmation_time_invalid` | error | 视频生成参数确认 confirmed_at 必须是带时区 ISO-8601 时间。 |
| `video_generation_interaction_confirmation_missing` | error | 视频生成参数确认必须登记 interaction.ask 返回 generate；普通文字确认不能替代执行确认。 |
| `video_generation_confirmation_missing` | error | <动态生成，见源码> |
| `video_generation_confirmation_id_missing` | error | <动态生成，见源码> |
| `video_tool_call_id_missing` | error | <动态生成，见源码> |
| `video_tool_called_at_invalid` | error | <动态生成，见源码> |
| `video_confirmation_after_tool_call` | error | <动态生成，见源码> |
| `video_generation_supersedes_time_invalid` | error | 替代确认的 confirmed_at 必须晚于被替代确认。 |
| `video_generation_confirmation_attempt_not_incremented` | error | 返修或重生确认的 attempt 必须高于其覆盖的旧确认。 |
| `video_generation_confirmation_initial_attempt_invalid` | error | 首次覆盖一组 SEG 的确认 attempt 必须为 1。 |
| `video_generation_count_mismatch` | error | planned_video_count 必须等于本轮确认覆盖的 SEG 数。 |
| `video_generation_confirmation_field_missing` | error | <动态生成，见源码> |
| `lightweight_planning_parameters_missing` | error | 轻量模式生成确认必须登记已展示的规划参数列表。 |
| `video_generation_parameter_table_missing` | error | 必须登记实际展示的一张本批次合并参数确认表。 |
| `lightweight_planning_preview_rows_invalid` | error | 轻量模式规划五列预览必须为 1-8 行。 |
| `video_generation_storyboard_rows_invalid` | error | 本批次五列分镜表必须每个 SEG 恰好一行，行数等于“数量”。 |
| `video_generation_confirmation_id_mismatch` | error | <动态生成，见源码> |
| `video_generation_total_duration_mismatch` | error | 批次 duration_s 必须等于逐段时长之和。 |
| `lightweight_planning_parameters_incomplete` | error | <动态生成，见源码> |
| `lightweight_planning_quantity_invalid` | error | 轻量模式视频数量必须为 1。 |
| `video_generation_displayed_quantity_mismatch` | error | 参数确认表“数量”必须等于 planned_video_count。 |
| `video_generation_displayed_duration_count_mismatch` | error | 参数确认表必须按 SEG 分别展示时长，项数等于“数量”。 |
| `video_generation_displayed_model_mismatch` | error | 参数确认表中的视频模型必须匹配本批次 model。 |
| `video_generation_displayed_aspect_ratio_mismatch` | error | 参数确认表中的画幅必须匹配本批次 aspect_ratio。 |
| `lightweight_planning_preview_field_missing` | error | 轻量模式规划五列预览每行必须填写时间、剧情动作、声音、运镜衔接和段尾功能/承接；不得要求每段另造钩子。 |
| `video_generation_segment_details_not_displayed` | error | <动态生成，见源码> |
| `video_generation_confirmation_not_latest` | error | <动态生成，见源码> |
| `video_generation_segment_duration_invalid` | error | <动态生成，见源码> |
| `video_generation_segment_duration_id_mismatch` | error | <动态生成，见源码> |
| `video_generation_segment_duration_mismatch` | error | <动态生成，见源码> |
| `video_generation_parameter_table_field_missing` | error | <动态生成，见源码> |
| `video_generation_displayed_total_duration_mismatch` | error | 参数确认表中的总时长必须等于本批次逐段时长之和。 |
| `video_generation_storyboard_row_invalid` | error | <动态生成，见源码> |
| `video_generation_storyboard_segment_mismatch` | error | <动态生成，见源码> |
| `video_generation_parameter_table_text_mismatch` | error | <动态生成，见源码> |
| `video_generation_displayed_duration_mismatch` | error | <动态生成，见源码> |
| `video_generation_storyboard_field_missing` | error | <动态生成，见源码> |
| `video_generation_storyboard_speech_missing` | error | <动态生成，见源码> |
| `video_generation_storyboard_text_mismatch` | error | <动态生成，见源码> |
| `asset_usage_plan_missing` | error | storyboard 必须登记 asset_usage_plan（资产需求清单的结构化同源数据）。 |
| `asset_usage_plan_invalid` | error | asset_usage_plan 每条必须是对象。 |
| `asset_usage_plan_invalid` | error | asset_usage_plan 缺少 asset_id。 |
| `asset_usage_unknown_asset` | error | <动态生成，见源码> |
| `asset_usage_segments_invalid` | error | <动态生成，见源码> |
| `reference_role_asset_mismatch` | error | <动态生成，见源码> |
| `asset_usage_unknown_segment` | error | <动态生成，见源码> |
| `asset_required_but_unplanned` | error | <动态生成，见源码> |
| `asset_planned_but_unregistered` | warning | <动态生成，见源码> |
| `asset_version_inconsistent` | warning | <动态生成，见源码> |
