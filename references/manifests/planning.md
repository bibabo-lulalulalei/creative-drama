# Manifest 分册 · 规划与项目入口 JSON

> 由 manifests.md 物理拆分：本分册只含具体 JSON schema；设计原则、统一目录、状态失效拓扑与「不进入 JSON 的内容」保留在 [../manifests.md](../manifests.md)。
> 需要哪个 schema 读对应小节（read_reference 可按阶段/条件路由到本节），不整篇通读本分册。

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

