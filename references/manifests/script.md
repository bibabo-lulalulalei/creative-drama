# Manifest 分册 · 剧本与项目数据卡

> 由 manifests.md 物理拆分：本分册只含具体 JSON schema；设计原则、统一目录、状态失效拓扑与「不进入 JSON 的内容」保留在 [../manifests.md](../manifests.md)。
> 需要哪个 schema 读对应小节（read_reference 可按阶段/条件路由到本节），不整篇通读本分册。

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
      "speech_lines": [ {"line_id": "LINE001", "speaker": "CHR001", "voice_id": "VOICE001", "type": "on_screen_dialogue|narration|voiceover|inner_monologue", "source_text": "", "spoken_text": "", "delivery_intent": "", "pause_plan": "", "emotion": "", "emphasis_words": []} ]
    }
  ]
}
```

各集 `script_contract` 重算 `source_markdown` 正文 SHA 并比对 `source_sha256`，另核 revision、唯一场次标题、事件摘录逐字命中与逐字台词来源。`events` 只索引实际发生的事件，不设数量；无台词时 `speech_lines` 为空。当前 script 确认记录保存 `source_snapshot: {file, revision, sha256}`、confirmation_id、真实用户原文；分镜消费该确认版本。`duration_s` 仅保留原规划预测，内容推导改变时不覆写已确认剧本。真实已确认亮点仍逐项承接，不要求新增 primary 名额。

