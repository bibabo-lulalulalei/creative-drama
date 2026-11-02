# lint 源码导航

> 自动生成；维护时查询后只读取目标函数范围。

查询：`python scripts/build_lint_contract.py --code <码>`；另支持 `--stage`、`--module`、`--symbol`。

| 模块 | 职责 | 文件 | 小字典 |
|---|---|---|---|
| `adopted_cut` | 实际采用出点合同。只核指纹/坐标，不判断… | `tools/video/adopted_cut.py` | [函数](source-index/adopted_cut.md) |
| `build_lint_contract` | Generate lint navigation and detailed, on-demand rule contra… | `scripts/build_lint_contract.py` | [函数](source-index/build_lint_contract.md) |
| `content_first` | 项目适配及只读对账；时间数学由 timeline_core … | `scripts/content_first.py` | [函数](source-index/content_first.md) |
| `drama_lint` | 只读流程检查：结构、算术、依赖、源版本与… | `scripts/drama_lint.py` | [函数](source-index/drama_lint.md) |
| `h3_contract` | H3 离线合同与同次快照请求准备。无凭证、HTT… | `tools/video/h3_contract.py` | [函数](source-index/h3_contract.md) |
| `lint_checks` | Focused checks behind the drama_lint command; use the genera… | `scripts/lint_checks/__init__.py` | [函数](source-index/lint_checks.md) |
| `lint_checks.assets` | Asset versions, reusable states, approved voice samples and … | `scripts/lint_checks/assets.py` | [函数](source-index/lint_checks.assets.md) |
| `lint_checks.causal` | World facts, beat coverage, collective profiles and causal l… | `scripts/lint_checks/causal.py` | [函数](source-index/lint_checks.causal.md) |
| `lint_checks.common` | Shared file, JSON, duration, table and issue helpers. | `scripts/lint_checks/common.py` | [函数](source-index/lint_checks.common.md) |
| `lint_checks.constants` | Shared stage names, exact enums and package-relative resourc… | `scripts/lint_checks/constants.py` | [函数](source-index/lint_checks.constants.md) |
| `lint_checks.delivery` | Accepted segment ordering, continuity reports and final adop… | `scripts/lint_checks/delivery.py` | [函数](source-index/lint_checks.delivery.md) |
| `lint_checks.keyframes` | Keyframe manifests, source shots and asset-reference checks. | `scripts/lint_checks/keyframes.py` | [函数](source-index/lint_checks.keyframes.md) |
| `lint_checks.planning` | Planning duration contracts and explicit confirmation bounds… | `scripts/lint_checks/planning.py` | [函数](source-index/lint_checks.planning.md) |
| `lint_checks.prompts` | Media inputs, reference markers, prompt contracts and genera… | `scripts/lint_checks/prompts.py` | [函数](source-index/lint_checks.prompts.md) |
| `lint_checks.rhythm` | Rhythm-library loading and objective storyboard timing check… | `scripts/lint_checks/rhythm.py` | [函数](source-index/lint_checks.rhythm.md) |
| `lint_checks.skill` | Skill frontmatter, reference-index anchors and Markdown link… | `scripts/lint_checks/skill.py` | [函数](source-index/lint_checks.skill.md) |
| `lint_checks.stages` | Episode directories, manifest identity and required stage ar… | `scripts/lint_checks/stages.py` | [函数](source-index/lint_checks.stages.md) |
| `lint_checks.state` | Workflow state, user confirmations and operation-log checks. | `scripts/lint_checks/state.py` | [函数](source-index/lint_checks.state.md) |
| `lint_checks.storyboard` | Storyboard structure, coverage, references and asset reconci… | `scripts/lint_checks/storyboard.py` | [函数](source-index/lint_checks.storyboard.md) |
| `lint_checks.video` | Video manifests, generation confirmations and quality accept… | `scripts/lint_checks/video.py` | [函数](source-index/lint_checks.video.md) |
| `preflight_video` | 预检已形成的完整 SEG；不要求生成授权/结果… | `scripts/preflight_video.py` | [函数](source-index/preflight_video.md) |
| `rhythm_engine` | Content-first CLI：累计已经设计的时间、核对合… | `scripts/rhythm_engine.py` | [函数](source-index/rhythm_engine.md) |
| `timeline_core` | Content-first 时间核算：保留声明的安排，只检… | `scripts/timeline_core.py` | [函数](source-index/timeline_core.md) |
| `video_confirmations` | 冻结的历史生成确认与当前请求分开核对；只… | `scripts/video_confirmations.py` | [函数](source-index/video_confirmations.md) |
