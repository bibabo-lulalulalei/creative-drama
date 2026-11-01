# lint 检查合同 · skill 阶段

> 由 build_lint_contract.py 从实际 STAGE_CHECKS 与共享调用图生成；禁止手改。
> 只证明结构、来源、算术、依赖与技术合同；内容须按观看顺序独立审校。

common 随生产阶段运行；skill 使用 `--stage skill`。

轻量走同一内核和单任务预检适配，不要求伪造完整模式上游。

| 检查码 | 级别 | 查什么 | 来源 |
|---|---|---|---|
| `beat_library_desync` | error | 词汇生成物与源库不同，请重生成。 | `drama_lint.check_beat_library_desync` |
| `beat_library_unavailable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_beat_library_desync` |
| `markdown_file_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_skill_package` |
| `markdown_link_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_skill_package` |
| `reference_map_anchor_unresolved` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_skill_package` |
| `reference_map_file_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_skill_package` |
| `reference_map_file_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_skill_package` |
| `reference_map_missing` | error | 缺少 references/reference_map.json 原文读取索引。 | `drama_lint.check_skill_package` |
| `reference_map_path_outside_skill` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_skill_package` |
| `reference_map_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_skill_package` |
| `skill_body_empty` | error | SKILL.md 正文不能为空。 | `drama_lint.check_skill_package` |
| `skill_description_forbidden_text` | error | Skill description 含禁止的格式或占位内容。 | `drama_lint.check_skill_package` |
| `skill_description_invalid` | error | Skill description 必须是非空、未加引号的单行标量。 | `drama_lint.check_skill_package` |
| `skill_file_missing` | error | Skill 根目录缺少 SKILL.md。 | `drama_lint.check_skill_package` |
| `skill_file_unreadable` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_skill_package` |
| `skill_frontmatter_missing` | error | SKILL.md 缺少合法的 YAML frontmatter。 | `drama_lint.check_skill_package` |
| `skill_name_invalid` | error | Skill name 必须是 2-64 位小写字母、数字或单连字符。 | `drama_lint.check_skill_package` |
| `skill_name_path_mismatch` | error | Skill name 必须与目录名一致。 | `drama_lint.check_skill_package` |
| `skill_reference_missing` | error | 动态消息；按当前对象及源码核对 | `drama_lint.check_skill_package` |
