# lint 检查合同 · planning 阶段

> 本卡片由 `scripts/build_lint_contract.py` 从 `drama_lint.py` 机读生成，禁止手改。
> 用途：开工前读这张卡知道本阶段 lint 会查什么；报错后按码查修复方向。
> 与源码不一致时以源码为准，并重跑 `python scripts/build_lint_contract.py --check`。

本阶段新增检查项：9。运行命令：`python scripts/drama_lint.py --stage planning`（skill 阶段在 skill 根目录运行）。

| 检查码 | 级别 | 查什么（源码原文消息） |
|---|---|---|
| `required_artifact_missing` | error | 缺少当前阶段所需产物。 |
| `combined_story_outline_reference_invalid` | error | <动态生成，见源码> |
| `storyboard_source_markdown_unreadable` | error | <动态生成，见源码> |
| `storyboard_fifteen_columns_missing` | error | 完整分镜表必须包含一个十五列表格。 |
| `combined_story_outline_unreadable` | error | <动态生成，见源码> |
| `highlight_ledger_invalid` | error | 完整模式 script_contract.highlight_ledger 必须是数组。 |
| `primary_highlight_missing` | error | 完整模式每集 script_contract.highlight_ledger 必须至少包含一个有效的 primary 亮点。 |
| `combined_story_outline_section_missing` | error | <动态生成，见源码> |
| `episode_id_mismatch` | error | <动态生成，见源码> |
