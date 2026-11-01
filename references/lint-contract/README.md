# 压缩恢复注册表（recovery-registry）

> **什么时候读这页**：上下文被自动压缩后（你突然"失忆"）、新会话接手项目、或任何"我不知道干到哪了"的时刻。这是恢复的第一跳，读它 ~1K，比重读阶段包便宜 50 倍。
>
恢复先读制作状态定位当前集/阶段，再按 confirmation_id 读取真实有效确认及用户条件，不能只看最后几行。读取 drama_plan.duration_contract 的来源确认、当前规划预测、episode.planned_content_duration_s、时间输入和分镜版本；生成前另读当前 gen.preflight/request_snapshot/最新有效确认，生成后读取媒体实测及 adopted_cut_out。四种时间不可互相覆盖，摘要不能继承为预算。缺来源或未知归属时报告缺项，禁止猜测迁移。

按当前任务加载对应阶段阅读包（轻量用真实 `--stage lightweight`，返修用 repair + affected 条件），再读 common 与阶段 lint 卡。必要上游按依赖读取，不把 lint 卡当导演方法；卡片只说明客观检查，不证明内容可拍/审美。候选展示、质量合格、用户接受分开记录。

## 阶段 → 干什么 → 读什么

| 阶段 | 该阶段产出 | 必读（按需加载） | 关键约束（压缩最容易丢的三条） |
|---|---|---|---|
| planning | drama_plan.json + 参数确认表 | planning 阶段包 | 语言静默锁定入 language_contract 不展示；索引建立**在用户确认后**；字幕默认关闭 |
| script | 全局故事包 + 逐集 完整剧本.md + script_contract_ep_N.json | script 阶段包 | 产物只有 2 份/集；关系张力在 script_contract.relationship_tension；设定摘要现场渲染不落盘 |
| assets | CHR/SCN/PROP/VOICE/STYLE 资产 + registry/usage | assets 阶段包 | 只做当前集资产；复用优先查 registry；`--ref` 强制门 |
| storyboard | 总控卡 + 十五列分镜 + storyboard_ep_N.json + rhythm_input | storyboard 阶段包 | 内容设计先行；声明区间共享核算；内容/整数请求/技术尾余量分开；独立观看审校 |
| keyframes | 高光 KF 图 + keyframe_manifest | keyframes 阶段包 | 张数按真实用途需求统计，零需求按原阶段确认；档位跟随 aspect_ratio；KF≠FRM |
| video | SEG 片段 + H3 成稿 + video_manifest + FRM/SEAM 记录 | video 阶段包 | 导演包与成稿各自落盘；先预检再确认；continuous 后段须先锁实际出点和帧 |
| final | trim/concat/字幕 + delivery_manifest + 唯一成片 | delivery 阶段包 | fps 24；只交付一个视频版本；固定区域水印用 erase |

## 用户口头决定的抢救规则

实测压缩会丢"为什么"（语体选 C 档的理由、否决某稿的原因——丢 9/11 份摘要）。抢救协议：

- 用户给出**理由/偏好/档位选择**时，当场在回复里复述确认，并提示用户："这个决定我会记入确认记录，下集继续沿用"
- 阶段确认的 AskUserQuestion 提交前，把当轮对话中的口头附加条件（如"语体偏古一点"）**写进该阶段确认的上下文说明**，随确认原文一起落盘 `用户确认记录.jsonl`
- 恢复后对关键口径不确定时：先查 `用户确认记录.jsonl` 与 `drama_plan.json.explicit_overrides`，仍没有就问用户一句话，**不要凭感觉选**

## lint 卡片目录（字典层入口）

| 文件 | 何时读 |
|---|---|
| `references/lint-contract/common.md` | 任何阶段跑 lint 前（状态机/目录/操作日志检查） |
| `references/lint-contract/<stage>.md` | 开工前 + lint 报错后按码反查 |
| `references/lint-contract/skill.md` | 改 skill 本身后自检 |
| `manifest.json` | 校验卡片是否与源码一致（`python scripts/build_lint_contract.py --check`） |

改了 `drama_lint.py` 之后必须重跑 `python scripts/build_lint_contract.py` 更新卡片，`--check` 会抓漂移。
