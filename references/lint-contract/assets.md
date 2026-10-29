# lint 检查合同 · assets 阶段

> 本卡片由 `scripts/build_lint_contract.py` 从 `drama_lint.py` 机读生成，禁止手改。
> 用途：开工前读这张卡知道本阶段 lint 会查什么；报错后按码查修复方向。
> 与源码不一致时以源码为准，并重跑 `python scripts/build_lint_contract.py --check`。

本阶段新增检查项：63。运行命令：`python scripts/drama_lint.py --stage assets`（skill 阶段在 skill 根目录运行）。

本阶段同时全量复核以下上游检查（报错时先读对应上游卡）：
- planning 阶段卡 · `check_stage_artifacts` —— assets 阶段产物存在性
- planning 阶段卡 · `check_episode_manifest_ids` —— episode_manifest 与 stage 绑定

| 检查码 | 级别 | 查什么（源码原文消息） |
|---|---|---|
| `reused_episode_assets_invalid` | error | <动态生成，见源码> |
| `assets_invalid` | error | asset_registry.assets 必须是数组。 |
| `asset_id_missing` | error | 资产缺少 asset_id。 |
| `asset_status_invalid` | error | <动态生成，见源码> |
| `visual_reference_decision_invalid` | error | <动态生成，见源码> |
| `image_gen_should_not_have_visual_inputs` | error | <动态生成，见源码> |
| `image_gen_visual_reference_available` | error | <动态生成，见源码> |
| `image_gen_visual_reference_decision_conflict` | error | <动态生成，见源码> |
| `image_edit_reference_missing` | error | <动态生成，见源码> |
| `image_edit_visual_reference_decision_conflict` | error | <动态生成，见源码> |
| `character_state_asset_requires_image_edit` | error | <动态生成，见源码> |
| `collective_usage_scope_mismatch` | error | <动态生成，见源码> |
| `reused_episode_asset_invalid` | error | <动态生成，见源码> |
| `reused_episode_source_missing` | error | <动态生成，见源码> |
| `reused_episode_asset_ref_missing` | error | <动态生成，见源码> |
| `reused_episode_asset_not_approved` | error | <动态生成，见源码> |
| `reused_episode_asset_duplicate` | error | <动态生成，见源码> |
| `episode_asset_duplicate` | error | <动态生成，见源码> |
| `episode_asset_status_invalid` | error | <动态生成，见源码> |
| `episode_visual_reference_decision_invalid` | error | <动态生成，见源码> |
| `episode_image_gen_should_not_have_visual_inputs` | error | <动态生成，见源码> |
| `episode_image_gen_visual_reference_available` | error | <动态生成，见源码> |
| `episode_image_gen_visual_reference_decision_conflict` | error | <动态生成，见源码> |
| `episode_image_edit_reference_missing` | error | <动态生成，见源码> |
| `episode_image_edit_visual_reference_decision_conflict` | error | <动态生成，见源码> |
| `episode_character_state_asset_requires_image_edit` | error | <动态生成，见源码> |
| `asset_entity_scope_invalid` | error | <动态生成，见源码> |
| `asset_entity_scope_not_character` | error | <动态生成，见源码> |
| `asset_version_duplicate` | error | <动态生成，见源码> |
| `asset_id_prefix_mismatch` | error | <动态生成，见源码> |
| `asset_file_missing` | error | <动态生成，见源码> |
| `project_visual_mode_missing_or_invalid` | error | <动态生成，见源码> |
| `style_asset_type_missing` | error | STYLE001 approved 前必须登记 style_asset_type=global_visual_language_moodboard。 |
| `style_asset_type_invalid` | error | STYLE001 必须登记为 global_visual_language_moodboard。 |
| `style_scene_atmosphere_links_missing` | error | STYLE001 approved 时 style_scene_atmosphere_links 必须是非空数组。 |
| `style_moodboard_contains_characters_unknown` | error | STYLE001 全局风格 moodboard 必须明确 contains_story_characters=false。 |
| `style_moodboard_contains_props_unknown` | error | STYLE001 全局风格 moodboard 必须明确 contains_story_props=false。 |
| `asset_usage_unknown_shared_asset` | error | <动态生成，见源码> |
| `asset_usage_shared_version_missing` | error | <动态生成，见源码> |
| `asset_usage_duplicate` | error | <动态生成，见源码> |
| `reused_episode_source_invalid` | error | <动态生成，见源码> |
| `reused_episode_asset_source_not_found` | error | <动态生成，见源码> |
| `reused_episode_asset_file_missing` | error | <动态生成，见源码> |
| `episode_project_visual_mode_missing_or_invalid` | error | <动态生成，见源码> |
| `episode_asset_file_missing` | error | <动态生成，见源码> |
| `collective_asset_scope_mismatch` | error | <动态生成，见源码> |
| `style_visual_language_missing` | error | STYLE001 必须登记色彩、光线、构图、材质或空间氛围等视觉语言。 |
| `asset_usage_unknown_shared_version` | error | <动态生成，见源码> |
| `reused_episode_asset_files_mismatch` | error | <动态生成，见源码> |
| `collective_asset_data_card_missing` | error | <动态生成，见源码> |
| `style_visual_language_too_sparse` | error | STYLE001 视觉语言至少填写两类：palette/lighting/composition/materials/space_atmosphere/texture_or_grain。 |
| `asset_usage_shared_not_approved` | error | <动态生成，见源码> |
| `character_entity_scope_invalid` | error | <动态生成，见源码> |
| `collective_character_id_invalid` | error | <动态生成，见源码> |
| `collective_profile_missing` | error | <动态生成，见源码> |
| `collective_group_type_missing` | error | <动态生成，见源码> |
| `collective_count_range_missing` | error | <动态生成，见源码> |
| `collective_voice_mode_invalid` | error | <动态生成，见源码> |
| `collective_asset_ref_mismatch` | error | <动态生成，见源码> |
| `collective_individual_voice_invalid` | error | <动态生成，见源码> |
| `collective_count_range_invalid` | error | <动态生成，见源码> |
| `collective_profile_field_missing` | error | <动态生成，见源码> |
| `collective_profile_field_invalid` | error | <动态生成，见源码> |
