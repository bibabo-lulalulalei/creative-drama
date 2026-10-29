# lint 检查合同 · final 阶段

> 本卡片由 `scripts/build_lint_contract.py` 从 `drama_lint.py` 机读生成，禁止手改。
> 用途：开工前读这张卡知道本阶段 lint 会查什么；报错后按码查修复方向。
> 与源码不一致时以源码为准，并重跑 `python scripts/build_lint_contract.py --check`。

本阶段新增检查项：42。运行命令：`python scripts/drama_lint.py --stage final`（skill 阶段在 skill 根目录运行）。

本阶段同时全量复核以下上游检查（报错时先读对应上游卡）：
- planning 阶段卡 · `check_stage_artifacts` —— final 阶段产物存在性
- planning 阶段卡 · `check_episode_manifest_ids` —— episode_manifest 与 stage 绑定
- assets 阶段卡 · `check_assets` —— 资产索引
- assets 阶段卡 · `validate_collective_profiles` —— 群像画像一致性
- storyboard 阶段卡 · `check_beat_library_desync` —— 节拍库漂移
- storyboard 阶段卡 · `check_rhythm_reconciliation` —— 引擎对账
- storyboard 阶段卡 · `check_rhythm_diversity` —— 节奏健康度
- storyboard 阶段卡 · `check_storyboards` —— 分镜全链（final 阶段也复核）
- keyframes 阶段卡 · `check_keyframes` —— KF 清单对账
- video 阶段卡 · `check_video` —— video_manifest 复核（require_accepted=true）
- video 阶段卡 · `check_prompt_markers` —— 成稿标记与台词逐字
- video 阶段卡 · `check_prompt_preflight` —— 成稿预检
- video 阶段卡 · `check_h3_prompt` —— 成稿存在/哈希
- video 阶段卡 · `check_video_generation_confirmations` —— 生成确认记录
- video 阶段卡 · `check_asset_usage_reconciliation` —— 资产双向对账

| 检查码 | 级别 | 查什么（源码原文消息） |
|---|---|---|
| `episode_id_mismatch` | error | delivery_manifest episode_id 与目录不一致。 |
| `assembly_confirmation_purpose_invalid` | error | assembly_confirmation.confirmation_purpose 必须为 final_assembly。 |
| `assembly_confirmation_call_id_missing` | error | assembly_confirmation 必须记录 interaction_ask_call_id。 |
| `assembly_confirmation_result_invalid` | error | assembly_confirmation.interaction_ask_result 必须为 proceed_assembly。 |
| `assembly_confirmation_user_message_missing` | error | assembly_confirmation.user_message 不能为空。 |
| `assembly_confirmation_time_invalid` | error | assembly_confirmation.confirmed_at 必须是带时区 ISO-8601 时间。 |
| `assembly_confirmation_video_record_missing` | error | assembly_confirmation 必须与同集 stage=video 用户确认记录使用同一 interaction.ask 调用 ID 和 proceed_assembly 结果。 |
| `subtitle_enabled_invalid` | error | subtitle_enabled 必须是布尔值；默认 false，用户明确要求字幕时为 true。 |
| `delivery_status_not_deliverable` | error | delivery_manifest.status 必须为 deliverable 或 candidate；blocked 不得交付。 |
| `delivery_duration_invalid` | error | delivery_manifest.duration_s 必须是数字。 |
| `clean_master_missing` | error | clean_master 必须指向当前分集目录下真实媒体文件。 |
| `subtitle_master_missing` | error | 字幕开启时 subtitle_master 必须指向当前分集目录下真实媒体文件。 |
| `outputs_invalid` | error | outputs 必须是路径数组，或每项包含 file。 |
| `assembly_confirmation_segments_mismatch` | error | assembly_confirmation.segment_ids 必须按顺序精确等于当前成片采用的 accepted SEG。 |
| `lightweight_assembly_confirmation_invalid` | error | 轻量模式单条视频不得创建拼接确认。 |
| `assembly_confirmation_missing` | error | delivery_manifest 必须登记进入成片拼接的 interaction.ask 确认。 |
| `delivery_quality_gate_invalid` | error | 新版 delivery_manifest 必须记录 content_quality_gate。 |
| `outputs_mismatch` | error | outputs 必须与用户可见正式交付文件精确一致：字幕关闭时只交付 [clean_master]。 |
| `basic_qc_reports_invalid` | error | basic_qc_reports 必须是数组。 |
| `subtitle_alignment_report_missing` | error | 字幕开启时必须存在 subtitle_alignment_report（字幕对齐报告）。 |
| `subtitle_source_missing` | error | 字幕开启时必须存在当前分集目录下的 subtitle_source。 |
| `subtitle_final_missing` | error | 字幕开启时必须存在当前分集目录下的 subtitle_final。 |
| `delivery_non_accepted_segment` | error | <动态生成，见源码> |
| `delivery_quality_gate_blockers_invalid` | error | content_quality_gate.blockers 必须是数组。 |
| `delivery_without_quality_pass` | error | deliverable 必须通过整片内容质量门且无阻断项。 |
| `delivery_deviation_acceptance_missing` | error | 整片带偏差交付必须引用用户明确接受记录。 |
| `subtitle_disabled_field_not_empty` | error | <动态生成，见源码> |
| `outputs_mismatch` | error | outputs 必须与用户可见正式交付文件精确一致：字幕开启时只交付 [subtitle_master]。 |
| `subtitle_alignment_report_invalid` | error | subtitle_alignment_report 必须指向当前分集目录下未 blocked 的内部追溯文件。 |
| `subtitle_source_name_invalid` | error | subtitle_source 应指向 字幕_时间轴_vNN_ep_N.srt。 |
| `subtitle_final_name_invalid` | error | subtitle_final 应指向 字幕_最终版_vNN_ep_N.json。 |
| `delivery_duration_out_of_contract` | error | <动态生成，见源码> |
| `episode_id_mismatch` | error | continuity episode_id 与目录不一致。 |
| `continuity_frames_invalid` | error | continuity.frames 必须是数组。 |
| `continuity_seams_invalid` | error | continuity.seams 必须是数组。 |
| `continuity_frame_file_missing` | error | <动态生成，见源码> |
| `continuity_frame_suffix_invalid` | error | <动态生成，见源码> |
| `continuity_frame_roles_missing` | error | <动态生成，见源码> |
| `continuity_seam_missing` | error | <动态生成，见源码> |
| `continuity_seam_not_verified` | error | <动态生成，见源码> |
| `continuity_seam_cut_missing` | error | <动态生成，见源码> |
| `continuity_seam_window_invalid` | error | <动态生成，见源码> |
