# lint 检查合同 · final 阶段

> 由 build_lint_contract.py 从实际 STAGE_CHECKS 与共享调用图生成；按需读取。
> 只证明结构、来源、算术、依赖与技术合同；内容须按观看顺序独立审校。

本卡是增量卡，仅列成片（delivery）阶段自有检查；与 common/video/keyframes/storyboard/assets 等前序阶段共享的完整联合视图用 `python scripts/build_lint_contract.py --rules final` 动态获取，单条报错的完整说明仍用 `python scripts/build_lint_contract.py --code <检查码>`。

运行：`python scripts/drama_lint.py <skill-root> --project-root <project> --stage final`。

| 检查码 | 级别 | 查什么 | 来源 |
|---|---|---|---|
| `adopted_cut_out_invalid` | error | adopted_segments 必须是实际采用区间数组 | `lint_checks.delivery.check_adopted_delivery`（305–328，触发 314） |
| `adopted_cut_out_invalid` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `lint_checks.delivery.check_adopted_delivery`（305–328，触发 328） |
| `adopted_cut_out_invalid` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `lint_checks.delivery.check_continuity_for_delivery`（107–170，触发 164） |
| `assembly_confirmation_call_id_missing` | error | assembly_confirmation 必须记录 interaction_ask_call_id。 | `lint_checks.delivery.check_delivery`（173–302，触发 194） |
| `assembly_confirmation_missing` | error | delivery_manifest 必须登记进入成片拼接的 interaction.ask 确认。 | `lint_checks.delivery.check_delivery`（173–302，触发 189） |
| `assembly_confirmation_purpose_invalid` | error | assembly_confirmation.confirmation_purpose 必须为 final_assembly。 | `lint_checks.delivery.check_delivery`（173–302，触发 192） |
| `assembly_confirmation_result_invalid` | error | assembly_confirmation.interaction_ask_result 必须为 proceed_assembly。 | `lint_checks.delivery.check_delivery`（173–302，触发 196） |
| `assembly_confirmation_segments_mismatch` | error | assembly_confirmation.segment_ids 必须按顺序精确等于当前成片采用的 accepted SEG。 | `lint_checks.delivery.check_delivery`（173–302，触发 276） |
| `assembly_confirmation_time_invalid` | error | assembly_confirmation.confirmed_at 必须是带时区 ISO-8601 时间。 | `lint_checks.delivery.check_delivery`（173–302，触发 200） |
| `assembly_confirmation_user_message_missing` | error | assembly_confirmation.user_message 不能为空。 | `lint_checks.delivery.check_delivery`（173–302，触发 198） |
| `assembly_confirmation_video_record_missing` | error | assembly_confirmation 必须与同集 stage=video 用户确认记录使用同一 interaction.ask 调用 ID 和 proceed_assembly 结果。 | `lint_checks.delivery.check_delivery`（173–302，触发 212） |
| `basic_qc_report_blocked` | error | 基础媒体可用性检查结果为 blocked，不得交付。 | `lint_checks.delivery.check_report_entries`（87–104，触发 104） |
| `basic_qc_report_invalid` | error | basic_qc_reports 每项必须是路径或对象。 | `lint_checks.delivery.check_report_entries`（87–104，触发 102） |
| `basic_qc_report_missing` | error | 基础质检报告不存在：{entry} | `lint_checks.delivery.check_report_entries`（87–104，触发 96） |
| `basic_qc_report_missing` | error | 基础质检报告不存在：{report_file} | `lint_checks.delivery.check_report_entries`（87–104，触发 100） |
| `basic_qc_reports_count_invalid` | error | basic_qc_reports 数量应为 {expected_count}。 | `lint_checks.delivery.check_report_entries`（87–104，触发 92） |
| `basic_qc_reports_invalid` | error | basic_qc_reports 必须是数组。 | `lint_checks.delivery.check_delivery`（173–302，触发 256） |
| `basic_qc_reports_invalid` | error | basic_qc_reports 必须是数组。 | `lint_checks.delivery.check_report_entries`（87–104，触发 89） |
| `clean_master_missing` | error | clean_master 必须指向当前分集目录下真实媒体文件。 | `lint_checks.delivery.check_delivery`（173–302，触发 237） |
| `continuity_frame_file_missing` | error | 连续性抽帧文件不存在：{file_value} | `lint_checks.delivery.check_continuity_for_delivery`（107–170，触发 129） |
| `continuity_frame_roles_missing` | error | {segment_id} 连续性抽帧缺少 start\|scene\|tail：{missing}。 | `lint_checks.delivery.check_continuity_for_delivery`（107–170，触发 136） |
| `continuity_frame_suffix_invalid` | error | 连续性抽帧必须是图片文件：{file_value} | `lint_checks.delivery.check_continuity_for_delivery`（107–170，触发 131） |
| `continuity_frames_invalid` | error | continuity.frames 必须是数组。 | `lint_checks.delivery.check_continuity_for_delivery`（107–170，触发 117） |
| `continuity_seam_cut_missing` | error | {left} -> {right} 关键接缝缺少 selected_cut。 | `lint_checks.delivery.check_continuity_for_delivery`（107–170，触发 166） |
| `continuity_seam_missing` | error | 缺少 {left} -> {right} 的 seam 记录。 | `lint_checks.delivery.check_continuity_for_delivery`（107–170，触发 149） |
| `continuity_seam_not_verified` | error | {left} -> {right} seam 必须通过检查后才能作为合格成片接缝。 | `lint_checks.delivery.check_continuity_for_delivery`（107–170，触发 152） |
| `continuity_seam_window_invalid` | error | {left} -> {right} {field} 必须至少覆盖 12 帧，才能验证并选定安全剪切点。 | `lint_checks.delivery.check_continuity_for_delivery`（107–170，触发 170） |
| `continuity_seams_invalid` | error | continuity.seams 必须是数组。 | `lint_checks.delivery.check_continuity_for_delivery`（107–170，触发 139） |
| `delivery_duration_invalid` | error | delivery_manifest.duration_s 必须是数字。 | `lint_checks.delivery.check_delivery`（173–302，触发 235） |
| `delivery_duration_out_of_contract` | error | {label} 实测 {value}s 不在 duration_contract {mode} 范围 [{lower}, {upper}]s；不得以计划时长代替实测。 | `lint_checks.delivery.check_delivery`（173–302，触发 302） |
| `delivery_non_accepted_segment` | error | delivery 使用了未验收（accepted）的视频片段：{segment_id} | `lint_checks.delivery.check_delivery`（173–302，触发 279） |
| `delivery_quality_gate_blockers_invalid` | error | content_quality_gate.blockers 必须是数组。 | `lint_checks.delivery.check_delivery`（173–302，触发 224） |
| `delivery_quality_gate_invalid` | error | delivery_manifest 必须记录 content_quality_gate。 | `lint_checks.delivery.check_delivery`（173–302，触发 220） |
| `delivery_status_not_deliverable` | error | delivery_manifest.status 必须为 deliverable 或 candidate；blocked 不得交付。 | `lint_checks.delivery.check_delivery`（173–302，触发 217） |
| `delivery_without_quality_pass` | error | deliverable 必须通过整片内容质量门且无阻断项。 | `lint_checks.delivery.check_delivery`（173–302，触发 227） |
| `duration_contract_invalid` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `lint_checks.delivery.check_delivery`（173–302，触发 290） |
| `duration_display_invalid` | error | {label} duration_display 应为 {expected}。 | `lint_checks.common.check_duration_pair`（182–197，触发 197） |
| `duration_invalid` | error | {label} duration_s 必须是数字。 | `lint_checks.common.check_duration_pair`（182–197，触发 192） |
| `episode_id_mismatch` | error | continuity episode_id 与目录不一致。 | `lint_checks.delivery.check_continuity_for_delivery`（107–170，触发 113） |
| `episode_id_mismatch` | error | delivery_manifest episode_id 与目录不一致。 | `lint_checks.delivery.check_delivery`（173–302，触发 186） |
| `outputs_invalid` | error | outputs 必须是路径数组，或每项包含 file。 | `lint_checks.delivery.check_delivery`（173–302，触发 246） |
| `outputs_mismatch` | error | outputs 必须与用户可见正式交付文件精确一致：字幕关闭时只交付 [clean_master]。 | `lint_checks.delivery.check_delivery`（173–302，触发 248） |
| `outputs_mismatch` | error | outputs 必须与用户可见正式交付文件精确一致：字幕开启时只交付 [subtitle_master]。 | `lint_checks.delivery.check_delivery`（173–302，触发 250） |
| `subtitle_alignment_report_invalid` | error | subtitle_alignment_report 必须指向当前分集目录下未 blocked 的内部追溯文件。 | `lint_checks.delivery.check_delivery`（173–302，触发 262） |
| `subtitle_alignment_report_missing` | error | 字幕开启时必须存在 subtitle_alignment_report（字幕对齐报告）。 | `lint_checks.delivery.check_delivery`（173–302，触发 260） |
| `subtitle_disabled_field_not_empty` | error | 字幕关闭时 {field} 必须留空。 | `lint_checks.delivery.check_delivery`（173–302，触发 243） |
| `subtitle_enabled_invalid` | error | subtitle_enabled 必须是布尔值；默认 false，用户明确要求字幕时为 true。 | `lint_checks.delivery.check_delivery`（173–302，触发 215） |
| `subtitle_final_missing` | error | 字幕开启时必须存在当前分集目录下的 subtitle_final。 | `lint_checks.delivery.check_delivery`（173–302，触发 270） |
| `subtitle_final_name_invalid` | error | subtitle_final 应指向 字幕_最终版_vNN_ep_N.json。 | `lint_checks.delivery.check_delivery`（173–302，触发 272） |
| `subtitle_master_missing` | error | 字幕开启时 subtitle_master 必须指向当前分集目录下真实媒体文件。 | `lint_checks.delivery.check_delivery`（173–302，触发 239） |
| `subtitle_source_missing` | error | 字幕开启时必须存在当前分集目录下的 subtitle_source。 | `lint_checks.delivery.check_delivery`（173–302，触发 265） |
| `subtitle_source_name_invalid` | error | subtitle_source 应指向 字幕_时间轴_vNN_ep_N.srt。 | `lint_checks.delivery.check_delivery`（173–302，触发 267） |
