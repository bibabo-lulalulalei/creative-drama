# 项目、分集与素材 Manifest Ref

本文件是目录、命名、JSON 字段、枚举、基数和引用关系的唯一权威入口：本页前部保留设计原则、统一目录、状态失效拓扑与「不进入 JSON 的内容」，后部「分册」按阶段维护各 JSON 的完整 schema，按 `reference_map.json` 路由定位到具体标题子树，不整篇通读。项目初始化、接收用户素材、进入任一生产阶段、恢复中断任务或交付分集时先读本页；需要具体 schema 时按 `reference_map.json` 路由（或按分册标题定位）读对应小节。创作正文仍以 Markdown 为准，不在 JSON 中复制整篇正文。

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
    │   │   ├── 分镜_阅读稿_ep_1.md            # 含附录 A 节拍去向、附录 B 资产使用摘要，随同一确认门提交
    │   │   ├── 导演总控卡_ep_1.md             # 含逐段执行区（SEG 规划与跨片段连续性唯一书面载体）
    │   │   └── 分镜_完整分镜表_ep_1.md
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

`scripts/drama_lint.py` 在分镜阶段检查 `storyboard_ep_N.json`、`分镜_阅读稿_ep_N.md`、`导演总控卡_ep_N.md` 和 `分镜_完整分镜表_ep_N.md`，并客观确认完整分镜表存在十五列。SEG 规划与跨片段连续性写进导演总控卡逐段执行区，节拍去向与资产使用摘要作为阅读稿附录 A/B 提交，均不另建文件。不得同时创建导演阐述、导演控制包、执行表、连续性账本或强风格系统卡形成第二套决策中心。
剧情关键帧在分镜确认后命名为 `关键帧_KFxxx_SEGxxx_highlight-N_vNN_ep_N.[ext]`；`highlight-N` 是同一 SEG 内从 `1` 开始的高光序号。目录中的 `ep_1` 仅为实例。
主要场景必须生成共享布局参考图，用于锁定空间拓扑、门窗朝向、固定陈设和基础光位；它不是逐镜剧情画面，不替代分镜场景合同。剧情关键帧在分镜确认后按 SEG 生成并进入 `关键帧/`，视频完成后另从真实画面提取 FRM，两者分别承担“生成前目标”和“生成后事实”。

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
   - 删除行级 `display_text` 与 `spoken_text`：台词只存 `source_text` 一层（用户原文审计层，逐字保留）；带标点阅读面、无标点机器串与字幕正文都由 `source_text` 现场渲染/去标点派生，不再存储（见 delivery.md「台词与字幕文本合同」），旧项目残留字段忽略不读、迁移时删除。
2. **数据卡与 drama_plan 无需改文件**：权威文件 schema 零变更、机器加载器零改动；变化的只是创作读取路径——分集创作默认读 `asset_usage_ep_N.json` 分卡与 drama_plan 顶层组/字段路径，全文只在规划确认展示、规划修订或报告缺项补读时打开（读取面合同分别见 assets.md「资产 JSON 登记」、planning.md「下游读取面合同」）。
3. **验收**：清理后重跑 `python scripts/drama_lint.py <skill-root> --project-root <项目根> --stage <stage>`，0 error 即该阶段迁移完成；未清理的残留旧字段不阻断门，只在下次修订时删除。

# 分册 Schema（按阶段）

## Manifest 分册 · 规划与项目入口 JSON

### project_manifest.json

只做项目总索引，不复制 `drama_plan.json` 的创意与模型字段：

```json
{
  "project_id": "",
  "revision": 1,
  "format_mode": "single_short|multi_episode|micro_film|long_form_video",
  "episode_count": 1,
  "episode_ids": ["ep_1"],
  "plan_path": "00_制作控制/drama_plan.json",
  "state_path": "00_制作控制/制作状态.json",
  "source_manifest_path": "00_制作控制/source_manifest.json",
  "project_data_card_path": "00_制作控制/project_data_card.json",
  "shared_asset_registry_path": "shared/03_资产/asset_registry.json",
  "episode_seams_path": "00_制作控制/episode_seams.json",
  "project_script_manifest_path": "01_剧本/project_script_manifest.json",
  "episode_manifests": {
    "ep_1": "episodes/ep_1/episode_manifest_ep_1.json"
  }
}
```

分集目录集合必须与 `drama_plan.json.scale_plan.episode_durations_s` 一一对应：缺集或计划外目录立即阻断；每集 `episode_manifest` 的七个 `stage_manifests` 指针必须指向规定的标准路径，缺失阶段产物另按必需产物阻断。`project_manifest.json` 的 `episode_ids`、`episode_manifests` 等索引字段当前只做文件存在性检查，不参与自动一致性裁决——作者仍须保证它们与 scale_plan、实际目录和文件一致，此项为审校责任。规划必须包含 `duration_contract`（mode/scope/target_duration_s/tolerance_ratio/bounds/source/confirmation_ref）；`scale_plan` 的逐集时长只作预测并核内部求和，用户目标范围按合同 scope 独立校验，不得回传到镜头配平。unbounded 的 target/tolerance/bounds 为 null；exact 的 bounds 为 `[target,target]`、tolerance 为 null 或 0；target_band 的 bounds 为 `[target*(1-tolerance),target*(1+tolerance)]`，容差是来源明确的有限 `[0,1)` 数值，不能默认补入。真实约束必须回指包含同一合同快照的有效确认。
从剧本阶段开始必须创建 `project_script_manifest_path` 指向的项目级剧本索引，并创建 `project_data_card_path` 指向项目数据卡；`episode_seams_path` 指向实际跨集接缝文件。

### source_manifest.json

用户上传和外部引用的图片、视频、音频、文档必须登记；没有素材时写空 `sources`，不得省略文件：

```json
{
  "project_id": "",
  "revision": 1,
  "sources": [
    { "source_id": "SRC001", "media_type": "image|video|audio|document", "source_uri": "", "stored_path": "", "sha256": "", "source_origin": "user_upload|external_reference|generated" }
  ]
}
```

- 每个用户提供的 URL、附件 ID 或输入实例都必须先作为独立来源登记，即使系统提示给出相同 `local path`、相同 `image.png` 或相同 basename。`source_uri` 保存原始 URL 或可追溯附件标识；实际保存本地副本时，`stored_path` 使用 `SRCxxx` 唯一命名，禁止不同来源互相覆盖。只有实际读取并计算得到的字节哈希相同，才允许标记为重复内容；重复内容仍保留各自 `source_id` 与原始 URL 记录，不能删除来源。
- 本地文件记录实际 `stored_path` 和 `sha256`。HTTP(S) 文件 URL 保存原始字符串，不做可能改变签名的规范化；H3 原样直传，无需下载、复制、base64 或绑定本地副本。只有真实落盘才登记本地路径和字节哈希；仅凭 URL 不得声称验证了远端字节。视觉参考仍须逐张实际查看，文字来源仍须真实读取内容；这些内容核实不等于为 H3 强制保存副本。
- `stored_path` 必须是项目根目录内的相对路径；登记时据实填写实际字节 SHA-256。当前结构检查只验证 `source_manifest.json` 存在，不重算 `sources[].sha256`——哈希一致性由登记环节与审校核对，不得凭声明值声称已验证字节。
- 需要复制或下载到项目内的输入统一保存为 `00_制作控制/输入素材/来源_SRCxxx_[原始名称]_vNN.[ext]`；仅服务单集时追加 `_ep_N`。
- 用途、采用范围和授权说明可按项目需要补充，但不作为自动检查字段。

### drama_plan.json 易错字段最小样例

完整字段清单与语义以 `planning.md`「drama_plan.json」为唯一权威，这里只给结构检查高频报错字段的最小写法。下游阶段按 planning.md「下游读取面合同」走顶层组/字段路径定点读取，不整读全文。`creative_mechanism.candidates` 必须是对象数组，不得写成字符串数组；顶层 `primary` 必须与某个 `candidates[].primary` **逐字一致**；`supporting` 必须是数组（可空）：

```json
"creative_mechanism": {
  "selection_mode": "divergent",
  "candidates": [
    {"primary": "EMO-01：全家误会驱动的身份反转，结尾解开。", "supporting": []},
    {"primary": "FAM-02：亲戚撮合制造的连环窘迫。", "supporting": ["辅助机制：旧物件触发的闪回对照。"]}
  ],
  "primary": "EMO-01：全家误会驱动的身份反转，结尾解开。",
  "supporting": []
}
```

`audience_plan.execution_sources` 是固定四键、逐字字段路径的对象，不得写成列表或自拟文案：

```json
"execution_sources": {
  "viewing_focus": "audience_plan.viewing_focus",
  "emotional_payoff": "audience_plan.emotional_payoff",
  "platform_viewing_context": "audience_plan.platform_viewing_context",
  "expression_boundaries": "audience_plan.expression_boundaries"
}
```

`style_contract` 必填九字段，排除项字段名是复数 `excluded_mechanisms`（不是 `excluded_mechanics`）：

```json
"style_contract": {
  "anchor_type": "画风谱系",
  "anchor": "具体锚点",
  "lighting": "光线机制",
  "color": "色彩关系",
  "composition": "构图骨架",
  "material": "材质表现",
  "camera_tendency": "镜头倾向",
  "sound_tendency": "声音倾向",
  "excluded_mechanisms": ["明确排除的机制一", "明确排除的机制二"]
}
```

`scale_plan` 的显示字段不加“约”等修饰：逐集显示按 `48秒`/`60秒`/`X分钟`/`X分Y秒`；总数超过 60 秒必须同时写精确秒数与分钟换算：

