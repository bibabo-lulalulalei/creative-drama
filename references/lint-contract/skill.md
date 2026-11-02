# lint 检查导航 · skill 阶段

> 从实际 STAGE_CHECKS 生成；仅核结构、来源、算术、依赖与技术合同。

定位：`python scripts/build_lint_contract.py --stage skill`；报错用 `--code <码>`。
源码目录与分模块字典：[source-index.md](source-index.md)。

| 入口 symbol | 文件 | 行范围 |
|---|---|---|
| `lint_checks.skill.check_skill_package` | `scripts/lint_checks/skill.py` | 71–190 |
| `lint_checks.rhythm.check_beat_library_desync` | `scripts/lint_checks/rhythm.py` | 42–50 |
