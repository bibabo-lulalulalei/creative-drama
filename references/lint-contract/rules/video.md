# lint 检查合同 · video 阶段

> 由 build_lint_contract.py 从实际 STAGE_CHECKS 与共享调用图生成；按需读取。
> 只证明结构、来源、算术、依赖与技术合同；内容须按观看顺序独立审校。

运行：`python scripts/drama_lint.py <skill-root> --project-root <project> --stage video`。

| 检查码 | 级别 | 查什么 | 来源 |
|---|---|---|---|
| `accepted_segment_output_missing` | error | {segment_id} 已 accepted，但 output_file 不存在。 | `lint_checks.video.check_video`（26–210，触发 194） |
| `accepted_segment_prompt_missing` | error | {segment_id} 已 accepted，但 H3 成稿文件不存在。 | `lint_checks.video.check_video`（26–210，触发 196） |
| `accepted_without_quality_gate` | error | {segment_id} 只有通过质量门或用户接受明确偏差后才能 accepted。 | `lint_checks.video.check_video`（26–210，触发 208） |
| `adopted_cut_out_invalid` | error | continuous 后段需先锁采用出点和真实入站帧，再编译 | `preflight_video.prepare_full`（126–174，触发 162） |
| `asset_entity_scope_invalid` | error | {asset_id or '角色资产'} entity_scope 必须为 individual 或 collective。 | `lint_checks.assets.check_assets`（182–471，触发 201） |
| `asset_entity_scope_not_character` | error | {asset_id or '资产'} 只有 character 类资产可填写 entity_scope。 | `lint_checks.assets.check_assets`（182–471，触发 207） |
| `asset_file_missing` | error | 资产缺本地文件或有效 HTTP(S) 引用：{file_value} | `lint_checks.assets.check_assets`（182–471，触发 228） |
| `asset_id_missing` | error | 资产缺少 asset_id。 | `lint_checks.assets.check_assets`（182–471，触发 218） |
| `asset_id_prefix_mismatch` | error | {asset_id} 与 category={category} 的前缀不一致。 | `lint_checks.assets.check_assets`（182–471，触发 216） |
| `asset_planned_but_unregistered` | warning | {segment_id} 计划传入 {asset_id}，但 asset_usage_plan 未登记该绑定；临时增补必须回头登记。 | `lint_checks.storyboard.check_asset_usage_reconciliation`（425–510，触发 510） |
| `asset_ref_invalid` | error | {owner} 的 asset_refs 必须是非空字符串。 | `lint_checks.prompts.check_asset_ref`（52–65，触发 54） |
| `asset_ref_unknown` | error | {owner} 引用了不存在的资产版本：{ref} | `lint_checks.prompts.check_asset_ref`（52–65，触发 60） |
| `asset_ref_version_missing` | error | {owner} 引用资产 {ref} 时必须带版本号。 | `lint_checks.prompts.check_asset_ref`（52–65，触发 57） |
| `asset_refs_invalid` | error | {keyframe_id or '关键帧'} asset_refs 必须是数组。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 77） |
| `asset_required_but_unplanned` | error | {asset_id} 在 asset_usage_plan 中绑定 {segment_id}，但该段 reference_input_plan 未计划传入。 | `lint_checks.storyboard.check_asset_usage_reconciliation`（425–510，触发 500） |
| `asset_status_invalid` | error | 资产状态无效：{status} | `lint_checks.assets.check_assets`（182–471，触发 222） |
| `asset_usage_duplicate` | error | {episode_id} 共享资产重复：{asset_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 342） |
| `asset_usage_plan_invalid` | error | asset_usage_plan 每条必须是对象。 | `lint_checks.storyboard.check_asset_usage_reconciliation`（425–510，触发 478） |
| `asset_usage_plan_invalid` | error | asset_usage_plan 缺少 asset_id。 | `lint_checks.storyboard.check_asset_usage_reconciliation`（425–510，触发 482） |
| `asset_usage_plan_missing` | error | storyboard 必须登记 asset_usage_plan（资产需求清单的结构化同源数据）。 | `lint_checks.storyboard.check_asset_usage_reconciliation`（425–510，触发 471） |
| `asset_usage_segments_invalid` | error | {asset_id} 的 segments 必须是非空数组（可用 ["*"] 表示全部片段）。 | `lint_checks.storyboard.check_asset_usage_reconciliation`（425–510，触发 491） |
| `asset_usage_shared_not_approved` | error | {episode_id} 只能引用 registry 中 approved 的共享资产版本：{asset_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 339） |
| `asset_usage_shared_version_missing` | error | {episode_id} 共享资产必须填写 version：{asset_id} | `lint_checks.assets.check_assets`（182–471，触发 333） |
| `asset_usage_unknown_asset` | error | asset_usage_plan 引用了未登记的资产：{asset_id} | `lint_checks.storyboard.check_asset_usage_reconciliation`（425–510，触发 485） |
| `asset_usage_unknown_segment` | error | {asset_id} 绑定了不存在的片段：{segment_id} | `lint_checks.storyboard.check_asset_usage_reconciliation`（425–510，触发 496） |
| `asset_usage_unknown_shared_asset` | error | {episode_id} 引用了 registry 中不存在的共享资产：{asset_id} | `lint_checks.assets.check_assets`（182–471，触发 331） |
| `asset_usage_unknown_shared_version` | error | {episode_id} 引用了 registry 中不存在的共享资产版本：{asset_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 337） |
| `asset_version_duplicate` | error | asset_id + version 重复：{asset_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 212） |
| `asset_version_inconsistent` | warning | {segment_id} 计划传入 {asset_id} {planned_by_segment[segment_id][asset_id]}，与台账登记版本 {registered_versions[asset_id]} 不一致。 | `lint_checks.storyboard.check_asset_usage_reconciliation`（425–510，触发 506） |
| `assets_invalid` | error | asset_registry.assets 必须是数组。 | `lint_checks.assets.check_assets`（182–471，触发 303） |
| `audience_execution_contract_mismatch` | error | audience_execution.{field}.contract 必须逐字继承已确认 audience_plan.{field}。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 217） |
| `audience_execution_field_missing` | error | audience_execution.{field} 必须填写 contract。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 211） |
| `audience_execution_missing` | error | storyboard 必须登记从已确认 audience_plan 派生的 audience_execution。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 200） |
| `audience_execution_ref_invalid` | error | audience_execution.{field} 引用了不存在的场次或镜头：{unknown_refs} | `lint_checks.storyboard.check_storyboards`（75–372，触发 224） |
| `audience_execution_refs_missing` | error | audience_execution.{field}.scene_or_shot_ids 必须列出落地场次或镜头。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 220） |
| `audience_execution_revision_invalid` | error | audience_execution.source_plan_revision 必须是正整数。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 204） |
| `audience_execution_revision_mismatch` | error | audience_execution.source_plan_revision 必须等于当前已确认 drama_plan revision。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 206） |
| `audience_execution_source_field_invalid` | error | audience_execution.{field}.source_field 必须为 {expected_source}。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 215） |
| `audio_input_field_missing` | error | audio_inputs.{field} 必须填写。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 40） |
| `audio_input_file_missing` | error | 输入文件不存在或不是项目相对路径：{file_value} | `lint_checks.prompts.ordered_inputs`（15–49，触发 44） |
| `audio_input_invalid` | error | audio_inputs 每项必须是对象。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 25） |
| `audio_input_order_invalid` | error | audio_inputs.order 必须是整数。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 31） |
| `audio_input_order_not_contiguous` | error | audio_inputs.order 必须从 1 连续递增。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 48） |
| `audio_input_role_invalid` | error | audio_inputs.role 无效：{role} | `lint_checks.prompts.ordered_inputs`（15–49，触发 36） |
| `audio_inputs_invalid` | error | audio_inputs 必须是数组。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 19） |
| `beat_coverage_missing` | error | storyboard 必须登记 beat_coverage：剧本每条动作/事件的去向台账。 | `lint_checks.causal.check_beat_coverage`（35–72，触发 48） |
| `beat_disposition_invalid` | error | {label} disposition 无效。 | `lint_checks.causal.check_beat_coverage`（35–72，触发 58） |
| `beat_drop_reason_missing` | error | {label} 被 dropped 但未给理由。 | `lint_checks.causal.check_beat_coverage`（35–72，触发 65） |
| `beat_id_duplicate` | error | {scope} 中 beat_id 重复：{value} | `lint_checks.common.check_unique`（200–214，触发 211） |
| `beat_id_missing` | error | {scope} 缺少 beat_id。 | `lint_checks.common.check_unique`（200–214，触发 208） |
| `beat_incomplete` | error | {label} 缺少 scene 或 summary。 | `lint_checks.causal.check_beat_coverage`（35–72，触发 61） |
| `beat_invalid` | error | 第 {index} 条 beat 必须是对象。 | `lint_checks.causal.check_beat_coverage`（35–72，触发 53） |
| `beat_target_missing` | error | {label} disposition={disposition} 时 target_shots 必须非空。 | `lint_checks.causal.check_beat_coverage`（35–72，触发 68） |
| `beat_unknown_shot` | error | {label} 引用了不存在的镜头：{unknown} | `lint_checks.causal.check_beat_coverage`（35–72，触发 72） |
| `causal_chain_breakpoint_risk_invalid` | warning | {chain_id} breakpoint_risk={risk} 不在 C1-C5 内。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 287） |
| `causal_chain_cross_episode_not_closed` | error | {chain_id} 引用 {target_episode}，但目标集 causal_ledger 没有回指 {episode_id} 的链。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 328） |
| `causal_chain_cross_episode_ref_invalid` | error | {chain_id}.cross_episode_refs 每项必须含 episode_id（ep_N）与 note。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 313） |
| `causal_chain_cross_episode_refs_invalid` | error | {chain_id}.cross_episode_refs 必须是数组。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 309） |
| `causal_chain_empty` | warning | {chain_id} 未引用任何本集镜头，也没有跨集引用（空链）。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 330） |
| `causal_chain_highlight_binding_ref_unknown` | error | {chain_id} 的 highlight_binding_ref 指向不存在的亮点绑定：{binding_ref}。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 290） |
| `causal_chain_invalid` | error | causal_ledger 每条必须是对象。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 273） |
| `causal_chain_reaction_before_evidence` | error | {chain_id} 的反应镜头早于证据镜头（按 shots[] 数组序）。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 335） |
| `causal_chain_ref_unknown` | warning | 导演总控卡台词证据链引用了不存在的链：{ref_id}。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 395） |
| `causal_chain_result_before_reaction` | error | {chain_id} 的结果镜头早于反应镜头（按 shots[] 数组序）。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 337） |
| `causal_chain_shot_unknown` | error | {chain_id}.{field} 引用了不存在的本集镜头：{unknown}；跨集镜头登记 cross_episode_refs，不进本集数组。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 302） |
| `causal_chain_shots_invalid` | error | {chain_id}.{field} 必须是 shot_id 字符串数组。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 298） |
| `causal_chain_trigger_fact_missing` | error | {chain_id} 缺少 trigger_fact。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 277） |
| `causal_chain_trigger_source_missing` | error | {chain_id} 缺少 trigger_source（ref_type/ref_id）。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 282） |
| `causal_chain_visibility_contract_missing` | error | {chain_id} 缺少 visibility_contract（证据在哪些镜头以什么程度必须可见/可听）。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 279） |
| `causal_evidence_establishes_missing` | error | {shot_id} 被因果链列为证据位，必须填写 establishes。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 353） |
| `causal_evidence_visibility_missing` | error | {shot_id} 被因果链列为证据位，必须填写 evidence_visibility（枚举 {sorted(EVIDENCE_VISIBILITIES)}）。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 355） |
| `causal_ledger_missing` | error | storyboard 必须登记 causal_ledger 数组（无反应/证据依赖链的集登记空数组）。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 266） |
| `causal_reaction_responds_to_missing` | error | {shot_id} 被因果链列为反应/结果位，必须填写 responds_to。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 359） |
| `causal_ref_id_missing` | error | {owner} 缺少 ref_id。 | `lint_checks.causal.validate_causal_ref`（143–167，触发 163） |
| `causal_ref_invalid` | error | {owner} 的引用必须是含 ref_type/ref_id 的对象。 | `lint_checks.causal.validate_causal_ref`（143–167，触发 155） |
| `causal_ref_type_invalid` | error | {owner} 的 ref_type 无效：{ref_type}（枚举 {sorted(CAUSAL_REF_TYPES)}）。 | `lint_checks.causal.validate_causal_ref`（143–167，触发 159） |
| `causal_ref_unknown` | error | {owner} 引用了不存在的 {ref_type}：{ref_id}。 | `lint_checks.causal.validate_causal_ref`（143–167，触发 167） |
| `causal_responds_to_missing` | error | {shot_id} causal_role={role} 必须填写 responds_to。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 253） |
| `causal_role_invalid` | warning | {shot_id} causal_role={role} 不在枚举 {sorted(CAUSAL_ROLES)} 内。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 250） |
| `causal_role_missing` | error | {shot_id} 缺少 causal_role（每镜必填，枚举 {sorted(CAUSAL_ROLES)}）。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 248） |
| `causal_seam_invariant_missing` | warning | {chain_id} 的证据跨 {pair[0]}->{pair[1]} 传递给反应位，{seam_id}.required_invariants 必须派生写入该链 visibility_contract 条款。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 389） |
| `causal_seam_invariant_unknown` | warning | {chain_id} 的证据跨 {pair[0]}->{pair[1]} 传递给反应位，但找不到连续性账本，无法核对 {seam_id}.required_invariants 派生。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 385） |
| `causal_trigger_fact_missing` | warning | {shot_id}.responds_to 缺少 trigger_fact（该镜回应的已建立事实）。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 257） |
| `chain_id_duplicate` | error | {scope} 中 chain_id 重复：{value} | `lint_checks.common.check_unique`（200–214，触发 211） |
| `chain_id_missing` | error | {scope} 缺少 chain_id。 | `lint_checks.common.check_unique`（200–214，触发 208） |
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
| `content_review_open_issue` | error | 有未解决的内容设计问题 | `content_first.check_review`（189–197，触发 196） |
| `content_review_open_issue` | error | 缺内容审校记录；字段存在不证明摄影成立 | `content_first.check_review`（189–197，触发 194） |
| `content_review_stale` | error | 内容审校不对应当前设计/源/时间输入 | `content_first.check_review`（189–197，触发 192） |
| `cut_motivation_invalid` | error | {shot_id} cut_motivation 无效，必须是 {sorted(CUT_MOTIVATIONS)} 之一。 | `lint_checks.rhythm.check_shot_rhythm_fields`（101–116，触发 116） |
| `delivery_package_file_missing` | error | {segment_id} 登记了 compiled_prompt_file（五段交付包），但文件不存在。 | `lint_checks.video.check_video`（26–210，触发 141） |
| `director_control_card_invalid` | error | storyboard.director_control_card 必须指向 {expected_director_card}。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 98） |
| `director_control_card_missing` | error | 分镜阶段必须存在唯一导演总控卡。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 100） |
| `director_package_sha256_mismatch` | error | 导演包 SHA 与实际文件不同。 | `lint_checks.video.check_video`（26–210，触发 143） |
| `downstream_asset_not_approved` | error | {owner} 引用了未 approved 的资产版本：{ref} | `lint_checks.prompts.check_asset_ref`（52–65，触发 63） |
| `downstream_asset_version_stale` | error | {owner} 仍引用旧资产版本 {ref}；最新 approved 版本是 {asset_version_key(asset_id, latest)}。 | `lint_checks.assets.check_stale_asset_version`（86–93，触发 93） |
| `downstream_state_not_approved` | error | {owner} 引用了未 approved 的状态资产：{ref} | `lint_checks.prompts.check_state_ref`（68–78，触发 76） |
| `episode_asset_duplicate` | error | {episode_id} 分集资产重复：{asset_id} {state_id} {version} | `lint_checks.assets.check_assets`（182–471，触发 426） |
| `episode_asset_file_missing` | error | 分集资产缺本地文件或有效 HTTP(S) 引用：{file_value} | `lint_checks.assets.check_assets`（182–471，触发 470） |
| `episode_asset_status_invalid` | error | 分集资产状态无效：{item.get('status')} | `lint_checks.assets.check_assets`（182–471，触发 430） |
| `episode_character_state_asset_requires_image_edit` | error | {asset_id or '角色状态资产'} 是人物状态资产时必须基于已批准人物图使用 image_edit；除非用户明确要求重做并记录 explicit_user_override。 | `lint_checks.assets.check_assets`（182–471，触发 466） |
| `episode_confirmation_missing_episode_id` | error | 用户确认记录第 {line_number} 行 {stage} 阶段必须填写 episode_id。 | `lint_checks.state.load_confirmation_records`（18–111，触发 59） |
| `episode_id_mismatch` | error | keyframe_manifest episode_id 与目录不一致。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 27） |
| `episode_id_mismatch` | error | storyboard episode_id 与目录不一致。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 95） |
| `episode_id_mismatch` | error | video_manifest episode_id 与目录不一致。 | `lint_checks.video.check_video`（26–210，触发 39） |
| `episode_id_mismatch` | error | {stage} episode_id 必须等于目录 ID：{episode_id} | `lint_checks.stages.check_episode_manifest_ids`（28–35，触发 35） |
| `episode_image_edit_reference_missing` | error | {asset_id or '分集资产'} 使用 image_edit 时必须登记实际参考来源。 | `lint_checks.assets.check_assets`（182–471，触发 461） |
| `episode_image_edit_visual_reference_decision_conflict` | error | {asset_id or '分集资产'} 使用 image_edit 时 visual_reference_decision 不能写 none_available。 | `lint_checks.assets.check_assets`（182–471，触发 463） |
| `episode_image_gen_should_not_have_visual_inputs` | error | {asset_id or '分集资产'} 使用 image_gen 时不应登记图片参考输入。 | `lint_checks.assets.check_assets`（182–471，触发 455） |
| `episode_image_gen_visual_reference_available` | error | {asset_id or '分集资产'} 已登记可用视觉参考，必须使用 image_edit；除非用户明确要求不参考并记录 explicit_user_override。 | `lint_checks.assets.check_assets`（182–471，触发 457） |
| `episode_image_gen_visual_reference_decision_conflict` | error | {asset_id or '分集资产'} visual_reference_decision=used 时不能使用 image_gen。 | `lint_checks.assets.check_assets`（182–471，触发 459） |
| `episode_keyframe_count_mismatch` | error | 本集实际有效关键帧数量 {actual_total} 必须等于 storyboard.keyframe_requests 规划总数 {planned_total}。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 112） |
| `episode_project_visual_mode_missing_or_invalid` | error | {asset_id or '分集资产'} approved 图片资产必须登记有效 project_visual_mode。 | `lint_checks.assets.check_assets`（182–471，触发 453） |
| `episode_segment_index_invalid` | error | 视频段索引需从 1 起唯一正整数 | `video_confirmations.validate_confirmations`（22–151，触发 36） |
| `episode_segment_index_not_contiguous` | error | 视频段索引必须连续 | `video_confirmations.validate_confirmations`（22–151，触发 40） |
| `episode_visual_reference_decision_invalid` | error | {asset_id or '分集资产'} visual_reference_decision 无效：{visual_reference_decision} | `lint_checks.assets.check_assets`（182–471，触发 441） |
| `evidence_visibility_invalid` | error | {shot_id} evidence_visibility 无效：{visibility}（枚举 {sorted(EVIDENCE_VISIBILITIES)}）。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 260） |
| `fact_id_duplicate` | error | {scope} 中 fact_id 重复：{value} | `lint_checks.common.check_unique`（200–214，触发 211） |
| `fact_id_missing` | error | {scope} 缺少 fact_id。 | `lint_checks.common.check_unique`（200–214，触发 208） |
| `file_missing` | error | 缺少流程所需文件。 | `lint_checks.common.load_json`（22–30，触发 27） |
| `generated_segment_h3_prompt_missing` | error | {segment_id} 已生成或进入候选/验收状态，必须登记真实存在的 h3_prompt_file。 | `lint_checks.prompts.check_h3_prompt`（164–196，触发 194） |
| `generated_segment_h3_prompt_sha256_missing` | error | {segment_id} 已生成或进入候选/验收状态，必须登记提交给模型的 H3 成稿 h3_prompt_sha256。 | `lint_checks.prompts.check_h3_prompt`（164–196，触发 196） |
| `generated_segment_prompt_missing` | error | {segment_id} 已生成或进入候选/验收状态，必须登记真实存在的 H3 成稿文件。 | `lint_checks.video.check_video`（26–210，触发 180） |
| `generated_segment_prompt_sha256_missing` | error | {segment_id} 已生成或进入候选/验收状态，必须登记实际提交 Prompt 文件的 prompt_sha256。 | `lint_checks.video.check_video`（26–210，触发 182） |
| `generation_prompt_file_missing` | error | {owner_label} 生成图片 Prompt 文件不存在。 | `lint_checks.common.check_generation_prompt_file`（135–154，触发 149） |
| `generation_prompt_path_missing` | error | {owner_label} 使用 {tool} 生成图片时必须登记项目相对 prompt_path。 | `lint_checks.common.check_generation_prompt_file`（135–154，触发 147） |
| `generation_prompt_unreadable` | error | {owner_label} 生成图片 Prompt 无法读取：{exc} | `lint_checks.common.check_generation_prompt_file`（135–154，触发 154） |
| `h3_compilation_mismatch` | error | 编译映射镜头集合/顺序不符 | `lint_checks.prompts.check_prompt_preflight`（289–299，触发 297） |
| `h3_compilation_mismatch` | error | 编译映射需指向成稿实际段落；引用不证明语义保真 | `h3_contract.prepare_request`（339–411，触发 392） |
| `h3_compilation_mismatch` | error | 编译映射须按当前 SEG 镜头顺序完整覆盖 | `preflight_video.validate_compilation_map`（51–123，触发 54） |
| `h3_compilation_mismatch` | error | 镜头编译的 SEG 局部时间与核算不符 | `preflight_video.validate_compilation_map`（51–123，触发 77） |
| `h3_deployment_missing` | error | 缺 workflow：在 Skill .env 设置 H3_WORKFLOW、h3.json.deployment.workflow 或 gen.extra.workflow | `h3_contract.resolve_deployment`（75–93，触发 92） |
| `h3_input_invalid` | error | inputs 必须是数组，可空 | `h3_contract._media`（213–277，触发 216） |
| `h3_input_invalid` | error | manifest 的参考媒体时长与实际请求不同 | `preflight_video.validate_manifest_inputs`（17–33，触发 33） |
| `h3_input_invalid` | error | manifest 的实际输入顺序/文件或原样 URL/职责与 gen 不同 | `preflight_video.validate_manifest_inputs`（17–33，触发 25） |
| `h3_input_invalid` | error | 参考单条时长超能力 | `h3_contract._media`（213–277，触发 273） |
| `h3_input_invalid` | error | 参考累计时长超能力 | `h3_contract._media`（213–277，触发 276） |
| `h3_input_invalid` | error | 只支持项目内文件或 HTTP(S) URL | `h3_contract._media`（213–277，触发 237） |
| `h3_input_invalid` | error | 已选全参考模式缺实际参考输入；交回 h3-prompt-writing 核对 | `h3_contract._media`（213–277，触发 252） |
| `h3_input_invalid` | error | 显式 slot 必须匹配该模态数组顺序 | `h3_contract._media`（213–277，触发 228） |
| `h3_input_invalid` | error | 本地媒体扩展名与 kind 不符 | `h3_contract._media`（213–277，触发 242） |
| `h3_input_invalid` | error | 每项需要有效 kind/path | `h3_contract._media`（213–277，触发 225） |
| `h3_input_invalid` | error | 输入条目或字段无效，不静默丢弃 | `h3_contract._media`（213–277，触发 222） |
| `h3_input_invalid` | error | 输入超真实总文件上限 | `h3_contract._media`（213–277，触发 260） |
| `h3_input_invalid` | error | 输入超真实模态槽位上限 | `h3_contract._media`（213–277，触发 258） |
| `h3_input_invalid` | error | 音视频参考需登记已探测时长；URL 不在预检时下载 | `h3_contract._media`（213–277，触发 270） |
| `h3_input_invalid` | error | 音频参考需要真实视觉输入 | `h3_contract._media`（213–277，触发 262） |
| `h3_input_marker_mismatch` | error | 成稿媒体标记必须逐项对应实际输入槽位，无遗漏或未知引用 | `h3_contract.check_media_markers`（318–323，触发 323） |
| `h3_mode_invalid` | error | 未知 H3 模式 | `h3_contract._media`（213–277，触发 249） |
| `h3_mode_invalid` | error | 锚帧数与当前模式不符 | `h3_contract._media`（213–277，触发 254） |
| `h3_prompt_empty` | error | {segment_id} 的 H3 成稿为空。 | `lint_checks.prompts.check_h3_prompt`（164–196，触发 178） |
| `h3_prompt_impure` | error | H3 字段正文为空 | `h3_contract.check_purity`（96–128，触发 126） |
| `h3_prompt_impure` | error | H3 字段缺失、重复、未知或顺序不符 | `h3_contract.check_purity`（96–128，触发 124） |
| `h3_prompt_impure` | error | H3 正文为空 | `h3_contract.check_purity`（96–128，触发 98） |
| `h3_prompt_impure` | error | 混入交付包/分隔符/围栏；不提取子串提交 | `h3_contract.check_purity`（96–128，触发 101） |
| `h3_prompt_impure` | error | 混入标题、表格或独立说明；只允许 H3 字段正文 | `h3_contract.check_purity`（96–128，触发 128） |
| `h3_prompt_impure` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `lint_checks.prompts._check_h3_prompt_purity`（210–214，触发 214） |
| `h3_prompt_impure` | error | 锚帧首行后需空行和 H3 正文 | `h3_contract.check_purity`（96–128，触发 118） |
| `h3_prompt_impure` | error | 首行不符合当前 H3 模式；合法锚帧指令须保持官方格式 | `h3_contract.check_purity`（96–128，触发 115） |
| `h3_prompt_missing` | error | {segment_id} 登记的 h3_prompt_file 不存在。 | `lint_checks.prompts.check_h3_prompt`（164–196，触发 173） |
| `h3_prompt_path_invalid` | error | {segment_id} h3_prompt_file 必须是项目相对路径。 | `lint_checks.prompts.check_h3_prompt`（164–196，触发 170） |
| `h3_prompt_sha256_mismatch` | error | {segment_id} h3_prompt_sha256 与实际 H3 成稿不一致。 | `lint_checks.prompts.check_h3_prompt`（164–196，触发 190） |
| `h3_prompt_sha256_unreadable` | error | 无法读取 H3 成稿计算 sha256：{exc} | `lint_checks.prompts.check_h3_prompt`（164–196，触发 187） |
| `h3_prompt_unreadable` | error | {segment_id} 的 H3 成稿无法读取：{exc} | `lint_checks.prompts.check_h3_prompt`（164–196，触发 180） |
| `h3_request_invalid` | error | SEG 不存在或重复 | `preflight_video.prepare_full`（126–174，触发 139） |
| `h3_request_invalid` | error | aspect 不符合能力档 | `h3_contract._parameters`（163–210，触发 184） |
| `h3_request_invalid` | error | base_url 需 HTTP(S) URL | `h3_contract._parameters`（163–210，触发 179） |
| `h3_request_invalid` | error | extra 必须是已声明配置字段的对象 | `h3_contract.resolve_deployment`（75–93，触发 80） |
| `h3_request_invalid` | error | extra 需 workflow，未知字段不得静默忽略 | `h3_contract._parameters`（163–210，触发 176） |
| `h3_request_invalid` | error | gen 必须为有限 JSON | `h3_contract.prepare_request`（339–411，触发 344） |
| `h3_request_invalid` | error | gen 必须是对象 | `h3_contract.resolve_deployment`（75–93，触发 77） |
| `h3_request_invalid` | error | gen 必须是对象，且只能包含已声明字段 | `h3_contract._parameters`（163–210，触发 165） |
| `h3_request_invalid` | error | options 必须是有限 JSON | `h3_contract._parameters`（163–210，触发 203） |
| `h3_request_invalid` | error | resolution 不符合能力档 | `h3_contract._parameters`（163–210，触发 182） |
| `h3_request_invalid` | error | seed 必须整数 | `h3_contract._parameters`（163–210，触发 209） |
| `h3_request_invalid` | error | 当前封装的画幅方向由 resolution 承载；aspect 需与实际 resolution 一致 | `h3_contract._parameters`（163–210，触发 190） |
| `h3_request_invalid` | error | 模型必须是当前 H3 能力档 | `h3_contract._parameters`（163–210，触发 167） |
| `h3_request_invalid` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `h3_contract._parameters`（163–210，触发 196） |
| `h3_reserved_option` | error | options 不能覆盖正文、时长、已知参数或媒体槽位 | `h3_contract._parameters`（163–210，触发 199） |
| `h3_runtime_invalid` | error | {key} 必须是有限正数 | `h3_contract._parameters`（163–210，触发 207） |
| `highlight_binding_aftereffect_before_payoff` | error | {highlight_id or '亮点绑定'} 的余震镜头不得早于兑现或反应镜头。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 330） |
| `highlight_binding_aftereffect_invalid` | error | {highlight_id or '亮点绑定'}.aftereffect_shot_ids 必须是数组。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 322） |
| `highlight_binding_aftereffect_missing` | error | {highlight_id or '亮点绑定'} 必须填写本集 aftereffect_shot_ids 或跨集 deferred_aftereffect_ref。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 334） |
| `highlight_binding_aftereffect_scope_conflict` | error | {highlight_id or '亮点绑定'} 已填写本集余震时 deferred_aftereffect_ref 必须为空。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 332） |
| `highlight_binding_deferred_episode_invalid` | error | {highlight_id or '亮点绑定'} deferred_aftereffect_ref.episode_id 必须是计划内分集。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 339） |
| `highlight_binding_deferred_episode_order_invalid` | error | {highlight_id or '亮点绑定'} deferred_aftereffect_ref 必须指向后续分集。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 341） |
| `highlight_binding_deferred_highlight_missing` | error | {highlight_id or '亮点绑定'} deferred_aftereffect_ref.highlight_id 必须存在于目标集 script_contract.highlight_ledger。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 353） |
| `highlight_binding_deferred_ref_invalid` | error | {highlight_id or '亮点绑定'} deferred_aftereffect_ref 必须填写 highlight_id 和 binding_id。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 344） |
| `highlight_binding_execution_missing` | error | {highlight_id or '亮点绑定'} 缺少 {field}。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 356） |
| `highlight_binding_invalid` | error | highlight_bindings 每项必须是对象。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 291） |
| `highlight_binding_reaction_before_payoff` | error | {highlight_id or '亮点绑定'} 的反应镜头不得早于兑现镜头。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 318） |
| `highlight_binding_segment_invalid` | error | {highlight_id or '亮点绑定'} 引用了不存在的 segment_id：{segment_id} | `lint_checks.storyboard.check_storyboards`（75–372，触发 298） |
| `highlight_binding_segment_mismatch` | error | {highlight_id or '亮点绑定'} 的镜头不属于 {segment_id}：{wrong_segment} | `lint_checks.storyboard.check_storyboards`（75–372，触发 311） |
| `highlight_binding_shot_invalid` | error | {highlight_id or '亮点绑定'}.aftereffect_shot_ids 引用了不存在的本集镜头：{unknown_refs} | `lint_checks.storyboard.check_storyboards`（75–372，触发 326） |
| `highlight_binding_shot_invalid` | error | {highlight_id or '亮点绑定'}.{field} 引用了不存在的镜头：{unknown_refs} | `lint_checks.storyboard.check_storyboards`（75–372，触发 308） |
| `highlight_binding_shots_missing` | error | {highlight_id or '亮点绑定'}.{field} 必须至少包含一个镜头。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 304） |
| `highlight_binding_unknown` | error | 分镜绑定了剧本中不存在的亮点：{highlight_id} | `lint_checks.storyboard.check_storyboards`（75–372，触发 295） |
| `highlight_bindings_missing` | error | storyboard.highlight_bindings 必须是数组并覆盖剧本主要亮点。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 243） |
| `highlight_id_duplicate` | error | {scope} 中 highlight_id 重复：{value} | `lint_checks.common.check_unique`（200–214，触发 211） |
| `highlight_id_missing` | error | {scope} 缺少 highlight_id。 | `lint_checks.common.check_unique`（200–214，触发 208） |
| `highlight_ledger_invalid` | error | script_contract.highlight_ledger 必须是数组。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 165） |
| `highlight_ledger_invalid` | error | script_contract.highlight_ledger 必须是数组。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 229） |
| `image_edit_reference_missing` | error | {asset_id} 使用 image_edit 时必须登记实际参考来源。 | `lint_checks.assets.check_assets`（182–471，触发 258） |
| `image_edit_visual_reference_decision_conflict` | error | {asset_id} 使用 image_edit 时 visual_reference_decision 不能写 none_available。 | `lint_checks.assets.check_assets`（182–471，触发 260） |
| `image_gen_should_not_have_visual_inputs` | error | {asset_id} 使用 image_gen 时不应登记图片参考输入。 | `lint_checks.assets.check_assets`（182–471，触发 252） |
| `image_gen_visual_reference_available` | error | {asset_id} 已登记可用视觉参考，必须使用 image_edit；除非用户明确要求不参考并记录 explicit_user_override。 | `lint_checks.assets.check_assets`（182–471，触发 254） |
| `image_gen_visual_reference_decision_conflict` | error | {asset_id} visual_reference_decision=used 时不能使用 image_gen。 | `lint_checks.assets.check_assets`（182–471，触发 256） |
| `inherited_aftereffect_binding_fields_missing` | error | inherited_aftereffect_bindings 必须填写 binding_id、source_episode_id 和 source_highlight_id。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 269） |
| `inherited_aftereffect_binding_invalid` | error | inherited_aftereffect_bindings 每项必须是对象。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 262） |
| `inherited_aftereffect_binding_shot_invalid` | error | {binding_id or '跨集余震承接'} 引用了不存在的本集镜头：{unknown_refs} | `lint_checks.storyboard.check_storyboards`（75–372，触发 275） |
| `inherited_aftereffect_binding_shots_missing` | error | {binding_id or '跨集余震承接'} 必须绑定本集真实 shot_ids。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 271） |
| `inherited_aftereffect_bindings_invalid` | error | inherited_aftereffect_bindings 必须是数组。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 258） |
| `inherited_aftereffect_source_missing` | error | {binding_id or '跨集余震承接'} 找不到来源集对应 deferred_aftereffect_ref。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 288） |
| `interaction_call_id_reused` | error | 用户确认记录第 {line_number} 行 interaction_ask_call_id 已被其他用途使用。 | `lint_checks.state.load_confirmation_records`（18–111，触发 76） |
| `intermediate_stable_hold_reason_missing` | error | {segment_id or index} 是中间片段，使用 stable_hold 时必须填写 tail_hold_reason。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 180） |
| `json_invalid` | error | JSON 无法读取或解析，后续关系无法确认：{exc} | `lint_checks.common.load_json`（22–30，触发 29） |
| `keyframe_count_mismatch` | error | {segment_id} 实际有效关键帧数量 {actual_count} 必须等于 storyboard.keyframe_requests 规划数量 {planned_count}。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 116） |
| `keyframe_file_missing` | error | 关键帧文件不存在：{file_value} | `lint_checks.keyframes.check_keyframes`（15–116，触发 69） |
| `keyframe_file_name_invalid` | error | {keyframe_id or '关键帧'} 文件名必须使用 highlight-N 高光序号。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 71） |
| `keyframe_highlight_index_duplicate` | error | {segment_id} 的 highlight_index={highlight_index} 重复。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 62） |
| `keyframe_highlight_index_invalid` | error | {keyframe_id or '关键帧'} highlight_index 必须是从 1 开始的正整数。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 58） |
| `keyframe_id_duplicate` | error | {scope} 中 keyframe_id 重复：{value} | `lint_checks.common.check_unique`（200–214，触发 211） |
| `keyframe_id_missing` | error | {scope} 缺少 keyframe_id。 | `lint_checks.common.check_unique`（200–214，触发 208） |
| `keyframe_identity_mismatch` | error | 有效 KF 必须逐项对应实际请求 ID，数量相同不能代替。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 108） |
| `keyframe_requests_invalid` | error | {segment_id} keyframe_requests 必须是数组；未选中本集高光时可省略或填空数组。 | `lint_checks.rhythm.check_keyframe_request_plan`（74–92，触发 84） |
| `keyframe_role_invalid` | error | {keyframe_id or '关键帧'} role 必须为 highlight。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 55） |
| `keyframe_role_missing` | error | {segment_id} 已规划 keyframe_requests 时，required_keyframe_roles 必须包含 highlight。 | `lint_checks.rhythm.check_keyframe_request_plan`（74–92，触发 89） |
| `keyframe_role_without_request` | error | {segment_id} 标记了 highlight 但没有 keyframe_requests；未选中本集高光时不要登记关键帧职责。 | `lint_checks.rhythm.check_keyframe_request_plan`（74–92，触发 91） |
| `keyframe_tool_not_image_edit` | error | {keyframe_id or '关键帧'} 必须使用 image_edit I2I 生成，不得使用 image_gen 或纯文生图。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 73） |
| `keyframe_unknown_segment` | error | 关键帧引用了不存在的 segment_id：{segment_id} | `lint_checks.keyframes.check_keyframes`（15–116，触发 48） |
| `keyframe_unknown_shot` | error | 关键帧引用了不存在的 shot_id：{shot_id} | `lint_checks.keyframes.check_keyframes`（15–116，触发 50） |
| `keyframe_unknown_used_segment` | error | used_by_segments 引用了不存在的 segment_id：{used_segment} | `lint_checks.keyframes.check_keyframes`（15–116，触发 66） |
| `keyframe_unplanned_segment` | error | {segment_id} 实际生成了 {actual_count} 张有效关键帧，但 storyboard.keyframe_requests 未规划该段关键帧。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 104） |
| `keyframes_invalid` | error | keyframes 必须是数组。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 31） |
| `occluded_establishes_missing` | warning | {shot_id} evidence_visibility=occluded 时必须在 establishes 写明遮挡理由与揭示点。 | `lint_checks.causal.check_causal_ledger`（202–395，触发 262） |
| `opening_binding_marker_missing` | error | 第 {order} 张参考图缺少对应 <图片{order}>/<IMG{order}> 标记。 | `lint_checks.storyboard.check_reference_plan`（375–407，触发 398） |
| `pack_drift` | error | SEG 内容/请求/尾余量/设计依赖不符 | `content_first.reconcile_storyboard`（207–249，触发 234） |
| `pack_drift` | error | beat_groups 必须为数组 | `timeline_core.validate_timeline_shape`（77–150，触发 114） |
| `pack_drift` | error | group_id 必须唯一且非空 | `timeline_core.compute_groups`（289–360，触发 319） |
| `pack_drift` | error | segment_id 必须为非空字符串 | `timeline_core.compute_groups`（289–360，触发 356） |
| `pack_drift` | error | segment_id 重复 | `timeline_core.compute_groups`（289–360，触发 358） |
| `pack_drift` | error | 组 {gid} 含未知/空镜头 | `timeline_core.compute_groups`（289–360，触发 323） |
| `pack_drift` | error | 组必须按正式顺序恰好覆盖所有镜头，无重漏 | `timeline_core.compute_groups`（289–360，触发 353） |
| `pack_drift` | error | 视频 SEG 不在当前分镜 | `preflight_video.prepare_full`（126–174，触发 143） |
| `pack_drift` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `preflight_video.validate_segment_timing`（36–48，触发 48） |
| `pack_drift` | error | 镜头组字段非法 | `timeline_core.compute_groups`（289–360，触发 314） |
| `pack_drift` | error | 需要导演声明的合法镜头组，不自动制造切点 | `timeline_core.compute_groups`（289–360，触发 307） |
| `planning_interaction_confirmation_missing` | error | 最新 planning 确认必须记录 project_execution、真实 interaction_ask_call_id 和 proceed_project。 | `lint_checks.state.load_confirmation_records`（18–111，触发 110） |
| `preflight_binding_mismatch` | error | manifest binding_id 不符 | `lint_checks.prompts.check_prompt_preflight`（289–299，触发 295） |
| `preflight_binding_mismatch` | error | preflight 必须为完整回执对象 | `h3_contract.prepare_request`（339–411，触发 353） |
| `preflight_binding_mismatch` | error | 当前设计/请求不符 manifest 绑定 | `lint_checks.video.check_video`（26–210，触发 152） |
| `preflight_binding_mismatch` | error | 执行请求缺冻结的 workflow/base_url；先预检写回再确认 | `h3_contract.resolve_deployment`（75–93，触发 84） |
| `preflight_binding_mismatch` | error | 缺独立 H3 文件路径 | `h3_contract.prepare_request`（339–411，触发 356） |
| `preflight_binding_mismatch` | error | 读取时检测到文件变化 | `h3_contract.snapshot_bytes`（45–52，触发 51） |
| `preflight_binding_mismatch` | error | 调用方正文与当前 H3 文件不同 | `h3_contract.prepare_request`（339–411，触发 361） |
| `preflight_binding_mismatch` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `lint_checks.prompts.check_prompt_preflight`（289–299，触发 299） |
| `preflight_binding_mismatch` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `lint_checks.video.check_video`（26–210，触发 154） |
| `preflight_binding_mismatch` | error | 预检缺失或当前文件/参数/输入/出点/源依赖已变，POST 前阻断 | `h3_contract.prepare_request`（339–411，触发 404） |
| `preflight_dependency_invalid` | error | dependencies 必须为对象数组 | `h3_contract.prepare_request`（339–411，触发 367） |
| `preflight_dependency_invalid` | error | 依赖镜头不存在或顺序已变 | `h3_contract.scoped_design`（131–145，触发 139） |
| `preflight_dependency_invalid` | error | 依赖镜头范围无效 | `h3_contract.scoped_design`（131–145，触发 134） |
| `preflight_dependency_invalid` | error | 入站出点必须登记依赖 | `h3_contract.prepare_request`（339–411，触发 380） |
| `preflight_dependency_invalid` | error | 导演包与纯 H3 成稿必须是两个独立文件 | `h3_contract.prepare_request`（339–411，触发 373） |
| `preflight_dependency_invalid` | error | 未知依赖角色 | `h3_contract.dependency_snapshot`（280–307，触发 282） |
| `preflight_dependency_invalid` | error | 缺当前内容对照引用或实际编译映射 | `h3_contract.prepare_request`（339–411，触发 388） |
| `preflight_dependency_invalid` | error | 需导演包和实际分镜设计依赖 | `h3_contract.prepare_request`（339–411，触发 371） |
| `previous_tail_source_type_invalid` | error | {segment_id} 上一段尾帧必须以 source_type=frame 真实传入。 | `lint_checks.video.check_video`（26–210，触发 116） |
| `primary_highlight_binding_missing` | error | 以下主要亮点未绑定到分镜：{missing_primary} | `lint_checks.storyboard.check_storyboards`（75–372，触发 359） |
| `project_confirmation_has_episode` | error | 用户确认记录第 {line_number} 行 planning 阶段不得填写 episode_id。 | `lint_checks.state.load_confirmation_records`（18–111，触发 57） |
| `project_visual_mode_missing_or_invalid` | error | {asset_id or '资产'} approved 图片资产必须登记有效 project_visual_mode。 | `lint_checks.assets.check_assets`（182–471，触发 250） |
| `prompt_audio_markers_mismatch` | error | Prompt 中{label}标记 {actual} 必须与实际输入 order {expected} 一致（写法以 h3-prompt-writing 为准）。 | `lint_checks.prompts.check_prompt_markers`（107–161，触发 137） |
| `prompt_image_markers_mismatch` | error | Prompt 中{label}标记 {actual} 必须与实际输入 order {expected} 一致（写法以 h3-prompt-writing 为准）。 | `lint_checks.prompts.check_prompt_markers`（107–161，触发 137） |
| `prompt_marker_language_mixed` | error | 同一 Prompt 不要混用中文和英文多媒体标记。 | `lint_checks.prompts.check_prompt_markers`（107–161，触发 141） |
| `prompt_missing` | error | Prompt 文件不存在。 | `lint_checks.prompts.check_prompt_markers`（107–161，触发 124） |
| `prompt_path_invalid` | error | compiled_prompt_file 必须是项目相对路径。 | `lint_checks.video.check_video`（26–210，触发 177） |
| `prompt_sha256_mismatch` | error | {segment_id} prompt_sha256 与实际 Prompt 文件不一致。 | `lint_checks.video.check_video`（26–210，触发 175） |
| `prompt_sha256_unreadable` | error | 无法读取 Prompt 计算 sha256：{exc} | `lint_checks.video.check_video`（26–210，触发 172） |
| `prompt_speech_line_missing` | error | Prompt 缺少当前 SEG 台词原文：{spoken} | `lint_checks.prompts.check_prompt_markers`（107–161，触发 161） |
| `prompt_subject_marker_label_missing` | error | Prompt 使用 <主体{order}>/<SUBJ{order}> 时，必须至少一次写成 <主体{order}>(名称) 或 <SUBJ{order}>(name) 绑定主体身份。 | `lint_checks.prompts.check_prompt_markers`（107–161，触发 146） |
| `prompt_subtitle_bracket_invalid` | error | 未启用字幕时，最终视频 Prompt 不允许出现【】字幕源标识。 | `lint_checks.prompts.check_prompt_markers`（107–161，触发 148） |
| `prompt_unreadable` | error | Prompt 无法读取：{exc} | `lint_checks.prompts.check_prompt_markers`（107–161，触发 129） |
| `prompt_video_markers_mismatch` | error | Prompt 中{label}标记 {actual} 必须与实际输入 order {expected} 一致（写法以 h3-prompt-writing 为准）。 | `lint_checks.prompts.check_prompt_markers`（107–161，触发 137） |
| `quality_deviation_acceptance_missing` | error | 偏差接受需回指同一结果文件/指纹、范围和明确偏差的真实确认，非空引用不能代替。 | `lint_checks.video.check_quality_acceptance`（213–225，触发 225） |
| `ref_audio_not_voice_sample` | error | {segment_id} 的音频参考必须指向 shared/03_资产/音色/ 下已批准 VOICE 样音（路径：{audio_rel}）；禁止台词级 TTS 临时音频进入 ref_audio 槽位——正片台词由 H3 原生生成，参考只锁声线。 | `lint_checks.video.check_video`（26–210，触发 129） |
| `reference_input_field_missing` | error | reference_inputs.{field} 必须填写。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 40） |
| `reference_input_file_missing` | error | 输入文件不存在或不是项目相对路径：{file_value} | `lint_checks.prompts.ordered_inputs`（15–49，触发 44） |
| `reference_input_file_suffix_invalid` | error | reference_inputs.file 必须是图片文件：{file_value} | `lint_checks.prompts.ordered_inputs`（15–49，触发 46） |
| `reference_input_invalid` | error | reference_inputs 每项必须是对象。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 25） |
| `reference_input_order_invalid` | error | reference_inputs.order 必须是整数。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 31） |
| `reference_input_order_not_contiguous` | error | reference_inputs.order 必须从 1 连续递增。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 48） |
| `reference_input_plan_incomplete` | error | 参考图计划缺少 {field}。 | `lint_checks.storyboard.check_reference_plan`（375–407，触发 405） |
| `reference_input_plan_invalid` | error | reference_input_plan 必须是数组。 | `lint_checks.storyboard.check_reference_plan`（375–407，触发 385） |
| `reference_input_plan_invalid` | error | 第 {index} 条参考计划必须是对象。 | `lint_checks.storyboard.check_reference_plan`（375–407，触发 390） |
| `reference_input_plan_missing` | error | 每个 SEG 必须填写 reference_input_plan。 | `lint_checks.storyboard.check_reference_plan`（375–407，触发 382） |
| `reference_input_role_invalid` | error | reference_inputs.role 无效：{role} | `lint_checks.prompts.ordered_inputs`（15–49，触发 36） |
| `reference_inputs_invalid` | error | reference_inputs 必须是数组。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 19） |
| `reference_order_invalid` | error | 参考图 order 必须是整数。 | `lint_checks.storyboard.check_reference_plan`（375–407，触发 400） |
| `reference_order_not_contiguous` | error | 参考图 order 必须从 1 连续递增。 | `lint_checks.storyboard.check_reference_plan`（375–407，触发 407） |
| `reference_role_asset_mismatch` | error | {segment_id} 资产 {asset_id} 的职责 {role} 与资产类型不匹配。 | `lint_checks.storyboard.check_asset_usage_reconciliation`（425–510，触发 466） |
| `reference_role_invalid` | error | 参考图职责无效：{role} | `lint_checks.storyboard.check_reference_plan`（375–407，触发 402） |
| `required_artifact_missing` | error | 缺少当前阶段所需产物。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 132） |
| `required_reference_role_invalid` | error | required_reference_roles 含无效职责。 | `lint_checks.video.check_video`（26–210，触发 94） |
| `required_reference_role_not_passed` | error | required_reference_roles 未真实传入：{missing} | `lint_checks.video.check_video`（26–210，触发 97） |
| `required_reference_roles_missing` | error | {segment_id} 使用图片或分镜声明图片职责时必须填写 required_reference_roles。 | `lint_checks.video.check_video`（26–210，触发 92） |
| `required_reference_roles_unexpected` | error | 没有图片输入时 required_reference_roles 应为空或省略。 | `lint_checks.video.check_video`（26–210，触发 99） |
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
| `segment_density_profile_invalid` | error | {label} density_profile 无效。 | `lint_checks.rhythm.check_segment_shot_count`（53–71，触发 64） |
| `segment_duration_mismatch` | error | {segment_id} duration_s 必须等于其 shot_ids 时长之和。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 167） |
| `segment_id_duplicate` | error | {scope} 中 segment_id 重复：{value} | `lint_checks.common.check_unique`（200–214，触发 211） |
| `segment_id_missing` | error | {scope} 缺少 segment_id。 | `lint_checks.common.check_unique`（200–214，触发 208） |
| `segment_shot_ids_invalid` | error | {segment_id or index} 缺少 shot_ids 数组。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 151） |
| `segment_shot_mode_invalid` | error | {label} shot_mode 必须为 edited 或 true_one_take。 | `lint_checks.rhythm.check_segment_shot_count`（53–71，触发 66） |
| `segment_tail_mode_invalid` | error | {segment_id or index} tail_mode 无效。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 178） |
| `segment_unknown_shot` | error | {segment_id} 引用了不存在的 shot_id：{shot_id} | `lint_checks.storyboard.check_storyboards`（75–372，触发 155） |
| `shot_beat_type_invalid` | error | {shot_id} beat_type 无效，必须是 beat_types.json 的 keys 之一：{sorted(valid_beat_types)}。 | `lint_checks.rhythm.check_shot_rhythm_fields`（101–116，触发 113） |
| `shot_duration_total_mismatch` | error | shots.duration_s 之和必须等于 storyboard.duration_s。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 141） |
| `shot_id_duplicate` | error | {scope} 中 shot_id 重复：{value} | `lint_checks.common.check_unique`（200–214，触发 211） |
| `shot_id_missing` | error | {scope} 缺少 shot_id。 | `lint_checks.common.check_unique`（200–214，触发 208） |
| `shot_segment_mismatch` | error | {shot_id} 的 segment_id 与 segments[].shot_ids 不一致。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 157） |
| `shot_unknown_segment` | error | shots 中引用了不存在的 segment_id：{sorted(unknown_segment_refs)} | `lint_checks.storyboard.check_storyboards`（75–372，触发 197） |
| `shots_covered_multiple_times` | error | 以下镜头被多个 segment 重复覆盖：{sorted(duplicated)} | `lint_checks.storyboard.check_storyboards`（75–372，触发 194） |
| `shots_not_covered` | error | 以下镜头未被任何 segment 覆盖：{sorted(missing)} | `lint_checks.storyboard.check_storyboards`（75–372，触发 192） |
| `source_event_uncovered` | error | {bid} dropped 需对应源版本的明确删戏授权，reason 不解除覆盖 | `content_first.validate_coverage`（147–186，触发 177） |
| `source_event_uncovered` | error | {bid} 处置枚举无效 | `content_first.validate_coverage`（147–186，触发 179） |
| `source_event_uncovered` | error | {bid} 未被真实目标镜头的时间项承接 | `content_first.validate_coverage`（147–186，触发 170） |
| `source_event_uncovered` | error | {eid} 缺必要事实摘要 | `content_first.source_index_from_contract`（33–91，触发 73） |
| `source_event_uncovered` | error | {scene.get('scene_id')} 需 events 源索引（不设数量） | `content_first.source_index_from_contract`（33–91，触发 59） |
| `source_event_uncovered` | error | 事件索引必须是对象 | `content_first.source_index_from_contract`（33–91，触发 63） |
| `source_event_uncovered` | error | 未知/重复处置 {bid} | `content_first.validate_coverage`（147–186，触发 163） |
| `source_event_uncovered` | error | 源事件处置集合不符，缺失 {sorted(expected - seen)} | `content_first.validate_coverage`（147–186，触发 181） |
| `source_event_uncovered` | error | 覆盖行必须是对象 | `content_first.validate_coverage`（147–186，触发 159） |
| `source_event_uncovered` | error | 需要 beat_coverage 多对多承接 | `content_first.validate_coverage`（147–186，触发 152） |
| `source_line_uncovered` | error | speech_lines 必须是数组，可空 | `content_first.source_index_from_contract`（33–91，触发 77） |
| `source_line_uncovered` | error | {uid} 说话者与源台词不符 | `timeline_core.reconcile_timeline`（153–286，触发 190） |
| `source_line_uncovered` | error | 单镜发声分片须保留完整源台词 | `preflight_video.validate_compilation_map`（51–123，触发 120） |
| `source_line_uncovered` | error | 台词索引必须是对象 | `content_first.source_index_from_contract`（33–91，触发 81） |
| `source_line_uncovered` | error | 已知台词未出现在对应发声块 | `h3_contract.prepare_request`（339–411，触发 395） |
| `source_line_uncovered` | error | 编译映射的逐字人声须来自当前源台词，不能省略或换文 | `preflight_video.validate_compilation_map`（51–123，触发 123） |
| `source_line_uncovered` | error | 缺人声 {sorted(missing)} | `content_first.validate_coverage`（147–186，触发 185） |
| `source_line_uncovered` | error | 跨镜/跨 SEG 需明确逐字发声分片，不由秒数猜词 | `preflight_video.validate_compilation_map`（51–123，触发 115） |
| `source_revision_mismatch` | error | script contract 缺 scenes | `content_first.source_index_from_contract`（33–91，触发 37） |
| `source_revision_mismatch` | error | source_script 需 file/revision/sha256 | `timeline_core.validate_timeline_shape`（77–150，触发 89） |
| `source_revision_mismatch` | error | {eid} source_excerpt 不在对应场次原文 | `content_first.source_index_from_contract`（33–91，触发 71） |
| `source_revision_mismatch` | error | {lid} 台词不在对应源场次 | `content_first.source_index_from_contract`（33–91，触发 89） |
| `source_revision_mismatch` | error | {sid} 需唯一场次标题以定位源原文 | `content_first.source_index_from_contract`（33–91，触发 49） |
| `source_revision_mismatch` | error | 剧本正文与源索引 SHA 不一致 | `content_first.load_source`（94–144，触发 106） |
| `source_revision_mismatch` | error | 无法核对源剧本: {exc} | `content_first.load_source`（94–144，触发 143） |
| `source_revision_mismatch` | error | 时间输入不是当前源剧本文件/版本 | `content_first.load_source`（94–144，触发 103） |
| `source_revision_mismatch` | error | 源剧本正文 SHA 不符。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 169） |
| `source_revision_mismatch` | error | 源场次 ID 必须唯一且非空 | `content_first.source_index_from_contract`（33–91，触发 44） |
| `source_revision_mismatch` | error | 源确认 ID 不存在或重复 | `h3_contract.dependency_snapshot`（280–307，触发 303） |
| `source_revision_mismatch` | error | 缺当前源剧本 SHA/版本对应的真实确认来源 | `content_first.load_source`（94–144，触发 119） |
| `speech_line_invalid` | error | speech_lines 第 {index} 条必须是对象。 | `lint_checks.prompts.check_prompt_markers`（107–161，触发 153） |
| `speech_line_spoken_text_missing` | error | speech_lines 第 {index} 条缺少 spoken_text。 | `lint_checks.prompts.check_prompt_markers`（107–161，触发 157） |
| `speech_line_voice_anchor_inconsistent` | error | {segment_label} speech_lines 第 {index} 条 voice_id={voice_id} 的 voice_anchor 必须与同一人物前文完全一致。 | `lint_checks.prompts.check_voice_anchor_consistency`（267–286，触发 286） |
| `speech_line_voice_anchor_missing` | error | {segment_label} speech_lines 第 {index} 条有 voice_id 但缺少固定 voice_anchor。 | `lint_checks.prompts.check_voice_anchor_consistency`（267–286，触发 280） |
| `speech_line_voice_anchor_missing` | error | {segment_label} speech_lines 第 {index} 条未传 VOICE 音频时必须填写固定 voice_anchor。 | `lint_checks.prompts.check_voice_audio_inputs`（221–264，触发 237） |
| `speech_line_voice_input_missing` | error | {segment_label} speech_lines 第 {index} 条 voice_id 未在 voice_inputs 中登记：{voice_id} | `lint_checks.prompts.check_voice_audio_inputs`（221–264，触发 264） |
| `speech_span_discontinuous` | error | {uid} 跨镜连续发声的绝对时间不连续 | `timeline_core.reconcile_timeline`（153–286，触发 278） |
| `speech_span_discontinuous` | error | 跨 SEG 发声须有真实实施方式和声音承接审校引用 | `preflight_video.validate_compilation_map`（51–123，触发 89） |
| `speech_span_incomplete` | error | {uid} 分片未覆盖完整演读估计 | `timeline_core.reconcile_timeline`（153–286，触发 282） |
| `speech_span_incomplete` | error | {uid} 分片遗漏/重叠/越界 | `timeline_core.reconcile_timeline`（153–286，触发 276） |
| `speech_span_incomplete` | error | 发声分片须为对象数组 | `preflight_video.validate_compilation_map`（51–123，触发 63） |
| `speech_span_incomplete` | error | 发声分片须唯一对应实际镜头及 utterance，不得漏文、错绑或重复 | `preflight_video.validate_compilation_map`（51–123，触发 71） |
| `speech_span_incomplete` | error | 发声分片须引用实际人声事件 | `preflight_video.validate_compilation_map`（51–123，触发 66） |
| `speech_span_incomplete` | error | 声音承接须明确完整逐字分片 | `preflight_video.validate_compilation_map`（51–123，触发 105） |
| `speech_span_incomplete` | error | 跨镜/跨 SEG 发声分片必须按 utterance 顺序逐字覆盖源台词，无遗漏或重复 | `preflight_video.validate_compilation_map`（51–123，触发 112） |
| `speech_timing_basis_invalid` | error | timing_basis 字段无效 | `timeline_core.validate_timeline_shape`（77–150，触发 102） |
| `speech_timing_basis_invalid` | error | {uid} 测量需本句实存音频/指纹/范围；音色样音不算 | `timeline_core.reconcile_timeline`（153–286，触发 203） |
| `speech_timing_basis_invalid` | error | {uid} 缺演读依据 | `timeline_core.reconcile_timeline`（153–286，触发 193） |
| `speech_timing_basis_invalid` | error | {uid} 需说明本次演读估计 | `timeline_core.reconcile_timeline`（153–286，触发 196） |
| `state_ref_invalid` | error | {owner} 的 state_refs 必须是非空字符串。 | `lint_checks.prompts.check_state_ref`（68–78，触发 70） |
| `state_ref_unknown` | error | {owner} 引用了不存在的状态资产：{ref} | `lint_checks.prompts.check_state_ref`（68–78，触发 73） |
| `state_refs_invalid` | error | {keyframe_id or '关键帧'} state_refs 必须是数组。 | `lint_checks.keyframes.check_keyframes`（15–116，触发 84） |
| `storyboard_fifteen_columns_missing` | error | 完整分镜表必须包含一个十五列表格。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 114） |
| `storyboard_required_role_not_inherited` | error | {segment_id} 未继承 storyboard.required_reference_roles：{missing} | `lint_checks.video.check_video`（26–210，触发 102） |
| `storyboard_required_role_not_passed` | error | {segment_id} 的 storyboard.required_reference_roles 未真实传入：{missing} | `lint_checks.video.check_video`（26–210，触发 105） |
| `storyboard_shape_invalid` | error | storyboard 必须包含 shots 和 segments 数组。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 119） |
| `storyboard_source_markdown_invalid` | error | storyboard.source_markdown 必须指向 {expected_source_markdown}。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 104） |
| `storyboard_source_markdown_missing` | error | 十五列完整分镜表文件不存在。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 106） |
| `storyboard_source_markdown_unreadable` | error | 十五列完整分镜表无法读取：{exc} | `lint_checks.storyboard.check_storyboards`（75–372，触发 111） |
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
| `technical_handle_unresolved` | error | 组 {gid} 的技术尾余量需末镜结束处非 speech 过程延续设计 | `timeline_core.compute_groups`（289–360，触发 338） |
| `timeline_dependency_conflict` | error | {eid} 开始早于 {ref} 结束；返回导演设计，不自动移动 | `timeline_core.reconcile_timeline`（153–286，触发 259） |
| `timeline_dependency_cycle` | error | after 中存在自依赖或循环 | `timeline_core.reconcile_timeline`（153–286，触发 270） |
| `timeline_field_unknown` | error | speech 文本只回指 utterance，不另建权威 | `timeline_core.validate_timeline_shape`（77–150，触发 138） |
| `timeline_field_unknown` | error | 不支持字段 {key}；核算不接受预算或动作/反应计数 | `timeline_core._unknown`（67–74，触发 73） |
| `timeline_field_unknown` | error | 非 speech 不能携带 utterance | `timeline_core.validate_timeline_shape`（77–150，触发 143） |
| `timeline_id_duplicate` | error | 无效/重复 line_id {lid} | `content_first.source_index_from_contract`（33–91，触发 87） |
| `timeline_id_duplicate` | error | 无效/重复源事件 {eid} | `content_first.source_index_from_contract`（33–91，触发 69） |
| `timeline_id_duplicate` | error | 重复 {kind} ID: {value} | `timeline_core.reconcile_timeline`（153–286，触发 167） |
| `timeline_number_invalid` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 143） |
| `timeline_number_invalid` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `lint_checks.storyboard.check_storyboards`（75–372，触发 164） |
| `timeline_number_invalid` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `timeline_core.reconcile_timeline`（153–286，触发 176） |
| `timeline_ref_unknown` | error | {eid} after 引用不存在: {ref} | `timeline_core.reconcile_timeline`（153–286，触发 254） |
| `timeline_ref_unknown` | error | {eid} 找不到 utterance {uid} | `timeline_core.reconcile_timeline`（153–286，触发 234） |
| `timeline_ref_unknown` | error | {eid} 找不到源引用 {ref} | `timeline_core.reconcile_timeline`（153–286，触发 224） |
| `timeline_ref_unknown` | error | {uid} 找不到 line:{line_id} | `timeline_core.reconcile_timeline`（153–286，触发 188） |
| `timeline_shape_invalid` | error | episode_id 必须为 ep_N | `timeline_core.validate_timeline_shape`（77–150，触发 82） |
| `timeline_shape_invalid` | error | scene_id 必须非空字符串 | `timeline_core.validate_timeline_shape`（77–150，触发 112） |
| `timeline_shape_invalid` | error | scenes 必须是非空数组 | `timeline_core.validate_timeline_shape`（77–150，触发 105） |
| `timeline_shape_invalid` | error | shot_id 必须非空字符串 | `timeline_core.validate_timeline_shape`（77–150，触发 124） |
| `timeline_shape_invalid` | error | speech 需 utterance_id/utterance_offset_s | `timeline_core.validate_timeline_shape`（77–150，触发 136） |
| `timeline_shape_invalid` | error | utterance/line/speaker 需非空 ID | `timeline_core.validate_timeline_shape`（77–150，触发 98） |
| `timeline_shape_invalid` | error | utterances 必须为数组，可空 | `timeline_core.validate_timeline_shape`（77–150，触发 92） |
| `timeline_shape_invalid` | error | {field} 必须为字符串数组 | `timeline_core.validate_timeline_shape`（77–150，触发 149） |
| `timeline_shape_invalid` | error | {kind} ID 必须非空 | `timeline_core.reconcile_timeline`（153–286，触发 164） |
| `timeline_shape_invalid` | error | 场次必须有 shots | `timeline_core.validate_timeline_shape`（77–150，触发 117） |
| `timeline_shape_invalid` | error | 必须是对象 | `timeline_core._unknown`（67–74，触发 69） |
| `timeline_shape_invalid` | error | 未知过程 kind | `timeline_core.validate_timeline_shape`（77–150，触发 133） |
| `timeline_shape_invalid` | error | 每镜至少一个时间过程 | `timeline_core.validate_timeline_shape`（77–150，触发 127） |
| `timeline_shape_invalid` | error | 非 speech 需非空 process | `timeline_core.validate_timeline_shape`（77–150，触发 141） |
| `timeline_shot_set_mismatch` | error | 分镜与时间输入的镜头集合/顺序不一致 | `content_first.reconcile_storyboard`（207–249，触发 214） |
| `timeline_shot_set_mismatch` | error | 分镜阅读稿不可用: {exc} | `content_first.reconcile_storyboard`（207–249，触发 248） |
| `timeline_shot_set_mismatch` | error | 十五列阅读稿的镜头集合/顺序需与同源时间输入一致 | `content_first.check_reading_times`（298–312，触发 301） |
| `timing_budget_input_forbidden` | error | 不支持字段 {key}；核算不接受预算或动作/反应计数 | `timeline_core._unknown`（67–74，触发 73） |
| `timing_input_invalid` | error | 当前时间合同不可核对：{exc} | `lint_checks.rhythm.check_rhythm_reconciliation`（119–130，触发 130） |
| `timing_output_drift` | error | {expected['shot_id']} {field} 与同源重算不符 | `content_first.reconcile_storyboard`（207–249，触发 219） |
| `timing_output_drift` | error | {shot['shot_id']} 阅读稿时间列不符，需同源渲染 | `content_first.check_reading_times`（298–312，触发 311） |
| `timing_output_drift` | error | 分镜总长/规范时间指纹不符 | `content_first.reconcile_storyboard`（207–249，触发 221） |
| `tool_capabilities_invalid` | error | 真实 H3 能力缺失，不能跳过 pack。 | `lint_checks.rhythm.check_rhythm_reconciliation`（119–130，触发 124） |
| `tool_capabilities_invalid` | error | 真实工具能力缺失或损坏: {exc} | `timeline_core.compute_groups`（289–360，触发 302） |
| `tool_duration_unrepresentable` | error | 组 {gid} 内容 {seconds(content)}s 超真实能力；保留设计，返回导演/用户处理 | `timeline_core.compute_groups`（289–360，触发 329） |
| `tool_duration_unrepresentable` | error | 请求时长不在真实整数能力范围；不自动取整 | `h3_contract._parameters`（163–210，触发 173） |
| `tool_duration_unrepresentable` | error | 请求时长必须为合法整数秒 | `h3_contract._parameters`（163–210，触发 171） |
| `true_one_take_shot_count_invalid` | error | {label} 标记为 true_one_take 时必须且只能包含 1 个镜头。 | `lint_checks.rhythm.check_segment_shot_count`（53–71，触发 70） |
| `video_confirmation_after_tool_call` | error | 工具事实和时间需在确认之后 | `video_confirmations.validate_confirmations`（22–151，触发 150） |
| `video_duration_invalid` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `lint_checks.video.check_video`（26–210，触发 60） |
| `video_duration_invalid` | error | 运行时说明表达式：str(exc)；运行结果给出实际对象与详情，按定位核对完整函数及依赖。 | `lint_checks.video.check_video`（26–210，触发 75） |
| `video_duration_mismatch` | error | video 总长需等于各整数请求时长之和。 | `lint_checks.video.check_video`（26–210，触发 58） |
| `video_edit_source_invalid` | error | video_edit 必须且只能登记一个 source_video_for_edit 源视频。 | `lint_checks.video.check_video`（26–210，触发 108） |
| `video_generation_confirmation_attempt_invalid` | error | 实际生成尝试需递增 | `video_confirmations.validate_confirmations`（22–151，触发 89） |
| `video_generation_confirmation_id_duplicate` | error | 确认需唯一稳定 ID | `video_confirmations.validate_confirmations`（22–151，触发 49） |
| `video_generation_confirmation_invalid` | error | 历史确认必须是对象 | `video_confirmations.validate_confirmations`（22–151，触发 43） |
| `video_generation_confirmation_missing` | error | {seg.get('segment_id')} 缺有效生成确认 | `video_confirmations.validate_confirmations`（22–151，触发 139） |
| `video_generation_confirmation_not_latest` | error | 生成结果须引用最新有效确认 | `video_confirmations.validate_confirmations`（22–151，触发 146） |
| `video_generation_confirmation_overlap` | error | 重新确认需显式替代覆盖各 SEG 的最新有效确认，历史保留 | `video_confirmations.validate_confirmations`（22–151，触发 85） |
| `video_generation_confirmation_range_invalid` | error | 冻结请求索引必须连续整数 | `video_confirmations.validate_confirmations`（22–151，触发 77） |
| `video_generation_confirmation_time_invalid` | error | 历史确认必须按带时区实际时间递增 | `video_confirmations.validate_confirmations`（22–151，触发 53） |
| `video_generation_confirmations_missing` | error | generation_confirmations 必须为数组 | `video_confirmations.validate_confirmations`（22–151，触发 26） |
| `video_generation_count_mismatch` | error | 批次范围/数量不符冻结请求 | `video_confirmations.validate_confirmations`（22–151，触发 80） |
| `video_generation_current_snapshot_mismatch` | error | {seg.get('segment_id')} 只与覆盖它的最新有效确认比较；参数变更须重新确认 | `video_confirmations.validate_confirmations`（22–151，触发 143） |
| `video_generation_displayed_quantity_mismatch` | error | 展示数量不符冻结请求 | `video_confirmations.validate_confirmations`（22–151，触发 113） |
| `video_generation_interaction_confirmation_missing` | error | 执行确认需真实 AskUserQuestion generate 和用户原文 | `video_confirmations.validate_confirmations`（22–151，触发 57） |
| `video_generation_parameter_table_field_missing` | error | 展示参数缺 {field} | `video_confirmations.validate_confirmations`（22–151，触发 111） |
| `video_generation_parameter_table_missing` | error | 需保存实际展示参数 | `video_confirmations.validate_confirmations`（22–151，触发 107） |
| `video_generation_segment_details_not_displayed` | error | 确认文本需展示每段冻结请求长度 | `video_confirmations.validate_confirmations`（22–151，触发 118） |
| `video_generation_segment_duration_mismatch` | error | 历史确认时长按各自冻结请求核验 | `video_confirmations.validate_confirmations`（22–151，触发 104） |
| `video_generation_snapshot_invalid` | error | 冻结快照必须是有限数值组成的合法 JSON | `video_confirmations.validate_confirmations`（22–151，触发 67） |
| `video_generation_snapshot_invalid` | error | 冻结请求的 SEG ID 必须非空且唯一 | `video_confirmations.validate_confirmations`（22–151，触发 74） |
| `video_generation_snapshot_invalid` | error | 快照每段需整数请求时长和对应实际参数 | `video_confirmations.validate_confirmations`（22–151，触发 99） |
| `video_generation_snapshot_invalid` | error | 快照缺预检 binding_id | `video_confirmations.validate_confirmations`（22–151，触发 101） |
| `video_generation_snapshot_invalid` | error | 每次确认需冻结本批连续 1–2 段请求 | `video_confirmations.validate_confirmations`（22–151，触发 62） |
| `video_generation_snapshot_mismatch` | error | 历史确认快照 SHA 不符，不能用当前 SEG 覆盖历史 | `video_confirmations.validate_confirmations`（22–151，触发 70） |
| `video_generation_storyboard_field_missing` | error | 预览缺实际 {field} | `video_confirmations.validate_confirmations`（22–151，触发 130） |
| `video_generation_storyboard_rows_invalid` | error | 需保存实际五列预览 | `video_confirmations.validate_confirmations`（22–151，触发 121） |
| `video_generation_storyboard_rows_invalid` | error | 预览行必须是对象 | `video_confirmations.validate_confirmations`（22–151，触发 123） |
| `video_generation_storyboard_segment_mismatch` | error | 历史五列表按冻结请求核验 | `video_confirmations.validate_confirmations`（22–151，触发 126） |
| `video_input_field_missing` | error | video_inputs.{field} 必须填写。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 40） |
| `video_input_file_missing` | error | 输入文件不存在或不是项目相对路径：{file_value} | `lint_checks.prompts.ordered_inputs`（15–49，触发 44） |
| `video_input_invalid` | error | video_inputs 每项必须是对象。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 25） |
| `video_input_order_invalid` | error | video_inputs.order 必须是整数。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 31） |
| `video_input_order_not_contiguous` | error | video_inputs.order 必须从 1 连续递增。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 48） |
| `video_input_role_invalid` | error | video_inputs.role 无效：{role} | `lint_checks.prompts.ordered_inputs`（15–49，触发 36） |
| `video_inputs_invalid` | error | video_inputs 必须是数组。 | `lint_checks.prompts.ordered_inputs`（15–49，触发 19） |
| `video_quality_gate_blocked_claim` | error | {segment_id} 存在阻断项，不能标记 quality_gate=pass。 | `lint_checks.video.check_video`（26–210，触发 206） |
| `video_quality_gate_blockers_invalid` | error | {segment_id}.quality_gate.blockers 必须是数组。 | `lint_checks.video.check_video`（26–210，触发 203） |
| `video_quality_gate_invalid` | error | {segment_id} 必须记录 quality_gate 状态。 | `lint_checks.video.check_video`（26–210，触发 199） |
| `video_reference_unknown_keyframe` | error | {segment_id} 引用了不存在的关键帧：{source_id} | `lint_checks.video.check_video`（26–210，触发 123） |
| `video_segment_duration_mismatch` | error | {segment_id} 请求时长必须与分镜 request_duration_s 一致。 | `lint_checks.video.check_video`（26–210，触发 73） |
| `video_segment_invalid` | error | segments 每项必须是对象。 | `lint_checks.video.check_video`（26–210，触发 64） |
| `video_segment_missing` | error | video_manifest 缺少 storyboard segment：{missing_segments} | `lint_checks.video.check_video`（26–210，触发 52） |
| `video_segment_not_accepted` | error | {segment_id or '视频片段'} 必须在进入成片阶段前登记 status=accepted。 | `lint_checks.video.check_video`（26–210，触发 187） |
| `video_segment_not_ready_for_confirmation` | error | {segment_id or '视频片段'} 在发起拼接确认前必须登记 status=candidate 或 accepted。 | `lint_checks.video.check_video`（26–210，触发 189） |
| `video_segment_output_missing` | error | {segment_id} 已进入候选状态，但 output_file 不存在。 | `lint_checks.video.check_video`（26–210，触发 191） |
| `video_segment_unplanned` | error | video_manifest 含 storyboard 中不存在的 segment：{extra_segments} | `lint_checks.video.check_video`（26–210，触发 54） |
| `video_segments_invalid` | error | video_manifest.segments 必须是数组。 | `lint_checks.video.check_video`（26–210，触发 44） |
| `video_state_refs_missing` | error | {segment.get('segment_id') or 'segment'} 传入角色/道具状态参考图时必须登记 approved state_refs。 | `lint_checks.prompts.check_video_state_refs`（199–207，触发 204） |
| `video_status_invalid` | error | 视频片段状态无效：{status} | `lint_checks.video.check_video`（26–210，触发 185） |
| `video_tool_mode_invalid` | error | {segment_id or 'segment'} tool_mode 无效：{tool_mode} | `lint_checks.video.check_video`（26–210，触发 82） |
| `video_unknown_segment` | error | 视频引用了分镜中不存在的 segment_id：{segment_id} | `lint_checks.video.check_video`（26–210，触发 68） |
| `visual_reference_decision_invalid` | error | {asset_id} visual_reference_decision 无效：{visual_reference_decision} | `lint_checks.assets.check_assets`（182–471，触发 239） |
| `voice_audio_input_missing` | error | {segment_label} 支持音频输入且有 speech_lines 时必须上传 approved VOICE 音频。 | `lint_checks.prompts.check_voice_audio_inputs`（221–264，触发 241） |
| `voice_audio_support_flag_missing` | error | {segment_label} 已传 voice_audio_reference 时 audio_input_supported 必须为 true。 | `lint_checks.prompts.check_voice_audio_inputs`（221–264，触发 243） |
| `voice_inputs_incomplete` | error | {segment_label} voice_inputs 必须填写 voice_id 和 resource_id。 | `lint_checks.prompts.check_voice_audio_inputs`（221–264，触发 258） |
| `voice_inputs_missing` | error | {segment_label} 有 speech_lines 时必须登记 voice_inputs。 | `lint_checks.prompts.check_voice_audio_inputs`（221–264，触发 245） |
| `voice_inputs_without_audio_reference` | error | {segment_label} 未传 VOICE 音频时不得登记 voice_inputs；请改用 speech_lines.voice_anchor 作为文字音色锚点。 | `lint_checks.prompts.check_voice_audio_inputs`（221–264，触发 232） |
| `voice_sample_duration_invalid` | error | {label} 音色 {duration}s 不满足能力档案的音频参考范围 {ranges}；资产阶段处理后试听，不自动补静音或批准。 | `lint_checks.assets.check_voice_sample`（96–141，触发 134） |
| `voice_sample_duration_mismatch` | error | {label} 登记时长与本地音频实测不同。 | `lint_checks.assets.check_voice_sample`（96–141，触发 139） |
| `voice_sample_invalid` | error | {label} 音色技术核验失败：{exc} | `lint_checks.assets.check_voice_sample`（96–141，触发 141） |
| `voice_sample_source_invalid` | error | {asset_id} 原批准记录未登记为 voice。 | `lint_checks.assets.check_reused_voice_sample`（144–179，触发 177） |
| `voice_sample_source_invalid` | error | {asset_id} 音色复用来源必须指向更早分集。 | `lint_checks.assets.check_reused_voice_sample`（144–179，触发 156） |
| `voice_sample_source_invalid` | error | {asset_id} 音色复用链缺唯一、文件一致的 approved 来源。 | `lint_checks.assets.check_reused_voice_sample`（144–179，触发 172） |
| `world_fact_category_invalid` | error | 第 {index} 条世界事实 category 无效：{fact.get('category')} | `lint_checks.causal.check_world_facts`（14–32，触发 30） |
| `world_fact_incomplete` | error | 第 {index} 条世界事实缺少 statement 或 source（剧本出处）。 | `lint_checks.causal.check_world_facts`（14–32，触发 32） |
| `world_fact_invalid` | error | 第 {index} 条世界事实必须是对象。 | `lint_checks.causal.check_world_facts`（14–32，触发 27） |
| `world_facts_missing` | error | storyboard 必须登记 inherited_world_facts：从剧本继承的季节/节日/时辰/天气等世界事实。 | `lint_checks.causal.check_world_facts`（14–32，触发 22） |