```json
"scale_plan": {
  "episode_count": 3,
  "episode_durations_s": [75, 80, 90],
  "episode_duration_displays": ["1分15秒", "1分20秒", "1分30秒"],
  "total_duration_s": 245,
  "total_duration_display": "245秒/4分5秒"
}
```

### episode_manifest_ep_N.json

每集总入口只保存身份和各阶段文件指针：

```json
{
  "project_id": "",
  "episode_id": "ep_1",
  "revision": 1,
  "duration_s": 120,
  "planned_content_duration_s": null,
  "stage_manifests": { "script": "episodes/ep_1/01_剧本/script_contract_ep_1.json", "storyboard": "episodes/ep_1/02_分镜/storyboard_ep_1.json", "assets": "episodes/ep_1/03_资产/asset_usage_ep_1.json", "keyframes": "episodes/ep_1/03_资产/keyframe_manifest_ep_1.json", "video": "episodes/ep_1/04_视频片段/video_manifest_ep_1.json", "continuity": "episodes/ep_1/04_视频片段/continuity_ep_1.json", "delivery": "episodes/ep_1/05_成片/delivery_manifest_ep_1.json" }
}
```

`duration_s` 保留开局规划预测；`planned_content_duration_s` 由同源核算更新。生成请求时长在 video/gen，媒体实测时长在 probe/采用记录，不用其覆盖预测。

### episode_seams.json

只登记跨集边界；集内片段接缝由 `continuity_ep_N.json` 管理：

```json
{
  "project_id": "",
  "revision": 1,
  "seams": [
    { "seam_id": "EPSEAM001", "from_episode": "ep_1", "to_episode": "ep_2", "from_segment": "", "to_segment": "", "actual_tail_frame": "episodes/ep_1/04_视频片段/抽帧/FRMxxx_tail_vNN_ep_1.png", "actual_tail_sha256": "", "visual_state": {}, "audio_state": {}, "unresolved_hooks": [], "cut_strategy": "", "seam_mode": "continuous|elliptical", "required_invariants": ["identity", "screen_direction"], "permitted_deltas": [], "status": "planned|verified|blocked" }
  ]
}
```

单集作品保留该文件并写空 `seams`。`continuous` 表示叙事状态连续，`permitted_deltas` 必须为空；`elliptical` 表示明确的时间、空间或认知跳跃，必须列出至少一个允许变化维度。跨集接缝在分镜阶段可先写 `planned`；上一集视频完成后复核画面、声音、未决钩子、接缝模式和切换策略，再改为 `verified`。`continuous` 必须把真实尾帧路径和 SHA-256 写入 `actual_tail_frame/actual_tail_sha256`；`elliptical` 可记录尾帧供追溯，但下一集不必把它作为视觉输入。下一集首段只能消费完整复制的 verified 记录。
### 合规证明_阶段名.json

只有运行环境或用户明确要求额外审计证明时，才在 `00_制作控制/合规证明/` 保存对应证明；它不是常规阶段准出硬门。完整委派规则读取 `delegation.md`，建议结构为：

```json
{
  "stage": "planning|script|assets|storyboard|keyframes|video|final",
  "executor": "main_agent|main_agent_director",
  "delegated": false,
  "skill_read": ["SKILL.md"],
  "upstream_artifacts": [ { "path": "项目根目录内相对路径", "sha256": "64位小写十六进制", "revision": 1 } ],
  "tool_calls": [ { "operation_id": "与操作日志一致的唯一 ID", "tool": "实际工具名", "status": "completed", "evidence_path": "/absolute/path/to/evidence", "evidence_sha256": "64位小写十六进制", "observed_metadata": {"width": 1080, "height": 1920} } ],
  "delegations": [],
  "forbidden_tools_used": [],
  "declaration": "本阶段严格遵循skill要求，未使用禁止的替代工具；本阶段委派情况与 delegation.md 一致"
}
```

`planning|script|storyboard` 的 `delegated` 必须为 `false` 且 `delegations` 为空。`assets|keyframes` 只有在图片工具执行被外包时才记录委派；`video` 只要发生实际视频生成/编辑工具调用，`delegated` 必须为 `true` 并记录 `video_execution` 交接包；`final` 只要发生拼接、裁剪、混音、mux、字幕烧录等媒体变更工具调用，`delegated` 必须为 `true` 并记录 `final_media_execution` 交接包。每个交接包使用 Skill 内或项目内相对路径，保存逐文件输出白名单、实际输出、硬约束、验收标准、检查命令和禁止再委派声明；交付记录写入、用户交付、确认工具调用和阶段状态收口不得出现在 subagent 委派范围内。
当前 `drama_lint.py` 的输出就是本次结构检查结果，不回填到被检查的合规证明中，避免证明文件预先声明自身已通过。`declaration` 必须以 `本阶段严格遵循skill要求，未使用禁止的替代工具` 开头，后面允许追加本阶段真实说明。
规划、剧本和分镜属于纯文件创作阶段，没有外部生成调用时 `tool_calls` 直接写空数组，不得虚构 `file_creation`。除规划外，`upstream_artifacts` 必须完整覆盖上一阶段当前确认产物，每项记录项目内绝对路径、确认 revision 和确认记录中的 SHA-256。资产、关键帧、视频和成片属于生成或媒体处理阶段，必须保存实际调用；每项引用 `操作日志.jsonl` 中同名、同阶段且状态为 `succeeded` 的 `operation_id`，工具名必须一致，证据文件必须列在该操作的 `outputs` 中、实际存在且 SHA-256 匹配。图片和视频输出还必须保存真实文件探测得到的 `observed_metadata`，并与日志 `output_metadata` 一致。

## Manifest 分册 · 状态、确认与操作日志

### 制作状态.json

这是项目级与逐集阶段状态的唯一数据源。阶段判断只读取本文件；`drama_plan.json` 和 `episode_manifest_ep_N.json` 分别保存规划数据和文件指针：

```json
{
  "project_id": "",
  "revision": 1,
  "current_stage": "planning",
  "current_episode": null,
  "phases": { "planning": "in_progress", "script": "pending", "assets": "pending", "storyboard": "pending", "keyframes": "pending", "video": "pending", "final": "pending" },
  "episodes": { "ep_1": { "manifest": "episodes/ep_1/episode_manifest_ep_1.json", "stage_status": { "script": "pending", "assets": "pending", "storyboard": "pending", "keyframes": "pending", "video": "pending", "final": "pending" } } },
  "last_successful_operation": ""
}
```

状态只允许 `pending|in_progress|awaiting_confirmation|confirmed|invalidated|blocked`。项目级故事包阶段使用 `current_stage: script` 与 `current_episode: null`；项目级确认后使用 `current_stage: script` 与 `current_episode: ep_1` 开始第 1 集详细剧本。媒体或文档验证通过后才能递增 revision 并更新状态；文件存在、接口成功或聊天中声称完成都不能单独证明阶段完成。

### 用户确认记录.jsonl

每次收到用户对当前阶段的明确确认后追加一行，禁止代理预写、补写或把无回复视为确认：

```json
{"stage":"planning","episode_id":"","revision":1,"decision":"confirmed","confirmation_mode":"full","changed_artifacts":[],"impact_scope":[],"confirmation_purpose":"project_execution","interaction_ask_call_id":"实际确认调用 ID","interaction_ask_result":"proceed_project","user_message":"用户通过确认工具确认项目方案的原文","confirmed_at":"2026-09-08T12:00:00+08:00"}
{"stage":"script","episode_id":"ep_1","revision":2,"decision":"confirmed","confirmation_mode":"full","changed_artifacts":[],"impact_scope":[],"confirmation_purpose":"","interaction_ask_call_id":"","interaction_ask_result":"","user_message":"用户确认第 1 集详细剧本的原文","confirmed_at":"2026-09-08T12:05:00+08:00"}
{"stage":"assets","episode_id":"ep_1","revision":2,"decision":"confirmed","confirmation_mode":"full|incremental","base_revision":1,"changed_artifacts":[],"impact_scope":[],"confirmation_purpose":"","interaction_ask_call_id":"","interaction_ask_result":"","user_message":"用户本轮明确回复原文","confirmed_at":"2026-09-08T12:10:00+08:00"}
```

- `planning` 始终是项目级确认。`script` 有两种作用域：项目级故事包确认的 `episode_id` 留空；分集详细剧本确认必须填写当前 `episode_id`。`assets|storyboard|keyframes|video|final` 始终填写当前 `episode_id`。同名阶段在不同作用域或不同集的确认记录不能互相替代。
- `target_stage=video|final` 时，planning 写 `project_execution/proceed_project`。所有视频生成确认结构只读取 `interaction-ask-video-clarification-ref.md`。
- 当目标继续到成片时，进入拼接的同一次 AskUserQuestion 还必须原子写入 `stage=video` 的确认记录：`confirmation_purpose: video_acceptance_and_final_assembly`、与 `assembly_confirmation` 相同的 `interaction_ask_call_id`、`interaction_ask_result: proceed_assembly`。当 `objective.target_stage=video` 时，video 阶段只做普通产物确认并停止，不创建虚假的拼接授权。
- `user_message` 保存触发继续的用户原文；空值、系统生成文字或仅有内部检查结果无效。
- `confirmed_at` 必须是带时区的 ISO-8601 时间。
- 首次确认或重大修改使用 `confirmation_mode: full`；此时 `base_revision` 可省略，`changed_artifacts` 与 `impact_scope` 可为空。已有真实全量确认基础上的局部微调可使用 `incremental`，必须记录上一全量确认 revision、实际变化文件和影响范围；禁止第一次确认就写 `incremental`。
- 用户提出修改时不写 `confirmed`；完成修改、重新展示并再次收到明确确认后才追加新记录。
- 阶段状态写为 `confirmed` 时必须存在同阶段有效确认记录；后续阶段校验会据此阻断跳步。

