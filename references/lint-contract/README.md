# 压缩恢复注册表（recovery-registry）

> **什么时候读这页**：上下文被自动压缩后（你突然"失忆"）、新会话接手项目、或任何"我不知道干到哪了"的时刻。这是恢复的第一跳，读它 ~1K，比重读阶段包便宜 50 倍。
>
> 恢复三步（固定顺序，不要跳）：
> 1. 读 `00_制作控制/制作状态.json` —— 当前阶段 `current_stage`、当前集 `current_episode`、各阶段状态
> 2. 读 `00_制作控制/用户确认记录.jsonl` **尾部**（最后 3-5 行）—— 用户最近确认了什么、原文是什么
> 3. 读 `references/lint-contract/<当前阶段>.md` —— 本阶段 lint 会查什么（本阶段的产物合同）
>
> 然后按当前阶段继续。**不要**重读完整对话、不要重读全部 reference、不要重读已完成阶段的包。

## 阶段 → 干什么 → 读什么

| 阶段 | 该阶段产出 | 必读（按需加载） | 关键约束（压缩最容易丢的三条） |
|---|---|---|---|
| planning | drama_plan.json + 参数确认表 | planning 阶段包 | 语言静默锁定入 language_contract 不展示；索引建立**在用户确认后**；字幕默认关闭 |
| script | 全局故事包 + 逐集 完整剧本.md + script_contract_ep_N.json | script 阶段包 | 产物只有 2 份/集；关系张力在 script_contract.relationship_tension；设定摘要现场渲染不落盘 |
| assets | CHR/SCN/PROP/VOICE/STYLE 资产 + registry/usage | assets 阶段包 | 只做当前集资产；复用优先查 registry；`--ref` 强制门 |
| storyboard | 总控卡 + 十五列分镜 + storyboard_ep_N.json + rhythm_input | storyboard 阶段包 | **beat_groups 必填**（组 4-15s 整数秒，边界=剪辑点）；语速常数只引节拍库 §5；节奏算术全部引擎写回 |
| keyframes | 高光 KF 图 + keyframe_manifest | keyframes 阶段包 | 张数按 kf-count 公式；档位跟随 aspect_ratio；KF≠FRM |
| video | SEG 片段 + H3 成稿 + video_manifest + FRM/SEAM 记录 | video 阶段包 | 成稿是唯一落盘 Prompt；gen.duration_s 整数秒；依赖图=链内串行链间并行 |
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
