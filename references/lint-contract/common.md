# lint 检查合同 · common 阶段

> 本卡片由 `scripts/build_lint_contract.py` 从 `drama_lint.py` 机读生成，禁止手改。
> 用途：开工前读这张卡知道本阶段 lint 会查什么；报错后按码查修复方向。
> 与源码不一致时以源码为准，并重跑 `python scripts/build_lint_contract.py --check`。

本阶段新增检查项：83。运行命令：`python scripts/drama_lint.py --stage common`（skill 阶段在 skill 根目录运行）。

| 检查码 | 级别 | 查什么（源码原文消息） |
|---|---|---|
| `episode_directory_missing` | error | <动态生成，见源码> |
| `episode_directory_unplanned` | error | <动态生成，见源码> |
| `episode_id_mismatch` | error | <动态生成，见源码> |
| `stage_manifests_missing` | error | episode_manifest 必须使用顶层 stage_manifests，不得使用旧字段 manifests。 |
| `stage_manifest_path_invalid` | error | <动态生成，见源码> |
| `current_stage_invalid` | error | current_stage 不是有效阶段。 |
| `phases_invalid` | error | phases 必须是对象。 |
| `target_stage_invalid` | error | drama_plan.objective.target_stage 必须是有效阶段。 |
| `lightweight_scope_invalid` | error | lightweight 只允许单集，且总时长不得超过当前视频模型轻量上限：seedance 2.0 系列 15 秒，seedance 2.5 为 30 秒。 |
| `episode_states_invalid` | error | 制作状态.json.episodes 必须是对象并覆盖全部计划分集。 |
| `phase_status_invalid` | error | <动态生成，见源码> |
| `current_episode_must_be_empty` | error | <动态生成，见源码> |
| `phase_confirmation_missing` | error | <动态生成，见源码> |
| `episode_states_missing` | error | <动态生成，见源码> |
| `episode_states_unplanned` | error | <动态生成，见源码> |
| `phase_order_invalid` | error | <动态生成，见源码> |
| `future_phase_status_invalid` | error | <动态生成，见源码> |
| `phase_merged_invalid` | error | <动态生成，见源码> |
| `current_episode_invalid` | error | 逐集生产阶段必须把 current_episode 指向计划内分集。 |
| `current_stage_beyond_target` | error | <动态生成，见源码> |
| `project_prerequisite_not_confirmed` | error | 进入逐集生产前 phases.planning 必须为 confirmed。 |
| `project_prerequisite_not_confirmed` | error | 进入逐集生产前项目级 phases.script 必须为 confirmed；合法轻量模式可为 merged。 |
| `episode_id_invalid` | error | <动态生成，见源码> |
| `episode_stage_statuses_invalid` | error | <动态生成，见源码> |
| `episode_stage_statuses_missing` | error | <动态生成，见源码> |
| `aggregate_phase_confirmed_early` | error | <动态生成，见源码> |
| `current_phase_status_invalid` | error | <动态生成，见源码> |
| `episode_stage_status_invalid` | error | <动态生成，见源码> |
| `episode_phase_merged_invalid` | error | <动态生成，见源码> |
| `episode_confirmation_missing` | error | <动态生成，见源码> |
| `aggregate_phase_status_mismatch` | error | <动态生成，见源码> |
| `episode_stage_before_planning_confirmed` | error | <动态生成，见源码> |
| `episode_script_started_before_global_confirmation` | error | <动态生成，见源码> |
| `episode_script_confirmation_missing` | error | <动态生成，见源码> |
| `aggregate_current_phase_mismatch` | error | <动态生成，见源码> |
| `aggregate_future_phase_started` | error | <动态生成，见源码> |
| `episode_stage_before_script_confirmed` | error | <动态生成，见源码> |
| `aggregate_previous_phase_invalid` | error | <动态生成，见源码> |
| `future_episode_script_started_early` | error | <动态生成，见源码> |
| `current_episode_script_incomplete` | error | <动态生成，见源码> |
| `previous_episode_incomplete` | error | <动态生成，见源码> |
| `previous_episode_beyond_target` | error | <动态生成，见源码> |
| `future_episode_started_early` | error | <动态生成，见源码> |
| `episode_phase_order_invalid` | error | <动态生成，见源码> |
| `episode_future_phase_status_invalid` | error | <动态生成，见源码> |
| `episode_current_phase_status_invalid` | error | <动态生成，见源码> |
| `operation_log_unreadable` | error | <动态生成，见源码> |
| `forbidden_media_tool_used` | error | <动态生成，见源码> |
| `plan_revision_invalid` | error | drama_plan.revision 必须是正整数。 |
| `selected_direction_missing` | error | drama_plan 必须锁定 selected_direction_id。 |
| `creative_mechanism_missing` | error | drama_plan 必须填写 creative_mechanism。 |
| `rhythm_design_missing` | error | drama_plan 必须填写六步推导后的 rhythm_design。 |
| `scale_plan_missing` | error | drama_plan 缺少 scale_plan。 |
| `episode_count_invalid` | error | episode_count 必须是正整数。 |
| `episode_durations_invalid` | error | episode_durations_s 数量必须等于 episode_count。 |
| `episode_duration_displays_invalid` | error | episode_duration_displays 数量必须等于 episode_count。 |
| `total_duration_invalid` | error | total_duration_s 必须是数字。 |
| `duration_contract_missing_legacy` | warning | 旧版 drama_plan 未登记 duration_contract；新项目必须显式写 target_band/exact/unbounded，存量项目暂按旧计划解释。 |
| `creative_mechanism_selection_mode_invalid` | error | creative_mechanism.selection_mode 必须为 divergent 或 user_locked。 |
| `creative_mechanism_candidates_invalid` | error | <动态生成，见源码> |
| `creative_mechanism_selected_missing` | error | creative_mechanism.primary 必须锁定唯一主机制。 |
| `creative_mechanism_selected_supporting_invalid` | error | creative_mechanism.supporting 必须保留 1-3 个辅助机制。 |
| `rhythm_intensity_invalid` | error | rhythm_design.intensity_sequence 只能是 1-5 的整数数组，如 [3,2,4]。 |
| `<动态码，见源码>` | error | <动态生成，见源码> |
| `episode_duration_invalid` | error | <动态生成，见源码> |
| `total_duration_mismatch` | error | total_duration_s 必须等于各集 episode_durations_s 之和。 |
| `duration_contract_invalid` | error | duration_contract.mode/scope 必须是有效枚举。 |
| `subtitle_enabled_invalid` | error | delivery_settings.subtitle_enabled 必须是布尔值；默认 false，用户明确要求字幕时为 true。 |
| `subtitle_disabled_policy_missing` | error | 字幕关闭时 subtitle_policy 必须为 disabled。 |
| `final_deliverables_invalid` | error | <动态生成，见源码> |
| `creative_mechanism_selected_unknown` | error | creative_mechanism.primary 必须来自当前候选主机制之一。 |
| `rhythm_design_field_missing` | error | <动态生成，见源码> |
| `audience_plan_execution_sources_invalid` | error | audience_plan.execution_sources 必须逐项锁定四个 audience_execution 源字段。 |
| `creative_mechanism_primary_missing` | error | <动态生成，见源码> |
| `creative_mechanism_supporting_invalid` | error | <动态生成，见源码> |
| `duration_contract_unbounded_invalid` | error | unbounded 模式的 target_duration_s/tolerance_ratio 必须为 null。 |
| `duration_contract_target_invalid` | error | target_band/exact 必须提供正数 target_duration_s。 |
| `duration_contract_exact_invalid` | error | exact 模式 tolerance_ratio 必须为 0。 |
| `duration_contract_tolerance_invalid` | error | target_band tolerance_ratio 必须在 [0,1)；默认 0.10。 |
| `planned_duration_out_of_contract` | error | <动态生成，见源码> |
