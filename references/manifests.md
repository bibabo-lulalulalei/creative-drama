# 项目、分集与素材 Manifest Ref

本文件是目录、命名、JSON 字段、枚举、基数和引用关系的唯一权威入口，分两处维护：本页保留设计原则、统一目录、状态失效拓扑与「不进入 JSON 的内容」；各 JSON 的完整 schema 在 `manifests/` 分册按阶段维护，定位见下文「Schema 分册索引」。项目初始化、接收用户素材、进入任一生产阶段、恢复中断任务或交付分集时先读本页；需要具体 schema 时按 `reference_map.json` 路由（或按下表定位）读分册中的对应小节，不整篇通读任一分册。创作正文仍以 Markdown 为准，不在 JSON 中复制整篇正文。

## 权威引用

- 规划字段及确认事务：`planning.md`。
- 剧本、分镜、资产、视频和成片的内容规则：对应阶段 Reference。
- 本文件只定义目录、命名、JSON schema、引用关系、状态和基数；不重新定义生成算法、创作阈值或人工审美标准。
- 本文件定义的 schema、基数和引用关系，以及对应阶段权威 Reference 定义的准出条件，是产物合同；`scripts/drama_lint.py` 只负责实现其中可客观检查的部分。文档示例与校验器发生遗漏或冲突时，先按本文件和对应阶段 Reference 判断正确合同，再修正过时的一方；不得扭曲真实产物来迁就校验器。

## 设计原则

- 必须在根目录 `01_剧本/` 先保存项目级完整故事包；多集项目覆盖全局故事圣经、全部分集推进总纲、人物弧、伏笔账本和最终结局。逐集可执行剧本进入 `episodes/ep_N/`，只在该集开始制作时生成，完整写出场次、动作和全部人声文本。
- 项目级 JSON 管理跨集事实、来源、项目数据卡、共享资产、跨集接缝与索引；分集 JSON 管理本集状态、引用和阶段产物。
- 项目级故事包确认后把 `current_episode` 设为 `ep_1`，从该集详细剧本开始逐集生产。共享资产可以在首次实际需要的分集创建并进入 `asset_registry.json`；后续集先从共享登记和已完成分集资产中复用 approved 版本，只把新增或状态变化项写入本集资产。
- 跨集稳定的角色基准图、主要场景参考图、核心道具、音色和全局风格 moodboard 只保存于 `shared/`，不复制到每集目录。
- `00_制作控制/project_data_card.json` 是角色、场景、道具和音色“不可变身份 + 可变状态时间线”的单一事实源。下游只填写片段增量，不得手工复述另一套基础设定。
- 当集新增或变化的服装、伤痕、年龄、伪装和道具状态保存在对应 `episodes/ep_N/03_资产/`；分镜确认后生成的剧情关键帧仍集中保存在该目录下的 `关键帧/`，但阶段状态独立记录为 `keyframes`。
- 生成前关键帧使用 `KFxxx`，直接绑定已确认的 SEG、SHOT 和职责；视频生成后的实际抽帧使用 `FRMxxx`，用于记录模型真实输出。KF 与 FRM 不得混用或互相覆盖。
- Markdown 面向用户和人工审阅；JSON 面向工具执行、依赖追踪、版本恢复和结构校验。JSON 只引用 Markdown 路径与哈希，不复制完整剧本、分镜说明或质检长文。
- 文件中的 `episode_id` 固定使用 `ep_1`、`ep_2`……；文件名最后一个业务后缀也使用 `_ep_N`，版本号放在它之前，例如 `角色_CHR001_林远_战损_v02_ep_2.png`。
- 稳定 ID 在项目内唯一。集号表示使用范围，不重新编号同一个角色、场景、道具、音色、风格、镜头、片段或帧。
- 路径全部相对项目根目录保存；每项记录包含 schema 版本和 revision。已确认版本不得原地覆盖。

## 统一目录