### 操作日志.jsonl

每次外部生成、媒体处理或重要阶段状态变更追加一行；普通 Markdown/JSON 写入不需要伪装成工具调用。尚未发生操作时允许文件为空：

```json
{"operation_id":"","input_revision":1,"stage":"","target_ids":[],"tool":"","tool_call_id":"","params_summary":{},"attempt":1,"status":"started|succeeded|partial|failed","outputs":[],"output_metadata":{},"tool_calls":[],"recovery_action":"","timestamp":"2026-09-08T12:00:00+08:00"}
```

操作日志按时间顺序追加，不修改历史行。`tool_call_id` 登记真实工具调用 ID（无工具调用的内部动作如 rollback 写空串），`tool_calls` 登记同一次操作内的多次工具调用；lint 只校验日志可逐行解析且无禁用工具名，不要求哈希链。恢复任务时先读取 `制作状态.json`、`last_successful_operation`、操作日志和实际文件。外部调用部分成功时保留成功输出，只补失败项，不重复执行已成功调用。

### 校验器效率模式

- `--stage planning|script|assets|storyboard|keyframes|video|final|all` 选择阶段检查范围；`--stage all` 用于最终发布或专项审计。
- 校验器执行所选阶段的完整检查，只报告问题，不创建、补写或修改项目文件。
- 项目初始化、新版本复制、引用更新和剧本合同同步当前均由主 Agent 按本文件规则完成，不得调用校验器未提供的参数。

## Manifest 分册 · 剧本与项目数据卡

### project_script_manifest.json

项目级剧本索引必须创建，只保留合并故事文件的固定指针；完整剧本、分集覆盖与跨集闭合都由 Markdown 正文和逐集合同承载，不在此复制第二份登记。

```json
{
  "project_id": "",
  "revision": 1,
  "global_story_and_episode_outline": "01_剧本/剧本_全局设定与分集总纲.md"
}
```

- 项目级故事包检查要求 `剧本_全局设定与分集总纲.md` 和项目级完整剧本 `剧本_全剧完整剧本.md` 正文存在（必需产物门）；后者必须完整覆盖开端、发展、高潮、结局、人物弧、主要伏笔及每集/单部局势变化，但不替代逐集执行剧本。设定摘要在剧本阶段确认时现场渲染，不落盘。
- 本索引的自动校验范围：文件存在、`global_story_and_episode_outline` 固定指针及合并文件的两个规定一级章节。真正重算正文 SHA 的对象是各集 `script_contract`（见下节）。
- `global_story_and_episode_outline` 固定指向合并文件。该文件必须同时包含“全局故事圣经”和“分集推进总纲”两个一级章节，不再保存两个独立同名文件；总纲表覆盖全部集数，集数、顺序与时长与 `drama_plan.json` 一致。
- 每集详细完整剧本与 `script_contract` 在该集开始制作时保存到 `episodes/ep_N/01_剧本/`，路径由 `episode_manifest.stage_manifests` 登记、必需产物门强制存在；分集正文必须细化项目级完整故事，不得改变其中的核心因果、结局或集间承接。需要改变时先更新项目级故事包并使受影响分集失效。

### project_data_card.json

本文件在项目级完整剧本确定后立即创建。它是“一次定义、全局引用”的机器权威。身份字段不可被分集覆盖；服装、发型、妆容、伤痕、场景布置、灯光和道具完整性等变化只能通过带时间范围与原因的状态记录生效：

最小合法骨架（内联对象表示「内含这些字段」，字段含义、枚举与示例值见后续字段表；场景/道具状态记录与角色状态同构、差异见表注；集体角色见本节后文群像示例）：

```json
{
  "project_id": "",
  "revision": 1,
  "global_settings": { "project_name": "", "style_asset_id": "STYLE001", "ratio": "9:16", "episode_count": 2, "episode_durations_s": [], "subtitle_style": {} },
  "shared_baseline": { "registry_revision": 1, "status": "planned|approved|not_created", "approved_asset_ids": [] },
  "characters": [
    {
      "character_id": "CHR001",
      "entity_scope": "individual",
      "identity_locked": { "representation_type": "live_action_human", "age_or_life_stage": "", "face_features": {}, "skin_fur_feather_scale": "", "identity_marks": [], "height_and_body": "", "voice_id": "VOICE001" },
      "state_timeline": [ { "state_id": "STATE001", "effective_from": "ep_1:E01S01", "effective_to": "", "reason": "", "changed_fields": ["initial_state"], "affected_shot_ids": [], "affected_segment_ids": [], "asset_version_ids": [], "clothing": {}, "hairstyle": {}, "makeup": {}, "injury_or_surface_state": {} } ],
      "asset_refs": { "turnaround": "CHR001", "face_anchor": "CHR001", "state_assets": [] }
    }
  ],
  "scenes": [ { "scene_id": "SCN001", "layout_locked": {}, "consistency_anchors": [], "base_lighting_locked": {}, "state_timeline": [], "asset_ref": "SCN001" } ],
  "props": [ { "prop_id": "PROP001", "scale_class": "handheld", "scale_reference": "", "appearance_locked": {}, "narrative_functions": [], "state_timeline": [], "asset_ref": "PROP001" } ],
  "voices": [ { "voice_id": "VOICE001", "owner_id": "CHR001", "voice_locked": {}, "voice_anchor": "", "asset_ref": "VOICE001" } ]
}
```

顶层与全局：

| 字段 | 取值/基数 |
|---|---|
| `project_id` / `revision` | 项目 ID；数据卡每次修订递增 revision |
| `global_settings.project_name / style_asset_id / ratio` | 项目名；全局风格资产 ID（如 STYLE001）；画幅如 `9:16`（工具参数，不写进交付包） |
| `global_settings.episode_count / episode_durations_s` | 集数；各集时长（秒）数组，与规划一致 |
| `global_settings.subtitle_style` | 字幕样式对象；默认字幕关闭时为空对象 |
| `shared_baseline.registry_revision / approved_asset_ids` | 共享库修订号；已批准资产 ID 列表 |
| `shared_baseline.status` | 枚举 `planned` / `approved` / `not_created`（状态切换规则见本节后文） |

`characters[]`：

| 字段 | 取值/基数 |
|---|---|
| `character_id` / `entity_scope` | CHR 稳定 ID；枚举 `individual`（缺省值）/ `collective`（后者字段形状见群像示例） |
| `identity_locked.representation_type` | 如 `live_action_human`；非真人画风须全项目同一画风 |
| `identity_locked.age_or_life_stage / face_features / skin_fur_feather_scale / identity_marks / height_and_body` | 年龄或生命阶段、面部特征、肤色/物种表面、身份标志、身高体型——身份锁定项 |
| `identity_locked.voice_id` | 绑定的 VOICE ID |
| `state_timeline[].state_id / effective_from / effective_to / reason / changed_fields` | 状态记录五要素；时间点格式 `ep_1:E01S01`，开放端 `effective_to` 写空串；初始状态 `changed_fields` 为 `["initial_state"]` |
| `state_timeline[].clothing / hairstyle / makeup / injury_or_surface_state` | 服装、发型、妆容、伤痕/表面状态对象 |
| `state_timeline[].affected_shot_ids / affected_segment_ids / asset_version_ids` | 受影响镜头、片段与状态资产版本；基础初始状态可空数组 |
| `asset_refs.turnaround / face_anchor / state_assets` | 三视图资产 ID、头部锚点 ID（如 CHR001）、状态资产列表 |

`scenes[]`：

| 字段 | 取值/基数 |
|---|---|
| `scene_id` / `asset_ref` | SCN 稳定 ID 与场景资产引用 |
| `layout_locked.space_boundary / doors_windows / fixed_furniture / main_routes` | 户型边界、门窗朝向、固定家具、主要通道；例「办公桌居中 文件柜靠入口右侧」 |
| `consistency_anchors` | **3-5 个**唯一可见锚点，每个含对象＋外观＋固定位置；例「后墙中央停在 10:17 的圆形挂钟」「左侧百叶窗缺失第三片叶片」 |
| `base_lighting_locked.source / direction / temperature` | 只锁剧本实际使用的基础光照；例「阴天上午的窗外自然光 / 从画面左侧射入 / 偏冷中性色温」 |
| `state_timeline[]` | 与角色状态同构，**去掉换装四字段、改为 `observable_state`**（一句话可观察结果，例「冷光从左侧进入 固定陈设保持基准布局」） |

`props[]`：

| 字段 | 取值/基数 |
|---|---|
| `prop_id` / `asset_ref` | PROP 稳定 ID 与道具资产引用 |
| `scale_class / scale_reference` | 尺度类别（如 `handheld`）与尺度参照；例「成人单手可握 约 9 厘米长」 |
| `appearance_locked.shape / material / identity_marks` | 形状、材质、标志性磨损；例 `["右下角三道斜向划痕"]` |
| `narrative_functions[]` | 逐场 `{episode_id, scene_id, function}`，登记剧情功能 |
| `state_timeline[]` | 与场景状态同构（`observable_state`）；位置、归属、开合、内容物、破损与完整性变化入状态 |

`voices[]`：

| 字段 | 取值/基数 |
|---|---|
| `voice_id` / `owner_id` / `asset_ref` | VOICE 稳定 ID、归属角色 ID、音色资产 ID |
| `voice_locked.*` | 8 项：`age_and_gender_expression` / `pitch_and_timbre` / `accent_and_language` / `pace` / `rhythm_and_pauses` / `baseline_emotion` / `sentence_ending` / `forbidden_drift` |
| `voice_anchor` | 自然语言声音锚点，声音单定义：台词行只存 `voice_id`，由本表按 ID 解析锚点，`speech_lines` 不再复制该字段；例「25岁年轻女性 声音清亮 普通话标准 略带紧张感 语速偏快」 |

