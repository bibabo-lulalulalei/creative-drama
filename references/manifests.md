# 项目、分集与素材 Manifest Ref

当项目初始化、接收用户素材、进入任一生产阶段、恢复中断任务或交付分集时读取本文件。本文件是目录、命名、JSON 字段、枚举、基数和引用关系的唯一权威；创作正文仍以 Markdown 为准，不在 JSON 中复制整篇正文。

## 权威引用

- 规划字段及确认事务：`planning.md`。
- 剧本、分镜、资产、视频和成片的内容规则：对应阶段 Reference。
- 本文件只定义目录、命名、JSON schema、引用关系、状态和基数；不重新定义生成算法、创作阈值或人工审美标准。
- 本文件定义的 schema、基数和引用关系，以及对应阶段权威 Reference 定义的准出条件，是产物合同；`scripts/drama_lint.py` 只负责实现其中可客观检查的部分。文档示例与校验器发生遗漏或冲突时，先按本文件和对应阶段 Reference 判断正确合同，再修正过时的一方；不得扭曲真实产物来迁就校验器。

## 设计原则

- 完整模式必须在根目录 `01_剧本/` 先保存项目级完整故事包；多集项目覆盖全局故事圣经、全部分集推进总纲、人物弧、伏笔账本和最终结局。逐集可执行剧本进入 `episodes/ep_N/`，只在该集开始制作时生成，完整写出场次、动作和全部人声文本。轻量模式不要求建立独立剧本文件。
- 项目级 JSON 管理跨集事实、来源、项目数据卡、共享资产、跨集接缝与索引；分集 JSON 管理本集状态、引用和阶段产物。
- 项目级故事包确认后把 `current_episode` 设为 `ep_1`，从该集详细剧本开始逐集生产。共享资产可以在首次实际需要的分集创建并进入 `asset_registry.json`；后续集先从共享登记和已完成分集资产中复用 approved 版本，只把新增或状态变化项写入本集资产。
- 跨集稳定的角色基准图、主要场景参考图、核心道具、音色和全局风格 moodboard 只保存于 `shared/`，不复制到每集目录。
- 完整模式中，`00_制作控制/project_data_card.json` 是角色、场景、道具和音色“不可变身份 + 可变状态时间线”的单一事实源。下游只填写片段增量，不得手工复述另一套基础设定；轻量模式不创建该文件。
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
│   ├── project_data_card.json       # 仅完整模式
│   ├── source_manifest.json
│   ├── 制作状态.json
│   ├── 用户确认记录.jsonl
│   ├── episode_seams.json           # 仅完整模式
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
│   ├── 批次/
│   │   └── batch-NNN_ep_N.json
│   └── 校验报告/                 # 仅保存自动媒体检查结果
├── 01_剧本/                         # 完整模式必有；轻量模式不创建独立剧本层
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
    │   │   ├── storyboard_ep_1.json           # 仅完整模式
    │   │   ├── rhythm_input_ep_1.json         # 仅完整模式；节奏语义输入，引擎唯一计算源的上游
    │   │   ├── 分镜_阅读稿_ep_1.md            # 仅完整模式
    │   │   ├── 导演总控卡_ep_1.md             # 仅完整模式
    │   │   ├── 分镜_完整分镜表_ep_1.md
    │   │   ├── 分镜_视频片段执行表_ep_1.md    # 仅完整模式
    │   │   ├── 分镜_连续性账本_ep_1.md        # 仅完整模式
    │   │   └── 分镜_资产需求清单_ep_1.md      # 仅完整模式
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
    │   │   ├── 提示词_SEGxxx_vNN_ep_1.md
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

`00_制作控制/校验报告/` 中需要逐集定位的报告也追加 `_ep_N`；项目级汇总报告不追加集号。
`scripts/drama_lint.py` 在完整模式分镜阶段检查 `storyboard_ep_N.json`、`分镜_阅读稿_ep_N.md`、`导演总控卡_ep_N.md` 和 `分镜_完整分镜表_ep_N.md`，并客观确认完整分镜表存在十五列。视频片段执行表、连续性账本和资产需求清单仍按 `storyboard.md` 生成，并由主 Agent 人工复核；不能因为校验器尚未逐项检查而省略。轻量模式只检查 `分镜_完整分镜表_ep_1.md` 及其十五列结构，不创建或检查其余分镜配套文件。不得同时创建导演阐述、导演控制包或强风格系统卡形成第二套决策中心。
剧情关键帧在分镜确认后命名为 `关键帧_KFxxx_SEGxxx_highlight-N_vNN_ep_N.[ext]`；`highlight-N` 是同一 SEG 内从 `1` 开始的高光序号。目录中的 `ep_1` 仅为实例。
主要场景必须生成共享布局参考图，用于锁定空间拓扑、门窗朝向、固定陈设和基础光位；它不是逐镜剧情画面，不替代分镜场景合同。剧情关键帧在分镜确认后按 SEG 生成并进入 `关键帧/`，视频完成后另从真实画面提取 FRM，两者分别承担“生成前目标”和“生成后事实”。

## 全局 JSON

### project_manifest.json

只做项目总索引，不复制 `drama_plan.json` 的创意与模型字段：