```text
<工作区>/artifacts/<项目名>/
├── 00_制作控制/
│   ├── drama_plan.json
│   ├── project_manifest.json
│   ├── project_data_card.json
│   ├── source_manifest.json
│   ├── 制作状态.json
│   ├── 用户确认记录.jsonl
│   ├── episode_seams.json
│   ├── 合规证明/                  # 仅在运行环境或用户要求审计证明时创建
│   │   ├── 合规证明_planning.json
│   │   ├── 合规证明_script.json
│   │   ├── 合规证明_assets.json
│   │   ├── 合规证明_storyboard.json
│   │   ├── 合规证明_keyframes.json
│   │   ├── 合规证明_video.json
│   │   └── 合规证明_final.json
│   ├── 输入素材/                    # 需要持久化的用户上传或外部下载文件
│   ├── 操作日志.jsonl
│   └── 批次/
│       └── batch-NNN_ep_N.json
├── 01_剧本/                         # 项目级故事包与索引
│   ├── project_script_manifest.json
│   ├── 项目_事实与假设.md
│   ├── 剧本_全局设定与分集总纲.md
│   └── 剧本_全剧完整剧本.md
├── shared/
│   └── 03_资产/
│       ├── 角色/
│       │   ├── 角色_CHRxxx_[名称]_[基准状态]_vNN.[ext]
│       │   └── 角色_资产说明.md
│       ├── 场景/
│       │   ├── 场景_SCNxxx_[名称]_布局参考_vNN.[ext]
│       │   └── 场景_资产说明.md
│       ├── 道具/
│       │   ├── 道具_PROPxxx_[名称]_[状态]_[multiview|main|detail]_vNN.[ext]
│       │   └── 道具_资产说明.md
│       ├── 音色/
│       │   ├── 音色_VOICExxx_[主体]_提示词_vNN.md
│       │   ├── 音色_VOICExxx_[主体]_vNN.[ext]
│       │   └── 音色_资产说明.md
│       ├── 风格/
│       │   ├── 风格_STYLE001_全局moodboard_vNN.[ext]
│       │   └── 风格_资产说明.md
│       └── asset_registry.json
└── episodes/
    ├── ep_1/
    │   ├── episode_manifest_ep_1.json
    │   ├── 01_剧本/
    │   │   ├── script_contract_ep_1.json
    │   │   └── 剧本_完整剧本_ep_1.md
    │   ├── 02_分镜/
    │   │   ├── storyboard_ep_1.json
    │   │   ├── rhythm_input_ep_1.json         # 节奏语义输入，引擎唯一计算源的上游
    │   │   ├── 分镜_阅读稿_ep_1.md
    │   │   ├── 分镜_转换差异台账_ep_1.md      # 随阅读稿提交用户确认
    │   │   ├── 分镜_因果链摘要_ep_1.md        # 随阅读稿提交用户确认
    │   │   ├── 导演总控卡_ep_1.md
    │   │   ├── 分镜_完整分镜表_ep_1.md
    │   │   ├── 分镜_视频片段执行表_ep_1.md
    │   │   ├── 分镜_连续性账本_ep_1.md
    │   │   └── 分镜_资产需求清单_ep_1.md
    │   ├── 03_资产/
    │   │   ├── 角色状态/
    │   │   │   └── 角色_CHRxxx_[名称]_[状态]_vNN_ep_1.[ext]
    │   │   ├── 道具状态/
    │   │   │   └── 道具_PROPxxx_[名称]_[状态]_[multiview|main|detail]_vNN_ep_1.[ext]
    │   │   ├── 关键帧/
    │   │   │   ├── 关键帧_KFxxx_SEGxxx_highlight-N_vNN_ep_1.[ext]
    │   │   │   └── 关键帧_资产说明_ep_1.md
    │   │   ├── asset_usage_ep_1.json
    │   │   └── keyframe_manifest_ep_1.json
    │   ├── 04_视频片段/
    │   │   ├── video_manifest_ep_1.json
    │   │   ├── continuity_ep_1.json
    │   │   ├── 视频_资产清单_ep_1.md
    │   │   ├── 提示词_SEGxxx_vNN_ep_1.h3.md
    │   │   ├── gen_SEGxxx_vNN_ep_1.json
    │   │   ├── 片段_SEGxxx_E01S01_vNN_ep_1.[ext]
    │   │   ├── 抽帧/
    │   │   │   ├── 抽帧_FRMxxx_SEGxxx_[start|scene|tail]_[HH-MM-SS-ms]_vNN_ep_1.[ext]
    │   │   │   └── 抽帧_连续性清单_ep_1.md
    │   │   └── 质检/
    │   │       ├── 质检_SEGxxx_vNN_ep_1.md
    │   │       └── 质检_接缝_SEAMxxx_SEGxxx_SEGyyy_vNN_ep_1.md
    │   └── 05_成片/
    │       ├── delivery_manifest_ep_1.json
    │       ├── 成片清单_ep_1.md
    │       ├── 质检_媒体探测_无字幕_vNN_ep_1.json
    │       ├── 质检_媒体探测_字幕版_vNN_ep_1.json
    │       ├── 质检_基础_无字幕_vNN_ep_1.json
    │       ├── 质检_基础_字幕版_vNN_ep_1.json
    │       ├── 质检_字幕对齐_vNN_ep_1.json
    │       ├── 字幕_时间轴_vNN_ep_1.srt
    │       ├── 字幕_最终版_vNN_ep_1.json
    │       ├── 字幕_烧录参数_vNN_ep_1.json
    │       ├── [项目名]_成片_[比例]_无字幕_vNN_ep_1.[ext]
    │       └── [项目名]_成片_[比例]_字幕烧录_vNN_ep_1.[ext]
    └── ep_2/
        └── ...
```