`characters[]` 中 `entity_scope` 为可选兼容字段，旧记录缺省按 `individual` 解释。匿名群众作为稳定群体建模时使用 `entity_scope: collective`，必须填写 `collective_profile` 并将 `asset_refs.collective_profile` 指向群像 CHR；集体角色不填写单人 `identity_locked`、三视图、头部锚点或固定单人 VOICE。`collective_profile` 的人数与构成描述群体范围，不表示每镜必须出现固定人数；逐镜真实人数和位置以分镜调度为准。

群像数据卡示例（字段完整性见下，ID 和范围按项目实际内容填写）：

```json
{
  "character_id": "CHR_CROWD_01",
  "entity_scope": "collective",
  "collective_profile": {
    "group_type": "",
    "count_range": {"min": 1, "max": 8},
    "age_and_gender_mix": [],
    "role_or_faction_mix": [],
    "wardrobe_palette_distribution": [],
    "silhouette_distinction_keys": [],
    "shared_props": [],
    "forbidden_features": [],
    "voice_mode": "none"
  },
  "asset_refs": {"collective_profile": "CHR_CROWD_01"}
}
```

在剧本阶段首次创建数据卡时写 `shared_baseline.status: planned`，资产阶段完成后更新为 `approved` 并填入真实批准资产 ID。

- 当前 `drama_lint.py` 对 `project_data_card.json` 只检查文件是否存在，不解析或评价其中的身份、关系、状态、声音和视觉合同内容；这些内容由主 Agent 按已确认剧本和阶段 Reference 人工复核。不得把 lint 通过解释为数据卡内容正确。
- 面部/头面结构、肤色或物种表面、身份标志、身高体型和 `voice_id` 属于身份锁定项，除非项目级剧本明确发生永久性身份变化，否则不得修改。
- `shared_baseline.status` 在 CHR/SCN/PROP/VOICE/STYLE 实际生成并通过集中验收前不得写 `approved`；分镜只能在该状态为 `approved` 且资产阶段经用户确认后开始。
- 服装、发型、妆容、伤痕和表面状态可变，但每次变化必须有 `state_id/effective_from/effective_to/reason/changed_fields`，且 `changed_fields` 不得为空；同一 SEG 内无换装/造型镜头时不得切换状态。
- 已进入分镜或生成阶段的状态变化还要填写 `affected_shot_ids`、`affected_segment_ids` 和 `asset_version_ids`；基础初始状态可以使用空数组。
- 场景 `layout_locked` 固定户型、门窗朝向、固定家具与主要通道；`consistency_anchors` 必须选择 `3-5` 个包含对象、外观和固定位置的唯一可见锚点；`base_lighting_locked` 只锁定剧本实际使用的基础光照，`state_timeline` 只记录有剧情原因的布置或灯光变化。
- 道具 `appearance_locked` 固定颜色、形状、材质和标志性磨损；`scale_class/scale_reference` 锁定尺度，`narrative_functions` 逐场记录剧情功能，位置、归属、开合、内容物、破损和完整性变化进入带原因与可观察结果的 `state_timeline`。
- 下游 Prompt 必须记录采用的数据卡 revision、角色/场景/道具 ID 与当前 `state_id`，不得复制后再自行改写基础设定。

### script_contract_ep_N.json

保存剧本的机器执行合同，不复制剧情梗概：

```json
{
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "source_markdown": "episodes/ep_1/01_剧本/剧本_完整剧本_ep_1.md",
  "source_sha256": "",
  "duration_s": 120,
  "opening_contract": {
    "plan_opening_id": "OPEN001",
    "inheritance_mode": "direct|episode_variation",
    "variation_reason": "",
    "primary_type": "mystery_question|world_spectacle|character_portrait|visual_spectacle|conflict_driven|custom",
    "supporting_types": [],
    "scene_id": "E01S01",
    "opening_window": "",
    "first_observable_promise": "",
    "escalation_trigger": "",
    "payoff_or_rollover": ""
  },
  "relationship_tension": [
    { "relationship_id": "REL001", "characters": ["CHR001", "CHR002"], "initial": { "power_gap": "", "information_gap": "", "emotional_gap": "" }, "change_nodes": [ {"scene_id": "E01S01", "cause": "", "after": { "power_gap": "", "information_gap": "", "emotional_gap": "" }, "blocking_implication": ""} ] }
  ],
  "highlight_ledger": [
    { "highlight_id": "HL001", "role": "primary|supporting", "episode_id": "ep_1", "scene_id": "E01S03", "dimension": "关系攻防|信息重释|专业能力|标志性场面|视觉母题|声音母题|表演瞬间|情绪余震|结构形式|传播台词|custom", "setup_evidence": "", "payoff_action": "", "state_change": "", "subject_function": "", "format_expression": "", "aftereffect": "" }
  ],
  "scenes": [
    {
      "scene_id": "E01S01",
      "location_id": "SCN001",
      "characters": ["CHR001"],
      "character_states": ["CHR001:STATE001"],
      "prop_states": ["PROP001:STATE001"],
      "data_card_deltas": [],
      "goal": "", "obstacle": "", "strategy_shift": "", "state_change": "",
      "entry_goal": "", "tactic": "", "countermove": "", "turn": "", "exit_value": "",
      "events": [ {"event_id": "B001", "source_excerpt": "源正文逐字摘录", "summary": "必要事件事实"} ],
      "speech_lines": [ {"line_id": "LINE001", "speaker": "CHR001", "voice_id": "VOICE001", "type": "on_screen_dialogue|narration|voiceover|inner_monologue", "source_text": "", "delivery_intent": "", "pause_plan": "", "emotion": "", "emphasis_words": []} ]
    }
  ]
}
```

各集 `script_contract` 重算 `source_markdown` 正文 SHA 并比对 `source_sha256`，另核 revision、唯一场次标题、事件摘录逐字命中与逐字台词来源。`events` 只索引实际发生的事件，不设数量；无台词时 `speech_lines` 为空。当前 script 确认记录保存 `source_snapshot: {file, revision, sha256}`、confirmation_id、真实用户原文；分镜消费该确认版本。`duration_s` 仅保留原规划预测，内容推导改变时不覆写已确认剧本。真实已确认亮点仍逐项承接，不要求新增 primary 名额。

## Manifest 分册 · 共享与分集资产

### asset_registry.json

共享资产的唯一权威登记：

```json
{
  "project_id": "",
  "revision": 1,
  "assets": [
    { "asset_id": "CHR001|SCN001|PROP001|VOICE001|STYLE001", "category": "character|scene|prop|voice|style", "entity_scope": "individual", "version": "v01", "status": "draft|reviewed|approved|rejected|superseded", "files": [], "reference_asset_ids": [], "generation": { "tool": "", "prompt_path": "" } }
  ]
}
```

资产媒体引用可登记项目内存在的文件或原样 HTTP(S) URL；URL 只核引用格式，不下载、不宣称远端可访问或字节已验证。新生成产物仍按阶段交付合同保存与检查本地文件。

`category: voice` 的条目只登记真实样音，使用 `file` 或单项 `files`；HTTP(S) URL 须从已知媒体事实登记 `duration_s`，lint 不下载。本地实际时长由 WAV 元数据或 ffprobe 核验，显式登记的时长须一致；技术通过不代表已试听或自动 approved。派生音频保留同一 VOICE 的来源及派生关系，经资产阶段重新验收后才能采用。

同一 `asset_id + version` 只允许一条权威记录。分集不得复制共享文件，只能通过 `asset_usage_ep_N.json` 引用。
`entity_scope` 仅适用于 `category: character`，旧记录缺省为 `individual`；群像 CHR 必须登记 `collective`，并与 `project_data_card.characters[].entity_scope` 一致。分集专属 CHR 的相同范围写在 `asset_usage_ep_N.json` 对应资产项中。lint 检查群像画像必需字段、群像 ID 与画像引用及各登记层的 `entity_scope` 一致性；缺画像、数据卡记录或登记漂移时报告对应 `collective_*` 错误。
图片资产的 `generation.tool` 只按当前目标实际采用的视觉输入填写：`generation.reference_inputs|input_files|input_images`、`reference_asset_ids` 和 `style_anchor_reference_ids` 均为空时才可使用 文生图（`img`）；其中任一项登记了真实图片时使用 参考生图（`img --ref`）。文本、脚本、知识来源或只含文字的截图不构成视觉参考。

`available_visual_reference_ids`（数组，可选）登记当前资产生成前扫描命中的可用视觉参考图（用户来源图、approved 资产版本、KF/FRM 或 moodboard 的资产/来源 ID）；与 `visual_reference_decision` 配套记录“命中后采用/剥离/待确认”的判断。进入该清单且被判定用于当前目标的图片，后续生成请求必须真实传入并按实际顺序登记；决定不传时必须在采用/剥离边界中写明全部维度无关、质量不可用、冲突待确认或用户明确断开。该字段可登记在资产条目或其 `generation` 对象上，lint 从两级合并读取。

### asset_usage_ep_N.json

保存本集资产快照和本集状态资产：

```json
{
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "shared_assets": [ { "asset_id": "CHR001", "entity_scope": "individual", "version": "v01" } ],
  "episode_assets": [ { "asset_id": "CHR001", "entity_scope": "individual", "state_id": "STATE002", "version": "v02", "files": ["episodes/ep_1/03_资产/角色状态/角色_CHR001_林远_战损_v02_ep_1.png"], "status": "draft|reviewed|approved|rejected|superseded" } ]
}
```

## Manifest 分册 · 分镜与节奏输入

### storyboard_ep_N.json

本 JSON 保存与十五列详细分镜逐镜对应的机器字段、片段规划和运镜合同：

