# 压缩恢复协议

上下文被自动压缩后、新会话接手项目，或不确定当前进度时，先走下面的 90 秒恢复路径继续干活。治理包不进任何阶段基线（一次约 6–7 万字节；19 次压缩重灌 19 次曾是主要空转来源），只在命中「治理包补载（按需）」的三个条件时才补载。

## 90 秒恢复路径（默认路径）

1. **定位状态**：读 `00_制作控制/制作状态.json`（`current_stage`、`current_episode`、各阶段与分集 phase）、`last_successful_operation` 和操作日志最后几行，确认最后完成的真实落盘动作。有效确认按 `confirmation_id` 回读 `用户确认记录.jsonl`，不能只看最后几行。
2. **跑当前阶段 lint**：`python scripts/drama_lint.py "<skill根>" --project-root "<项目根>" --stage <stage>`，用 issues 判断真实卡点；本地检查是压缩后最便宜的事实来源，不收费、不读源码。
3. **按提示修**：照 issue 的 message、path 就地修；不整读 `scripts/drama_lint.py` 源码，不预读全部导航。
4. **定点补教学**：要继续的具体动作方法不在上下文里时，用 `python scripts/read_reference.py --file references/<x>.md --section "<标题>"` 只读那一节（`--file` 不带 `--render`）；只有整个阶段方法都没装过（全新接手、不是压缩续跑）才用 `--stage <stage> --render` 装阶段必读。返修走 `--mode repair --render`，由 repair 的 `affected_*` 条件补齐受影响阶段。阶段硬门条（`skill-details.md` 的 `### <stage>`，含本阶段准出与确认类型）必须读到，可同样用 `--file references/skill-details.md --section "### <stage>"` 定点取。
5. **从卡点继续作业**：接上阶段固定作业顺序（storyboard：改创作设计 → 编辑 `rhythm_input` → `allocate --write` → `pack --write` → lint → 两项语义审校 → `stamp_review.py` 盖章；`content_review` 只由盖章命令写入，禁止手填）。摘要只用于定位，不继承其中的"缺失/不可用/已批准"断言。

下沉手册按需取（不在默认渲染内）：摘要与产物的信任边界——`python scripts/read_reference.py --file references/recovery.md --section "## 摘要与产物的信任边界（每次恢复都适用）"`
- 压缩最容易丢的硬约束（按阶段表）：`python scripts/read_reference.py --file references/recovery.md --section "## 压缩最容易丢的硬约束"`
- 用户口头决定的抢救规则：`python scripts/read_reference.py --file references/recovery.md --section "## 用户口头决定的抢救规则"`

走这条路径**不需要**重灌治理包。

## 治理包补载（按需，不再必做）

治理规则（控制合同全文、全局执行合同、状态/可见交付合同、统一目录与失效拓扑）不进任何阶段基线。仅当接下来要做以下任一事情时，才运行一次：

```
python scripts/read_reference.py --stage planning --condition governance_reload --render
```

- **跨阶段裁决或阶段状态推进**：要改 phase、请求阶段确认、判定版本失效/回退拓扑、做跨阶段复用裁决；
- **治理类 lint error**：drama_lint 报 state/stages 模块的检查码（确认授权、状态拓扑、落盘门一类），或要执行回退/恢复命令；
- **治理原文确实不在上下文**：被问到确认类型、授权边界、可见交付规则而手里没有原文把握——先按上面第 1–2 步定位，确认缺的是治理规则而不是阶段方法，再补载。

阶段独有方法不在治理包里：缺方法时走 90 秒路径第 4 步定点补读，不要用 governance_reload 代替教学。repair 路由入口也不默认装载治理包，仅保留 90 秒路径一节；走 repair 时命中本节三个条件之一，同样照跑上面的 governance_reload 命令。

## 摘要与产物的信任边界（每次恢复都适用）

- 资产 registry、usage、真实文件或原样 URL、有效确认及用户条件必须回读后再判断能否复用，不继承摘要中的"缺失/不可用/已批准"等断言。
- 读取 `drama_plan.duration_contract` 的来源确认、当前规划预测、`episode.planned_content_duration_s`、时间输入和分镜版本；生成前另读当前 `gen.preflight`/`request_snapshot`/最新有效确认，生成后读取媒体实测及 `adopted_cut_out`。四种时间不可互相覆盖，摘要不能继承为预算。
- 候选展示、质量合格、用户接受分开记录；缺来源或未知归属时报告具体缺项，禁止猜测迁移。

## 压缩最容易丢的硬约束

| 阶段 | 压缩最容易丢的三条 |
|---|---|
| planning | 语言静默锁定入 `language_contract` 不展示；待确认产物（含索引）在展示前门之前落盘、状态推进在用户确认后；形态门先于全套方案；字幕默认关闭 |
| script | 产物只有 2 份/集；关系张力在 `script_contract.relationship_tension`；设定摘要现场渲染不落盘 |
| assets | 只做当前集资产；复用优先查 registry；`--ref` 强制门 |
| storyboard | 内容设计先行；声明区间共享核算；内容/整数请求/技术尾余量分开；独立观看审校；`content_review` 只由 `stamp_review.py` 盖章 |
| keyframes | 张数按真实用途需求统计，零需求按原阶段确认；档位跟随 `aspect_ratio`；KF≠FRM |
| video | 导演包与成稿各自落盘；先预检再确认；continuous 后段须先锁实际出点和帧 |
| delivery | fps 24；只交付一个视频版本；固定区域水印用 erase |

## 用户口头决定的抢救规则

将用户决定及其理由写入确认记录，供压缩恢复后继续遵守：

- 用户给出**理由/偏好/档位选择**时，当场在回复里复述确认，并提示用户："这个决定我会记入确认记录，下集继续沿用"
- 阶段确认的 AskUserQuestion 提交前，把当轮对话中的口头附加条件（如"语体偏古一点"）**写进该阶段确认的上下文说明**，随确认原文一起落盘 `用户确认记录.jsonl`
- 恢复后对关键口径不确定时：先查 `用户确认记录.jsonl` 与 `drama_plan.json.explicit_overrides`，仍没有就问用户一句话，**不要凭感觉选**