`scripts/drama_lint.py` 在分镜阶段检查 `storyboard_ep_N.json`、`分镜_阅读稿_ep_N.md`、`导演总控卡_ep_N.md` 和 `分镜_完整分镜表_ep_N.md`，并客观确认完整分镜表存在十五列。视频片段执行表、连续性账本和资产需求清单仍按 `storyboard.md` 生成，并由主 Agent 人工复核；不能因为校验器尚未逐项检查而省略。不得同时创建导演阐述、导演控制包或强风格系统卡形成第二套决策中心。
剧情关键帧在分镜确认后命名为 `关键帧_KFxxx_SEGxxx_highlight-N_vNN_ep_N.[ext]`；`highlight-N` 是同一 SEG 内从 `1` 开始的高光序号。目录中的 `ep_1` 仅为实例。
主要场景必须生成共享布局参考图，用于锁定空间拓扑、门窗朝向、固定陈设和基础光位；它不是逐镜剧情画面，不替代分镜场景合同。剧情关键帧在分镜确认后按 SEG 生成并进入 `关键帧/`，视频完成后另从真实画面提取 FRM，两者分别承担“生成前目标”和“生成后事实”。

## Schema 分册索引

具体 JSON schema 全部在分册；下表给出定位，权威关系与本页相同：

| 分册 | JSON schema |
|---|---|
| `manifests/planning.md` | project_manifest / source_manifest / episode_manifest_ep_N / episode_seams / 合规证明_阶段名 |
| `manifests/state.md` | 制作状态 / 用户确认记录 / 操作日志 / 校验器效率模式 |
| `manifests/script.md` | project_script_manifest / project_data_card / script_contract_ep_N |
| `manifests/assets.md` | asset_registry / asset_usage_ep_N |
| `manifests/storyboard.md` | storyboard_ep_N / rhythm_input_ep_N |
| `manifests/keyframes.md` | keyframe_manifest_ep_N |
| `manifests/video.md` | video_manifest_ep_N / gen_SEGxxx_vNN_ep_N / continuity_ep_N |
| `manifests/delivery.md` | delivery_manifest_ep_N |

## 状态、失效与一致性