```json
{
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "source_markdown": "episodes/ep_1/02_分镜/分镜_完整分镜表_ep_1.md",
  "director_control_card": "episodes/ep_1/02_分镜/导演总控卡_ep_1.md",
  "source_sha256": "",
  "duration_s": 120,
  "timing_input_sha256": "规范时间投影 SHA",
  "content_review": { "reviewed_inputs": [], "open_issues": [] },
  "audience_execution": {
    "source_plan_revision": 1,
    "viewing_focus": { "source_field": "…", "contract": "…", "scene_or_shot_ids": [] },
    "emotional_payoff": { "source_field": "…", "contract": "…", "scene_or_shot_ids": [] },
    "platform_viewing_context": { "source_field": "…", "contract": "…", "scene_or_shot_ids": [] },
    "expression_boundaries": { "source_field": "…", "contract": "…", "scene_or_shot_ids": [] }
  },
  "highlight_bindings": [
    {
      "highlight_id": "HL001", "segment_id": "SEG003",
      "causal_chain": { "trigger": {"description": "", "shot_ids": ["…"]}, "change": {"description": "", "shot_ids": ["…"]}, "feedback": {"description": "", "shot_ids": ["…"]}, "result": {"description": "", "shot_ids": ["…"]} },
      "payoff_shot_ids": ["…"], "reaction_shot_ids": ["…"],
      "visual_execution": "", "performance_execution": "", "audio_execution": "",
      "aftereffect_shot_ids": ["…"], "deferred_aftereffect_ref": null, "compile_notes": ""
    }
  ],
  "inherited_aftereffect_bindings": [],
  "shots": [
    { "shot_id": "E01S01-SHOT001", "segment_id": "SEG001", "scene_id": "E01S01", "duration_s": 5.5, "time_range_s": [0, 5.5], "timing_events": [], "duration_basis": { "end_event_ids": ["V001"], "duration_s": 5.5 }, "beat_type": "suspense_reveal", "intensity": 3, "camera_family": "axial", "cut_motivation": "eyeline" }
  ],
  "segments": [
    { "segment_id": "SEG001", "group_id": "G001", "duration_s": 5.5, "request_duration_s": 6, "tail_handle_s": 0.5, "time_range_s": [0, 5.5], "design_sha256": "pack 生成", "tail_handle": { "mode": "continue_existing_process", "source_event_id": "V001", "description": "既有过程的技术尾延续" }, "keyframe_requests": [], "shot_mode": "edited|true_one_take", "density_profile": "high_density_short|dialogue_emotional|suspense_build|micro_film|custom", "density_rationale": "", "opening_event_chain": [], "tail_mode": "continuous_motion|cuttable_completion|stable_hold|loop_continuation", "tail_hold_reason": "", "tail_selection_reason": "", "one_take_route": null, "reference_input_plan": [ { "order": 1, "role": "identity_reference", "planned_source": "CHR001_v01（主角）", "opening_binding": "开场首镜旁注 <图片1> 用于锁脸", "adopt": "面部特征与身份标志严格继承", "exclude": "服装不取自本图，按 CHR001:STATE001" } ], "shot_ids": ["E01S01-SHOT001"] }
  ],
  "asset_usage_plan": [ { "asset_id": "CHR001", "version": "v01", "segments": ["SEG001"] } ],
  "inherited_world_facts": [ { "fact_id": "WF001", "category": "festival", "statement": "故事发生在中元节夜的河边集镇", "source": "剧本_完整剧本_ep_1.md E01S01 场景说明" } ],
  "beat_coverage": [ { "beat_id": "B001", "disposition": "kept", "scene": "E01S01", "summary": "灵位前白烛无故自燃", "target_shots": ["E01S01-SHOT001"] } ],
  "seams": [ { "seam_id": "SEAM001", "from_segment": "SEG001", "to_segment": "SEG002" } ]
}
```

分镜索引自动检查正文引用、镜头编号、片段对镜头的完整覆盖、相邻片段引用、亮点绑定和受众执行落点。`shot_mode` 只能为 `edited|true_one_take`；`true_one_take` 必须且只能引用一个 SHOT，总控卡说明与顺看审校确认无硬切、隐藏切、遮挡伪切、匹配剪辑或时间跳跃，`one_take_route` 记录连续摄影机路线及由观看对象、空间、主体关系、光影/焦点或可见信息形成的可读节点（不设数量）。`density_profile` 为可选定性标注（枚举见样例），`density_rationale` 按需记录主导负载与排除理由；复杂动作在正文说明跨镜承接，不另设计数表或逐镜自证字段。`opening_event_chain` 仅在规划明确采用黄金三秒机制时记录异常/承诺、主体行动/目标和反馈/观看关系变化。`tail_mode` 按片段职责选择（算法见 storyboard.md「尾态选择算法」），`tail_selection_reason` 记依据；中间 SEG 默认 `continuous_motion|cuttable_completion`，用 `stable_hold` 时填 `tail_hold_reason`，最终 SEG 默认 `stable_hold`，Loop 用 `loop_continuation`。`highlight_bindings[].causal_chain` 按触发、变化、反馈、结果记录可观察事实和镜头；兑现映射到 `payoff_shot_ids`，反馈映射到 `reaction_shot_ids`，结果映射到本集 `aftereffect_shot_ids` 或跨集引用。`highlight_bindings` 必须覆盖 `script_contract.highlight_ledger` 全部 `role=primary` 项；`segment_id` 是兑现所在 SEG，`payoff_shot_ids` 必须属于该 SEG，`reaction_shot_ids` 可落在本集后续 SEG 且不得早于兑现镜头。余震在本集发生时填真实 `aftereffect_shot_ids`（不得早于兑现/反应镜头）；后续集回收时留空该数组，`deferred_aftereffect_ref` 写成 `{"episode_id":"ep_2","highlight_id":"HL001","binding_id":"HL001-aftereffect"}`。目标集用相同 `binding_id` 写入 `inherited_aftereffect_bindings[]`，结构为 `{"binding_id":"","source_episode_id":"ep_1","source_highlight_id":"HL001","shot_ids":[]}` 形成反向承接。每项必须填视觉、表演、声音、视频编译说明。`audience_execution.source_plan_revision` 必须等于当前已确认 `drama_plan.revision`；四项合同各自填固定 `source_field` 并逐字继承当前 `audience_plan` 对应值，再绑定真实场次或镜头，不得重新画像或更换受众。推导字段由主 Agent 按 `storyboard.md` 人工复核，lint 不对创意质量打分。

`shots[]` 的 `duration_s/time_range_s/timing_events/duration_basis` 来自同一时间内核；`duration_basis` 是结束过程 ID 的结构化追溯，`camera_family` 仅检索标注，均不按静态比例或标签时长验收。

`beat_coverage` 每个源 event_id 一条处置，`beat_id` 对应源事件；`disposition` 取 `kept|compressed|moved|dropped`，四枚举规则（`target_shots` 真实性、`dropped` 的 confirmation_ref 删戏门槛）以 storyboard.md「beat_coverage（节拍去向）」为权威，镜头时间项回指 `beat:<ID>`。人声由 line_id → utterance → speech 分片完整承接。

`reference_input_plan` 是每段必填数组（该段无图参考时写 `[]`）：每项含从 1 连续的 `order`、`role`、`planned_source`（形如 `CHR001_v01（名称）`）、`opening_binding`（必须含同序 `<图片N>`/`<IMGN>` 标记）、`adopt` 与 `exclude`。`role` 合法枚举：连续性四项 `previous_tail_as_start_frame`/`previous_scene_anchor_reference`/`previous_character_state_reference`/`previous_prop_state_reference`，高光 KF 用 `segment_highlight_reference`，资产职责六项 `identity_reference`/`character_state_reference`/`scene_layout`/`prop_structure`/`prop_state_reference`/`style_reference`。顶层 `asset_usage_plan` 登记资产→片段绑定（`segments` 非空，`["*"]` 表示全部片段），与各段输入计划双向对账、双向均为 error（台账绑定但段内未计划传入，或计划传入但台账漏登）。顶层 `inherited_world_facts` 必填，每条含 `fact_id`、`category`（season/festival/date/time_of_day/weather/location_fact/other）、`statement` 和剧本出处 `source`。

`content_review` 是独立观看顺序审校的精简索引（写入门、三元指纹与拒绝盖章规则见 storyboard.md「分镜内容人工复核」）：`reviewed_inputs` 绑定源脚本 SHA/revision、分镜设计投影和时间输入文件 SHA；`open_issues` 非空即拒绝盖章，空数组不构成摄影可达/时间真实/审美成立。设计投影仅排除顶层 review、preflight、confirmations、generation_confirmations、task_id、status、quality_gate、quality_review、output_file、generated_at、validated_at；不递归删除同名语义字段。设计改变后需重新核算/审校，运行事实追加不循环污染设计。

SEG ID 对未变镜头组保持稳定；组内容/摄影/时间变化后的失效规则同 storyboard.md「节奏流水线」合同。

### rhythm_input_ep_N.json

时间语义输入；先完成事件、观看方式、连续画面与摄影路线，再估具体过程。核算只保留声明的开始/持续/先后关系，不找最短排程。示例仅展示格式，数值不构成动作秒数表。

```json
{
  "episode_id": "ep_1",
  "source_script": { "file": "episodes/ep_1/01_剧本/script_contract_ep_1.json", "revision": 1, "sha256": "当前源文件字节 SHA" },
  "utterances": [],
  "scenes": [ { "scene_id": "E01S01", "shots": [ { "shot_id": "E01S01-SHOT001", "timeline": [ { "event_id": "V001", "kind": "visual", "process": "本次具体可见过程", "source_refs": ["beat:B001"], "start_s": 0, "duration_s": 5.3, "after": [] } ] } ], "beat_groups": [ { "group_id": "G001", "shot_ids": ["E01S01-SHOT001"], "tail_handle": { "mode": "continue_existing_process", "source_event_id": "V001", "description": "末镜既有过程继续，不加戏或拉伸前段" } } ] } ]
}
```

