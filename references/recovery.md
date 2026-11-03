# 压缩恢复协议

上下文被自动压缩后、新会话接手项目，或不确定当前进度时，先按本页定位状态与原始参考，再按当前阶段路由补读原始教学。

0. **治理包补载（必做）**：项目治理规则（控制合同全文、全局执行合同、状态/可见交付合同、统一目录与失效拓扑）只在规划阶段入口完整装载一次。若本会话未经历规划阶段，先运行 `python scripts/read_reference.py --stage planning --condition governance_reload --render` 一次取回全部治理章节正文，再继续后续步骤；阶段独有方法仍按下方第 4 步用当前阶段路由补齐。repair 模式入口本身已装载同一治理包，可直接从第 1 步开始。
1. 先读制作状态，定位当前集与阶段；按 `confirmation_id` 读取真实有效确认及用户条件，不能只看最后几行。
2. 摘要只用于定位：必须回读资产 registry、usage、真实文件或原样 URL、有效确认及用户条件，再判断能否复用，不继承摘要中的“缺失/不可用/已批准”等断言。
3. 读取 `drama_plan.duration_contract` 的来源确认、当前规划预测、`episode.planned_content_duration_s`、时间输入和分镜版本；生成前另读当前 `gen.preflight`/`request_snapshot`/最新有效确认，生成后读取媒体实测及 `adopted_cut_out`。四种时间不可互相覆盖，摘要不能继承为预算。
4. 按 `references/reference_map.json` 的当前阶段索引读取原始 Ref：制作用 `full`，返修用 `repair` 加最早受影响阶段的 `affected_*` 条件；正文用 `read_reference.py --stage <stage> --mode <full|repair> [--condition ...] --render` 一次取齐，不整文件 Read 必读章节；阶段硬门条（`skill-details.md` 的 `### <stage>`）含本阶段准出、确认类型与跨会话自检，必须读到；治理章节不随阶段重灌，缺失一律按第 0 步补载，原始合同不能变成可选备查。
5. 阶段开始先跑 `python scripts/build_reference_index.py --stdout --stage <stage>` 取阶段路由页；lint 排错先跑 `build_lint_contract.py --stage <stage>` 看入口，按码用 `--code` 查询，需要整体上下文跑 `--rules <stage>`（含 common 共享检查）现场生成，不整读 `scripts/lint_checks/` 源码，也不预读全部导航。
6. 候选展示、质量合格、用户接受分开记录；缺来源或未知归属时报告缺项，禁止猜测迁移。

## 压缩最容易丢的硬约束

| 阶段 | 压缩最容易丢的三条 |
|---|---|
| planning | 语言静默锁定入 `language_contract` 不展示；索引建立**在用户确认后**；字幕默认关闭 |
| script | 产物只有 2 份/集；关系张力在 `script_contract.relationship_tension`；设定摘要现场渲染不落盘 |
| assets | 只做当前集资产；复用优先查 registry；`--ref` 强制门 |
| storyboard | 内容设计先行；声明区间共享核算；内容/整数请求/技术尾余量分开；独立观看审校 |
| keyframes | 张数按真实用途需求统计，零需求按原阶段确认；档位跟随 `aspect_ratio`；KF≠FRM |
| video | 导演包与成稿各自落盘；先预检再确认；continuous 后段须先锁实际出点和帧 |
| delivery | fps 24；只交付一个视频版本；固定区域水印用 erase |

## 用户口头决定的抢救规则

将用户决定及其理由写入确认记录，供压缩恢复后继续遵守：

- 用户给出**理由/偏好/档位选择**时，当场在回复里复述确认，并提示用户："这个决定我会记入确认记录，下集继续沿用"
- 阶段确认的 AskUserQuestion 提交前，把当轮对话中的口头附加条件（如"语体偏古一点"）**写进该阶段确认的上下文说明**，随确认原文一起落盘 `用户确认记录.jsonl`
- 恢复后对关键口径不确定时：先查 `用户确认记录.jsonl` 与 `drama_plan.json.explicit_overrides`，仍没有就问用户一句话，**不要凭感觉选**
