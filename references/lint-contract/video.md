# lint 检查合同 · video 阶段

> 由 build_lint_contract.py 从实际 STAGE_CHECKS 与共享调用图生成；禁止手改。
> 只证明结构、来源、算术、依赖与技术合同；内容须按观看顺序独立审校。

运行：`python scripts/drama_lint.py <skill-root> --project-root <project> --stage video`。

轻量走同一内核和单任务预检适配，不要求伪造完整模式上游。

| 检查码 | 级别 | 查什么 | 来源 |
|---|---|---|---|
| `accepted_segment_output_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `accepted_segment_prompt_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `accepted_without_quality_gate` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `adopted_cut_out_invalid` | error | continuous 后段需先锁采用出点和真实入站帧，再编译 | `preflight_video.prepare_full` |
| `asset_entity_scope_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_entity_scope_not_character` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_file_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_id_missing` | error | 资产缺少 asset_id。 | `drama_lint.check_assets` |
| `asset_id_prefix_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_planned_but_unregistered` | warning | 动态消息；按当前对象及源码核对 | `drama_lint.check_asset_usage_reconciliation` |
| `asset_ref_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_asset_ref` |
| `asset_ref_unknown` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_asset_ref` |
| `asset_ref_version_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_asset_ref` |
| `asset_refs_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `asset_required_but_unplanned` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_asset_usage_reconciliation` |
| `asset_status_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_usage_duplicate` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_usage_plan_invalid` | error | asset_usage_plan 每条必须是对象。 | `drama_lint.check_asset_usage_reconciliation` |
| `asset_usage_plan_invalid` | error | asset_usage_plan 缺少 asset_id。 | `drama_lint.check_asset_usage_reconciliation` |
| `asset_usage_plan_missing` | error | storyboard 必须登记 asset_usage_plan（资产需求清单的结构化同源数据）。 | `drama_lint.check_asset_usage_reconciliation` |
| `asset_usage_segments_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_asset_usage_reconciliation` |
| `asset_usage_shared_not_approved` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_usage_shared_version_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_usage_unknown_asset` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_asset_usage_reconciliation` |
| `asset_usage_unknown_segment` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_asset_usage_reconciliation` |
| `asset_usage_unknown_shared_asset` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_usage_unknown_shared_version` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_version_duplicate` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `asset_version_inconsistent` | warning | 动态消息；按当前对象及源码核对 | `drama_lint.check_asset_usage_reconciliation` |
| `assets_invalid` | error | asset_registry.assets 必须是数组。 | `drama_lint.check_assets` |
| `audience_execution_contract_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `audience_execution_field_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `audience_execution_missing` | error | storyboard 必须登记从已确认 audience_plan 派生的 audience_execution。 | `drama_lint.check_storyboards` |
| `audience_execution_ref_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `audience_execution_refs_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `audience_execution_revision_invalid` | error | audience_execution.source_plan_revision 必须是正整数。 | `drama_lint.check_storyboards` |
| `audience_execution_revision_mismatch` | error | audience_execution.source_plan_revision 必须等于当前已确认 drama_plan revision。 | `drama_lint.check_storyboards` |
| `audience_execution_source_field_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `beat_coverage_missing` | error | storyboard 必须登记 beat_coverage：剧本每条动作/事件的去向台账。 | `drama_lint.check_beat_coverage` |
| `beat_disposition_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_beat_coverage` |
| `beat_drop_reason_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_beat_coverage` |
| `beat_incomplete` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_beat_coverage` |
| `beat_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_beat_coverage` |
| `beat_target_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_beat_coverage` |
| `beat_unknown_shot` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_beat_coverage` |
| `causal_chain_breakpoint_risk_invalid` | warning | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_cross_episode_not_closed` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_cross_episode_ref_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_cross_episode_refs_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_empty` | warning | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_highlight_binding_ref_unknown` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_invalid` | error | causal_ledger 每条必须是对象。 | `drama_lint.check_causal_ledger` |
| `causal_chain_reaction_before_evidence` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_ref_unknown` | warning | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_result_before_reaction` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_shot_unknown` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_shots_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_trigger_fact_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_trigger_source_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_chain_visibility_contract_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_evidence_establishes_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_evidence_visibility_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_ledger_missing` | error | storyboard 必须登记 causal_ledger 数组（无反应/证据依赖链的集登记空数组）。 | `drama_lint.check_causal_ledger` |
| `causal_reaction_responds_to_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_ref_id_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_causal_ref` |
| `causal_ref_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_causal_ref` |
| `causal_ref_type_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_causal_ref` |
| `causal_ref_unknown` | error | 动态消息；按当前对象及源码核对 | `drama_lint.validate_causal_ref` |
| `causal_responds_to_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_role_invalid` | warning | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_role_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_seam_invariant_missing` | warning | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_seam_invariant_unknown` | warning | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `causal_trigger_fact_missing` | warning | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
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
| `confirmation_base_revision_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_base_revision_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_changed_artifacts_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_decision_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_episode_id_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_impact_scope_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_log_blank_line` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_log_json_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_log_missing` | error | 阶段已确认或推进到后续阶段时必须存在用户确认记录。 | `drama_lint.load_confirmation_records` |
| `confirmation_log_row_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_log_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_mode_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_revision_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_stage_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_time_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `confirmation_user_message_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `content_review_open_issue` | error | 有未解决的内容设计问题 | `content_first.check_review` |
| `content_review_open_issue` | error | 缺内容审校记录；字段存在不证明摄影成立 | `content_first.check_review` |
| `content_review_stale` | error | 内容审校不对应当前设计/源/时间输入 | `content_first.check_review` |
| `cut_motivation_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_shot_rhythm_fields` |
| `delivery_package_file_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `director_control_card_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `director_control_card_missing` | error | 分镜阶段必须存在唯一导演总控卡。 | `drama_lint.check_storyboards` |
| `director_package_sha256_mismatch` | error | 导演包 SHA 与实际文件不同。 | `drama_lint.check_video` |
| `downstream_asset_not_approved` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_asset_ref` |
| `downstream_asset_version_stale` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_stale_asset_version` |
| `downstream_state_not_approved` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state_ref` |
| `episode_asset_duplicate` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_asset_file_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_asset_status_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_character_state_asset_requires_image_edit` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_confirmation_missing_episode_id` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `episode_id_mismatch` | error | keyframe_manifest episode_id 与目录不一致。 | `drama_lint.check_keyframes` |
| `episode_id_mismatch` | error | storyboard episode_id 与目录不一致。 | `drama_lint.check_storyboards` |
| `episode_id_mismatch` | error | video_manifest episode_id 与目录不一致。 | `drama_lint.check_video` |
| `episode_id_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_episode_manifest_ids` |
| `episode_image_edit_reference_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_image_edit_visual_reference_decision_conflict` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_image_gen_should_not_have_visual_inputs` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_image_gen_visual_reference_available` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_image_gen_visual_reference_decision_conflict` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_keyframe_count_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `episode_project_visual_mode_missing_or_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `episode_segment_index_invalid` | error | 视频段索引需从 1 起唯一正整数 | `video_confirmations.validate_confirmations` |
| `episode_segment_index_not_contiguous` | error | 视频段索引必须连续 | `video_confirmations.validate_confirmations` |
| `episode_visual_reference_decision_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `evidence_visibility_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `file_missing` | error | 缺少流程所需文件。 | `drama_lint.load_json` |
| `generated_segment_h3_prompt_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_h3_prompt` |
| `generated_segment_h3_prompt_sha256_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_h3_prompt` |
| `generated_segment_prompt_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `generated_segment_prompt_sha256_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `generation_prompt_file_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_generation_prompt_file` |
| `generation_prompt_path_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_generation_prompt_file` |
| `generation_prompt_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_generation_prompt_file` |
| `h3_compilation_mismatch` | error | 编译映射镜头集合/顺序不符 | `drama_lint.check_prompt_preflight` |
| `h3_compilation_mismatch` | error | 编译映射需指向成稿实际段落；引用不证明语义保真 | `h3_contract.prepare_request` |
| `h3_compilation_mismatch` | error | 编译映射须按当前 SEG 镜头顺序完整覆盖 | `preflight_video.validate_compilation_map` |
| `h3_compilation_mismatch` | error | 镜头编译的 SEG 局部时间与核算不符 | `preflight_video.validate_compilation_map` |
| `h3_input_invalid` | error | inputs 必须是数组，可空 | `h3_contract._media` |
| `h3_input_invalid` | error | manifest 的参考媒体时长与实际请求不同 | `preflight_video.validate_manifest_inputs` |
| `h3_input_invalid` | error | manifest 的实际输入顺序/文件或原样 URL/职责与 gen 不同 | `preflight_video.validate_manifest_inputs` |
| `h3_input_invalid` | error | 参考单条时长超能力 | `h3_contract._media` |
| `h3_input_invalid` | error | 参考累计时长超能力 | `h3_contract._media` |
| `h3_input_invalid` | error | 只支持项目内文件或 HTTP(S) URL | `h3_contract._media` |
| `h3_input_invalid` | error | 显式 slot 必须匹配该模态数组顺序 | `h3_contract._media` |
| `h3_input_invalid` | error | 本地媒体扩展名与 kind 不符 | `h3_contract._media` |
| `h3_input_invalid` | error | 每项需要有效 kind/path | `h3_contract._media` |
| `h3_input_invalid` | error | 输入条目或字段无效，不静默丢弃 | `h3_contract._media` |
| `h3_input_invalid` | error | 输入超真实总文件上限 | `h3_contract._media` |
| `h3_input_invalid` | error | 输入超真实模态槽位上限 | `h3_contract._media` |
| `h3_input_invalid` | error | 音视频参考需登记已探测时长；URL 不在预检时下载 | `h3_contract._media` |
| `h3_input_invalid` | error | 音频参考需要真实视觉输入 | `h3_contract._media` |
| `h3_input_marker_mismatch` | error | 成稿媒体标记必须逐项对应实际输入槽位，无遗漏或未知引用 | `h3_contract.check_media_markers` |
| `h3_mode_invalid` | error | 声明模式与实际输入不符；禁止丢输入改路由 | `h3_contract._media` |
| `h3_mode_invalid` | error | 未知 H3 模式 | `h3_contract._media` |
| `h3_mode_invalid` | error | 锚帧数与当前模式不符 | `h3_contract._media` |
| `h3_prompt_empty` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_h3_prompt` |
| `h3_prompt_impure` | error | H3 字段正文为空 | `h3_contract.check_purity` |
| `h3_prompt_impure` | error | H3 字段缺失、重复、未知或顺序不符 | `h3_contract.check_purity` |
| `h3_prompt_impure` | error | H3 正文为空 | `h3_contract.check_purity` |
| `h3_prompt_impure` | error | 动态消息；按当前对象及源码核对 | `drama_lint._check_h3_prompt_purity` |
| `h3_prompt_impure` | error | 混入交付包/分隔符/围栏；不提取子串提交 | `h3_contract.check_purity` |
| `h3_prompt_impure` | error | 混入标题、表格或独立说明；只允许 H3 字段正文 | `h3_contract.check_purity` |
| `h3_prompt_impure` | error | 锚帧首行后需空行和 H3 正文 | `h3_contract.check_purity` |
| `h3_prompt_impure` | error | 首行不符合当前 H3 模式；合法锚帧指令须保持官方格式 | `h3_contract.check_purity` |
| `h3_prompt_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_h3_prompt` |
| `h3_prompt_path_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_h3_prompt` |
| `h3_prompt_sha256_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_h3_prompt` |
| `h3_prompt_sha256_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_h3_prompt` |
| `h3_prompt_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_h3_prompt` |
| `h3_request_invalid` | error | SEG 不存在或重复 | `preflight_video.prepare_full` |
| `h3_request_invalid` | error | aspect 不符合能力档 | `h3_contract._parameters` |
| `h3_request_invalid` | error | base_url 需 HTTP(S) URL | `h3_contract._parameters` |
| `h3_request_invalid` | error | extra 需 workflow，未知字段不得静默忽略 | `h3_contract._parameters` |
| `h3_request_invalid` | error | gen 必须为有限 JSON | `h3_contract.prepare_request` |
| `h3_request_invalid` | error | gen 必须是对象，且只能包含已声明字段 | `h3_contract._parameters` |
| `h3_request_invalid` | error | options 必须是有限 JSON | `h3_contract._parameters` |
| `h3_request_invalid` | error | resolution 不符合能力档 | `h3_contract._parameters` |
| `h3_request_invalid` | error | seed 必须整数 | `h3_contract._parameters` |
| `h3_request_invalid` | error | 动态消息；按当前对象及源码核对 | `h3_contract._parameters` |
| `h3_request_invalid` | error | 当前封装的画幅方向由 resolution 承载；aspect 需与实际 resolution 一致 | `h3_contract._parameters` |
| `h3_request_invalid` | error | 模型必须是当前 H3 能力档 | `h3_contract._parameters` |
| `h3_reserved_option` | error | options 不能覆盖正文、时长、已知参数或媒体槽位 | `h3_contract._parameters` |
| `h3_runtime_invalid` | error | 动态消息；按当前对象及源码核对 | `h3_contract._parameters` |
| `highlight_binding_aftereffect_before_payoff` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_aftereffect_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_aftereffect_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_aftereffect_scope_conflict` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_deferred_episode_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_deferred_episode_order_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_deferred_highlight_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_deferred_ref_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_execution_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_invalid` | error | highlight_bindings 每项必须是对象。 | `drama_lint.check_storyboards` |
| `highlight_binding_reaction_before_payoff` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_segment_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_segment_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_shot_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_shots_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_binding_unknown` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `highlight_bindings_missing` | error | storyboard.highlight_bindings 必须是数组并覆盖剧本主要亮点。 | `drama_lint.check_storyboards` |
| `highlight_ledger_invalid` | error | script_contract.highlight_ledger 必须是数组。 | `drama_lint.check_storyboards` |
| `highlight_ledger_invalid` | error | 完整模式 script_contract.highlight_ledger 必须是数组。 | `drama_lint.check_stage_artifacts` |
| `image_edit_reference_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `image_edit_visual_reference_decision_conflict` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `image_gen_should_not_have_visual_inputs` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `image_gen_visual_reference_available` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `image_gen_visual_reference_decision_conflict` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `image_to_video_input_invalid` | error | image_to_video 不支持上传视频、音频或 voice_inputs；本路由只能传参考图。 | `drama_lint.check_video` |
| `image_to_video_reference_missing` | error | image_to_video 必须登记实际传入参考图。 | `drama_lint.check_video` |
| `inherited_aftereffect_binding_fields_missing` | error | inherited_aftereffect_bindings 必须填写 binding_id、source_episode_id 和 source_highlight_id。 | `drama_lint.check_storyboards` |
| `inherited_aftereffect_binding_invalid` | error | inherited_aftereffect_bindings 每项必须是对象。 | `drama_lint.check_storyboards` |
| `inherited_aftereffect_binding_shot_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `inherited_aftereffect_binding_shots_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `inherited_aftereffect_bindings_invalid` | error | inherited_aftereffect_bindings 必须是数组。 | `drama_lint.check_storyboards` |
| `inherited_aftereffect_source_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `interaction_call_id_reused` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `intermediate_stable_hold_reason_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `json_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_json` |
| `keyframe_count_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `keyframe_file_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `keyframe_file_name_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `keyframe_highlight_index_duplicate` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `keyframe_highlight_index_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `keyframe_identity_mismatch` | error | 有效 KF 必须逐项对应实际请求 ID，数量相同不能代替。 | `drama_lint.check_keyframes` |
| `keyframe_requests_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframe_request_plan` |
| `keyframe_role_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `keyframe_role_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframe_request_plan` |
| `keyframe_role_without_request` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframe_request_plan` |
| `keyframe_tool_not_image_edit` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `keyframe_unknown_segment` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `keyframe_unknown_shot` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `keyframe_unknown_used_segment` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `keyframe_unplanned_segment` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `keyframes_invalid` | error | keyframes 必须是数组。 | `drama_lint.check_keyframes` |
| `lightweight_confirmation_call_mismatch` | error | 轻量每次生成确认须对应其真实 planning 调用，历史各自保留。 | `drama_lint.check_video` |
| `lightweight_planning_confirmation_missing` | error | 轻量唯一确认来自已完成内部设计的参数/预览 | `video_confirmations.validate_confirmations` |
| `lightweight_style_unresolved` | error | 轻量唯一生成确认前需确定具体画风 | `content_first.check_lightweight` |
| `lightweight_video_count_invalid` | error | 轻量模式必须只生成一个最终视频；多个独立视频必须拆为独立任务。 | `drama_lint.check_video` |
| `media_to_video_media_missing` | error | media_to_video 必须至少登记一个真实视频或音频输入。 | `drama_lint.check_video` |
| `occluded_establishes_missing` | warning | 动态消息；按当前对象及源码核对 | `drama_lint.check_causal_ledger` |
| `opening_binding_marker_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_reference_plan` |
| `pack_drift` | error | SEG 内容/请求/尾余量/设计依赖不符 | `content_first.reconcile_storyboard` |
| `pack_drift` | error | beat_groups 必须为数组 | `timeline_core.validate_timeline_shape` |
| `pack_drift` | error | group_id 必须唯一且非空 | `timeline_core.compute_groups` |
| `pack_drift` | error | segment_id 必须为非空字符串 | `timeline_core.compute_groups` |
| `pack_drift` | error | segment_id 重复 | `timeline_core.compute_groups` |
| `pack_drift` | error | 动态消息；按当前对象及源码核对 | `preflight_video.validate_segment_timing` |
| `pack_drift` | error | 动态消息；按当前对象及源码核对 | `timeline_core.compute_groups` |
| `pack_drift` | error | 组必须按正式顺序恰好覆盖所有镜头，无重漏 | `timeline_core.compute_groups` |
| `pack_drift` | error | 视频 SEG 不在当前分镜 | `preflight_video.prepare_full` |
| `pack_drift` | error | 轻量 gen 的内容时间/尾余量与设计不同 | `preflight_video.prepare_lightweight` |
| `pack_drift` | error | 轻量请求时长不符实际单条设计 | `preflight_video.prepare_lightweight` |
| `pack_drift` | error | 镜头组字段非法 | `timeline_core.compute_groups` |
| `pack_drift` | error | 需要导演声明的合法镜头组，不自动制造切点 | `timeline_core.compute_groups` |
| `planning_interaction_confirmation_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `preflight_binding_mismatch` | error | manifest binding_id 不符 | `drama_lint.check_prompt_preflight` |
| `preflight_binding_mismatch` | error | preflight 必须为完整回执对象 | `h3_contract.prepare_request` |
| `preflight_binding_mismatch` | error | 当前设计/请求不符 manifest 绑定 | `drama_lint.check_video` |
| `preflight_binding_mismatch` | error | 缺独立 H3 文件路径 | `h3_contract.prepare_request` |
| `preflight_binding_mismatch` | error | 读取时检测到文件变化 | `h3_contract.snapshot_bytes` |
| `preflight_binding_mismatch` | error | 调用方正文与当前 H3 文件不同 | `h3_contract.prepare_request` |
| `preflight_binding_mismatch` | error | 预检缺失或当前文件/参数/输入/出点/源依赖已变，POST 前阻断 | `h3_contract.prepare_request` |
| `preflight_dependency_invalid` | error | dependencies 必须为对象数组 | `h3_contract.prepare_request` |
| `preflight_dependency_invalid` | error | 依赖镜头不存在或顺序已变 | `h3_contract.scoped_design` |
| `preflight_dependency_invalid` | error | 依赖镜头范围无效 | `h3_contract.scoped_design` |
| `preflight_dependency_invalid` | error | 入站出点必须登记依赖 | `h3_contract.prepare_request` |
| `preflight_dependency_invalid` | error | 导演包与纯 H3 成稿必须是两个独立文件 | `h3_contract.prepare_request` |
| `preflight_dependency_invalid` | error | 未知依赖角色 | `h3_contract.dependency_snapshot` |
| `preflight_dependency_invalid` | error | 缺当前内容对照引用或实际编译映射 | `h3_contract.prepare_request` |
| `preflight_dependency_invalid` | error | 需导演包和实际分镜/轻量设计依赖 | `h3_contract.prepare_request` |
| `previous_tail_source_type_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `primary_highlight_binding_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `project_confirmation_has_episode` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `project_visual_mode_missing_or_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `prompt_marker_language_mixed` | error | 同一 Prompt 不要混用中文和英文多媒体标记。 | `drama_lint.check_prompt_markers` |
| `prompt_missing` | error | Prompt 文件不存在。 | `drama_lint.check_prompt_markers` |
| `prompt_path_invalid` | error | compiled_prompt_file 必须是项目相对路径。 | `drama_lint.check_video` |
| `prompt_sha256_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `prompt_sha256_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `prompt_speech_line_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_prompt_markers` |
| `prompt_subject_marker_label_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_prompt_markers` |
| `prompt_subtitle_bracket_invalid` | error | 未启用字幕时，最终视频 Prompt 不允许出现【】字幕源标识。 | `drama_lint.check_prompt_markers` |
| `prompt_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_prompt_markers` |
| `quality_deviation_acceptance_missing` | error | 偏差接受需回指同一结果文件/指纹、范围和明确偏差的真实确认，非空引用不能代替。 | `drama_lint.check_quality_acceptance` |
| `ref_audio_not_voice_sample` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `reference_input_file_suffix_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.ordered_inputs` |
| `reference_input_plan_incomplete` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_reference_plan` |
| `reference_input_plan_invalid` | error | reference_input_plan 必须是数组。 | `drama_lint.check_reference_plan` |
| `reference_input_plan_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_reference_plan` |
| `reference_input_plan_missing` | error | 每个 SEG 必须填写 reference_input_plan。 | `drama_lint.check_reference_plan` |
| `reference_order_invalid` | error | 参考图 order 必须是整数。 | `drama_lint.check_reference_plan` |
| `reference_order_not_contiguous` | error | 参考图 order 必须从 1 连续递增。 | `drama_lint.check_reference_plan` |
| `reference_role_asset_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_asset_usage_reconciliation` |
| `reference_role_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_reference_plan` |
| `required_artifact_missing` | error | 缺少当前阶段所需产物。 | `drama_lint.check_stage_artifacts` |
| `required_reference_role_invalid` | error | required_reference_roles 含无效职责。 | `drama_lint.check_video` |
| `required_reference_role_not_passed` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `required_reference_roles_missing` | error | image_to_video 必须声明 required_reference_roles。 | `drama_lint.check_video` |
| `required_reference_roles_missing` | error | media_to_video 使用图片或分镜声明图片职责时必须填写 required_reference_roles。 | `drama_lint.check_video` |
| `required_reference_roles_unexpected` | error | media_to_video 没有图片输入时 required_reference_roles 应为空或省略。 | `drama_lint.check_video` |
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
| `segment_density_profile_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_segment_shot_count` |
| `segment_duration_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `segment_shot_ids_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `segment_shot_mode_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_segment_shot_count` |
| `segment_tail_mode_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `segment_unknown_shot` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `shot_beat_type_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_shot_rhythm_fields` |
| `shot_duration_total_mismatch` | error | shots.duration_s 之和必须等于 storyboard.duration_s。 | `drama_lint.check_storyboards` |
| `shot_segment_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `shot_unknown_segment` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `shots_covered_multiple_times` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `shots_not_covered` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `source_event_uncovered` | error | 事件索引必须是对象 | `content_first.source_index_from_contract` |
| `source_event_uncovered` | error | 动态消息；按当前对象及源码核对 | `content_first.source_index_from_contract` |
| `source_event_uncovered` | error | 动态消息；按当前对象及源码核对 | `content_first.validate_coverage` |
| `source_event_uncovered` | error | 覆盖行必须是对象 | `content_first.validate_coverage` |
| `source_event_uncovered` | error | 需要 beat_coverage 多对多承接 | `content_first.validate_coverage` |
| `source_line_uncovered` | error | speech_lines 必须是数组，可空 | `content_first.source_index_from_contract` |
| `source_line_uncovered` | error | 动态消息；按当前对象及源码核对 | `content_first.validate_coverage` |
| `source_line_uncovered` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `source_line_uncovered` | error | 单镜发声分片须保留完整源台词 | `preflight_video.validate_compilation_map` |
| `source_line_uncovered` | error | 台词索引必须是对象 | `content_first.source_index_from_contract` |
| `source_line_uncovered` | error | 已知台词未出现在对应发声块 | `h3_contract.prepare_request` |
| `source_line_uncovered` | error | 编译映射的逐字人声须来自当前源台词，不能省略或换文 | `preflight_video.validate_compilation_map` |
| `source_line_uncovered` | error | 跨镜/跨 SEG 需明确逐字发声分片，不由秒数猜词 | `preflight_video.validate_compilation_map` |
| `source_line_uncovered` | error | 轻量人声未完整承接 | `content_first.check_lightweight` |
| `source_revision_mismatch` | error | script contract 缺 scenes | `content_first.source_index_from_contract` |
| `source_revision_mismatch` | error | source_script 需 file/revision/sha256 | `timeline_core.validate_timeline_shape` |
| `source_revision_mismatch` | error | 剧本正文与源索引 SHA 不一致 | `content_first.load_source` |
| `source_revision_mismatch` | error | 动态消息；按当前对象及源码核对 | `content_first.load_source` |
| `source_revision_mismatch` | error | 动态消息；按当前对象及源码核对 | `content_first.source_index_from_contract` |
| `source_revision_mismatch` | error | 时间输入不是当前源剧本文件/版本 | `content_first.load_source` |
| `source_revision_mismatch` | error | 源剧本正文 SHA 不符。 | `drama_lint.check_stage_artifacts` |
| `source_revision_mismatch` | error | 源场次 ID 必须唯一且非空 | `content_first.source_index_from_contract` |
| `source_revision_mismatch` | error | 源确认 ID 不存在或重复 | `h3_contract.dependency_snapshot` |
| `source_revision_mismatch` | error | 缺当前源剧本 SHA/版本对应的真实确认来源 | `content_first.load_source` |
| `speech_line_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_prompt_markers` |
| `speech_line_spoken_text_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_prompt_markers` |
| `speech_line_voice_anchor_inconsistent` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_voice_anchor_consistency` |
| `speech_line_voice_anchor_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_voice_anchor_consistency` |
| `speech_line_voice_anchor_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_voice_audio_inputs` |
| `speech_line_voice_input_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_voice_audio_inputs` |
| `speech_span_discontinuous` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `speech_span_discontinuous` | error | 跨 SEG 发声须有真实实施方式和声音承接审校引用 | `preflight_video.validate_compilation_map` |
| `speech_span_incomplete` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `speech_span_incomplete` | error | 发声分片须为对象数组 | `preflight_video.validate_compilation_map` |
| `speech_span_incomplete` | error | 发声分片须唯一对应实际镜头及 utterance，不得漏文、错绑或重复 | `preflight_video.validate_compilation_map` |
| `speech_span_incomplete` | error | 发声分片须引用实际人声事件 | `preflight_video.validate_compilation_map` |
| `speech_span_incomplete` | error | 声音承接须明确完整逐字分片 | `preflight_video.validate_compilation_map` |
| `speech_span_incomplete` | error | 跨镜/跨 SEG 发声分片必须按 utterance 顺序逐字覆盖源台词，无遗漏或重复 | `preflight_video.validate_compilation_map` |
| `speech_timing_basis_invalid` | error | timing_basis 字段无效 | `timeline_core.validate_timeline_shape` |
| `speech_timing_basis_invalid` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `state_ref_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state_ref` |
| `state_ref_unknown` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state_ref` |
| `state_refs_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_keyframes` |
| `storyboard_fifteen_columns_missing` | error | 完整分镜表必须包含一个十五列表格。 | `drama_lint.check_stage_artifacts` |
| `storyboard_fifteen_columns_missing` | error | 完整分镜表必须包含一个十五列表格。 | `drama_lint.check_storyboards` |
| `storyboard_required_role_not_inherited` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `storyboard_required_role_not_passed` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `storyboard_shape_invalid` | error | storyboard 必须包含 shots 和 segments 数组。 | `drama_lint.check_storyboards` |
| `storyboard_source_markdown_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
| `storyboard_source_markdown_missing` | error | 十五列完整分镜表文件不存在。 | `drama_lint.check_storyboards` |
| `storyboard_source_markdown_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_stage_artifacts` |
| `storyboard_source_markdown_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
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
| `text_to_video_input_invalid` | error | text_to_video 只能用于没有图片、视频、音频或 voice_inputs 的片段。 | `drama_lint.check_video` |
| `timeline_dependency_conflict` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `timeline_dependency_cycle` | error | after 中存在自依赖或循环 | `timeline_core.reconcile_timeline` |
| `timeline_field_unknown` | error | speech 文本只回指 utterance，不另建权威 | `timeline_core.validate_timeline_shape` |
| `timeline_field_unknown` | error | 非 speech 不能携带 utterance | `timeline_core.validate_timeline_shape` |
| `timeline_id_duplicate` | error | 动态消息；按当前对象及源码核对 | `content_first.source_index_from_contract` |
| `timeline_id_duplicate` | error | 动态消息；按当前对象及源码核对 | `timeline_core.reconcile_timeline` |
| `timeline_number_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_storyboards` |
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
| `timeline_shot_set_mismatch` | error | 分镜与时间输入的镜头集合/顺序不一致 | `content_first.reconcile_storyboard` |
| `timeline_shot_set_mismatch` | error | 动态消息；按当前对象及源码核对 | `content_first.reconcile_storyboard` |
| `timeline_shot_set_mismatch` | error | 十五列阅读稿的镜头集合/顺序需与同源时间输入一致 | `content_first.check_reading_times` |
| `timing_input_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_rhythm_reconciliation` |
| `timing_input_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_stage_artifacts` |
| `timing_output_drift` | error | 分镜总长/规范时间指纹不符 | `content_first.reconcile_storyboard` |
| `timing_output_drift` | error | 动态消息；按当前对象及源码核对 | `content_first.check_reading_times` |
| `timing_output_drift` | error | 动态消息；按当前对象及源码核对 | `content_first.reconcile_storyboard` |
| `tool_capabilities_invalid` | error | 动态消息；按当前对象及源码核对 | `timeline_core.compute_groups` |
| `tool_capabilities_invalid` | error | 真实 H3 能力缺失，不能跳过 pack。 | `drama_lint.check_rhythm_reconciliation` |
| `tool_duration_unrepresentable` | error | 动态消息；按当前对象及源码核对 | `timeline_core.compute_groups` |
| `tool_duration_unrepresentable` | error | 请求时长不在真实整数能力范围；不自动取整 | `h3_contract._parameters` |
| `tool_duration_unrepresentable` | error | 请求时长必须为合法整数秒 | `h3_contract._parameters` |
| `tool_duration_unrepresentable` | error | 轻量只允许一个真实生成任务；不自动扩范围 | `content_first.check_lightweight` |
| `true_one_take_shot_count_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_segment_shot_count` |
| `video_confirmation_after_tool_call` | error | 工具事实和时间需在确认之后 | `video_confirmations.validate_confirmations` |
| `video_duration_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_duration_mismatch` | error | video 总长需等于各整数请求时长之和。 | `drama_lint.check_video` |
| `video_edit_input_invalid` | error | video_edit 只登记源视频，不登记图片、音频或 voice_inputs。 | `drama_lint.check_video` |
| `video_edit_source_invalid` | error | video_edit 必须且只能登记一个 source_video_for_edit 源视频。 | `drama_lint.check_video` |
| `video_generation_confirmation_attempt_invalid` | error | 实际生成尝试需递增 | `video_confirmations.validate_confirmations` |
| `video_generation_confirmation_id_duplicate` | error | 确认需唯一稳定 ID | `video_confirmations.validate_confirmations` |
| `video_generation_confirmation_invalid` | error | 历史确认必须是对象 | `video_confirmations.validate_confirmations` |
| `video_generation_confirmation_missing` | error | 动态消息；按当前对象及源码核对 | `video_confirmations.validate_confirmations` |
| `video_generation_confirmation_not_latest` | error | 生成结果须引用最新有效确认 | `video_confirmations.validate_confirmations` |
| `video_generation_confirmation_overlap` | error | 重新确认需显式替代覆盖各 SEG 的最新有效确认，历史保留 | `video_confirmations.validate_confirmations` |
| `video_generation_confirmation_range_invalid` | error | 冻结请求索引必须连续整数 | `video_confirmations.validate_confirmations` |
| `video_generation_confirmation_time_invalid` | error | 历史确认必须按带时区实际时间递增 | `video_confirmations.validate_confirmations` |
| `video_generation_confirmations_missing` | error | generation_confirmations 必须为数组 | `video_confirmations.validate_confirmations` |
| `video_generation_count_mismatch` | error | 批次范围/数量不符冻结请求 | `video_confirmations.validate_confirmations` |
| `video_generation_current_snapshot_mismatch` | error | 动态消息；按当前对象及源码核对 | `video_confirmations.validate_confirmations` |
| `video_generation_displayed_quantity_mismatch` | error | 展示数量不符冻结请求 | `video_confirmations.validate_confirmations` |
| `video_generation_interaction_confirmation_missing` | error | 执行确认需真实 AskUserQuestion generate 和用户原文 | `video_confirmations.validate_confirmations` |
| `video_generation_parameter_table_field_missing` | error | 动态消息；按当前对象及源码核对 | `video_confirmations.validate_confirmations` |
| `video_generation_parameter_table_missing` | error | 需保存实际展示参数 | `video_confirmations.validate_confirmations` |
| `video_generation_segment_details_not_displayed` | error | 确认文本需展示每段冻结请求长度 | `video_confirmations.validate_confirmations` |
| `video_generation_segment_duration_mismatch` | error | 历史确认时长按各自冻结请求核验 | `video_confirmations.validate_confirmations` |
| `video_generation_snapshot_invalid` | error | 冻结快照必须是有限数值组成的合法 JSON | `video_confirmations.validate_confirmations` |
| `video_generation_snapshot_invalid` | error | 冻结请求的 SEG ID 必须非空且唯一 | `video_confirmations.validate_confirmations` |
| `video_generation_snapshot_invalid` | error | 快照每段需整数请求时长和对应实际参数 | `video_confirmations.validate_confirmations` |
| `video_generation_snapshot_invalid` | error | 快照缺预检 binding_id | `video_confirmations.validate_confirmations` |
| `video_generation_snapshot_invalid` | error | 每次确认需冻结本批连续 1–2 段请求；轻量一段 | `video_confirmations.validate_confirmations` |
| `video_generation_snapshot_mismatch` | error | 历史确认快照 SHA 不符，不能用当前 SEG 覆盖历史 | `video_confirmations.validate_confirmations` |
| `video_generation_storyboard_field_missing` | error | 动态消息；按当前对象及源码核对 | `video_confirmations.validate_confirmations` |
| `video_generation_storyboard_rows_invalid` | error | 需保存实际五列预览 | `video_confirmations.validate_confirmations` |
| `video_generation_storyboard_rows_invalid` | error | 预览行必须是对象 | `video_confirmations.validate_confirmations` |
| `video_generation_storyboard_segment_mismatch` | error | 历史五列表按冻结请求核验 | `video_confirmations.validate_confirmations` |
| `video_quality_gate_blocked_claim` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_quality_gate_blockers_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_quality_gate_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_reference_unknown_keyframe` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_segment_duration_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_segment_invalid` | error | segments 每项必须是对象。 | `drama_lint.check_video` |
| `video_segment_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_segment_not_accepted` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_segment_not_ready_for_confirmation` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_segment_output_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_segment_unplanned` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_segments_invalid` | error | video_manifest.segments 必须是数组。 | `drama_lint.check_video` |
| `video_state_refs_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video_state_refs` |
| `video_status_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_tool_mode_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `video_unknown_segment` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_video` |
| `visual_reference_decision_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_assets` |
| `voice_audio_input_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_voice_audio_inputs` |
| `voice_audio_support_flag_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_voice_audio_inputs` |
| `voice_inputs_incomplete` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_voice_audio_inputs` |
| `voice_inputs_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_voice_audio_inputs` |
| `voice_inputs_without_audio_reference` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_voice_audio_inputs` |
| `world_fact_category_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_world_facts` |
| `world_fact_incomplete` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_world_facts` |
| `world_fact_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_world_facts` |
| `world_facts_missing` | error | storyboard 必须登记 inherited_world_facts：从剧本继承的季节/节日/时辰/天气等世界事实。 | `drama_lint.check_world_facts` |