时间最多三位小数、内部整数毫秒；start 非负、duration 正数有限，拒绝 bool/字符串/NaN/Inf，不舍入。ID 唯一，after 引用已声明 event_id；依赖环、先后冲突、未知引用均阻断，程序不改排程。每镜取过程最大结束时间，按正式镜头顺序累加场次/集；并行按声明区间而非简单相加。

非 speech 的 kind 为 `visual|camera|hold`，需具体 `process`；`source_refs` 解析 `beat:|line:|chain:|asset_state:`，不得引用不存在的事实。speech 只写 `utterance_id/utterance_offset_s/start_s/duration_s/after`，不重复维护台词文本。utterance 结构：`{utterance_id, line_id, speaker_ref, estimated_duration_s, timing_basis}`；依据为 `director_estimate` + 本次演读 note，或 `existing_measurement` + file/sha256/range_s/evidence（本句真实测量，不是音色样音）。同一发声分片完整、无重叠遗漏，跨镜绝对时间连续。跨镜时各 compilation_map.speech_spans 明确 event_id/spoken_text，按 utterance_offset 顺序逐字拼回一次完整源台词，不逐镜重抄整句。跨 SEG 另需 video.speech_bridge 含 implementation、review_ref 及 utterance_spans（每项 utterance_id/event_id/spoken_text），各镜采用同一逐字分片。程序不从秒数猜词，也不证明接缝音效自然；无可靠实施返回导演层。

未知字段报错；不接受 total/target/segment 预算、动作或反应计数、merge、风格时间覆盖。`beat_type/intensity/speech_pace/note` 仅可选注释，时间投影递归排除它们，不影响核算。

`beat_groups` 是明确剪辑边界，不是自动装箱。组按正式顺序完整覆盖所有镜头，内容时间不必整数。请求时间取满足 h3.json 能力的最小整数秒，尾差 `tail_handle_s` 仅延续末镜结束处的非 speech 过程；超能力或无合法尾设计即报错，不自动缩短/分镜/换模型。

`allocate --write` 只写派生字段及 episode.planned_content_duration_s，不覆盖规划估时；所有语义/文件/镜头检查写入前完成。阅读稿时间列同源渲染，缺镜/额外镜/顺序不符不部分写回。`pack --write` 保持稳定身份并按真实设计失效。KF 数来自实际 `keyframe_requests`，不由时长推导。

## Manifest 分册 · 关键帧

### keyframe_manifest_ep_N.json

保存分镜确认后生成的剧情关键帧职责、文件与验收状态：

```json
{
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "script_contract": "episodes/ep_1/01_剧本/script_contract_ep_1.json",
  "storyboard_manifest": "episodes/ep_1/02_分镜/storyboard_ep_1.json",
  "project_data_card": "00_制作控制/project_data_card.json",
  "keyframes": [
    {
      "keyframe_id": "KF001", "segment_id": "SEG001", "shot_id": "E01S01-SHOT001", "role": "highlight", "highlight_index": 1, "data_card_revision": 1,
      "asset_refs": ["CHR001_v01", "SCN001_v01", "PROP001_v01"], "state_refs": ["CHR001:STATE001"], "information_triggers": ["space_anchor"],
      "narrative_state": "", "character_state": {}, "prop_state": {}, "scene_and_light": {}, "camera_and_composition": {}, "continuity_from": "",
      "prompt_path": "episodes/ep_1/03_资产/提示词/提示词_KF001_SEG001_highlight-1_v01_ep_1.md",
      "file": "episodes/ep_1/03_资产/关键帧/关键帧_KF001_SEG001_highlight-1_v01_ep_1.png",
      "tool": "image_edit", "model": "", "version": "v01", "status": "draft|reviewed|approved|rejected|superseded", "used_by_segments": ["SEG001"]
    }
  ]
}
```

- `storyboard_manifest` 必须引用当前已确认分镜；`segment_id`、`shot_id` 和 `used_by_segments` 必须与分镜中的真实片段和镜头一致。
- `role` 固定为 `highlight`，`highlight_index` 是同一 SEG 内从 `1` 开始的高光序号。关键帧只锁定剧情峰值，不承担生成式首帧或尾帧职责。
- 同一视频片段采用的高光关键帧必须与 `storyboard_ep_N.json` 的高光需求一致；片段首尾连续性由真实 FRM、总控卡逐段执行区和 `SEAMxxx` 负责。
- `tool/model/version/status` 记录 `keyframes.md` 的实际生成结果；视频输入关系记录 `video.md` 的实际调用结果。
- 视频生成后的 `FRMxxx` 抽帧不能回写覆盖 `KFxxx`；偏差登记并按内容质量门处理：关键偏差阻断合格接受，非关键偏差须明确接受；只有用户主动要求修改并重新确认后才返修分镜、关键帧或视频。

## Manifest 分册 · 视频生成与连续性

### video_manifest_ep_N.json

作为本集视频生成结果的权威索引；`00_制作控制/批次/*.json` 继续保存单次请求快照：

```json
{
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "storyboard_manifest": "episodes/ep_1/02_分镜/storyboard_ep_1.json",
  "duration_s": 12,
  "generation_confirmations": [
    {
      "confirmation_id": "VC001",
      "attempt": 1,
      "supersedes_confirmation_ids": [],
      "batch_start_segment_index": 1,
      "batch_end_segment_index": 1,
      "duration_s": 12,
      "planned_video_count": 1,
      "segment_durations": [ {"segment_id": "SEG001", "duration_s": 12} ],
      "displayed_parameter_table": { "task_type": "", "delivery_format": "", "quantity": 1, "total_duration": "12秒", "aspect_ratio_and_resolution": "", "model": "MiniMax H3", "visual_and_continuity": "", "audio_and_subtitles": "", "reference_materials": "" },
      "displayed_storyboard_rows": [ { "segment_id": "SEG001", "duration_s": 12, "visual_content": "", "subject_action": "画面过程（含人物动作；可为非人物主导的画面发展）", "audio": "", "camera_and_materials": "" } ],
      "final_parameters_text": "<用户实际看到的完整普通文本快照：一张两列参数表＋一张五列分镜表，不得有第三张表；内容规则见本节后文>",
      "interaction_ask_call_id": "",
      "interaction_ask_result": "generate",
      "user_message": "",
      "confirmed_at": "2026-09-08T12:00:00+08:00"
    }
  ],
  "segments": [
    {
      "segment_id": "SEG001", "episode_segment_index": 1, "shot_ids": ["E01S01-SHOT001"],
      "tool_mode": "image_to_video",
      "duration_s": 12, "content_duration_s": 11.5, "tail_handle_s": 0.5,
      "binding_id": "preflight 生成", "request_snapshot": {},
      "observable_state_changes": ["门缝光带中掠过一道影子"],
      "compiled_prompt_file": "episodes/ep_1/04_视频片段/交付包_SEG001_v01_ep_1.md", "prompt_sha256": "",
      "h3_prompt_file": "episodes/ep_1/04_视频片段/提示词_SEG001_v01_ep_1.h3.md", "h3_prompt_sha256": "",
      "gen_file": "episodes/ep_1/04_视频片段/gen_SEG001_v01_ep_1.json", "h3_mode": "I2VA",
      "compilation_map": [ {"shot_id": "E01S01-SHOT001", "content_range_s": [0, 11.5], "text_excerpt": "", "spoken_texts": []} ],
      "reference_inputs": [ {"order": 1, "source_type": "asset", "source_id": "CHR001_v01", "file": "shared/03_资产/角色/角色_CHR001_林远_基准状态_v01.png", "role": "identity_reference", "adopt": "采用的身份/状态事实", "exclude": "字幕、水印、平台界面、无关背景与无关人物"} ],
      "required_reference_roles": ["identity_reference"],
      "audio_input_supported": false, "audio_inputs": [], "video_inputs": [], "voice_inputs": [],
      "native_audio_supported": true, "speech_mode": "native_required",
      "speech_lines": [ {"speaker": "", "voice_id": "VOICE001", "type": "on_screen_dialogue", "source_text": "", "delivery_intent": "", "pause_plan": "", "emotion": "", "emphasis_words": []} ],
      "generation_confirmation_id": "VC001",
      "tool_call_id": "", "tool_called_at": "2026-09-08T12:01:00+08:00",
      "output_file": "episodes/ep_1/04_视频片段/片段_SEG001_E01S01_v01_ep_1.mp4",
      "status": "candidate|accepted|rejected|blocked",
      "quality_gate": { "status": "pending|pass|blocked|deviation_accepted", "blockers": [], "deviations": [], "user_acceptance_ref": "" },
      "incoming_episode_seam": null
    }
  ]
}
```

枚举与关键字段（状态语义与确认规则见本节后文）：

