# lint 检查导航 · common 阶段

> 从实际 STAGE_CHECKS 生成；仅核结构、来源、算术、依赖与技术合同。

定位：`python scripts/build_lint_contract.py --stage common`；报错用 `--code <码>`。
源码目录与分模块字典：[source-index.md](source-index.md)。

| 入口 symbol | 文件 | 行范围 |
|---|---|---|
| `lint_checks.planning.check_plan_durations` | `scripts/lint_checks/planning.py` | 13–159 |
| `lint_checks.stages.check_episode_directories` | `scripts/lint_checks/stages.py` | 14–25 |
| `lint_checks.stages.check_episode_entry_manifests` | `scripts/lint_checks/stages.py` | 38–61 |
| `lint_checks.state.check_state` | `scripts/lint_checks/state.py` | 158–356 |
| `lint_checks.state.check_operation_log_tools` | `scripts/lint_checks/state.py` | 114–134 |
