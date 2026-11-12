# 分镜逐场候选接口

用于正式制作分镜的创作与机器登记。导演卡已经写完，也从下一未登记场开始；卡中预写的镜数或 SEG 编号不证明十五列表与时间输入已保存。源剧情、观看关系、摄影和表演由导演决定，本接口只保存、校验和合并，不生成剧情或按模板补动作。

## 接手与保存

在 skill 目录执行：

```text
python scripts/prepare_storyboard.py --project-root "<root>" --episode ep_1 --include-global
```

默认返回下一未登记场的原文、合同、相关状态、`source_binding` 和 `next_action`；已经掌握全局约束时省略 `--include-global`。指定其他场用 `--scene E01S02`，只看导航用 `--list`。继承已有导演卡的本场设计，遇到设计问题才补原始方法；不要因导演卡已有整集规划转为一次录入全集。

模型直接写本场 JSON 到项目分镜目录，例如 `本场输入_E01S01.json`，然后执行：

```text
python scripts/storyboard_draft.py save --project-root "<root>" --episode ep_1 --scene E01S01 --input "<root>/episodes/ep_1/02_分镜/本场输入_E01S01.json"
```

输入只复用原有分镜和时间语义字段，外加本场十五列正文：

| 顶层键 | 内容 |
| --- | --- |
| `source_script` | 原样使用准备结果的 `source_binding`（file/revision/sha256），保存时核当前真实确认；不能编造或继承过期摘要 |
| `storyboard` | 本场 `shots`、`beat_coverage`，以及已经形成的创意字段；受众只选 `audience_execution.<项>.scene_or_shot_ids` 落点，不抄合同原句；不填派生时间、SEG 或审校章 |
| `rhythm_input` | 本场 `utterances` 与唯一 `scenes[]`；时间项沿用原 `visual/speech/camera/hold` 语义，组边界由导演选择 |
| `markdown` | 本场完整十五列表原文，镜号/顺序与两份索引一致；时间和片段可先写“待核算/待分组” |

最小示例仅说明接口：假定当前源 B001 为“人物抬手示意”，没有台词；改用实际场次的源 ID、画面与过程，不把示例秒数、镜数或拍法套给其他戏。`source_script.sha256` 换成准备工具返回的真实值。

```json
{
  "source_script": {"file": "episodes/ep_1/01_剧本/script_contract_ep_1.json", "revision": 1, "sha256": "当前source_binding.sha256"},
  "storyboard": {
    "shots": [{"shot_id": "E01S01-SHOT001", "scene_id": "E01S01", "cut_motivation": "eyeline"}],
    "beat_coverage": [{"beat_id": "B001", "disposition": "kept", "scene": "E01S01", "summary": "人物抬手示意", "target_shots": ["E01S01-SHOT001"]}]
  },
  "rhythm_input": {
    "utterances": [],
    "scenes": [{
      "scene_id": "E01S01",
      "shots": [{"shot_id": "E01S01-SHOT001", "timeline": [{"event_id": "E01S01-V001", "kind": "visual", "process": "手从门侧抬起，停在听者视线中", "source_refs": ["beat:B001"], "start_s": 0, "duration_s": 3, "after": []}]}],
      "beat_groups": [{"group_id": "E01S01-G001", "shot_ids": ["E01S01-SHOT001"], "tail_handle": {"mode": "continue_existing_process", "source_event_id": "E01S01-V001", "description": "手势停留过程继续，不新增动作"}}]
    }]
  },
  "markdown": "| 场次 | 视频片段 | 镜号 | 镜头职责 | 时长 | 画面描述 | 景别 | 机位 | 光影 | 对白 | 音效 | 摄影过程 | 切入切出 | 连续性 | 承接 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n| E01S01 | 待分组 | E01S01-SHOT001 | 让挽留进入对方视线 | 待核算 | 手从门侧抬起，停在听者视线中 | 中景 | 听者侧眼平 | 沿用场景光 | 无 | 衣袖摩擦 | 固定观察门边二人 | 在听者看见手势时进入 | 手停在门边，不越轴 | 接听者的视线 |\n"
}
```

含对白时，`utterances` 用真实 `line_id/speaker_ref`，填演读估时和依据；`speech` 项引用其 `utterance_id` 及连续分片，不复制整句源台词到机器时间项。细节缺用法时只读 manifests 的 `### rhythm_input_ep_N.json`；十五列方法见 storyboard-review.md 的「各列要求」。shot/event/group ID 在全集唯一，优先以场次 ID 作前缀；同一 utterance 跨场时使用同一 ID 和相同定义，分片在合并后核连续性。

成功即已将本场候选保存在 `02_分镜/.draft/<scene_id>.json`，回执给出保存位置和下一场；按同样接口继续。`status` 可查询进度，重复保存同场只替换该场草稿。保存只检查源身份和局部输入结构；跨场 moved、发声和先后关系保留原语义，留待全场合并核对，不为通过局部检查改戏。草稿不是阶段批准：未完全集不发布整集时长、不修改制作状态、不盖章，也不运行全阶段 lint。保存报错按返回路径修本场字段，不要求先摸清全部实现。

## 全场齐备后

```text
python scripts/storyboard_draft.py assemble --project-root "<root>" --episode ep_1
```

程序核源版本与全部草稿，将实际创意数组、十五列和时间输入无损合并到原标准三件产物：`storyboard_ep_1.json`、`rhythm_input_ep_1.json`、`分镜_完整分镜表_ep_1.md`。版本、数据卡 revision、受众合同原句/字段路径/源 revision，以及源合同已有的结构化世界事实由程序复制；不选择受众落点，不从自然语言猜世界事实，源缺失也不补造。不改已有导演卡；相同全局字段只保留一份，显式合同冲突会拒绝合并。已有标准产物时拒绝静默覆盖，应从实际已有文件的缺口继续，不能为套接口删掉原产物。

随后按 storyboard-timing.md「节奏流水线」运行 allocate → pack，按真实 SEG 补执行增量、亮点/受众/资产与接缝绑定、KF 用途，补完执行设计后再 pack 一次，同源渲染 SEG、资产聚合和附录，再对照源稿连看和盖章。完整结构缺字段时才读取 manifests 的 `### storyboard_ep_N.json`。草稿保存/合并没有替代完整源覆盖、台词、连续性、资产身份与状态检查，也没有替代独立内容审校。