| 字段 | 取值/基数 |
|---|---|
| `generation_confirmations[].planned_video_count` | 枚举 `1` / `2`；等于确认范围内 SEG 数、`segment_durations` 项数、`displayed_parameter_table.quantity`、`displayed_storyboard_rows` 行数 |
| `displayed_parameter_table` | 9 个字段：`task_type / delivery_format / quantity / total_duration / aspect_ratio_and_resolution / model / visual_and_continuity / audio_and_subtitles / reference_materials`；按当前批次真实值渲染；逐段时长以根级 `segment_durations` 为结构化对账副本，展示表不另存第三份 |
| `displayed_storyboard_rows[].subject_action` | 兼容机器字段名，语义为「画面过程（含人物动作）」，可描述非人物主导的画面发展；每个 SEG 恰好一行 |
| `segments[].h3_mode` | `T2VA`（纯文本）/ `I2VA`（单锚帧）/ `FL2VA`（首-尾双锚帧）/ `L2VA`（尾锚帧）/ `Ref2VA`（多媒体）；模式集合以 `tools/video/h3.json` capabilities 为准，锚帧首行语义以 `h3-prompt-writing` 为准；逐 SEG 记录实际返回模式，同批次内可不同 |
| `segments[].speech_mode` / `speech_lines[].type` | `native_required`；type 枚举 `on_screen_dialogue / narration / voiceover / inner_monologue`（人声合同见 video.md）；无人声按合同标记 `no_human_voice` 或 `ambient_only` |
| `segments[].status` / `quality_gate.status` | `candidate / accepted / rejected / blocked`；`pending / pass / blocked / deviation_accepted`（语义见后文） |
| `segments[].incoming_episode_seam` | ep_2 及以后首段写 `episode_seams.json` 对应 EPSEAM 完整快照；ep_1 首段及各集非首段写 `null` |

`h3-prompt-writing` 返回值按下表登记到批次快照与对应 SEG/manifest 记录，字段名与枚举保持返回值原样（返回值整体示例见 video.md「图片输入合同」）：

| 字段 | 取值/基数 |
|---|---|
| `task_type` | 返回的任务类型（如 `r2v`），按原值登记，不据媒体种类反推 |
| `segments[].planned_shot_count` | 正整数；严格等于 `shot_plan` 数组长度并与分镜镜头数一致，逐镜填写 |
| `segments[].shot_plan[]` | 每镜 `shot_id / shot_size / camera_position / camera_phases[] / subject_action / visual_process / cut_trigger`；`subject_action` 可选，人物不是画面发展来源时留空，由 `visual_process` 写清环境、空间、物件、光影、焦点、遮挡、声音或构图如何发展 |
| `segments[].shot_plan[].camera_phases[]` | 同一镜头内按顺序发生的摄影与画面阶段；每阶段 `time_or_trigger / image_development / camera_process / focus_or_framing`；数量按内容需要决定，不是必填条数门。`motion_family / motion_path` 等分类字段仅作内部索引可选字段，不是创作菜单、必填项或生成指令 |
| `segments[].incoming_seam` | 集内接缝完整对象，区别于跨集 `incoming_episode_seam`；字段为 `seam_id / previous_segment_id / previous_tail_frame_id / previous_tail_state / current_start_state / cut_type / seam_mode / outgoing_window_frames / incoming_window_frames / action_phase / screen_position_and_direction / camera_angle_and_motion / prop_contact / axis_and_light / sound_bridge / transition_anchor / required_invariants / permitted_deltas / proof_requirement / fallback`；首段写 `START/not_applicable` 形，结构与 SEAM 记录一致 |
| `reference_basis[]` | 创作职责台账；逐项为 `asset_id` 或 `keyframe_id` 之一、`role`、`passed_to_tool: true`；只登记视频工具真实接收的参考，与 `reference_inputs` 逐项对应；只在 Prompt 写 ID 不算传入 |
| `reference_frame_mode` / `reference_frame_path` | 帧参考实际模式（如 `actual_image_input`）与路径，按返回值登记 |
| `segments[].subtitle_enabled` / `video_generation_subtitles` / `subtitle_render_stage` | 字幕开关与渲染阶段（如 `disabled`），按返回值和字幕合同登记 |
| `generation_route` | `{decision, reason, continuity_method, fallback}`；`decision` 枚举 `new_segment / regenerate_segment / return_upstream` |

视频 manifest 填写 `project_data_card_revision` 和 `storyboard_manifest`，以维持生成追溯。

`segments[].status` 的状态语义固定为：

`quality_gate` 是内容质量与结构接受的独立门：`pending` 仅可用于候选；`blocked` 表示关键剧情/证据/台词/身份/动作/接缝/导演意图不合格；`pass` 要求无阻断项；`deviation_accepted` 只允许非关键偏差，且必须关联用户明确接受记录。`segments[].status=accepted` 必须同时满足 `quality_gate.status=pass|deviation_accepted`；不得把文件可播放或 lint 通过当作内容合格证明。

- `candidate`：片段已生成、保存、具备可渲染输出并完成即时交付，但尚未完成视频阶段用户确认；`drama_lint.py --stage video` 在发起确认前允许该状态。
- `accepted`：用户已明确接受该片段。目标继续到成片时，只能在 `proceed_assembly` 确认成功后，与视频阶段确认记录和 `assembly_confirmation` 原子写入；`objective.target_stage=video` 时，在普通视频阶段确认成功后写入。
- `rejected|blocked`：不得进入拼接或成片。`drama_lint.py --stage final|all` 要求本次采用的全部 SEG 均为 `accepted`。

`segments[].compiled_prompt_file` 指向**导演交付包（五段式）**（`episodes/ep_N/04_视频片段/交付包_SEGxxx_vNN_ep_N.md`，交给 `h3-prompt-writing` skill 的输入文件，也是返修回溯凭证）；`segments[].h3_prompt_file` 指向**提交给模型的 H3 成稿**（`提示词_SEGxxx_vNN_ep_N.h3.md`；写法与字段结构以 `h3-prompt-writing` skill 为准，本仓不复述）——成稿只含 H3 正文字段，不含交付包内容（两文件物理分离，禁止合并后切分）；`segments[].gen_file` 是该镜 `tools/video/h3.py` 的 gen.json；三者同一 `_vNN` 版本，`h3_mode` 记录实际调用 `h3-prompt-writing` 返回的模式（逐 SEG，同批次内可不同），参考用法与输入映射同样采用其返回值；本 Skill 不另行推断模式。已生成或候选状态必须登记成稿及其哈希与 gen.json 路径。

`gen_file.preflight` 是唯一客观预检回执，不设 review/revision 次数门。video 仅登记同一 binding_id、request_snapshot、两份 Prompt 路径与各自字节 SHA。编译映射按当前镜头顺序覆盖 content_range_s，逐字台词位于实际发声块；人工仍需逐段对照摄影、证据、表演和继承事实。

`generation_confirmations[]` 每项对应一次真实批次确认，必须满足：

- `confirmation_id` 全局唯一，`attempt` 为从 `1` 递增的正整数。首次确认的 `supersedes_confirmation_ids` 为空；重生或返修覆盖既有 SEG 时，新增确认记录并在该数组中列出所有范围重叠的旧确认 ID，禁止删除历史确认。替代关系只对新旧确认范围的交集生效：例如旧确认覆盖 SEG001-SEG002、新确认只覆盖 SEG001，则旧确认对 SEG002 继续有效。替代确认时间必须晚于被替代确认，每个 SEG 的 `generation_confirmation_id` 必须指向覆盖该 SEG 的最新有效确认。
- `planned_video_count` 只能为 `1|2`，并等于确认范围内 SEG 数、`segment_durations` 项数、`displayed_parameter_table.quantity` 和 `displayed_storyboard_rows` 行数。
- `segment_durations` 按 `episode_segment_index` 排序，每项 `segment_id` 与 `duration_s` 必须和该次冻结的 request_snapshot 对应 SEG 完全一致；当前 SEG 仅与覆盖它的最新有效确认比较；`duration_s` 是本批次总时长，必须等于各项之和。
- `displayed_parameter_table` 表示实际展示的一张两列表格，字段不得拆成逐 SEG 参数表；其中“数量”必须按当前批次真实值渲染，“分段时长”行在 `final_parameters_text` 中逐段可核验（见下条），不再在表对象内另存字符串副本。
- `displayed_storyboard_rows` 表示实际展示的一张五列表格；机器结构将第一列拆为 `segment_id + duration_s`，其余四列依次为 `visual_content`、`subject_action`、`audio`、`camera_and_materials`。其中 `subject_action` 是兼容既有机器字段名的“画面过程（含人物动作）”，可以描述非人物主导的画面发展。每个 SEG 恰好一行，只能引用当前批次已确认分镜和真实素材。
- `final_parameters_text` 保存用户实际看到的完整普通文本，必须包含一张两列参数表和一张五列分镜表，不得包含第三张表；两张表之后才允许调用 AskUserQuestion。

`reference_inputs` / `video_inputs` / `audio_inputs` 只登记实际提交媒体，mode 与参考用法采用 `h3-prompt-writing` 的实际返回值，不通过媒体种类反推。三类数组每项含从 1 连续的 `order`、真实文件或原样 HTTP(S) URL（`file`）、唯一 `role` 与非空 `adopt`/`exclude`（逐项采用与剥离边界）；图片项带 `source_id`（带版本资产 ID，或 KF/FRM/用户素材标识）与 `source_type`，视频/音频项带 `resource_id`；drama_lint 按下列枚举校验 role——图片：`identity_reference`、`character_state_reference`、`scene_layout`、`prop_structure`、`prop_state_reference`、`segment_highlight_reference`、`previous_tail_as_start_frame`、`previous_scene_anchor_reference`、`previous_character_state_reference`、`previous_prop_state_reference`、`style_reference`；视频：`source_video_for_edit`、`previous_segment_video_reference`、`style_video_reference`、`character_video_reference`、`scene_video_reference`；音频：`voice_audio_reference`、`music_reference`、`sound_effect_reference`、`ambient_reference`。视频重生成的制作目标必须有一个真实待修改源视频，登记在 `video_inputs` 中（含资源编号和文件路径）；重生片段沿用同一 SEG 的已确认时长与画幅参数，由冻结快照对账，不另设保持性登记对象。

