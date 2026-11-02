# lint 检查导航 · keyframes 阶段

> 从实际 STAGE_CHECKS 生成；仅核结构、来源、算术、依赖与技术合同。

共享检查：[common](common.md)。

定位：`python scripts/build_lint_contract.py --stage keyframes`；报错用 `--code <码>`。
源码目录与分模块字典：[source-index.md](source-index.md)。

| 入口 symbol | 文件 | 行范围 |
|---|---|---|
| `lint_checks.stages.check_stage_artifacts` | `scripts/lint_checks/stages.py` | 64–173 |
| `lint_checks.stages.check_episode_manifest_ids` | `scripts/lint_checks/stages.py` | 28–35 |
| `lint_checks.assets.check_assets` | `scripts/lint_checks/assets.py` | 182–471 |
| `lint_checks.storyboard.check_storyboards` | `scripts/lint_checks/storyboard.py` | 75–372 |
| `lint_checks.keyframes.check_keyframes` | `scripts/lint_checks/keyframes.py` | 15–116 |
