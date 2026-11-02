# lint 检查合同 · skill 阶段

> 由 build_lint_contract.py 从实际 STAGE_CHECKS 与共享调用图生成；按需读取。
> 只证明结构、来源、算术、依赖与技术合同；内容须按观看顺序独立审校。

运行：`python scripts/drama_lint.py <skill-root> --project-root <project> --stage skill`。

| 检查码 | 级别 | 查什么 | 来源 |
|---|---|---|---|
| `beat_library_desync` | error | 词汇生成物与源库不同，请重生成。 | `lint_checks.rhythm.check_beat_library_desync`（42–50，触发 48） |
| `beat_library_unavailable` | error | 可选词汇安装损坏：{exc} | `lint_checks.rhythm.check_beat_library_desync`（42–50，触发 50） |
| `creative_index_anchor_unresolved` | error | creative-index.md 的锚点 {anchor} 在 {rel} 中命中次数不等于 1。 | `lint_checks.skill.check_skill_package`（71–190，触发 165） |
| `creative_index_file_missing` | error | creative-index.md 指向的原文文件不存在或不可读：{rel} | `lint_checks.skill.check_skill_package`（71–190，触发 159） |
| `creative_index_file_undeclared` | error | creative-index.md 标题 {headings[0]} 之前未声明所属原文文件。 | `lint_checks.skill.check_skill_package`（71–190，触发 151） |
| `creative_index_missing` | error | 缺少 references/creative-index.md 创作方法小索引。 | `lint_checks.skill.check_skill_package`（71–190，触发 144） |
| `creative_index_unreadable` | error | creative-index.md 无法读取：{exc} | `lint_checks.skill.check_skill_package`（71–190，触发 146） |
| `markdown_file_unreadable` | error | Markdown 文件无法读取：{exc} | `lint_checks.skill.check_skill_package`（71–190，触发 176） |
| `markdown_link_missing` | error | Markdown 相对链接不存在：{raw_target} | `lint_checks.skill.check_skill_package`（71–190，触发 190） |
| `reference_map_anchor_unresolved` | error | 阶段 {stage_name} 的锚点 {anchor} 在 {rel} 中命中次数不等于 1。 | `lint_checks.skill.check_skill_package`（71–190，触发 138） |
| `reference_map_file_missing` | error | 阶段 {stage_name} 的原文文件不存在：{rel} | `lint_checks.skill.check_skill_package`（71–190，触发 129） |
| `reference_map_file_unreadable` | error | reference_map 引用文件无法读取：{rel}：{exc} | `lint_checks.skill.check_skill_package`（71–190，触发 134） |
| `reference_map_missing` | error | 缺少 references/reference_map.json 原文读取索引。 | `lint_checks.skill.check_skill_package`（71–190，触发 114） |
| `reference_map_path_outside_skill` | error | 阶段 {stage_name} 的原文路径越出 Skill：{rel} | `lint_checks.skill.check_skill_package`（71–190，触发 126） |
| `reference_map_unreadable` | error | reference_map.json 无法解析：{exc} | `lint_checks.skill.check_skill_package`（71–190，触发 117） |
| `skill_body_empty` | error | SKILL.md 正文不能为空。 | `lint_checks.skill.check_skill_package`（71–190，触发 102） |
| `skill_description_forbidden_text` | error | Skill description 含禁止的格式或占位内容。 | `lint_checks.skill.check_skill_package`（71–190，触发 100） |
| `skill_description_invalid` | error | Skill description 必须是非空、未加引号的单行标量。 | `lint_checks.skill.check_skill_package`（71–190，触发 98） |
| `skill_file_missing` | error | Skill 根目录缺少 SKILL.md。 | `lint_checks.skill.check_skill_package`（71–190，触发 76） |
| `skill_file_unreadable` | error | SKILL.md 无法读取：{exc} | `lint_checks.skill.check_skill_package`（71–190，触发 79） |
| `skill_frontmatter_missing` | error | SKILL.md 缺少合法的 YAML frontmatter。 | `lint_checks.skill.check_skill_package`（71–190，触发 84） |
| `skill_name_invalid` | error | Skill name 必须是 2-64 位小写字母、数字或单连字符。 | `lint_checks.skill.check_skill_package`（71–190，触发 94） |
| `skill_name_path_mismatch` | error | Skill name 必须与目录名一致。 | `lint_checks.skill.check_skill_package`（71–190，触发 96） |
| `skill_reference_missing` | error | SKILL.md 引用的本地文件不存在：{relative} | `lint_checks.skill.check_skill_package`（71–190，触发 108） |
