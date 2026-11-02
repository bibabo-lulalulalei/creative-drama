# lint 检查合同 · common 阶段

> 由 build_lint_contract.py 从实际 STAGE_CHECKS 与共享调用图生成；按需读取。
> 只证明结构、来源、算术、依赖与技术合同；内容须按观看顺序独立审校。

common 随各生产阶段运行；请使用当前生产阶段的 `--stage`，CLI 不接受 `--stage common`。

| 检查码 | 级别 | 查什么 | 来源 |
|---|---|---|---|
| `aggregate_current_phase_mismatch` | error | phases.{stage} 必须与 {current_episode}.{stage} 当前活动状态一致。 | `lint_checks.state.check_state`（158–356，触发 352） |
| `aggregate_future_phase_started` | error | phases.{stage} 与已完成分集的聚合状态不一致。 | `lint_checks.state.check_state`（158–356，触发 354） |
| `aggregate_phase_confirmed_early` | error | phases.{stage} 只有在全部分集该阶段完成后才能写 confirmed。 | `lint_checks.state.check_state`（158–356，触发 326） |
| `aggregate_phase_status_mismatch` | error | phases.{stage} 必须反映全部分集已完成。 | `lint_checks.state.check_state`（158–356，触发 348） |
| `aggregate_previous_phase_invalid` | error | phases.{stage} 已有分集完成但尚未全量完成，必须保持 in_progress 或合法完成态。 | `lint_checks.state.check_state`（158–356，触发 356） |
| `audience_plan_execution_sources_invalid` | error | audience_plan.execution_sources 必须逐项锁定四个 audience_execution 源字段。 | `lint_checks.planning.check_plan_durations`（13–159，触发 91） |
| `audience_plan_field_missing` | error | audience_plan.{field} 必须填写。 | `lint_checks.planning.check_plan_durations`（13–159，触发 81） |
| `audience_plan_missing` | error | drama_plan 缺少 audience_plan。 | `lint_checks.planning.check_plan_durations`（13–159，触发 77） |
| `confirmation_base_revision_invalid` | error | 用户确认记录第 {line_number} 行 incremental 必须填写整数 base_revision。 | `lint_checks.state.load_confirmation_records`（18–111，触发 81） |
| `confirmation_base_revision_missing` | error | 用户确认记录第 {line_number} 行找不到同阶段对应的全量确认 base_revision。 | `lint_checks.state.load_confirmation_records`（18–111，触发 83） |
| `confirmation_changed_artifacts_missing` | error | 用户确认记录第 {line_number} 行 incremental 必须填写 changed_artifacts。 | `lint_checks.state.load_confirmation_records`（18–111，触发 85） |
| `confirmation_decision_invalid` | error | 用户确认记录第 {line_number} 行 decision 必须是 confirmed。 | `lint_checks.state.load_confirmation_records`（18–111，触发 61） |
| `confirmation_episode_id_invalid` | error | 用户确认记录第 {line_number} 行 episode_id 无效。 | `lint_checks.state.load_confirmation_records`（18–111，触发 55） |
| `confirmation_impact_scope_missing` | error | 用户确认记录第 {line_number} 行 incremental 必须填写 impact_scope。 | `lint_checks.state.load_confirmation_records`（18–111，触发 87） |
| `confirmation_log_blank_line` | error | 用户确认记录第 {line_number} 行为空行。 | `lint_checks.state.load_confirmation_records`（18–111，触发 40） |
| `confirmation_log_json_invalid` | error | 用户确认记录第 {line_number} 行不是有效 JSON：{exc} | `lint_checks.state.load_confirmation_records`（18–111，触发 45） |
| `confirmation_log_missing` | error | 阶段已确认或推进到后续阶段时必须存在用户确认记录。 | `lint_checks.state.load_confirmation_records`（18–111，触发 29） |
| `confirmation_log_row_invalid` | error | 用户确认记录第 {line_number} 行必须是对象。 | `lint_checks.state.load_confirmation_records`（18–111，触发 48） |
| `confirmation_log_unreadable` | error | 用户确认记录无法读取：{exc} | `lint_checks.state.load_confirmation_records`（18–111，触发 32） |
| `confirmation_mode_invalid` | error | 用户确认记录第 {line_number} 行 confirmation_mode 无效。 | `lint_checks.state.load_confirmation_records`（18–111，触发 63） |
| `confirmation_revision_invalid` | error | 用户确认记录第 {line_number} 行 revision 必须是整数。 | `lint_checks.state.load_confirmation_records`（18–111，触发 65） |
| `confirmation_stage_invalid` | error | 用户确认记录第 {line_number} 行 stage 无效。 | `lint_checks.state.load_confirmation_records`（18–111，触发 52） |
| `confirmation_time_invalid` | error | 用户确认记录第 {line_number} 行 confirmed_at 必须是带时区 ISO-8601 时间。 | `lint_checks.state.load_confirmation_records`（18–111，触发 70） |
| `confirmation_user_message_missing` | error | 用户确认记录第 {line_number} 行 user_message 不能为空。 | `lint_checks.state.load_confirmation_records`（18–111，触发 67） |
| `creative_mechanism_candidates_invalid` | error | 当前 selection_mode 的 creative_mechanism.candidates 必须包含真实采用的候选。 | `lint_checks.planning.check_plan_durations`（13–159，触发 36） |
| `creative_mechanism_missing` | error | drama_plan 必须填写 creative_mechanism。 | `lint_checks.planning.check_plan_durations`（13–159，触发 27） |
| `creative_mechanism_primary_missing` | error | 创意机制候选 {index} 必须填写主机制。 | `lint_checks.planning.check_plan_durations`（13–159，触发 41） |
| `creative_mechanism_selected_missing` | error | creative_mechanism.primary 必须锁定唯一主机制。 | `lint_checks.planning.check_plan_durations`（13–159，触发 48） |
| `creative_mechanism_selected_supporting_invalid` | error | creative_mechanism.supporting 必须是实际辅助机制列表，可空。 | `lint_checks.planning.check_plan_durations`（13–159，触发 53） |
| `creative_mechanism_selected_unknown` | error | creative_mechanism.primary 必须来自当前候选主机制之一。 | `lint_checks.planning.check_plan_durations`（13–159，触发 50） |
| `creative_mechanism_selection_mode_invalid` | error | creative_mechanism.selection_mode 必须为 divergent 或 user_locked。 | `lint_checks.planning.check_plan_durations`（13–159，触发 31） |
| `creative_mechanism_supporting_invalid` | error | 创意机制候选 {index} supporting 必须是实际辅助机制列表，可空。 | `lint_checks.planning.check_plan_durations`（13–159，触发 45） |
| `current_episode_invalid` | error | 逐集生产阶段必须把 current_episode 指向计划内分集。 | `lint_checks.state.check_state`（158–356，触发 205） |
| `current_episode_must_be_empty` | error | current_stage={current} 时 current_episode 必须为空。 | `lint_checks.state.check_state`（158–356，触发 187） |
| `current_episode_script_incomplete` | error | {episode_id}.script 必须在后续生产前确认为 confirmed。 | `lint_checks.state.check_state`（158–356，触发 287） |
| `current_phase_status_invalid` | error | {stage} 是 current_stage，状态不能是 {value}。 | `lint_checks.state.check_state`（158–356，触发 200） |
| `current_stage_beyond_target` | error | current_stage={current} 不得晚于 objective.target_stage={target}。 | `lint_checks.state.check_state`（158–356，触发 207） |
| `current_stage_invalid` | error | current_stage 不是有效阶段。 | `lint_checks.state.check_state`（158–356，触发 167） |
| `duration_contract_invalid` | error | 时长合同枚举无效。 | `lint_checks.planning.check_plan_durations`（13–159，触发 138） |
| `duration_contract_invalid` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `lint_checks.planning.check_plan_durations`（13–159，触发 135） |
| `duration_contract_missing` | error | 新制作需显式登记 unbounded/exact/target_band 及真实来源。 | `lint_checks.planning.check_plan_durations`（13–159，触发 130） |
| `duration_contract_source_invalid` | error | 真实时长约束须回指同 scope/数值/性质的实际确认，不由估时推断。 | `lint_checks.planning.check_plan_durations`（13–159，触发 148） |
| `duration_contract_unbounded_invalid` | error | 未限定时 target/tolerance/bounds 需 null。 | `lint_checks.planning.check_plan_durations`（13–159，触发 141） |
| `duration_display_invalid` | error | {label} duration_display 应为 {expected}。 | `lint_checks.common.check_duration_pair`（182–197，触发 197） |
| `duration_invalid` | error | {label} duration_s 必须是数字。 | `lint_checks.common.check_duration_pair`（182–197，触发 192） |
| `episode_confirmation_missing` | error | {episode_id}.{stage} 已 confirmed，但缺少绑定该集的有效确认记录。 | `lint_checks.state.check_state`（158–356，触发 316） |
| `episode_confirmation_missing_episode_id` | error | 用户确认记录第 {line_number} 行 {stage} 阶段必须填写 episode_id。 | `lint_checks.state.load_confirmation_records`（18–111，触发 59） |
| `episode_count_invalid` | error | episode_count 必须是正整数。 | `lint_checks.planning.check_plan_durations`（13–159，触发 102） |
| `episode_current_phase_status_invalid` | error | {episode_id}.{stage} 是当前集阶段，状态不能是 {value}。 | `lint_checks.state.check_state`（158–356，触发 301） |
| `episode_directory_missing` | error | 计划内分集缺少目录：{missing} | `lint_checks.stages.check_episode_directories`（14–25，触发 23） |
| `episode_directory_unplanned` | error | 存在计划外分集目录：{extra} | `lint_checks.stages.check_episode_directories`（14–25，触发 25） |
| `episode_duration_displays_invalid` | error | episode_duration_displays 数量必须等于 episode_count。 | `lint_checks.planning.check_plan_durations`（13–159，触发 108） |
| `episode_duration_invalid` | error | 第 {index} 集规划预测无效：{exc}。 | `lint_checks.planning.check_plan_durations`（13–159，触发 114） |
| `episode_durations_invalid` | error | episode_durations_s 数量必须等于 episode_count。 | `lint_checks.planning.check_plan_durations`（13–159，触发 105） |
| `episode_future_phase_status_invalid` | error | {episode_id}.{stage} 晚于当前集 current_stage={current}，只能是 pending 或 invalidated。 | `lint_checks.state.check_state`（158–356，触发 294） |
| `episode_id_invalid` | error | 分集 ID 无效：{episode_id} | `lint_checks.state.check_state`（158–356，触发 241） |
| `episode_id_mismatch` | error | episode_manifest episode_id 必须等于目录 ID：{episode_id} | `lint_checks.stages.check_episode_entry_manifests`（38–61，触发 45） |
| `episode_phase_order_invalid` | error | {episode_id}.{stage} 应先完成后再进入 {current}。 | `lint_checks.state.check_state`（158–356，触发 292） |
| `episode_script_confirmation_missing` | error | {episode_id}.script 已 confirmed，但缺少绑定该集的详细剧本确认记录。 | `lint_checks.state.check_state`（158–356，触发 307） |
| `episode_script_started_before_global_confirmation` | error | {episode_id}.script 在项目级故事包确认前只能是 pending 或 invalidated。 | `lint_checks.state.check_state`（158–356，触发 261） |
| `episode_stage_before_planning_confirmed` | error | 项目仍在 planning，{episode_id}.{stage} 只能是 pending 或 invalidated。 | `lint_checks.state.check_state`（158–356，触发 257） |
| `episode_stage_before_script_confirmed` | error | 项目级故事包尚未确认，{episode_id}.{stage} 只能是 pending 或 invalidated。 | `lint_checks.state.check_state`（158–356，触发 265） |
| `episode_stage_status_invalid` | error | {episode_id}.{stage} 状态无效。 | `lint_checks.state.check_state`（158–356，触发 252） |
| `episode_stage_statuses_invalid` | error | {episode_id}.stage_status 必须是对象。 | `lint_checks.state.check_state`（158–356，触发 244） |
| `episode_stage_statuses_missing` | error | {episode_id}.stage_status 缺少阶段：{missing_stages} | `lint_checks.state.check_state`（158–356，触发 248） |
| `episode_states_invalid` | error | 制作状态.json.episodes 必须是对象并覆盖全部计划分集。 | `lint_checks.state.check_state`（158–356，触发 227） |
| `episode_states_missing` | error | 制作状态.json.episodes 缺少计划分集：{missing} | `lint_checks.state.check_state`（158–356，触发 235） |
| `episode_states_unplanned` | error | 制作状态.json.episodes 包含计划外分集：{extra} | `lint_checks.state.check_state`（158–356，触发 237） |
| `file_missing` | error | 缺少流程所需文件。 | `lint_checks.common.load_json`（22–30，触发 27） |
| `final_deliverables_invalid` | error | final_deliverables 必须只包含单一最终视频版本：{expected_deliverables}。 | `lint_checks.planning.check_plan_durations`（13–159，触发 158） |
| `forbidden_media_tool_used` | error | 操作日志第 {line_number} 行登记了禁用工具 {tool_name}；媒体处理必须使用 tools/video/ffmpeg_tool.py 本地链路。 | `lint_checks.state.check_operation_log_tools`（114–134，触发 134） |
| `future_episode_script_started_early` | error | {episode_id}.script 在该集开始制作前只能是 pending 或 invalidated。 | `lint_checks.state.check_state`（158–356，触发 280） |
| `future_episode_started_early` | error | {episode_id}.{stage} 在 {current_episode} 达到目标前只能是 pending 或 invalidated。 | `lint_checks.state.check_state`（158–356，触发 283） |
| `future_phase_status_invalid` | error | {stage} 晚于 current_stage={current}，只能是 pending 或 invalidated。 | `lint_checks.state.check_state`（158–356，触发 194） |
| `highlight_strategy_field_missing` | error | highlight_strategy.{field} 必须填写。 | `lint_checks.planning.check_plan_durations`（13–159，触发 81） |
| `highlight_strategy_missing` | error | drama_plan 缺少 highlight_strategy。 | `lint_checks.planning.check_plan_durations`（13–159，触发 77） |
| `interaction_call_id_reused` | error | 用户确认记录第 {line_number} 行 interaction_ask_call_id 已被其他用途使用。 | `lint_checks.state.load_confirmation_records`（18–111，触发 76） |
| `json_invalid` | error | JSON 无法读取或解析，后续关系无法确认：{exc} | `lint_checks.common.load_json`（22–30，触发 29） |
| `operation_log_unreadable` | error | 操作日志无法读取：{exc} | `lint_checks.state.check_operation_log_tools`（114–134，触发 121） |
| `phase_confirmation_missing` | error | {stage} 已 confirmed，但缺少{detail}的有效用户确认记录。 | `lint_checks.state.check_state`（158–356，触发 224） |
| `phase_order_invalid` | error | {stage} 应先完成后再进入 {current}。 | `lint_checks.state.check_state`（158–356，触发 192） |
| `phase_status_invalid` | error | {stage} 状态无效。 | `lint_checks.state.check_state`（158–356，触发 181） |
| `phases_invalid` | error | phases 必须是对象。 | `lint_checks.state.check_state`（158–356，触发 169） |
| `plan_revision_invalid` | error | drama_plan.revision 必须是正整数。 | `lint_checks.planning.check_plan_durations`（13–159，触发 19） |
| `planning_interaction_confirmation_missing` | error | 最新 planning 确认必须记录 project_execution、真实 interaction_ask_call_id 和 proceed_project。 | `lint_checks.state.load_confirmation_records`（18–111，触发 110） |
| `previous_episode_beyond_target` | error | {episode_id}.{stage} 超出 target_stage={target}，只能是 pending 或 invalidated。 | `lint_checks.state.check_state`（158–356，触发 277） |
| `previous_episode_incomplete` | error | {episode_id}.{stage} 必须完成后才能推进 {current_episode}。 | `lint_checks.state.check_state`（158–356，触发 275） |
| `project_confirmation_has_episode` | error | 用户确认记录第 {line_number} 行 planning 阶段不得填写 episode_id。 | `lint_checks.state.load_confirmation_records`（18–111，触发 57） |
| `project_prerequisite_not_confirmed` | error | 进入逐集生产前 phases.planning 必须为 confirmed。 | `lint_checks.state.check_state`（158–356，触发 209） |
| `project_prerequisite_not_confirmed` | error | 进入逐集生产前项目级 phases.script 必须为 confirmed。 | `lint_checks.state.check_state`（158–356，触发 211） |
| `rhythm_design_invalid` | error | rhythm_design 是可选定性观看意图。 | `lint_checks.planning.check_plan_durations`（13–159，触发 56） |
| `scale_plan_missing` | error | drama_plan 缺少 scale_plan。 | `lint_checks.planning.check_plan_durations`（13–159，触发 94） |
| `selected_direction_missing` | error | drama_plan 必须锁定 selected_direction_id。 | `lint_checks.planning.check_plan_durations`（13–159，触发 24） |
| `stage_manifest_path_invalid` | error | episode_manifest.stage_manifests.{stage} 必须指向 {expected_path}。 | `lint_checks.stages.check_episode_entry_manifests`（38–61，触发 61） |
| `stage_manifests_missing` | error | episode_manifest 必须使用顶层 stage_manifests 保存阶段文件指针。 | `lint_checks.stages.check_episode_entry_manifests`（38–61，触发 48） |
| `style_contract_field_missing` | error | style_contract.{field} 必须填写。 | `lint_checks.planning.check_plan_durations`（13–159，触发 81） |
| `style_contract_missing` | error | drama_plan 缺少 style_contract。 | `lint_checks.planning.check_plan_durations`（13–159，触发 77） |
| `subtitle_disabled_policy_missing` | error | 字幕关闭时 subtitle_policy 必须为 disabled。 | `lint_checks.planning.check_plan_durations`（13–159，触发 155） |
| `subtitle_enabled_invalid` | error | delivery_settings.subtitle_enabled 必须是布尔值；默认 false，用户明确要求字幕时为 true。 | `lint_checks.planning.check_plan_durations`（13–159，触发 153） |
| `target_stage_invalid` | error | drama_plan.objective.target_stage 必须是有效阶段。 | `lint_checks.planning.check_plan_durations`（13–159，触发 22） |
| `target_stage_invalid` | error | drama_plan.objective.target_stage 必须是有效阶段。 | `lint_checks.state.check_state`（158–356，触发 175） |
| `timing_budget_input_forbidden` | error | 规划不得预分配时间。 | `lint_checks.planning.check_plan_durations`（13–159，触发 58） |
| `total_duration_invalid` | error | total_duration_s 规划预测无效：{exc}。 | `lint_checks.planning.check_plan_durations`（13–159，触发 123） |
| `total_duration_mismatch` | error | total_duration_s 必须等于各集 episode_durations_s 之和。 | `lint_checks.planning.check_plan_durations`（13–159，触发 126） |
| `type_strategy_field_missing` | error | type_strategy.{field} 必须填写。 | `lint_checks.planning.check_plan_durations`（13–159，触发 81） |
| `type_strategy_missing` | error | drama_plan 缺少 type_strategy。 | `lint_checks.planning.check_plan_durations`（13–159，触发 77） |
