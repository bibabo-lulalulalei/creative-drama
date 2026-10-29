# lint 检查合同 · skill 阶段

> 本卡片由 `scripts/build_lint_contract.py` 从 `drama_lint.py` 机读生成，禁止手改。
> 用途：开工前读这张卡知道本阶段 lint 会查什么；报错后按码查修复方向。
> 与源码不一致时以源码为准，并重跑 `python scripts/build_lint_contract.py --check`。

本阶段新增检查项：16。运行命令：`python scripts/drama_lint.py --stage skill`（skill 阶段在 skill 根目录运行）。

| 检查码 | 级别 | 查什么（源码原文消息） |
|---|---|---|
| `skill_frontmatter_missing` | error | SKILL.md 缺少合法的 YAML frontmatter。 |
| `skill_name_invalid` | error | Skill name 必须是 2-64 位小写字母、数字或单连字符。 |
| `skill_name_path_mismatch` | error | Skill name 必须与目录名一致。 |
| `skill_description_invalid` | error | Skill description 必须是非空、未加引号的单行标量。 |
| `skill_description_forbidden_text` | error | Skill description 含禁止的格式或占位内容。 |
| `skill_body_empty` | error | SKILL.md 正文不能为空。 |
| `skill_file_missing` | error | Skill 根目录缺少 SKILL.md。 |
| `skill_file_unreadable` | error | <动态生成，见源码> |
| `skill_reference_missing` | error | <动态生成，见源码> |
| `reference_map_missing` | error | 缺少 references/reference_map.json 阶段包索引。 |
| `reference_map_unreadable` | error | <动态生成，见源码> |
| `markdown_file_unreadable` | error | <动态生成，见源码> |
| `markdown_link_missing` | error | <动态生成，见源码> |
| `reference_map_file_missing` | error | <动态生成，见源码> |
| `reference_map_file_unreadable` | error | <动态生成，见源码> |
| `reference_map_anchor_unresolved` | error | <动态生成，见源码> |