- `制作状态.json` 独占规划与生产阶段状态。`phases.planning` 与 `phases.script` 分别表示项目规划和项目级故事包硬门；`episodes.ep_N.stage_status.script` 表示该集详细剧本。资产及后续项目状态是逐集聚合视图。
- `current_stage: script` 且 `current_episode` 为空时表示项目级故事包；`current_stage: script` 且 `current_episode=ep_N` 时表示该集详细剧本。当前集更早阶段必须为 `confirmed`，更晚阶段只能为 `pending|invalidated`；更早集必须至少完成到 `objective.target_stage`，更晚集的详细剧本及后续阶段必须保持 `pending|invalidated`。当前集达到目标后，下一集总是从 `script` 开始。
- `episode_manifest_ep_N.json` 只保存身份、时长和文件指针；阶段状态与推进只读取 `制作状态.json`。
- 每集状态遵循本集阶段拓扑，但不同集允许处于不同阶段：项目仍在规划或项目级故事包阶段时，各分集生产阶段只能为 `pending|invalidated`；进入逐集循环后，仅 `current_episode` 可以处于活动状态，且先活动于 `script`。较早集必须达到目标阶段，较晚集不得提前生成详细剧本或进入资产阶段。
- `project_manifest.json` 是路径索引，`drama_plan.json` 是规划权威，`project_script_manifest.json` 是项目级完整剧本索引，`project_data_card.json` 是跨阶段设定与状态权威，`asset_registry.json` 是共享媒体资产权威，各自不得复制对方的完整字段。
- `剧本_全剧完整剧本.md` 是项目故事权威；逐集剧本与 `script_contract.relationship_tension` 是执行细化。修改项目级剧本中的核心因果、人物弧、结局或分集边界时，所有受影响 `script_contract_ep_N.json` 及下游阶段必须失效。
- 任一 Markdown 正文修改后更新对应 `source_sha256` 和 revision，并使依赖它的下游 manifest 状态变为 `invalidated`。
- 共享资产版本变化时，只更新 `asset_registry.json` 和受影响分集的 `asset_usage_ep_N.json`，不复制媒体文件。
- 规划阶段可以先登记未来阶段 manifest 的固定路径；进入对应阶段后，该阶段 JSON 中引用的路径必须存在。`episode_id`、文件后缀 `_ep_N`、所属目录 `episodes/ep_N/` 三者必须一致。
- 多集项目的 `episode_seams.json` 必须覆盖每对相邻集；单集作品使用 `ep_1` 且 `seams` 为空。

## 不进入 JSON 的内容

- 剧情梗概、人物小传、完整剧本文字。
- 面向用户的参数确认和按内容形态选择的五列剧情节奏预览。
- 人工审美评价、修改建议和完整看片记录。
- 策略库、风格库和方法说明。
- SRT、图片、音频和视频文件本体。

这些内容由对应 Markdown 或媒体文件承载；JSON 只保存路径、哈希、状态、结构化执行字段和引用关系。`script_contract_ep_N.json` 的场次合同字段与 `speech_lines` 属执行合同而非剧本正文副本，不在本清单限制内。

## 旧项目迁移清单（2026-11 schema 读取面调整）

本次调整只删冗余存储、不新增机器门：旧项目不迁移也能通过 lint，残留字段一律忽略不读；下列清理在下次修订对应文件时顺手完成，禁止用生成器/批处理脚本批量改写叙事产物（SKILL.md 读取协议第 7 条）。

1. **台词行去两字段（`script_contract_ep_N.json` 与 `video_manifest_ep_N.json` 的 `speech_lines[]`）**：
   - 删除行级 `voice_anchor`：声音锚点以 `project_data_card.json` 的 `voices[].voice_anchor` 单定义为准，lint 按 `voice_id` 解析。报 `speech_line_voice_unknown` 表示该 voice_id 不在 voices[]；报 `speech_line_voice_anchor_missing` 表示 voices[] 内锚点为空。旧码 `speech_line_voice_anchor_inconsistent` 已退役——单定义后跨行冲突在结构上不可能发生。
   - 删除行级 `display_text`：带标点阅读面改由 `source_text` 现场做标点/引号/空格规范渲染，不再存储；`source_text`（用户原文审计层）与 `spoken_text`（无标点机器层）两个存储层保留，规范化规则不变（见 delivery.md「台词与字幕文本合同」）。
2. **数据卡与 drama_plan 无需改文件**：权威文件 schema 零变更、机器加载器零改动；变化的只是创作读取路径——分集创作默认读 `asset_usage_ep_N.json` 分卡与 drama_plan 顶层组/字段路径，全文只在规划确认展示、规划修订或报告缺项补读时打开（读取面合同分别见 assets.md「资产 JSON 登记」、planning.md「下游读取面合同」）。
3. **验收**：清理后重跑 `python scripts/drama_lint.py <skill-root> --project-root <项目根> --stage <stage>`，0 error 即该阶段迁移完成；未清理的残留旧字段不阻断门，只在下次修订时删除。