```json
{
  "schema_version": "1.0",
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

`episode_ids`、`episode_manifests` 和 `drama_plan.json.scale_plan.episode_count` 必须一致，不允许缺集、重复或指向不存在的文件。新规划必须包含 `duration_contract`（mode/scope/target/tolerance/source/confirmed）；`scale_plan` 中逐集时长是估时分配，精确合同只校验计划内部求和，用户目标范围按合同 scope 校验，不得回传到镜头配平。
完整模式从剧本阶段开始必须创建 `project_script_manifest_path` 指向的项目级剧本索引，并创建 `project_data_card_path` 指向项目数据卡；`episode_seams_path` 指向实际跨集接缝文件。轻量模式不进入独立剧本、资产或分段接缝流程，将 `project_script_manifest_path`、`project_data_card_path`、`shared_asset_registry_path` 和 `episode_seams_path` 留空，不得为满足路径字段伪造这些文件。

### 制作状态.json

这是项目级与逐集阶段状态的唯一数据源。`drama_plan.json` 和 `episode_manifest_ep_N.json` 不再重复保存状态；旧项目已有的镜像字段允许保留，但不参与阶段判断，新项目不要创建：

```json
{
  "project_id": "",
  "revision": 1,
  "current_stage": "planning",
  "current_episode": null,
  "phases": {
    "planning": "in_progress",
    "script": "pending",
    "assets": "pending",
    "storyboard": "pending",
    "keyframes": "pending",
    "video": "pending",
    "final": "pending"
  },
  "episodes": {
    "ep_1": {
      "manifest": "episodes/ep_1/episode_manifest_ep_1.json",
      "stage_status": {
        "script": "pending",
        "assets": "pending",
        "storyboard": "pending",
        "keyframes": "pending",
        "video": "pending",
        "final": "pending"
      }
    }
  },
  "artifacts": [],
  "open_issues": [],
  "last_successful_operation": ""
}
```

状态只允许 `pending|in_progress|awaiting_confirmation|confirmed|merged|invalidated|blocked`。`merged` 只允许轻量模式中的 `script|assets|storyboard|keyframes|video`，表示这些阶段不建立独立产物包、用户交付和确认门；轻量模式仍必须保存十五列详细分镜并据此编译 Prompt，但不生成完整模式的其他创作配套文件。完整模式项目级故事包阶段使用 `current_stage: script` 与 `current_episode: null`；项目级确认后使用 `current_stage: script` 与 `current_episode: ep_1` 开始第 1 集详细剧本。轻量模式规划页取得 `generate` 后，立即把五个中间阶段写为 `merged`、把 `current_episode` 设为 `ep_1` 并进入 `final`。媒体或文档验证通过后才能递增 revision 并更新状态；文件存在、接口成功或聊天中声称完成都不能单独证明阶段完成。

### 用户确认记录.jsonl

每次收到用户对当前阶段的明确确认后追加一行，禁止代理预写、补写或把无回复视为确认：

```json
{"stage":"planning","episode_id":"","revision":1,"decision":"confirmed","confirmation_mode":"full","changed_artifacts":[],"impact_scope":[],"confirmation_purpose":"project_execution","interaction_ask_call_id":"实际确认调用 ID","interaction_ask_result":"proceed_project","user_message":"用户通过确认工具确认项目方案的原文","confirmed_at":"2026-09-08T12:00:00+08:00"}
{"stage":"script","episode_id":"ep_1","revision":2,"decision":"confirmed","confirmation_mode":"full","changed_artifacts":[],"impact_scope":[],"confirmation_purpose":"","interaction_ask_call_id":"","interaction_ask_result":"","user_message":"用户确认第 1 集详细剧本的原文","confirmed_at":"2026-09-08T12:05:00+08:00"}
{"stage":"assets","episode_id":"ep_1","revision":2,"decision":"confirmed","confirmation_mode":"full|incremental","base_revision":1,"changed_artifacts":[],"impact_scope":[],"confirmation_purpose":"","interaction_ask_call_id":"","interaction_ask_result":"","user_message":"用户本轮明确回复原文","confirmed_at":"2026-09-08T12:10:00+08:00"}
```

- `planning` 始终是项目级确认。`script` 有两种作用域：项目级故事包确认的 `episode_id` 留空；分集详细剧本确认必须填写当前 `episode_id`。`assets|storyboard|keyframes|video|final` 始终填写当前 `episode_id`。同名阶段在不同作用域或不同集的确认记录不能互相替代。
- 完整模式且 `target_stage=video|final` 时，planning 写 `project_execution/proceed_project`。轻量模式直接执行标准视频生成确认，planning 写 `video_generation/generate`；同一次调用还登记为当前唯一视频的 `generation_confirmations`。所有视频确认结构只读取 `interaction-ask-video-clarification-ref.md`。
- 当目标继续到成片时，进入拼接的同一次 AskUserQuestion 还必须原子写入 `stage=video` 的确认记录：`confirmation_purpose: video_acceptance_and_final_assembly`、与 `assembly_confirmation` 相同的 `interaction_ask_call_id`、`interaction_ask_result: proceed_assembly`。当 `objective.target_stage=video` 时，video 阶段只做普通产物确认并停止，不创建虚假的拼接授权。
- `user_message` 保存触发继续的用户原文；空值、系统生成文字或仅有内部检查结果无效。
- `confirmed_at` 必须是带时区的 ISO-8601 时间。
- 首次确认或重大修改使用 `confirmation_mode: full`；此时 `base_revision` 可省略，`changed_artifacts` 与 `impact_scope` 可为空。已有真实全量确认基础上的局部微调可使用 `incremental`，必须记录上一全量确认 revision、实际变化文件和影响范围；禁止第一次确认就写 `incremental`。
- 用户提出修改时不写 `confirmed`；完成修改、重新展示并再次收到明确确认后才追加新记录。
- 阶段状态写为 `confirmed` 时必须存在同阶段有效确认记录；后续阶段校验会据此阻断跳步。

### 合规证明_阶段名.json

只有运行环境或用户明确要求额外审计证明时，才在 `00_制作控制/合规证明/` 保存对应证明；它不是常规阶段准出硬门。完整委派规则读取 `delegation.md`，建议结构为：

```json
{
  "stage": "planning|script|assets|storyboard|keyframes|video|final",
  "executor": "main_agent|main_agent_director",
  "delegated": false,
  "skill_read": ["SKILL.md"],
  "upstream_artifacts": [
    {
      "path": "项目根目录内相对路径",
      "sha256": "64位小写十六进制",
      "revision": 1
    }
  ],
  "tool_calls": [
    {
      "operation_id": "与操作日志一致的唯一 ID",
      "tool": "实际工具名",
      "status": "completed",
      "evidence_path": "/absolute/path/to/evidence",
      "evidence_sha256": "64位小写十六进制",
      "observed_metadata": {"width": 1080, "height": 1920}
    }
  ],
  "delegations": [],
  "forbidden_tools_used": [],
  "declaration": "本阶段严格遵循skill要求，未使用禁止的替代工具；本阶段委派情况与 delegation.md 一致"
}
```

`planning|script|storyboard` 的 `delegated` 必须为 `false` 且 `delegations` 为空。`assets|keyframes` 只有在图片工具执行被外包时才记录委派；`video` 只要发生实际视频生成/编辑工具调用，`delegated` 必须为 `true` 并记录 `video_execution` 交接包；`final` 只要发生拼接、裁剪、混音、mux、字幕烧录等媒体变更工具调用，`delegated` 必须为 `true` 并记录 `final_media_execution` 交接包。每个交接包使用 Skill 内或项目内相对路径，保存逐文件输出白名单、实际输出、硬约束、验收标准、检查命令和禁止再委派声明；画布写入、用户交付、确认工具调用和阶段状态收口不得出现在 subagent 委派范围内。
当前 `drama_lint.py` 的输出就是本次结构检查结果，不回填到被检查的合规证明中，避免证明文件预先声明自身已通过。`declaration` 必须以 `本阶段严格遵循skill要求，未使用禁止的替代工具` 开头，后面允许追加本阶段真实说明。
规划、剧本和分镜属于纯文件创作阶段，没有外部生成调用时 `tool_calls` 直接写空数组，不得虚构 `file_creation`。除规划外，`upstream_artifacts` 必须完整覆盖上一阶段当前确认产物，每项记录项目内绝对路径、确认 revision 和确认记录中的 SHA-256。资产、关键帧、视频和成片属于生成或媒体处理阶段，必须保存实际调用；每项引用 `操作日志.jsonl` 中同名、同阶段且状态为 `succeeded` 的 `operation_id`，工具名必须一致，证据文件必须列在该操作的 `outputs` 中、实际存在且 SHA-256 匹配。图片和视频输出还必须保存真实文件探测得到的 `observed_metadata`，并与日志 `output_metadata` 一致。

### 操作日志.jsonl

每次外部生成、媒体处理或重要阶段状态变更追加一行；普通 Markdown/JSON 写入不需要伪装成工具调用。尚未发生操作时允许文件为空：

```json
{"operation_id":"","idempotency_key":"","input_revision":1,"stage":"","target_ids":[],"tool":"","params_summary":{},"attempt":1,"status":"started|succeeded|partial|failed","outputs":[],"output_metadata":{},"recovery_action":"","timestamp":"2026-09-08T12:00:00+08:00","prev_hash":"上一条 record_hash；首条为 64 个 0","record_hash":"当前对象移除 record_hash 后按键排序紧凑 JSON 的 SHA-256"}
```

操作日志按时间顺序追加，不修改历史行。`prev_hash` 与 `record_hash` 仅在运行环境提供可信签名或哈希能力时启用，不作为当前 `drama_lint.py` 的阶段硬门。恢复任务时先读取 `制作状态.json`、`last_successful_operation`、操作日志和实际文件。外部调用部分成功时保留成功输出，只补失败项，不重复执行已成功调用。

### 校验器效率模式

- `--stage planning|script|assets|storyboard|keyframes|video|final|all` 选择阶段检查范围；`--stage all` 用于最终发布或专项审计。
- `--changed-file <项目内文件>` 可重复传入，仅为旧调用兼容；当前实现仍执行所选 `--stage` 的完整检查，不做依赖图裁剪。
- `--fix` 仅为旧调用兼容，当前不自动创建、补写或修改任何项目文件。
- 项目初始化、新版本复制、引用更新和剧本合同同步当前均由主 Agent 按本文件规则完成，不得调用校验器未提供的参数。

### project_script_manifest.json

完整模式必须创建；轻量模式不创建本文件或独立 Markdown 剧本。完整模式的 Markdown `剧本_全剧完整剧本.md` 必须完整覆盖开端、发展、高潮、结局、人物弧、主要伏笔及每集/单部局势变化，但不替代逐集执行剧本：

```json
{
  "schema_version": "1.0",
  "project_id": "",
  "revision": 1,
  "global_story_and_episode_outline": "01_剧本/剧本_全局设定与分集总纲.md",
  "source_markdown": "01_剧本/剧本_全剧完整剧本.md",
  "source_sha256": "",
  "episode_count": 2,
  "total_duration_s": 240,
  "episodes": [
    {
      "episode_id": "ep_1",
      "duration_s": 120,
      "opening_state": "",
      "main_conflict": "",
      "major_turns": [],
      "climax_or_payoff": "",
      "ending_state": "",
      "next_hook": "",
      "detailed_script": "",
      "script_contract": ""
    }
  ],
  "character_arcs": [],
  "plot_threads": [],
  "final_resolution": ""
}
```

- 项目级故事包检查要求 `剧本_全局设定与分集总纲.md` 和项目级完整剧本正文存在（设定摘要在剧本阶段确认时现场渲染，不作为落盘产物检查）；未来集的 `detailed_script` 与 `script_contract` 允许为空。当前集详细剧本完成后再填写对应路径，且路径必须真实存在。
- `global_story_and_episode_outline` 固定指向合并文件。该文件必须同时包含“全局故事圣经”和“分集推进总纲”两个一级章节，不再保存两个独立同名文件。
- `episodes` 数量、顺序和时长必须与 `drama_plan.json` 一致，并覆盖每个 `ep_N` 的开场状态、冲突、主要变化、高潮/兑现、结尾状态及下一钩子。
- `character_arcs`、`plot_threads` 和 `final_resolution` 保证人物弧、伏笔与结局跨集闭合。
- 每集详细完整剧本在该集开始制作时保存到 `episodes/ep_N/01_剧本/`；它必须细化项目级完整故事，不得改变其中的核心因果、结局或集间承接。需要改变时先更新项目级故事包并使受影响分集失效。

### source_manifest.json

用户上传和外部引用的图片、视频、音频、文档必须登记；没有素材时写空 `sources`，不得省略文件：

```json
{
  "schema_version": "1.0",
  "project_id": "",
  "revision": 1,
  "sources": [
    {
      "source_id": "SRC001",
      "media_type": "image|video|audio|document",
      "source_uri": "",
      "stored_path": "",
      "sha256": "",
      "source_origin": "user_upload|external_reference|generated"
    }
  ]
}
```

- 每个用户提供的 URL、附件 ID 或输入实例都必须先作为独立来源登记，即使系统提示给出相同 `local path`、相同 `image.png` 或相同 basename。`source_uri` 保存原始 URL 或可追溯附件标识；`stored_path` 使用 `SRCxxx` 唯一命名，禁止多个不同 URL 写入同一路径或互相覆盖。只有逐 URL 读取、保存并计算 `sha256` 之后，才允许把内容哈希完全相同的文件标记为重复内容；重复内容仍保留各自 `source_id` 与原始 URL 记录，不能删除来源。
- 本地文件必须记录实际 `stored_path` 和 `sha256`；纯 URL 保存规范化 `source_uri`。需要作为视觉参考、文字来源或后续工具输入的 URL 必须下载或转存到项目内并记录 `stored_path`，不能只保留 URL 文本。
- `stored_path` 必须是项目根目录内的相对路径；结构检查会重新计算文件 SHA-256，声明值与当前文件不一致时立即阻断。
- 需要复制或下载到项目内的输入统一保存为 `00_制作控制/输入素材/来源_SRCxxx_[原始名称]_vNN.[ext]`；仅服务单集时追加 `_ep_N`。
- 用途、采用范围和授权说明可按项目需要补充，但不作为自动检查字段。

### project_data_card.json

本文件只用于完整模式，在项目级完整剧本确定后立即创建。它是“一次定义、全局引用”的机器权威。身份字段不可被分集覆盖；服装、发型、妆容、伤痕、场景布置、灯光和道具完整性等变化只能通过带时间范围与原因的状态记录生效：

```json
{
  "schema_version": "1.0",
  "project_id": "",
  "revision": 1,
  "global_settings": {
    "project_name": "",
    "style_asset_id": "STYLE001",
    "ratio": "9:16",
    "episode_count": 2,
    "episode_durations_s": [120, 120],
    "subtitle_style": {}
  },
  "shared_baseline": {
    "registry_revision": 1,
    "status": "planned|approved|not_created",
    "approved_asset_ids": []
  },
  "characters": [
    {
      "character_id": "CHR001",
      "entity_scope": "individual",
      "identity_locked": {
        "representation_type": "live_action_human",
        "age_or_life_stage": "",
        "face_features": {},
        "skin_fur_feather_scale": "",
        "identity_marks": [],
        "height_and_body": "",
        "voice_id": "VOICE001"
      },
      "state_timeline": [
        {
          "state_id": "STATE001",
          "effective_from": "ep_1:E01S01",
          "effective_to": "",
          "reason": "初始状态",
          "changed_fields": ["initial_state"],
          "affected_shot_ids": [],
          "affected_segment_ids": [],
          "asset_version_ids": [],
          "clothing": {},
          "hairstyle": {},
          "makeup": {},
          "injury_or_surface_state": {}
        }
      ],
      "asset_refs": {
        "turnaround": "CHR001",
        "face_anchor": "CHR001",
        "state_assets": []
      }
    }
  ],
  "scenes": [
    {
      "scene_id": "SCN001",
      "layout_locked": {
        "space_boundary": "长方形办公室",
        "doors_windows": "入口在前墙左侧 百叶窗在左墙",
        "fixed_furniture": "办公桌居中 文件柜靠入口右侧",
        "main_routes": "入口至办公桌之间保留直线通道"
      },
      "consistency_anchors": [
        "门口右侧的绿色铁皮文件柜",
        "后墙中央停在 10:17 的圆形挂钟",
        "左侧百叶窗缺失第三片叶片",
        "桌面右角的红色旋转电话",
        "从门口延伸到办公桌的黑白方砖"
      ],
      "base_lighting_locked": {
        "source": "阴天上午的窗外自然光",
        "direction": "从画面左侧射入",
        "temperature": "偏冷中性色温"
      },
      "state_timeline": [
        {
          "state_id": "STATE001",
          "effective_from": "ep_1:E01S01",
          "effective_to": "",
          "reason": "剧情初始发生在阴天上午",
          "changed_fields": ["initial_state"],
          "observable_state": "阴天上午 冷光从左侧进入 固定陈设保持基准布局",
          "affected_shot_ids": [],
          "affected_segment_ids": [],
          "asset_version_ids": []
        }
      ],
      "asset_ref": "SCN001"
    }
  ],
  "props": [
    {
      "prop_id": "PROP001",
      "scale_class": "handheld",
      "scale_reference": "成人单手可握 约 9 厘米长",
      "appearance_locked": {
        "shape": "长方形旧皮盒",
        "material": "深棕色磨损皮革",
        "identity_marks": ["右下角三道斜向划痕"]
      },
      "narrative_functions": [
        {"episode_id": "ep_1", "scene_id": "E01S01", "function": "制造父亲遗物的悬念"},
        {"episode_id": "ep_2", "scene_id": "E02S03", "function": "通过调包改变证据归属"}
      ],
      "state_timeline": [
        {
          "state_id": "STATE001",
          "effective_from": "ep_1:E01S01",
          "effective_to": "ep_2:E02S02",
          "reason": "初始状态",
          "changed_fields": ["initial_state"],
          "observable_state": "闭合 完整 内有文件 女主持有",
          "affected_shot_ids": [],
          "affected_segment_ids": [],
          "asset_version_ids": []
        }
      ],
      "asset_ref": "PROP001"
    }
  ],
  "voices": [
    {
      "voice_id": "VOICE001",
      "owner_id": "CHR001",
      "voice_locked": {
        "age_and_gender_expression": "",
        "pitch_and_timbre": "",
        "accent_and_language": "",
        "pace": "",
        "rhythm_and_pauses": "",
        "baseline_emotion": "",
        "sentence_ending": "",
        "forbidden_drift": []
      },
      "voice_anchor": "25岁年轻女性 声音清亮 普通话标准 略带紧张感 语速偏快",
      "asset_ref": "VOICE001"
    }
  ]
}
```

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

完整模式在剧本阶段首次创建数据卡时写 `shared_baseline.status: planned`，资产阶段完成后更新为 `approved` 并填入真实批准资产 ID。轻量模式不创建本文件；用户已有素材和文字约束直接由已确认规划、来源登记与内部十五列分镜承接。

- 当前 `drama_lint.py` 对 `project_data_card.json` 只检查文件是否存在，不解析或评价其中的身份、关系、状态、声音和视觉合同内容；这些内容由主 Agent 按已确认剧本和阶段 Reference 人工复核。不得把 lint 通过解释为数据卡内容正确。
- 面部/头面结构、肤色或物种表面、身份标志、身高体型和 `voice_id` 属于身份锁定项，除非项目级剧本明确发生永久性身份变化，否则不得修改。
- 完整模式中，`shared_baseline.status` 在 CHR/SCN/PROP/VOICE/STYLE 实际生成并通过集中验收前不得写 `approved`；分镜只能在该状态为 `approved` 且资产阶段经用户确认后开始。轻量模式不适用本数据卡及批准门。
- 服装、发型、妆容、伤痕和表面状态可变，但每次变化必须有 `state_id/effective_from/effective_to/reason/changed_fields`，且 `changed_fields` 不得为空；同一 SEG 内无换装/造型镜头时不得切换状态。
- 已进入分镜或生成阶段的状态变化还要填写 `affected_shot_ids`、`affected_segment_ids` 和 `asset_version_ids`；基础初始状态可以使用空数组。
- 场景 `layout_locked` 固定户型、门窗朝向、固定家具与主要通道；`consistency_anchors` 必须选择 `3-5` 个包含对象、外观和固定位置的唯一可见锚点；`base_lighting_locked` 只锁定剧本实际使用的基础光照，`state_timeline` 只记录有剧情原因的布置或灯光变化。
- 道具 `appearance_locked` 固定颜色、形状、材质和标志性磨损；`scale_class/scale_reference` 锁定尺度，`narrative_functions` 逐场记录剧情功能，位置、归属、开合、内容物、破损和完整性变化进入带原因与可观察结果的 `state_timeline`。
- 下游 Prompt 必须记录采用的数据卡 revision、角色/场景/道具 ID 与当前 `state_id`，不得复制后再自行改写基础设定。

### asset_registry.json

共享资产的唯一权威登记：

```json
{
  "schema_version": "1.0",
  "project_id": "",
  "revision": 1,
  "assets": [
    {
      "asset_id": "CHR001|SCN001|PROP001|VOICE001|STYLE001",
      "category": "character|scene|prop|voice|style",
      "entity_scope": "individual",
      "name": "",
      "version": "v01",
      "status": "draft|reviewed|approved|rejected|superseded",
      "files": [],
      "source_ids": [],
      "reference_asset_ids": [],
      "locked_features": [],
      "variable_states": [],
      "used_by_episodes": ["ep_1"],
      "used_by_shots": [],
      "generation": {
        "tool": "",
        "model": "",
        "prompt_path": ""
      },
      "last_reviewed": ""
    }
  ]
}
```

同一 `asset_id + version` 只允许一条权威记录。分集不得复制共享文件，只能通过 `asset_usage_ep_N.json` 引用。
`entity_scope` 仅适用于 `category: character`，旧记录缺省为 `individual`；群像 CHR 必须登记 `collective`，并与 `project_data_card.characters[].entity_scope` 一致。分集专属 CHR 的相同范围写在 `asset_usage_ep_N.json` 对应资产项中。lint 检查群像画像必需字段、群像 ID 与画像引用及各登记层的 `entity_scope` 一致性；缺画像、数据卡记录或登记漂移时报告对应 `collective_*` 错误。
图片资产的 `generation.tool` 只按当前目标实际采用的视觉输入填写：`generation.reference_inputs|input_files|input_images`、`reference_asset_ids` 和 `style_anchor_reference_ids` 均为空时才可使用 文生图（`img`）；其中任一项登记了真实图片时使用 参考生图（`img --ref`）。`source_ids` 只表示来源追溯，不单独决定工具路由；文本、脚本、知识来源或只含文字的截图不得因存在 `source_id` 被误判为视觉参考图。

`available_visual_reference_ids`（数组，可选）登记当前资产生成前扫描命中的可用视觉参考图（用户来源图、approved 资产版本、KF/FRM 或 moodboard 的资产/来源 ID）；与 `visual_reference_decision` 配套记录“命中后采用/剥离/待确认”的判断。进入该清单且被判定用于当前目标的图片，后续生成请求必须真实传入并按实际顺序登记；决定不传时必须在采用/剥离边界中写明全部维度无关、质量不可用、冲突待确认或用户明确断开。该字段可登记在资产条目或其 `generation` 对象上，lint 从两级合并读取。

### episode_seams.json

只登记跨集边界；集内片段接缝由 `continuity_ep_N.json` 管理：

```json
{
  "schema_version": "1.0",
  "project_id": "",
  "revision": 1,
  "seams": [
    {
      "seam_id": "EPSEAM001",
      "from_episode": "ep_1",
      "to_episode": "ep_2",
      "from_segment": "",
      "to_segment": "",
      "actual_tail_frame": "episodes/ep_1/04_视频片段/抽帧/FRMxxx_tail_vNN_ep_1.png",
      "actual_tail_sha256": "",
      "visual_state": {},
      "audio_state": {},
      "unresolved_hooks": [],
      "cut_strategy": "",
      "seam_mode": "continuous|elliptical",
      "required_invariants": ["identity", "screen_direction"],
      "permitted_deltas": [],
      "status": "planned|verified|blocked"
    }
  ]
}
```

完整模式的单集作品保留该文件并写空 `seams`。`continuous` 表示叙事状态连续，`permitted_deltas` 必须为空；`elliptical` 表示明确的时间、空间或认知跳跃，必须列出至少一个允许变化维度。跨集接缝在分镜阶段可先写 `planned`；上一集视频完成后复核画面、声音、未决钩子、接缝模式和切换策略，再改为 `verified`。`continuous` 必须把真实尾帧路径和 SHA-256 写入 `actual_tail_frame/actual_tail_sha256`；`elliptical` 可记录尾帧供追溯，但下一集不必把它作为视觉输入。下一集首段只能消费完整复制的 verified 记录。轻量模式只有一个视频，不创建本文件。
## 每集 JSON

### episode_manifest_ep_N.json

每集总入口只保存身份和各阶段文件指针：

```json
{
  "schema_version": "1.0",
  "project_id": "",
  "episode_id": "ep_1",
  "episode_number": 1,
  "revision": 1,
  "duration_s": 120,
  "duration_display": "2分钟",
  "stage_manifests": {
    "script": "episodes/ep_1/01_剧本/script_contract_ep_1.json",
    "storyboard": "episodes/ep_1/02_分镜/storyboard_ep_1.json",
    "assets": "episodes/ep_1/03_资产/asset_usage_ep_1.json",
    "keyframes": "episodes/ep_1/03_资产/keyframe_manifest_ep_1.json",
    "video": "episodes/ep_1/04_视频片段/video_manifest_ep_1.json",
    "continuity": "episodes/ep_1/04_视频片段/continuity_ep_1.json",
    "delivery": "episodes/ep_1/05_成片/delivery_manifest_ep_1.json"
  }
}
```

轻量模式仍保留同一 `stage_manifests` 键集，但 `script|assets|keyframes|continuity` 写空字符串，`storyboard` 直接指向 `episodes/ep_1/02_分镜/分镜_完整分镜表_ep_1.md`，`video|delivery` 指向实际 manifest。不得为填充这些路径创建无用途的完整模式文件。

### script_contract_ep_N.json

保存剧本的机器执行合同，不复制剧情梗概：

```json
{
  "schema_version": "1.0",
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "source_markdown": "episodes/ep_1/01_剧本/剧本_完整剧本_ep_1.md",
  "source_sha256": "",
  "duration_s": 120,
  "story_engine": {
    "dramatic_question": "",
    "protagonist_desire": "",
    "opposition": "",
    "stakes": "",
    "irreversible_choice": "",
    "episode_payoff": ""
  },
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
    {
      "relationship_id": "REL001",
      "characters": ["CHR001", "CHR002"],
      "initial": {"power_gap": "", "information_gap": "", "emotional_gap": ""},
      "change_nodes": [{"scene_id": "E01S01", "cause": "", "after": {"power_gap": "", "information_gap": "", "emotional_gap": ""}, "blocking_implication": ""}]
    }
  ],
  "reveal_ledger": [
    {"reveal_id": "REV001", "fact": "", "plant_scene": "E01S01", "development_scene": "E01S02", "reveal_scene": "E01S03", "consequence": ""}
  ],
  "shareable_line": {
    "mode": "dialogue|visual|sound|exception",
    "line_id": "LINE001",
    "text_or_motif": "",
    "placement": "climax|reversal|ending",
    "dramatic_support": ""
  },
  "highlight_ledger": [
    {
      "highlight_id": "HL001",
      "role": "primary|supporting",
      "episode_id": "ep_1",
      "scene_id": "E01S03",
      "dimension": "关系攻防|信息重释|专业能力|标志性场面|视觉母题|声音母题|表演瞬间|情绪余震|结构形式|传播台词|custom",
      "setup_evidence": "",
      "payoff_action": "",
      "state_change": "",
      "subject_function": "",
      "format_expression": "",
      "aftereffect": ""
    }
  ],
  "scenes": [
    {
      "scene_id": "E01S01",
      "location_id": "SCN001",
      "characters": ["CHR001"],
      "character_states": ["CHR001:STATE001"],
      "prop_states": ["PROP001:STATE001"],
      "data_card_deltas": [],
      "goal": "",
      "obstacle": "",
      "strategy_shift": "",
      "state_change": "",
      "entry_goal": "",
      "tactic": "",
      "countermove": "",
      "turn": "",
      "exit_value": "",
      "speech_lines": [
        {
          "line_id": "LINE001",
          "speaker": "CHR001",
          "voice_id": "VOICE001",
          "voice_anchor": "25岁年轻女性 声音清亮 普通话标准 略带紧张感 语速偏快",
          "type": "on_screen_dialogue|narration|voiceover|inner_monologue",
          "source_text": "",
          "display_text": "",
          "spoken_text": "",
          "delivery_intent": "",
          "pause_plan": "",
          "emotion": "",
          "emphasis_words": []
        }
      ]
    }
  ]
}
```

剧本索引自动检查正文引用、场次编号、音色资产引用及主要亮点 ID；剧情质量、关系、表演与表达仍由创作者和用户判断。`role=primary` 的亮点必须在分镜 `highlight_bindings` 中逐项兑现。

### storyboard_ep_N.json

本 JSON 只用于完整模式，保存与十五列详细分镜逐镜对应的机器字段、片段规划和运镜合同。轻量模式只生成 `分镜_完整分镜表_ep_1.md`，不创建本 JSON：

```json
{
  "schema_version": "1.1",
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "source_markdown": "episodes/ep_1/02_分镜/分镜_完整分镜表_ep_1.md",
  "director_control_card": "episodes/ep_1/02_分镜/导演总控卡_ep_1.md",
  "source_sha256": "",
  "duration_s": 120,
  "audience_execution": {
    "source_plan_revision": 1,
    "viewing_focus": {
      "source_field": "audience_plan.viewing_focus",
      "contract": "继承已确认受众的首要观看焦点",
      "scene_or_shot_ids": ["E01S01-SHOT001"]
    },
    "emotional_payoff": {
      "source_field": "audience_plan.emotional_payoff",
      "contract": "本集承担的情绪回报",
      "scene_or_shot_ids": ["E01S03-SHOT004"]
    },
    "platform_viewing_context": {
      "source_field": "audience_plan.platform_viewing_context",
      "contract": "已确认平台观看场景下的可读性执行",
      "scene_or_shot_ids": ["E01S01"]
    },
    "expression_boundaries": {
      "source_field": "audience_plan.expression_boundaries",
      "contract": "继承已确认表达禁区及规避方式",
      "scene_or_shot_ids": ["E01S02-SHOT003"]
    }
  },
  "highlight_bindings": [
    {
      "highlight_id": "HL001",
      "segment_id": "SEG003",
      "causal_chain": {
        "trigger": {"description": "", "shot_ids": ["E01S03-SHOT002"]},
        "change": {"description": "", "shot_ids": ["E01S03-SHOT003"]},
        "feedback": {"description": "", "shot_ids": ["E01S03-SHOT004"]},
        "result": {"description": "", "shot_ids": ["E01S04-SHOT001"]}
      },
      "payoff_shot_ids": ["E01S03-SHOT003"],
      "reaction_shot_ids": ["E01S03-SHOT004"],
      "visual_execution": "",
      "performance_execution": "",
      "audio_execution": "",
      "aftereffect_shot_ids": ["E01S04-SHOT001"],
      "deferred_aftereffect_ref": null,
      "compile_notes": ""
    }
  ],
  "inherited_aftereffect_bindings": [],
  "causal_ledger": [
    {
      "chain_id": "CL001",
      "trigger_fact": "嘴唇肿得老高（惩戒显形）",
      "trigger_source": {"ref_type": "beat", "ref_id": "B026"},
      "evidence_shot_ids": ["E01S04-SHOT002"],
      "reaction_shot_ids": ["E01S04-SHOT002", "E01S04-SHOT003"],
      "result_shot_ids": ["E01S04-SHOT004"],
      "cross_episode_refs": [],
      "visibility_contract": "肿唇在 SHOT002/003 必须部分可见（嘴角肿出、捂不住）；手部全遮即断链",
      "breakpoint_risk": "C2",
      "highlight_binding_ref": null
    }
  ],
  "shots": [
    {
      "shot_id": "E01S01-SHOT001",
      "segment_id": "SEG001",
      "scene_id": "E01S01",
      "duration_s": 5.5,
      "duration_basis": "节拍5.5(suspense_reveal)",
      "beat_type": "suspense_reveal",
      "intensity": 3,
      "spoken_text": "",
      "camera_family": "axial",
      "cut_motivation": "eyeline",
      "time_range": "45.0-50.5",
      "cut_tolerance_s": 1.0,
      "has_speech": false,
      "causal_role": "establish",
      "responds_to": null,
      "establishes": "本镜为下游建立的可见/可听事实（无则 null）",
      "evidence_visibility": "in_frame"
    }
  ],
  "rhythm_extremes": {
    "fastest": [
      {"shot_id": "E01S02-SHOT003", "duration_s": 1.5, "beat": "惊吓/冲突高点"},
      {"shot_id": "E01S02-SHOT001", "duration_s": 2.0, "beat": "动作/追逐"},
      {"shot_id": "E01S01-SHOT004", "duration_s": 2.5, "beat": "对白"}
    ],
    "slowest": [
      {"shot_id": "E01S01-SHOT001", "duration_s": 5.5, "beat": "悬念/揭示"},
      {"shot_id": "E01S03-SHOT002", "duration_s": 5.0, "beat": "情绪余韵"},
      {"shot_id": "E01S02-SHOT005", "duration_s": 4.5, "beat": "蓄压"}
    ]
  },
  "beat_duration_overrides": {},
  "engine_output_hash": "由引擎 allocate --write 写入的 sha256 指纹（勿手填，也不得留空串；lint 以此区分库版本过期与算术字段被手改）",
  "segments": [
    {
      "segment_id": "SEG001",
      "shot_mode": "edited|true_one_take",
      "density_profile": "high_density_short|dialogue_emotional|suspense_build|micro_film|custom",
      "density_rationale": "",
      "indivisible_action_units": [
        {
          "action_unit_id": "ACTU001",
          "state_before": "",
          "action_and_path": "",
          "feedback": "",
          "state_after": "",
          "shot_ids": ["E01S01-SHOT001"]
        }
      ],
      "opening_event_chain": [],
      "tail_mode": "continuous_motion|cuttable_completion|stable_hold|loop_continuation",
      "tail_hold_reason": "",
      "tail_selection_reason": "",
      "one_take_route": null,
      "shot_ids": ["E01S01-SHOT001"]
    }
  ],
  "seams": [
    {
      "seam_id": "SEAM001",
      "from_segment": "SEG001",
      "to_segment": "SEG002"
    }
  ]
}
```

分镜索引自动检查正文引用、镜头编号、片段对镜头的完整覆盖、相邻片段引用、主要亮点绑定和受众执行落点。`shot_mode` 只能为 `edited|true_one_take`；`true_one_take` 必须且只能引用一个 SHOT，并由导演总控卡证明没有硬切、隐藏切、遮挡伪切、匹配剪辑或时间跳跃，`one_take_route` 记录连续摄影机路线，以及由观看对象、空间、主体关系、光影/焦点或可见信息形成的至少三个可读节点。`density_profile` 用于区分高密度平台短片、对白/情感、悬疑蓄力、微电影/生活流和自定义节奏；`density_rationale` 记录主导内容负载和排除理由，`indivisible_action_units` 记录动作单元到 SHOT 的映射。镜头数量不按精确 15 秒触发硬配额；`opening_event_chain` 仅在规划目标明确采用黄金三秒机制时记录异常/承诺、主体行动/目标和反馈/观看关系变化。`tail_mode` 必须按片段职责选择，`tail_selection_reason` 记录选择依据；中间 SEG 默认 `continuous_motion|cuttable_completion`，使用 `stable_hold` 时填写 `tail_hold_reason`，最终 SEG 默认 `stable_hold`，Loop 使用 `loop_continuation`。`highlight_bindings[].causal_chain` 按触发、变化、反馈、结果记录可观察事实和镜头；变化/兑现映射到 `payoff_shot_ids`，反馈映射到 `reaction_shot_ids`，结果映射到本集 `aftereffect_shot_ids` 或跨集引用。`highlight_bindings` 必须覆盖 `script_contract.highlight_ledger` 中全部 `role=primary` 项；`segment_id` 是亮点兑现所在 SEG，`payoff_shot_ids` 必须属于该 SEG，`reaction_shot_ids` 可落在本集后续 SEG且不得早于兑现镜头。余震在本集发生时填写真实 `aftereffect_shot_ids`，这些镜头不得早于兑现/反应镜头；计划在后续集回收时留空该数组，并把 `deferred_aftereffect_ref` 写成 `{"episode_id":"ep_2","highlight_id":"HL001","binding_id":"HL001-aftereffect"}`。目标集对应绑定必须用相同 `binding_id` 写入 `inherited_aftereffect_bindings[]`，每项结构为 `{"binding_id":"","source_episode_id":"ep_1","source_highlight_id":"HL001","shot_ids":[]}`，形成反向承接。每项还必须填写视觉、表演、声音和视频编译说明。`audience_execution.source_plan_revision` 必须等于当前已确认 `drama_plan.revision`；四项执行合同必须各自填写固定 `source_field` 并逐字继承当前 `audience_plan` 对应值，再绑定到真实场次或镜头，不得在分镜阶段重新画像或更换受众。上述推导字段由主 Agent 按 `storyboard.md` 人工复核；lint 不对其创意质量打分。

`shots[]` 每镜机读字段（节奏与运镜检查用，规则见 `storyboard.md`）：`duration_s` 是 lint 节奏检查的权威时长，由引擎 `allocate --write` 写回；`duration_basis` 是该时长的发票，分项用 `+` 连接、括号内注释不参与加总、加总恒等于 `duration_s`（基础标签形如 `台词5.5(18字@4/s)`、`节拍4.0(opening_hook)`、`角色5(payoff)`，后续项仅可为 `取整±`/`夹取±`；存量 `配平±` 发票只作历史数据兼容，新计算禁止生成）；`beat_type`（可选）以 `scripts/beat_types.json` 的 `beat_types` keys 为准（核心 8 类冻结，扩展类见《节拍类型库》§2），lint 直接读该 json 校验、不在本文另列枚举，是单镜执行标注、与段级 `density_profile` 正交；`intensity`（1-5）与 `spoken_text`（该镜台词原文，无则空串）是节奏语义字段，与 `rhythm_input_ep_N.json` 同源；`camera_family` 每镜必填，使用 `static` 表示摄影机在该镜中固定，其他标签填写该镜最显著的摄影方式。它不完整表达复合摄影过程，也不限制可用的摄影方式；lint 按全体镜头统计 `static` 占比，超过 40% 即报错并阻断关键帧/视频阶段，具体规则见 `storyboard.md`「运镜与镜头差异化」。`cut_motivation`（可选）枚举 `match_on_action|eyeline|sound_bridge|occlusion|reaction|spatial|information|motivated_hard_cut`，段内末镜与一镜到底段唯一镜免填（存量项目的自由文本 `cut_motivation` 回填期报 info，应逐步改写为枚举）；`time_range`（可选）是期望区间而非承诺值，仅供 QC 容忍窗判定；`cut_tolerance_s`（默认 `1.0`，`duration_s < 2.5` 的镜与高节拍精度镜收紧 `0.5`，容忍窗为闭区间）；`has_speech`（可选布尔，该镜承载出镜对白/旁白/内心独白时置 `true`，beat 时长符合性检查跳过）。segment 级另有 `rhythm_uniform_exempt_reason`（可选，段内容确实均匀时填写理由，豁免段内时长全同检查）。计划层只承诺镜头顺序、每镜期望时长与段总时长，切点精确位置不是承诺项。

顶层节奏字段：`rhythm_extremes` 记录引擎 `stats` 输出的全片最快/最慢镜（与分场节奏卡 fastest/slowest 声明对账）；`beat_duration_overrides` 登记本集对节拍生效区间的覆盖（三层生效区间优先级：本集 overrides > 风格档案 > 库默认）；`engine_output_hash` 是引擎写回结果的指纹，lint 重算 `allocate` 输出与其不符即报 `engine_drift`。**分工铁律**：`duration_s`、`duration_basis`、镜数、段划分、`rhythm_extremes`、`engine_output_hash` 为算术字段，一律由 `scripts/rhythm_engine.py` 生成与写回；手改任何一个都报 `engine_drift`（error）。LLM 只维护 `rhythm_input_ep_N.json` 中的语义字段。

`shots[]` 单镜因果字段（`schema_version` `1.1` 起；推导时机见 `storyboard.md`「因果链台账」节）：`causal_role` 每镜必填、单值，语义为本镜**主**剪辑职责，枚举 `establish|evidence|reaction|result|transition`，与十五列分镜表「镜头职责」列对齐；一镜多职不在此字段表达——镜头出现在哪几条链、哪个角色位，由 `causal_ledger` 承载，避免同一事实两处登记。`responds_to` 结构为 `{"ref_type": "beat|shot|asset_state|world_fact", "ref_id": "B028", "trigger_fact": "该镜反应/结果所回应的已建立事实"}`：`causal_role=reaction|result` 的镜头必填；此外凡被任一链列入 `reaction_shot_ids|result_shot_ids` 的镜头，lint 反查此项必填（交叉规则，无论 `causal_role` 填什么）。`establishes`（本镜为下游建立的可见/可听事实，无则 `null`）与 `evidence_visibility`（枚举 `in_frame|partial|occluded|audio_only`）：凡被任一链列入 `evidence_shot_ids` 的镜头，lint 反查此两项必填（交叉规则，无论 `causal_role` 填什么）——「role 填 reaction 但实为证据镜」的镜头无法绕过证据字段强制。`evidence_visibility: occluded` 是合法值（允许有意遮挡做悬念），但填 `occluded` 时必须在 `establishes` 中写明遮挡理由与揭示点——把「遮」从默认行为变成需要论证的行为。`responds_to.ref_id` 与 `trigger_source.ref_id` 按 `ref_type` 解析：`beat` → `beat_coverage.beat_id`；`shot` → 本集 `shots[].shot_id`；`world_fact` → `inherited_world_facts.fact_id`（WF##）；`asset_state` → `project_data_card` 的 `state_id`（STATE###）；lint 按各自表查存在性。

`causal_ledger` 顶层因果链台账（`1.1` 起必填，数组可为空）：`beat_coverage` 回答「每条剧本 beat 去了哪」，`causal_ledger` 回答「跨镜头的因果链条是否闭合」；只登记含反应/态度转变/证据依赖的链，不全量复制 beat。`visibility_contract` 是核心产出物：一句话锁定「证据在哪些镜头、以什么程度必须可见/可听」，同时是剧本-分镜对照审校的对照表与视频交付包禁区来源（消费规则见 `video.md`）。证据/反应/结果跨集时按 `deferred_aftereffect_ref` 先例登记 `cross_episode_refs: [{"episode_id": "ep_2", "note": "…"}]`；本集 `shot_ids` 查存在性，跨集引用查对端闭合，且跨集引用不进本集三个 `shot_ids` 数组，避免误报。`breakpoint_risk` 登记断点风险类型（C1-C5，枚举定义见 `storyboard.md`），供审校重点核。`highlight_binding_ref`：该链已被某 `highlight_bindings` 覆盖时填其 `highlight_id`，不再重复登记四步结构。台账是镜头引用与可见性合同的唯一权威：总控卡台词证据链条目不列证据镜头号，改写 `causal_chain_ref: CLxxx` 引用（台词真假/误判标记、剧本来源场次、后果语义仍留总控卡），lint 双向对账；跨 SEG 的 `visibility_contract` 条款在分镜定稿时派生写入对应 `SEAMxxx.required_invariants`，台账仍为唯一权威，SEAM 卡为派生引用。

`schema_version` 检查集门控：`1.0` 为因果字段前的存量版本，lint 跳过单镜因果字段与 `causal_ledger` 的全部检查（旧项目不强制回填）；新建或修订分镜使用 `1.1`，启用本节全部因果检查。`revision` 是每项目独立递增，跨项目比较无意义，不作门控键。

### rhythm_input_ep_N.json

本 JSON 只用于完整模式，是节奏系统的**语义输入表**：LLM 只做语义判断（节拍拆解、动作单元计数、beat_type/intensity/spoken_text 标注）并填写本文件；全部算术（镜数、镜时长、SEG 装箱、极值、KF 张数）由 `scripts/rhythm_engine.py` 计算并写回 `storyboard_ep_N.json`：

```json
{
  "episode_id": "ep_1",
  "total_duration_s": 720,
  "engine_version": 2,
  "beat_library_version": 1,
  "style_profile": null,
  "beat_duration_overrides": {"suspense_reveal": [4.0, 8.0]},
  "scenes": [
    {
      "scene_id": "E01S01",
      "rhythm_card": {
        "waveform": "低—高—爆",
        "main_accent": "E01S01-SHOT013",
        "fastest_beat": "E01S01-SHOT014",
        "slowest_beat": "E01S01-SHOT013"
      },
      "boundary_candidates": ["E01S01-SHOT003", "E01S01-SHOT007"],
      "shots": [
        {
          "shot_id": "E01S01-SHOT014",
          "beat_type": "scare_climax",
          "intensity": 4,
          "spoken_text": "尔勿妄为也。",
          "speech_pace": "normal",
          "action_units": 1,
          "reaction_units": 0,
          "merge_with_next": false,
          "is_payoff": false,
          "is_final": false,
          "info_injection": false,
          "role_note": "惩戒发声"
        }
      ]
    }
  ]
}
```

逐字段说明（示例数值仅演示格式）：

- `episode_id` / `total_duration_s`：集标识与集总时长（秒）；`total_duration_s` 可供 `kf-count` 和计划范围核对使用，不是 `allocate` 的镜长配平输入。镜长只按逐镜语义字段计算，SEG 由 `pack` 按真实镜长装箱。
- `engine_version` / `beat_library_version`：填写时使用的引擎版本与《节拍类型库》版本；lint 发现 `beat_library_version` 与当前库不一致时报 `beat_library_stale`（warning，提示重跑引擎；重算对账按输入表记录的版本语义执行，不直接 error）。
- `style_profile`：风格档案名（无则 `null`）；三层生效区间优先级为「本集 `beat_duration_overrides` > 风格档案 > 库默认」。
- `beat_duration_overrides`：本集自己的校准声明，如「本集 12 分钟有余韵空间，悬念揭示用 [4.0, 8.0] 而非库默认区间」；键必须是 `beat_types.json` 的合法 beat_type。
- `rhythm_card`：每场开写前的分场节奏卡四行——`waveform`（情绪波形）、`main_accent`（主重拍镜）、`fastest_beat` / `slowest_beat`（最快拍/最长拍镜号）。先定调再填镜头；`fastest_beat`/`slowest_beat` 会被 lint 与引擎 `stats` 实际极值对账。
- `boundary_candidates`：剧情自然断点（可做 SEG 边界的镜号或位置描述），供 `pack` 装箱选用；禁止先切均长段再填内容。
- 逐镜字段：`beat_type`（以 `scripts/beat_types.json` 的 `beat_types` keys 为准）；`intensity`（1-5 强度分，引擎按它在生效区间内插值）；`spoken_text`（该镜台词原文，无则空串）；`speech_pace`（`normal|rapid` 两档，决定台词下限的语速常数，`speech.*` 参数以《节拍类型库》§5 为准）；`action_units` / `reaction_units` / `merge_with_next`（镜数校验式的三个原料：实列镜数 = Σ动作单元 + Σ反应单元 − Σ合并）；`is_payoff` / `is_final`（触发角色下限 `role_floors.payoff_s` / `role_floors.final_s`）；`info_injection`（单镜信息注入标记，触发 `shot_bounds.info_injection_threshold_s` 检查）；`role_note`（人读备注，不参与计算）。
- 段时长上限不在本文件登记：模型单次调用上限只读 `tools/video/h3.json` 能力档案（单一来源）。

**分工铁律**：本文件是唯一由 LLM 手写的节奏文件；storyboard JSON 的算术字段（`duration_s`、`duration_basis`、镜数、SEG 划分、`rhythm_extremes`、`engine_output_hash`、KF 区间）只能由引擎写入，lint 拿本文件重算对账，不一致即 `engine_drift`（error）。改语义必须重跑引擎。

lint 对本文件的四个检查码：

| 码 | 级别 | 触发 |
|---|---|---|
| `rhythm_input_missing` | error | 完整模式 storyboard 含算术字段但缺本文件 |
| `rhythm_input_incomplete` | error | 输入字段不全（缺 beat_type/intensity 等），引擎无法重算 |
| `engine_drift` | error | lint 调引擎按本文件重算，与 storyboard 算术字段逐项比对不一致 |
| `beat_library_stale` | warning | 本文件记录的 `beat_library_version` 与当前库不一致，提示重跑引擎 |

### asset_usage_ep_N.json

保存本集资产快照和本集状态资产：

```json
{
  "schema_version": "1.0",
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "shared_assets": [
    {
      "asset_id": "CHR001",
      "entity_scope": "individual",
      "version": "v01",
      "registry_path": "shared/03_资产/asset_registry.json",
      "used_by_shots": []
    }
  ],
  "episode_assets": [
    {
      "asset_id": "CHR001",
      "entity_scope": "individual",
      "state_id": "STATE002",
      "version": "v02",
      "files": ["episodes/ep_1/03_资产/角色状态/角色_CHR001_林远_战损_v02_ep_1.png"],
      "effective_shots": [],
      "status": "draft|reviewed|approved|rejected|superseded"
    }
  ]
}
```

### keyframe_manifest_ep_N.json

保存分镜确认后生成的剧情关键帧职责、文件与验收状态：

```json
{
  "schema_version": "1.0",
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "script_contract": "episodes/ep_1/01_剧本/script_contract_ep_1.json",
  "storyboard_manifest": "episodes/ep_1/02_分镜/storyboard_ep_1.json",
  "project_data_card": "00_制作控制/project_data_card.json",
  "keyframes": [
    {
      "keyframe_id": "KF001",
      "segment_id": "SEG001",
      "shot_id": "E01S01-SHOT001",
      "role": "highlight",
      "highlight_index": 1,
      "data_card_revision": 1,
      "asset_refs": ["CHR001_v01", "SCN001_v01", "PROP001_v01"],
      "state_refs": ["CHR001:STATE001"],
      "information_triggers": ["space_anchor"],
      "narrative_state": "",
      "character_state": {},
      "prop_state": {},
      "scene_and_light": {},
      "camera_and_composition": {},
      "continuity_from": "",
      "prompt_path": "episodes/ep_1/03_资产/提示词/提示词_KF001_SEG001_highlight-1_v01_ep_1.md",
      "prompt_sha256": "",
      "file": "episodes/ep_1/03_资产/关键帧/关键帧_KF001_SEG001_highlight-1_v01_ep_1.png",
      "tool": "image_edit",
      "model": "",
      "version": "v01",
      "status": "draft|reviewed|approved|rejected|superseded",
      "used_by_segments": ["SEG001"]
    }
  ]
}
```

- `storyboard_manifest` 必须引用当前已确认分镜；`segment_id`、`shot_id` 和 `used_by_segments` 必须与分镜中的真实片段和镜头一致。
- `role` 固定为 `highlight`，`highlight_index` 是同一 SEG 内从 `1` 开始的高光序号。关键帧只锁定剧情峰值，不承担生成式首帧或尾帧职责。
- 同一视频片段采用的高光关键帧必须与 `storyboard_ep_N.json` 的高光需求一致；片段首尾连续性由真实 FRM、连续性账本和 `SEAMxxx` 负责。
- `tool/model/version/status` 记录 `keyframes.md` 的实际生成结果；视频输入关系记录 `video.md` 的实际调用结果。
- 视频生成后的 `FRMxxx` 抽帧不能回写覆盖 `KFxxx`；偏差通过内部记录保存，只有用户主动要求修改并重新确认后才返修分镜、关键帧或视频。

### video_manifest_ep_N.json

作为本集视频生成结果的权威索引；`00_制作控制/批次/*.json` 继续保存单次请求快照：

```json
{
  "schema_version": "1.0",
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
      "model": "MiniMax H3",
      "aspect_ratio": "9:16",
      "duration_s": 12,
      "planned_video_count": 1,
      "segment_durations": [
        {"segment_id": "SEG001", "duration_s": 12}
      ],
      "displayed_parameter_table": {
        "task_type": "图片生成视频",
        "delivery_format": "MP4 视频片段",
        "quantity": 1,
        "segment_durations": ["SEG001：12秒"],
        "total_duration": "12秒",
        "aspect_ratio_and_resolution": "9:16，按当前模型实际分辨率",
        "model": "MiniMax H3",
        "visual_and_continuity": "按已确认角色、场景与上一段承接关系生成",
        "audio_and_subtitles": "保留本段完整对白，不生成画面字幕",
        "reference_materials": "当前角色、场景与高光关键帧",
      },
      "displayed_storyboard_rows": [
        {
          "segment_id": "SEG001",
          "duration_s": 12,
          "visual_content": "本段从起点到结果的可见剧情内容",
          "subject_action": "画面过程（含人物动作；人物动作不是观看重点时，说明环境/空间/物件/光影/焦点如何发展）",
          "audio": "声音类型与完整台词",
          "camera_and_materials": "摄影机与画面过程、阶段关系、承接方式及真实输入素材"
        }
      ],
      "creative_direction": "按已确认分镜生成本段剧情",
      "final_parameters_text": "| 参数 | 本批次确认值 |\\n|---|---|\\n| 任务类型 | 图片生成视频 |\\n| 交付格式 | MP4 视频片段 |\\n| 数量 | 1 |\\n| 分段时长 | SEG001：12秒 |\\n| 总时长 | 12秒 |\\n| 画幅与分辨率 | 9:16，按当前模型实际分辨率 |\\n| 视频模型 | MiniMax H3 |\\n| 视觉与连续性 | 按已确认角色、场景与上一段承接关系生成 |\\n| 声音与字幕 | 保留本段完整对白，不生成画面字幕 |\\n| 参考素材 | 当前角色、场景与高光关键帧 |\\n\\n| 片段与时长 | 画面内容 | 画面过程（含人物动作） | 声音与完整台词 | 摄影过程与素材 |\\n|---|---|---|---|---|\\n| SEG001｜12秒 | 本段从起点到结果的可见剧情内容 | 人物行动（如有）以及环境/空间/物件/光影/焦点发展 | 声音类型与完整台词 | 镜内摄影阶段、承接方式与真实输入素材 |",
      "interaction_ask_call_id": "实际确认调用 ID",
      "interaction_ask_result": "generate",
      "user_message": "用户通过确认工具选择生成的原文",
      "confirmed_at": "2026-09-08T12:00:00+08:00"
    }
  ],
  "segments": [
    {
      "segment_id": "SEG001",
      "episode_segment_index": 1,
      "shot_ids": ["E01S01-SHOT001"],
      "batch_id": "",
      "tool_mode": "image_to_video",
      "model": "MiniMax H3",
      "source_video_file": "",
      "edit_verification": null,
      "duration_s": 12,
      "observable_state_changes": ["门缝光带中掠过一道影子"],
      "compiled_prompt_file": "episodes/ep_1/04_视频片段/提示词_SEG001_v01_ep_1.md",
      "prompt_sha256": "",
      "h3_prompt_file": "episodes/ep_1/04_视频片段/提示词_SEG001_v01_ep_1.h3.md",
      "h3_prompt_sha256": "",
      "gen_file": "episodes/ep_1/04_视频片段/gen_SEG001_v01_ep_1.json",
      "h3_mode": "I2VA",
      "prompt_preflight": {
        "review_count": 1,
        "revision_count": 0,
        "final_validation_count": 1,
        "five_sections_in_order": true,
        "shot_ids_compiled_once": ["E01S01-SHOT001"],
        "result": "passed"
      },
      "reference_inputs": [
        {
          "order": 1,
          "source_type": "asset",
          "source_id": "CHR001_v01",
          "file": "shared/03_资产/角色/角色_CHR001_林远_基准状态_v01.png",
          "role": "identity_reference"
        }
      ],
      "required_reference_roles": ["identity_reference"],
      "audio_input_supported": false,
      "audio_inputs": [],
      "video_inputs": [],
      "voice_inputs": [],
      "native_audio_supported": true,
      "speech_mode": "native_required",
      "speech_lines": [
        {
          "speaker": "林远",
          "voice_id": "VOICE001",
          "voice_anchor": "28岁男性 声音低沉偏冷 平静克制 语速缓慢 字句间有停顿",
          "type": "on_screen_dialogue",
          "source_text": "你终于来了。",
          "display_text": "你终于来了。",
          "spoken_text": "你终于来了",
          "delivery_intent": "压低声音确认身份",
          "pause_plan": "",
          "emotion": "克制警觉",
          "emphasis_words": ["终于"]
        }
      ],
      "generation_confirmation_id": "VC001",
      "tool_call_id": "实际视频工具调用 ID",
      "tool_called_at": "2026-09-08T12:01:00+08:00",
      "output_file": "episodes/ep_1/04_视频片段/片段_SEG001_E01S01_v01_ep_1.mp4",
      "version": "v01",
      "status": "candidate|accepted|rejected|blocked",
      "quality_gate": {"status": "pending|pass|blocked|deviation_accepted", "blockers": [], "deviations": [], "user_acceptance_ref": ""},
      "qc_report": "",
      "incoming_episode_seam": null
    }
  ]
}
```

完整模式填写 `project_data_card_revision` 和 `storyboard_manifest`。轻量模式不创建这两个上游文件，因此在视频 manifest 中将对应字段留空；它改为通过请求快照记录 `episodes/ep_1/02_分镜/分镜_完整分镜表_ep_1.md` 和实际使用的 Prompt 路径，以维持生成追溯。

`segments[].status` 的状态语义固定为：

新建/修订的 `video_manifest` 使用 `schema_version: "1.1"`。`quality_gate` 是内容质量与结构接受的独立门：`pending` 仅可用于候选；`blocked` 表示关键剧情/证据/台词/身份/动作/接缝/导演意图不合格；`pass` 要求无阻断项；`deviation_accepted` 只允许非关键偏差，且必须关联用户明确接受记录。`segments[].status=accepted` 必须同时满足 `quality_gate.status=pass|deviation_accepted`；不得把文件可播放或 lint 通过当作内容合格证明。存量 `1.0` 按兼容规则读取，不强制补写历史质量门。

- `candidate`：片段已生成、保存、具备可渲染输出并完成即时交付，但尚未完成视频阶段用户确认；`drama_lint.py --stage video` 在发起确认前允许该状态。
- `accepted`：用户已明确接受该片段。目标继续到成片时，只能在 `proceed_assembly` 确认成功后，与视频阶段确认记录和 `assembly_confirmation` 原子写入；`objective.target_stage=video` 时，在普通视频阶段确认成功后写入。
- `rejected|blocked`：不得进入拼接或成片。`drama_lint.py --stage final|all` 要求本次采用的全部 SEG 均为 `accepted`。

`segments[].compiled_prompt_file` 是**五段导演交付包**，`segments[].h3_prompt_file` 是**提交给模型的 H3 成稿**（写法与字段结构以 `h3-prompt-writing` skill 为准，本仓不复述），`segments[].gen_file` 是该镜 `tools/video/h3.py` 的 gen.json；三者同一 `_vNN` 版本，`h3_mode` 记录该镜经判定的模式（逐镜判定，同批次内可不同）。已生成或候选状态必须同时登记交付包、成稿及其哈希与 gen.json 路径。

`segments[].prompt_preflight` 记录每份五段导演交付包唯一的一轮集中预检与最终客观校验。`review_count` 和 `final_validation_count` 固定为 `1`，`revision_count` 只能为 `0|1`；`five_sections_in_order` 必须为 `true`，`shot_ids_compiled_once` 必须按分镜顺序恰好列出当前 SEG 的全部镜头且不重复，`result` 必须为 `passed` 后才能调用视频生成工具。SHOT ID 只保存在该映射中，不要求出现在交付包或成稿的自然语言文本里。该结构只证明客观合同完成，不代替导演对节奏、表演和审美的判断。

`generation_confirmations[]` 每项对应一次真实批次确认，必须满足：

- `confirmation_id` 全局唯一，`attempt` 为从 `1` 递增的正整数。首次确认的 `supersedes_confirmation_ids` 为空；重生或返修覆盖既有 SEG 时，新增确认记录并在该数组中列出所有范围重叠的旧确认 ID，禁止删除历史确认。替代关系只对新旧确认范围的交集生效：例如旧确认覆盖 SEG001-SEG002、新确认只覆盖 SEG001，则旧确认对 SEG002 继续有效。替代确认时间必须晚于被替代确认，每个 SEG 的 `generation_confirmation_id` 必须指向覆盖该 SEG 的最新有效确认。
- `planned_video_count` 只能为 `1|2`，并等于确认范围内 SEG 数、`segment_durations` 项数、`displayed_parameter_table.quantity` 和 `displayed_storyboard_rows` 行数。
- `segment_durations` 按 `episode_segment_index` 排序，每项 `segment_id` 与 `duration_s` 必须和同一 `video_manifest` 中对应 SEG 完全一致；`duration_s` 是本批次总时长，必须等于各项之和。
- `displayed_parameter_table` 表示实际展示的一张两列表格，字段不得拆成逐 SEG 参数表；其中“数量”和“分段时长”必须按当前批次真实值渲染。
- `displayed_storyboard_rows` 表示实际展示的一张五列表格；机器结构将第一列拆为 `segment_id + duration_s`，其余四列依次为 `visual_content`、`subject_action`、`audio`、`camera_and_materials`。其中 `subject_action` 是兼容既有机器字段名的“画面过程（含人物动作）”，可以描述非人物主导的画面发展。每个 SEG 恰好一行，只能引用当前批次已确认分镜和真实素材。
- `final_parameters_text` 保存用户实际看到的完整普通文本，必须包含一张两列参数表和一张五列分镜表，不得包含第三张表；两张表之后才允许调用 AskUserQuestion。

轻量模式首次生成使用同一数组登记规划页的标准视频生成确认，并额外写 `confirmation_source: planning_preview`。范围固定为唯一视频；规划参数必须完整包含受保护确认 Ref 要求的任务类型、交付格式、数量、时长、比例与分辨率、视觉连续性、声音字幕、参考素材、模型限制与消耗。该记录的调用 ID、用户原文、时间和 `generate` 结果必须与 planning 确认一致。

纯文本视频（`h3` T2VA） 不得登记媒体输入；图生视频（`h3` I2VA） 只登记图片；多媒体视频（`h3` Ref2VA） 至少登记视频或音频，可同时登记图片；视频重生成（`h3`） 必须登记一个源视频，并写入 `edit_verification`：

```json
{
  "source_duration_s": 12,
  "output_duration_s": 12,
  "source_aspect_ratio": "9:16",
  "output_aspect_ratio": "9:16",
  "duration_preserved": true,
  "aspect_ratio_preserved": true
}
```

`ep_2` 及以后各集的首个 segment 将 `incoming_episode_seam` 写成 `episode_seams.json` 对应 `EPSEAMxxx` 的完整快照；`ep_1` 首段及非首段写 `null`。每个视频批次中的同名字段必须与该快照一致。

### continuity_ep_N.json

仅完整模式创建，用于保存本集抽帧和集内接缝；轻量模式不创建：

```json
{
  "schema_version": "1.0",
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "frames": [
    {
      "frame_id": "FRM001",
      "segment_id": "SEG001",
      "role": "start|scene|tail",
      "target_keyframe_id": "KF001",
      "timecode": "",
      "file": "",
      "observed_state": {},
      "keyframe_deviation": {
        "status": "accepted|rework",
        "differences": []
      }
    }
  ],
  "seams": [
    {
      "seam_id": "SEAM001",
      "from_segment": "SEG001",
      "to_segment": "SEG002",
      "outgoing_window_frames": 12,
      "incoming_window_frames": 12,
      "selected_cut": {},
      "comparison": {
        "character_position": "accepted|rework",
        "pose_and_action_phase": "accepted|rework",
        "camera_angle_and_axis": "accepted|rework",
        "scene_layout_and_light": "accepted|rework"
      },
      "status": "planned|verified|blocked"
    }
  ]
}
```

### delivery_manifest_ep_N.json

保存最终采用片段、音轨、字幕和交付文件：

```json
{
  "schema_version": "1.1",
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "duration_s": 120,
  "duration_display": "2分钟",
  "assembly_confirmation": {
    "confirmation_purpose": "final_assembly",
    "interaction_ask_call_id": "实际确认调用 ID",
    "interaction_ask_result": "proceed_assembly",
    "segment_ids": ["SEG001", "SEG002"],
    "user_message": "用户通过确认工具同意进入拼接的原文",
    "confirmed_at": "2026-09-08T12:30:00+08:00"
  },
  "subtitle_enabled": false,
  "clean_master": "episodes/ep_1/05_成片/[项目名]_成片_[比例]_无字幕_v01_ep_1.mp4",
  "subtitle_master": "",
    "subtitle_source": "",
  "subtitle_final": "",
  "subtitle_burn_params": "",
  "basic_qc_reports": [
    "episodes/ep_1/05_成片/质检_基础_无字幕_v01_ep_1.json"
  ],
  "subtitle_alignment_report": "",
  "outputs": [
    "episodes/ep_1/05_成片/[项目名]_成片_[比例]_无字幕_v01_ep_1.mp4"
  ],
  "status": "deliverable|candidate|blocked",
  "content_quality_gate": {"status": "pass|blocked|deviation_accepted", "blockers": [], "deviations": [], "user_acceptance_ref": ""}
}
```

新建/修订的 `delivery_manifest` 使用 `schema_version: "1.1"`。`deliverable` 必须通过整片顺读/观看质量门；关键因果、信息可见性、已确认台词、动作、身份、道具/空间连续性或关键接缝失败时为 `blocked`。非关键偏差须列明并引用用户接受记录后才能 `deviation_accepted`。存量 `1.0` 兼容读取。

轻量模式的 `project_data_card_revision` 留空，`assembly_confirmation` 使用空对象；完整模式按实际数据卡 revision 和拼接确认填写。

默认字幕关闭时，只保留无字幕母版对应的一项 `basic_qc_reports`，字幕相关路径留空，`outputs` 只能包含 `clean_master`。用户明确要求字幕时，无字幕母版作为内部烧录源保留，两种内部媒体各有一份基础可交付检查报告，并且必须存在字幕对齐报告；但 `outputs` 必须且只能包含 `subtitle_master`，不得把 `clean_master`、SRT、字幕 JSON 或检查报告作为额外交付物。

- 完整模式的 `assembly_confirmation` 保存进入本集成片拼接前的独立确认；`segment_ids` 必须按顺序精确等于本次采用的 accepted SEG，`interaction_ask_result` 固定为 `proceed_assembly`。轻量模式只有一个最终视频，不执行拼接，`assembly_confirmation` 留空。
- 最终交付校验时 `delivery_manifest_ep_N.json.status` 可以为 `deliverable|candidate`；`blocked` 不得交付。`candidate` 表示存在内部记录的内容风险，但只要客观可播放、可交付，就不得因最终内容质检缺失而扣住交付。该媒体状态不等于用户确认；用户确认仍记录在 `制作状态.json` 与 `用户确认记录.jsonl`。
- `basic_qc_reports` 由主 Agent 根据真实 `ffmpeg_tool probe` 探测终态与实际播放结果生成，分别绑定对应成片、输入文件哈希和媒体探测结果。
- `subtitle_alignment_report` 由主代理依据 `delivery.md` 的台词对齐规则生成，绑定当前分集 `script_contract` 的 `speech_lines` 和实际带音轨媒体的路径、字节数与 SHA-256。
- 基础媒体检查结果为 `blocked` 时不得交付；字幕关闭时不执行字幕对齐。字幕开启时，字幕对齐失败不使内部无字幕母版失效，但会阻断唯一交付物字幕版，修复前不得改交无字幕母版。需要人工判断的画面与表演问题直接查看成片，不要求额外填写固定 Markdown 报告。

## 状态、失效与一致性

- `制作状态.json` 独占规划与生产阶段状态。`phases.planning` 与 `phases.script` 分别表示项目规划和项目级故事包硬门；`episodes.ep_N.stage_status.script` 表示该集详细剧本。资产及后续项目状态是逐集聚合视图。
- `current_stage: script` 且 `current_episode` 为空时表示项目级故事包；`current_stage: script` 且 `current_episode=ep_N` 时表示该集详细剧本。当前集更早阶段必须为 `confirmed|merged`，更晚阶段只能为 `pending|invalidated`；更早集必须至少完成到 `objective.target_stage`，更晚集的详细剧本及后续阶段必须保持 `pending|invalidated`。当前集达到目标后，下一集总是从 `script` 开始。
- `episode_manifest_ep_N.json` 只保存身份、时长和文件指针，不再保存顶层 `status` 或 `stage_status`。旧项目中的同名镜像字段允许保留，但校验和推进只读取 `制作状态.json`。
- 每集状态遵循本集阶段拓扑，但不同集允许处于不同阶段：项目仍在规划或项目级故事包阶段时，各分集生产阶段只能为 `pending|invalidated`；进入逐集循环后，仅 `current_episode` 可以处于活动状态，且先活动于 `script`。较早集必须达到目标阶段，较晚集不得提前生成详细剧本或进入资产阶段。
- `project_manifest.json` 是路径索引，`drama_plan.json` 是规划权威，`project_script_manifest.json` 是项目级完整剧本索引，`project_data_card.json` 是跨阶段设定与状态权威，`asset_registry.json` 是共享媒体资产权威，各自不得复制对方的完整字段。
- `剧本_全剧完整剧本.md` 是项目故事权威；逐集剧本和人物关系张力矩阵是执行细化。修改项目级剧本中的核心因果、人物弧、结局或分集边界时，所有受影响 `script_contract_ep_N.json` 及下游阶段必须失效。
- 任一 Markdown 正文修改后更新对应 `source_sha256` 和 revision，并使依赖它的下游 manifest 状态变为 `invalidated`。
- 共享资产版本变化时，只更新 `asset_registry.json` 和受影响分集的 `asset_usage_ep_N.json`，不复制媒体文件。
- 规划阶段可以先登记未来阶段 manifest 的固定路径；进入对应阶段后，该阶段 JSON 中引用的路径必须存在。`episode_id`、文件后缀 `_ep_N`、所属目录 `episodes/ep_N/` 三者必须一致。
- 完整模式多集项目的 `episode_seams.json` 必须覆盖每对相邻集；完整模式单集作品使用 `ep_1` 且 `seams` 为空。轻量模式不创建该文件。

## 不进入 JSON 的内容

- 剧情梗概、人物小传、完整剧本文字。
- 面向用户的参数确认和按内容形态选择的五列剧情节奏预览。
- 人工审美评价、修改建议和完整看片记录。
- 策略库、风格库和方法说明。
- SRT、图片、音频和视频文件本体。

这些内容由对应 Markdown 或媒体文件承载；JSON 只保存路径、哈希、状态、结构化执行字段和引用关系。`script_contract_ep_N.json` 的场次合同字段与 `speech_lines` 属执行合同而非剧本正文副本，不在本清单限制内。