`ep_2` 及以后各集的首个 segment 将 `incoming_episode_seam` 写成 `episode_seams.json` 对应 `EPSEAMxxx` 的完整快照；`ep_1` 首段及非首段写 `null`。每个视频批次中的同名字段必须与该快照一致。

### gen_SEGxxx_vNN_ep_N.json

请求字段为 model/mode/duration_s/content_duration_s/tail_handle_s/aspect/seed/inputs/extra/preflight。mode 采用实际调用 `h3-prompt-writing` 的返回值；extra 含真实 workflow、base_url、resolution、options 及运行 polling/timeout。预检按 local-runtime 的优先级解析 workflow/base_url，写回 gen 后再展示确认；执行只使用冻结值。options 不得覆盖 prompt/duration/seed/resolution/媒体槽位等保留字段，未知输入不能静默丢弃。

可选 content_duration_s/tail_handle_s 一旦填写必须成对且精确相加等于请求时长，并与当前 SEG 对账。当前 AutoDL 封装没有独立 aspect_ratio 参数，只有 resolution 横/竖/1:1 枚举；aspect 如填写只是创作意图，须匹配该方向，不声称精确比例已独立提交。精确画幅要求需按真实工作流能力处理，不静默承诺。manifest 的输入 file/order/role 必须与 gen 中实际输入逐项一致；URL 不因规范路径而改写。

`preflight_video.py` 在用户生成确认前准备同一请求；回执含 h3_prompt_file/sha256、request_sha256、request_snapshot、dependencies、media、content_review_ref、compilation_map、inbound、binding_id、validated_at。绑定排除自身/时间戳及 polling/timeout，包含所有实际提交参数、媒体顺序、成稿与实际设计依赖。预检不要求已生成结果或 generate 授权；执行函数与 CLI 在任何 POST 前重验同一 PreparedRequest 和真实授权。

本地文件冻结实际字节 SHA，并用同一 bytes 装请求；HTTP(S) 文件 URL 原字符串直传，不下载、复制、base64 或要求本地副本。URL 媒体标记 identity=url_string_only、remote_bytes_verified=false；绑定只冻结 URL 字符串及提交参数，不声称验证远端字节。日志仅显示 binding/摘要，不输出签名 URL、token 或 data URI。

每条历史 generation_confirmation.request_snapshot 保存 `{segments: [{segment_id, episode_segment_index, duration_s, binding_id, request_snapshot}]}` 及 request_snapshot_sha256。总长/展示/参数按自己的冻结快照校验。global 用户确认记录保存 binding_ids 与以 binding_id 为键的 request_snapshots；新增确认显式 supersedes_confirmation_ids，保留历史，不能删旧记录消除错误。

### continuity_ep_N.json

用于保存本集抽帧和集内接缝：

```json
{
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "frames": [ { "frame_id": "FRM001", "segment_id": "SEG001", "role": "start|scene|tail", "timecode": "", "file": "" } ],
  "seams": [ { "seam_id": "SEAM001", "from_segment": "SEG001", "to_segment": "SEG002", "outgoing_window_frames": 12, "incoming_window_frames": 12, "selected_cut": {}, "comparison": { "character_position": "accepted|rework", "pose_and_action_phase": "accepted|rework", "camera_angle_and_axis": "accepted|rework", "scene_layout_and_light": "accepted|rework" }, "status": "planned|verified|blocked" } ]
}
```

连续后段编译前，主 Agent 查看前段实测媒体并锁定 `adopted_cut_out` 独立 JSON：source_video_file/source_video_sha256、adopted_in_s、timecode_s、measured_duration_s、frame_file/frame_sha256、fps、零起始 frame_number、frame_timecode_s、next_frame_timecode_s；cut_id 由 adopted_cut.validate_cut 算得。continuity.seams 登记 adopted_cut_out_file/cut_id，后段 video.inbound 使用 `{cut_file, cut_id}` 且真实输入 role=previous_tail_as_start_frame 指向同帧。timecode_s 是最终 trim 的排他结束边界；入站取该边界前最后保留帧。frame_timecode_s/next_frame_timecode_s 保存 ffprobe 解码帧 PTS 原文，尾帧的 next 为 null；不能把恰在结束边界、已被裁掉的帧作为入站，也不按平均帧率猜帧号。

`ffmpeg_tool.py lock-cut --project-root <root> --source <相对视频> --frame <新帧.png> --cut-file <新合同.json> --at <采用出点> --adopted-in <采用入点>` 用实测 probe 的解码帧 PTS 选取最后保留帧，按解码序号抽帧并登记指纹，不代替观看选点；不覆盖已登记版本。最终 trim 传同一 --adopted-cut-file/--adopted-cut-id，修改出点须新版本并重建受影响后段绑定。

出点/源/帧变化使该入站及依赖后段的预检/确认失效。最终 delivery.adopted_segments 每项登记 segment_id、source_video_file、start_s、end_s、cut_file、cut_id，连续片段必须使用同一采用区间；ffmpeg trim 复验同一 cut，不能在后段生成后悄悄换前段出点。无入站素材就沿用下一批确认，不能预授权未来未知帧或让执行者补写请求。

## Manifest 分册 · 成片交付

### delivery_manifest_ep_N.json

保存最终采用片段、音轨、字幕和交付文件：

```json
{
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "duration_s": 120,
  "duration_display": "2分钟",
  "assembly_confirmation": { "confirmation_purpose": "final_assembly", "interaction_ask_call_id": "实际确认调用 ID", "interaction_ask_result": "proceed_assembly", "segment_ids": ["SEG001", "SEG002"], "user_message": "用户通过确认工具同意进入拼接的原文", "confirmed_at": "2026-09-08T12:30:00+08:00" },
  "subtitle_enabled": false,
  "clean_master": "episodes/ep_1/05_成片/[项目名]_成片_[比例]_无字幕_v01_ep_1.mp4",
  "subtitle_master": "", "subtitle_source": "", "subtitle_final": "", "subtitle_burn_params": "",
  "basic_qc_reports": [ "episodes/ep_1/05_成片/质检_基础_无字幕_v01_ep_1.json" ],
  "subtitle_alignment_report": "",
  "outputs": [ "episodes/ep_1/05_成片/[项目名]_成片_[比例]_无字幕_v01_ep_1.mp4" ],
  "adopted_segments": [ { "segment_id": "SEG001", "source_video_file": "episodes/ep_1/04_视频片段/[项目名]_SEG001_v01_ep_1.mp4", "start_s": 0, "end_s": 5.5, "cut_file": "episodes/ep_1/04_视频片段/剪辑区间/cut_out_SEG001_for_SEG002_v01.json", "cut_id": "lock-cut 回执指纹" } ],
  "status": "deliverable|candidate|blocked",
  "content_quality_gate": { "status": "pass|blocked|deviation_accepted", "blockers": [], "deviations": [], "user_acceptance_ref": "" }
}
```

`deliverable` 必须通过整片顺读/观看质量门；关键因果、信息可见性、已确认台词、动作、身份、道具/空间连续性或关键接缝失败时为 `blocked`。非关键偏差须列明并引用用户接受记录后才能 `deviation_accepted`。

片段及整片的 `user_acceptance_ref` 回指真实确认的 `quality_deviation_snapshot`：episode_id、segment_id（整片为 null）、output_file、output_sha256、deviations。output_file 须为项目内相对路径，比对时按规范化相对 POSIX 路径等价判定（正反斜杠不影响同一性），但越界路径或不同文件不通过。输出或明确偏差改变后旧接受失效。blockers 非空不能 pass 或 deviation_accepted；程序核来源/范围，不判断偏差是否关键。

`project_data_card_revision` 按实际数据卡 revision 填写，`assembly_confirmation` 保存真实拼接确认。

默认字幕关闭时，只保留无字幕母版对应的一项 `basic_qc_reports`，字幕相关路径留空，`outputs` 只能包含 `clean_master`。用户明确要求字幕时，无字幕母版作为内部烧录源保留，两种内部媒体各有一份基础可交付检查报告，并且必须存在字幕对齐报告；但 `outputs` 必须且只能包含 `subtitle_master`，不得把 `clean_master`、SRT、字幕 JSON 或检查报告作为额外交付物。

- `assembly_confirmation` 保存进入本集成片拼接前的独立确认；`segment_ids` 必须按顺序精确等于本次采用的 accepted SEG，`interaction_ask_result` 固定为 `proceed_assembly`。
- `adopted_segments` 逐项登记连续后段实际入站的采用区间（`segment_id/source_video_file/start_s/end_s/cut_file/cut_id`）：只要存在带 `inbound` 的后段，每个入站 cut 必须在本数组有唯一对应行，且最终 trim 复验同一源文件与同一入/出点；无入站剪辑时写空数组。
- 最终交付校验时 `delivery_manifest_ep_N.json.status` 可以为 `deliverable|candidate`；`blocked` 不得交付。`candidate` 可以展示并明确内容风险；未通过内容质量门不能称为合格成片或进入 accepted。该媒体状态不等于用户确认；用户确认仍记录在 `制作状态.json` 与 `用户确认记录.jsonl`。
- `basic_qc_reports` 由主 Agent 根据真实 `ffmpeg_tool probe` 探测终态与实际播放结果生成，分别绑定对应成片、输入文件哈希和媒体探测结果。
- `subtitle_alignment_report` 由主代理依据 `delivery.md` 的台词对齐规则生成，绑定当前分集 `script_contract` 的 `speech_lines` 和实际带音轨媒体的路径、字节数与 SHA-256。
- 基础媒体检查结果为 `blocked` 时不得交付；字幕关闭时不执行字幕对齐。字幕开启时，字幕对齐失败不使内部无字幕母版失效，但会阻断唯一交付物字幕版，修复前不得改交无字幕母版。需要人工判断的画面与表演问题直接查看成片，不要求额外填写固定 Markdown 报告。
