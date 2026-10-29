# lint 检查合同 · keyframes 阶段

> 本卡片由 `scripts/build_lint_contract.py` 从 `drama_lint.py` 机读生成，禁止手改。
> 用途：开工前读这张卡知道本阶段 lint 会查什么；报错后按码查修复方向。
> 与源码不一致时以源码为准，并重跑 `python scripts/build_lint_contract.py --check`。

本阶段新增检查项：16。运行命令：`python scripts/drama_lint.py --stage keyframes`（skill 阶段在 skill 根目录运行）。

本阶段同时全量复核以下上游检查（报错时先读对应上游卡）：
- planning 阶段卡 · `check_stage_artifacts` —— keyframes 阶段产物存在性
- planning 阶段卡 · `check_episode_manifest_ids` —— episode_manifest 与 stage 绑定
- assets 阶段卡 · `check_assets` —— 资产索引
- assets 阶段卡 · `validate_collective_profiles` —— 群像画像一致性
- storyboard 阶段卡 · `check_beat_library_desync` —— 节拍库漂移
- storyboard 阶段卡 · `check_rhythm_reconciliation` —— 引擎对账
- storyboard 阶段卡 · `check_rhythm_diversity` —— 节奏健康度
- storyboard 阶段卡 · `check_storyboards` —— 分镜全链（keyframes 阶段也复核）

| 检查码 | 级别 | 查什么（源码原文消息） |
|---|---|---|
| `episode_id_mismatch` | error | keyframe_manifest episode_id 与目录不一致。 |
| `keyframes_invalid` | error | keyframes 必须是数组。 |
| `episode_keyframe_count_mismatch` | error | <动态生成，见源码> |
| `keyframe_unknown_segment` | error | <动态生成，见源码> |
| `keyframe_unknown_shot` | error | <动态生成，见源码> |
| `keyframe_role_invalid` | error | <动态生成，见源码> |
| `keyframe_highlight_index_invalid` | error | <动态生成，见源码> |
| `keyframe_file_missing` | error | <动态生成，见源码> |
| `keyframe_file_name_invalid` | error | <动态生成，见源码> |
| `keyframe_tool_not_image_edit` | error | <动态生成，见源码> |
| `keyframe_unplanned_segment` | error | <动态生成，见源码> |
| `keyframe_count_mismatch` | error | <动态生成，见源码> |
| `keyframe_unknown_used_segment` | error | <动态生成，见源码> |
| `asset_refs_invalid` | error | <动态生成，见源码> |
| `state_refs_invalid` | error | <动态生成，见源码> |
| `keyframe_highlight_index_duplicate` | error | <动态生成，见源码> |
