# 压缩恢复协议

上下文被自动压缩后、新会话接手项目，或不确定当前进度时，先走下面的 90 秒恢复路径继续干活。治理包不进任何阶段基线（整包一次约 5 万字节；19 次压缩重灌 19 次曾是主要空转来源）：常规阶段迁移只用 `--file/--section` 窄读控制合同两节（约 1 万字节，见下），整包只在命中「治理包补载（按需）」的条件时才补载。

## 90 秒恢复路径（默认路径）

1. 读取 `制作状态.json` 的当前阶段/集与最后成功动作；有效确认按 ID 定位用户确认台账，不从摘要继承“缺失/已批准”等判断。
2. **视频恢复**：查看当前段旁的 `h3_task_SEGxxx.json`。已有任务就用原 h3 命令或 `--resume` 恢复；已完成就给出视频路径。没有在途任务才用 `prepare_video.py --context` 取本段源信息并接 video.md 五步；不为未生成后段的聚合缺口反复 lint。
3. **其他阶段或确有错误**：只跑当前阶段 lint，按 message/path 修当前项。不要整读源码或重灌所有导航；普通已确认状态推进只读 control-contracts 的状态节。
4. 缺少具体方法才 `read_reference.py --file references/<x>.md --section <标题>` 定点补读。只有首次进入阶段才装基线；视频 H3 写作规则同阶段复用。完整治理仅用于初始化、版本失效、回退或治理错误。
5. 分镜恢复仍按既有作业顺序：创作设计 → rhythm_input → allocate/pack → lint → 两项内容审校 → stamp_review。视频执行的机器元数据由准备工具派生，禁止恢复时重新手抄。

下沉手册仅在具体问题需要时读取，不作为每次恢复前置。

## 治理包补载（按需，不再必做）

治理规则（控制合同全文、全局执行合同、状态/可见交付合同、统一目录与失效拓扑）不进任何阶段基线，读取分两层。

**常规阶段迁移走两节窄读（默认）。** 用户已确认后的状态推进（写 phase、追加操作日志、请求普通阶段确认）不整包补载，只读确认合同节：

```
python scripts/read_reference.py --file references/control-contracts.md --section "## 2. 阶段状态与确认"
```

要发项目执行确认或拼接确认（AskUserQuestion 非视频阶段迁移）时，加读：

```
python scripts/read_reference.py --file references/control-contracts.md --section "## 非视频生成的阶段迁移确认"
```

两节合计约 1 万字节。阶段独有方法不在治理包里：缺方法时走 90 秒路径第 4 步定点补读，不要用 governance_reload 代替教学。

**整包补载仅限以下场景。** 仅当接下来要做以下任一事情时，才运行一次：

```
python scripts/read_reference.py --stage planning --condition governance_reload --render
```

- **跨阶段裁决重场景**：项目初始化、规划确认、跨阶段复用裁决、版本失效/回退拓扑、revision 与受影响下游更新；
- **治理类 lint error**：drama_lint 报 state/stages 模块的检查码（确认授权、状态拓扑、落盘门一类），或要执行回退/恢复命令；
- **治理原文确实不在上下文**：被问到确认类型、授权边界、可见交付规则而手里没有原文把握——先按上面第 1–2 步定位，确认缺的是治理规则而不是阶段方法，再补载。

repair 路由入口也不默认装载治理包，仅保留 90 秒路径一节；走 repair 时常规迁移同样走两节窄读，命中上面整包条件之一才照跑 governance_reload 命令。

## 摘要与产物的信任边界（每次恢复都适用）

- 资产 registry、usage、真实文件或原样 URL、有效确认及用户条件必须回读后再判断能否复用，不继承摘要中的"缺失/不可用/已批准"等断言。
- 读取 `drama_plan.duration_contract` 的来源确认、当前规划预测、`episode.planned_content_duration_s`、时间输入和分镜版本；生成前另读 manifest 段内冻结 `request_snapshot` 与最新有效确认，生成后读取 probe 实测媒体信息及下段 `reference_inputs` 中的尾帧登记。四种时间不可互相覆盖，摘要不能继承为预算。
- 候选展示、内容观察、用户接受分开记录；缺来源或未知归属时报告具体缺项，禁止猜测迁移。

## 压缩最容易丢的硬约束

| 阶段 | 压缩最容易丢的三条 |
|---|---|
| planning | 语言静默锁定入 `language_contract` 不展示；待确认产物（含索引）在展示前门之前落盘、状态推进在用户确认后；形态门先于全套方案；字幕默认关闭 |
| script | 产物只有 2 份/集；关系张力在 `script_contract.relationship_tension`；设定摘要现场渲染不落盘 |
| assets | 只做当前集资产；复用优先查 registry；`--ref` 强制门 |
| storyboard | 内容设计先行；声明区间共享核算；内容/整数请求/技术尾余量分开；独立观看审校；`content_review` 只由 `stamp_review.py` 盖章 |
| keyframes | 张数按真实用途需求统计，零需求按原阶段确认；档位跟随 `aspect_ratio`；KF≠FRM |
| video | 复用已确认导演卡、独立保存 H3 成稿；准备命令自动校验后一次生成确认；continuous 后段须先锁实际出点和帧 |
| delivery | fps 24；只交付一个视频版本；固定区域水印用 erase |

## 用户口头决定的抢救规则

将用户决定及其理由写入确认记录，供压缩恢复后继续遵守：

- 用户给出**理由/偏好/档位选择**时，当场在回复里复述确认，并提示用户："这个决定我会记入确认记录，下集继续沿用"
- 阶段确认的 AskUserQuestion 提交前，把当轮对话中的口头附加条件（如"语体偏古一点"）**写进该阶段确认的上下文说明**，随确认原文经 `stamp_confirmation.py --user-message` 一起落盘 `用户确认记录.jsonl`
- 恢复后对关键口径不确定时：先查 `用户确认记录.jsonl` 与 `drama_plan.json.explicit_overrides`，仍没有就问用户一句话，**不要凭感觉选**
