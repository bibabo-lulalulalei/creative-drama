# lint 检查合同 · storyboard 阶段

> 本卡片由 `scripts/build_lint_contract.py` 从 `drama_lint.py` 机读生成，禁止手改。
> 用途：开工前读这张卡知道本阶段 lint 会查什么；报错后按码查修复方向。
> 与源码不一致时以源码为准，并重跑 `python scripts/build_lint_contract.py --check`。

本阶段新增检查项：89。运行命令：`python scripts/drama_lint.py --stage storyboard`（skill 阶段在 skill 根目录运行）。

本阶段同时全量复核以下上游检查（报错时先读对应上游卡）：
- planning 阶段卡 · `check_stage_artifacts` —— storyboard 阶段产物存在性
- planning 阶段卡 · `check_episode_manifest_ids` —— episode_manifest 与 stage 绑定
- assets 阶段卡 · `check_assets` —— 资产索引（storyboard 阶段也全量复核）
- assets 阶段卡 · `validate_collective_profiles` —— 群像画像一致性

| 检查码 | 级别 | 查什么（源码原文消息） |
|---|---|---|
| `beat_library_unavailable` | error | <动态生成，见源码> |
| `h3_capabilities_unavailable` | info | <动态生成，见源码> |
| `beat_library_desync` | error | references/节拍类型库.md 缺失：本库已入库为唯一人类权威，缺失即安装破损；恢复该文件后重跑 build_beat_types.py 再执行 lint。 |
| `beat_library_desync` | error | <动态生成，见源码> |
| `duration_basis_missing` | error | <动态生成，见源码> |
| `rhythm_input_incomplete` | error | rhythm_input 缺少 scenes 数组（顶层结构不符）；语义输入表必须按 scenes[].shots[] 嵌套填写（schema 见 manifests.md「rhythm_input_ep_N.json」节），镜头写在... |
| `duration_basis_sum_mismatch` | warning | <动态生成，见源码> |
| `duration_basis_clone` | warning | <动态生成，见源码> |
| `rhythm_input_incomplete` | error | <动态生成，见源码> |
| `rhythm_input_missing` | error | <动态生成，见源码> |
| `rhythm_extremes_missing` | warning | <动态生成，见源码> |
| `rhythm_card_extremes_mismatch` | warning | <动态生成，见源码> |
| `beat_monoculture` | warning | <动态生成，见源码> |
| `engine_drift` | error | <动态生成，见源码> |
| `pack_drift` | error | <动态生成，见源码> |
| `spoken_text_missing` | warning | <动态生成，见源码> |
| `speech_overrun` | warning | <动态生成，见源码> |
| `rhythm_extremes_mismatch` | warning | <动态生成，见源码> |
| `segment_cap_uniformity` | info | <动态生成，见源码> |
| `beat_override_unconstrained` | warning | <动态生成，见源码> |
| `beat_library_stale` | error | <动态生成，见源码> |
| `pack_no_valid_cut` | error | <动态生成，见源码> |
| `speech_underfill` | info | <动态生成，见源码> |
| `rhythm_duration_range_narrow` | warning | <动态生成，见源码> |
| `rhythm_uniform_segment` | warning | <动态生成，见源码> |
| `rhythm_distribution_flatline` | warning | <动态生成，见源码> |
| `rhythm_fast_pole_missing` | warning | <动态生成，见源码> |
| `rhythm_slow_pole_missing` | warning | <动态生成，见源码> |
| `rhythm_cut_type_repeat` | info | <动态生成，见源码> |
| `rhythm_uniform_segment_spirit` | warning | <动态生成，见源码> |
| `rhythm_shot_count_default` | warning | <动态生成，见源码> |
| `rhythm_peak_too_short` | warning | <动态生成，见源码> |
| `rhythm_beat_duration_mismatch` | warning | <动态生成，见源码> |
| `episode_id_mismatch` | error | storyboard episode_id 与目录不一致。 |
| `director_control_card_invalid` | error | <动态生成，见源码> |
| `storyboard_source_markdown_invalid` | error | <动态生成，见源码> |
| `storyboard_shape_invalid` | error | storyboard 必须包含 shots 和 segments 数组。 |
| `shots_not_covered` | error | <动态生成，见源码> |
| `shots_covered_multiple_times` | error | <动态生成，见源码> |
| `shot_unknown_segment` | error | <动态生成，见源码> |
| `audience_execution_missing` | error | storyboard 必须登记从已确认 audience_plan 派生的 audience_execution。 |
| `highlight_ledger_invalid` | error | script_contract.highlight_ledger 必须是数组。 |
| `highlight_bindings_missing` | error | storyboard.highlight_bindings 必须是数组并覆盖剧本主要亮点。 |
| `inherited_aftereffect_bindings_invalid` | error | inherited_aftereffect_bindings 必须是数组。 |
| `primary_highlight_binding_missing` | error | <动态生成，见源码> |
| `director_control_card_missing` | error | 分镜阶段必须存在唯一导演总控卡。 |
| `storyboard_source_markdown_missing` | error | 十五列完整分镜表文件不存在。 |
| `shot_duration_total_mismatch` | error | shots.duration_s 之和必须等于 storyboard.duration_s。 |
| `segment_shot_ids_invalid` | error | <动态生成，见源码> |
| `segment_tail_mode_invalid` | error | <动态生成，见源码> |
| `intermediate_stable_hold_reason_missing` | error | <动态生成，见源码> |
| `audience_execution_revision_invalid` | error | audience_execution.source_plan_revision 必须是正整数。 |
| `primary_highlight_missing` | error | 完整模式每集 script_contract.highlight_ledger 必须至少包含一个有效的 primary 亮点。 |
| `inherited_aftereffect_binding_invalid` | error | inherited_aftereffect_bindings 每项必须是对象。 |
| `inherited_aftereffect_binding_fields_missing` | error | inherited_aftereffect_bindings 必须填写 binding_id、source_episode_id 和 source_highlight_id。 |
| `inherited_aftereffect_binding_shots_missing` | error | <动态生成，见源码> |
| `inherited_aftereffect_source_missing` | error | <动态生成，见源码> |
| `highlight_binding_invalid` | error | highlight_bindings 每项必须是对象。 |
| `highlight_binding_unknown` | error | <动态生成，见源码> |
| `highlight_binding_segment_invalid` | error | <动态生成，见源码> |
| `highlight_binding_reaction_before_payoff` | error | <动态生成，见源码> |
| `highlight_binding_aftereffect_invalid` | error | <动态生成，见源码> |
| `segment_unknown_shot` | error | <动态生成，见源码> |
| `segment_duration_mismatch` | error | <动态生成，见源码> |
| `audience_execution_revision_mismatch` | error | audience_execution.source_plan_revision 必须等于当前已确认 drama_plan revision。 |
| `audience_execution_field_missing` | error | <动态生成，见源码> |
| `audience_execution_source_field_invalid` | error | <动态生成，见源码> |
| `audience_execution_contract_mismatch` | error | <动态生成，见源码> |
| `audience_execution_refs_missing` | error | <动态生成，见源码> |
| `audience_execution_ref_invalid` | error | <动态生成，见源码> |
| `inherited_aftereffect_binding_shot_invalid` | error | <动态生成，见源码> |
| `highlight_binding_shots_missing` | error | <动态生成，见源码> |
| `highlight_binding_shot_invalid` | error | <动态生成，见源码> |
| `highlight_binding_segment_mismatch` | error | <动态生成，见源码> |
| `highlight_binding_execution_missing` | error | <动态生成，见源码> |
| `storyboard_source_markdown_unreadable` | error | <动态生成，见源码> |
| `storyboard_fifteen_columns_missing` | error | 完整分镜表必须包含一个十五列表格。 |
| `shot_segment_mismatch` | error | <动态生成，见源码> |
| `highlight_binding_aftereffect_before_payoff` | error | <动态生成，见源码> |
| `highlight_binding_aftereffect_scope_conflict` | error | <动态生成，见源码> |
| `highlight_binding_aftereffect_missing` | error | <动态生成，见源码> |
| `highlight_binding_deferred_episode_invalid` | error | <动态生成，见源码> |
| `highlight_binding_deferred_ref_invalid` | error | <动态生成，见源码> |
| `highlight_binding_deferred_highlight_missing` | error | <动态生成，见源码> |
| `highlight_binding_deferred_episode_order_invalid` | error | <动态生成，见源码> |
