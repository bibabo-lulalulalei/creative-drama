# 压缩恢复注册表（recovery-registry）

> **什么时候读这页**：上下文被自动压缩后、新会话接手项目，或不确定当前进度时，先从本页定位状态与原始参考。
>
恢复先读制作状态定位当前集/阶段，再按 confirmation_id 读取真实有效确认及用户条件，不能只看最后几行。摘要只用于定位；必须回读资产 registry、usage、真实文件或原样 URL、有效确认及用户条件，再判断能否复用，不继承摘要中的“缺失/不可用/已批准”等断言。读取 drama_plan.duration_contract 的来源确认、当前规划预测、episode.planned_content_duration_s、时间输入和分镜版本；生成前另读当前 gen.preflight/request_snapshot/最新有效确认，生成后读取媒体实测及 adopted_cut_out。四种时间不可互相覆盖，摘要不能继承为预算。缺来源或未知归属时报告缺项，禁止猜测迁移。

按 `references/reference_map.json` 的当前阶段索引读取原始 Ref：制作使用 `full`，返修使用 `repair` 及最早受影响阶段的 `affected_*` 条件；阶段开始先读 common 与当前阶段导航，排错先按码查询完整规则说明和位置，任务需要时再读对应的完整 lint 合同卡或源码。恢复时按 `SKILL.md` 的动作触发表补齐 `skill-details.md` 的必要章节；原始合同不能变成可选备查。必要上游按依赖读取，不把 lint 卡当导演方法；卡片只说明客观检查，不证明内容可拍/审美。候选展示、质量合格、用户接受分开记录。

## 阶段 → 干什么 → 读什么

| 阶段 | 该阶段产出 | 必读（按需加载） | 关键约束（压缩最容易丢的三条） |
|---|---|---|---|
| planning | drama_plan.json + 参数确认表 | planning 索引对应原文 | 语言静默锁定入 language_contract 不展示；索引建立**在用户确认后**；字幕默认关闭 |
| script | 全局故事包 + 逐集 完整剧本.md + script_contract_ep_N.json | script 索引对应原文 | 产物只有 2 份/集；关系张力在 script_contract.relationship_tension；设定摘要现场渲染不落盘 |
| assets | CHR/SCN/PROP/VOICE/STYLE 资产 + registry/usage | assets 索引对应原文 | 只做当前集资产；复用优先查 registry；`--ref` 强制门 |
| storyboard | 总控卡 + 十五列分镜 + storyboard_ep_N.json + rhythm_input | storyboard 索引对应原文 | 内容设计先行；声明区间共享核算；内容/整数请求/技术尾余量分开；独立观看审校 |
| keyframes | 高光 KF 图 + keyframe_manifest | keyframes 索引对应原文 | 张数按真实用途需求统计，零需求按原阶段确认；档位跟随 aspect_ratio；KF≠FRM |
| video | SEG 片段 + H3 成稿 + video_manifest + FRM/SEAM 记录 | video 索引对应原文 | 导演包与成稿各自落盘；先预检再确认；continuous 后段须先锁实际出点和帧 |
| final | trim/concat/字幕 + delivery_manifest + 唯一成片 | delivery 索引对应原文 | fps 24；只交付一个视频版本；固定区域水印用 erase |

## 用户口头决定的抢救规则

将用户决定及其理由写入确认记录，供压缩恢复后继续遵守：

- 用户给出**理由/偏好/档位选择**时，当场在回复里复述确认，并提示用户："这个决定我会记入确认记录，下集继续沿用"
- 阶段确认的 AskUserQuestion 提交前，把当轮对话中的口头附加条件（如"语体偏古一点"）**写进该阶段确认的上下文说明**，随确认原文一起落盘 `用户确认记录.jsonl`
- 恢复后对关键口径不确定时：先查 `用户确认记录.jsonl` 与 `drama_plan.json.explicit_overrides`，仍没有就问用户一句话，**不要凭感觉选**

## lint 导航与按需读取

| 文件 | 何时读 |
|---|---|
| `common.md` 与 `<stage>.md` | 阶段开始的客观检查入口；报错后按码查完整规则 |
| `rules/<stage>.md` | 对应阶段的完整检查码、级别、说明和源码位置；按需排错 |
| `source-index.md` | 维护校验器时选择模块和函数 |
| `source-index/<module>.md` | 函数名 → 源文件与起止行；必要时可读完整目标模块及依赖 |
| `manifest.json` | 仅供生成器核对；运行 `--check` 获取结果 |

`scripts/drama_lint.py` 保留原命令入口，具体规则按职责放在 `scripts/lint_checks/`。常规创作只读短卡与所需原始 Ref；维护或排查校验器时，先查询所需位置：

```bash
python scripts/build_lint_contract.py --code file_missing
python scripts/build_lint_contract.py --symbol check_assets
python scripts/build_lint_contract.py --stage video
python scripts/build_lint_contract.py --module assets
```

查询由程序在进程内解析源码，返回匹配的文件、函数和行范围；`--code` 同时返回完整检查码、级别和规则说明，动态检查码也按源码中的实际有限取值定位，不执行被解析源码。新增无法解析的动态模板会明确报错，避免静默丢失索引。`--offset`、`--limit` 可在结果较多时主动分页，也可以直接读取定位到的完整目标模块。`rules/<stage>.md` 保留完整阶段规则，需要整体理解时可以完整读取，不必为排查单个检查码加载整个规则卡。

`line` / `end_line` 是函数范围，`issue_line` 是检查码产生位置。先按定位读取相关函数、模块和依赖；为了完整理解一个目标可以读取完整文件，不需要把固定行数限制当作规则。避免无目的地预读全部 lint 源码或所有合同卡。

短导航、模块小字典和完整规则卡由 AST 与实际 `STAGE_CHECKS` 生成。修改检查或移动函数后运行 `python scripts/build_lint_contract.py` 更新；`--check` 核对内容与行号是否漂移。这里不保存包含全部错误码定位的大 JSON 字典。
