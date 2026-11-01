# lint 检查合同 · common 阶段

> 由 build_lint_contract.py 从实际 STAGE_CHECKS 与共享调用图生成；禁止手改。
> 只证明结构、来源、算术、依赖与技术合同；内容须按观看顺序独立审校。

common 随生产阶段运行；skill 使用 `--stage skill`。

轻量走同一内核和单任务预检适配，不要求伪造完整模式上游。

| 检查码 | 级别 | 查什么 | 来源 |
|---|---|---|---|
| `aggregate_current_phase_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `aggregate_future_phase_started` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `aggregate_phase_confirmed_early` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `aggregate_phase_status_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `aggregate_previous_phase_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `audience_plan_execution_sources_invalid` | error | audience_plan.execution_sources 必须逐项锁定四个 audience_execution 源字段。 | `drama_lint.check_plan_durations` |
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
| `creative_mechanism_candidates_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_plan_durations` |
| `creative_mechanism_missing` | error | drama_plan 必须填写 creative_mechanism。 | `drama_lint.check_plan_durations` |
| `creative_mechanism_primary_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_plan_durations` |
| `creative_mechanism_selected_missing` | error | creative_mechanism.primary 必须锁定唯一主机制。 | `drama_lint.check_plan_durations` |
| `creative_mechanism_selected_supporting_invalid` | error | creative_mechanism.supporting 必须是实际辅助机制列表，可空。 | `drama_lint.check_plan_durations` |
| `creative_mechanism_selected_unknown` | error | creative_mechanism.primary 必须来自当前候选主机制之一。 | `drama_lint.check_plan_durations` |
| `creative_mechanism_selection_mode_invalid` | error | creative_mechanism.selection_mode 必须为 divergent 或 user_locked。 | `drama_lint.check_plan_durations` |
| `creative_mechanism_supporting_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_plan_durations` |
| `current_episode_invalid` | error | 逐集生产阶段必须把 current_episode 指向计划内分集。 | `drama_lint.check_state` |
| `current_episode_must_be_empty` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `current_episode_script_incomplete` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `current_phase_status_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `current_stage_beyond_target` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `current_stage_invalid` | error | current_stage 不是有效阶段。 | `drama_lint.check_state` |
| `duration_contract_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_plan_durations` |
| `duration_contract_invalid` | error | 时长合同枚举无效。 | `drama_lint.check_plan_durations` |
| `duration_contract_missing` | error | 新制作需显式登记 unbounded/exact/target_band 及真实来源。 | `drama_lint.check_plan_durations` |
| `duration_contract_source_invalid` | error | 真实时长约束须回指同 scope/数值/性质的实际确认，不由估时推断。 | `drama_lint.check_plan_durations` |
| `duration_contract_unbounded_invalid` | error | 未限定时 target/tolerance/bounds 需 null。 | `drama_lint.check_plan_durations` |
| `duration_display_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_duration_pair` |
| `duration_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_duration_pair` |
| `episode_confirmation_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_confirmation_missing_episode_id` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `episode_count_invalid` | error | episode_count 必须是正整数。 | `drama_lint.check_plan_durations` |
| `episode_current_phase_status_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_directory_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_episode_directories` |
| `episode_directory_unplanned` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_episode_directories` |
| `episode_duration_displays_invalid` | error | episode_duration_displays 数量必须等于 episode_count。 | `drama_lint.check_plan_durations` |
| `episode_duration_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_plan_durations` |
| `episode_durations_invalid` | error | episode_durations_s 数量必须等于 episode_count。 | `drama_lint.check_plan_durations` |
| `episode_future_phase_status_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_id_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_id_mismatch` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_episode_entry_manifests` |
| `episode_phase_merged_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_phase_order_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_schema_unsupported` | error | episode manifest 的 schema_version 必须为 1.1。 | `drama_lint.check_episode_entry_manifests` |
| `episode_script_confirmation_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_script_started_before_global_confirmation` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_stage_before_planning_confirmed` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_stage_before_script_confirmed` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_stage_status_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_stage_statuses_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_stage_statuses_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_states_invalid` | error | 制作状态.json.episodes 必须是对象并覆盖全部计划分集。 | `drama_lint.check_state` |
| `episode_states_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `episode_states_unplanned` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `file_missing` | error | 缺少流程所需文件。 | `drama_lint.load_json` |
| `final_deliverables_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_plan_durations` |
| `forbidden_media_tool_used` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_operation_log_tools` |
| `future_episode_script_started_early` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `future_episode_started_early` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `future_phase_status_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `interaction_call_id_reused` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `json_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_json` |
| `lightweight_scope_invalid` | error | lightweight 只允许单集；实际单条请求须由当前设计核算，并符合真实接口能力，不能按规划估时判断。 | `drama_lint.check_state` |
| `operation_log_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_operation_log_tools` |
| `phase_confirmation_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `phase_merged_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `phase_order_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `phase_status_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `phases_invalid` | error | phases 必须是对象。 | `drama_lint.check_state` |
| `plan_revision_invalid` | error | drama_plan.revision 必须是正整数。 | `drama_lint.check_plan_durations` |
| `planning_interaction_confirmation_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `planning_schema_unsupported` | error | planning 的 schema_version 必须为 1.1。 | `drama_lint.check_plan_durations` |
| `previous_episode_beyond_target` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `previous_episode_incomplete` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_state` |
| `project_confirmation_has_episode` | error | 动态消息；按当前对象及源码核对 | `drama_lint.load_confirmation_records` |
| `project_prerequisite_not_confirmed` | error | 进入逐集生产前 phases.planning 必须为 confirmed。 | `drama_lint.check_state` |
| `project_prerequisite_not_confirmed` | error | 进入逐集生产前项目级 phases.script 必须为 confirmed；合法轻量模式可为 merged。 | `drama_lint.check_state` |
| `rhythm_design_invalid` | error | rhythm_design 是可选定性观看意图。 | `drama_lint.check_plan_durations` |
| `scale_plan_missing` | error | drama_plan 缺少 scale_plan。 | `drama_lint.check_plan_durations` |
| `selected_direction_missing` | error | drama_plan 必须锁定 selected_direction_id。 | `drama_lint.check_plan_durations` |
| `stage_manifest_path_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_episode_entry_manifests` |
| `stage_manifests_missing` | error | episode_manifest 必须使用顶层 stage_manifests 保存阶段文件指针。 | `drama_lint.check_episode_entry_manifests` |
| `subtitle_disabled_policy_missing` | error | 字幕关闭时 subtitle_policy 必须为 disabled。 | `drama_lint.check_plan_durations` |
| `subtitle_enabled_invalid` | error | delivery_settings.subtitle_enabled 必须是布尔值；默认 false，用户明确要求字幕时为 true。 | `drama_lint.check_plan_durations` |
| `target_stage_invalid` | error | drama_plan.objective.target_stage 必须是有效阶段。 | `drama_lint.check_plan_durations` |
| `target_stage_invalid` | error | drama_plan.objective.target_stage 必须是有效阶段。 | `drama_lint.check_state` |
| `timing_budget_input_forbidden` | error | 规划不得预分配时间。 | `drama_lint.check_plan_durations` |
| `total_duration_invalid` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_plan_durations` |
| `total_duration_mismatch` | error | total_duration_s 必须等于各集 episode_durations_s 之和。 | `drama_lint.check_plan_durations` |
