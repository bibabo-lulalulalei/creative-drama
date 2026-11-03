# Manifest 分册 · 分镜与节奏输入

> 由 manifests.md 物理拆分：本分册只含具体 JSON schema；设计原则、统一目录、状态失效拓扑与「不进入 JSON 的内容」保留在 [../manifests.md](../manifests.md)。
> 需要哪个 schema 读对应小节（read_reference 可按阶段/条件路由到本节），不整篇通读本分册。

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
  "causal_ledger": [
    { "chain_id": "CL001", "trigger_fact": "…", "trigger_source": { "ref_type": "beat", "ref_id": "B026" }, "evidence_shot_ids": ["…"], "reaction_shot_ids": ["…"], "result_shot_ids": ["…"], "cross_episode_refs": [], "visibility_contract": "一句话锁定证据在哪些镜头、以什么程度必须可见/可听（如：肿唇在反应镜必须部分可见，手部全遮即断链）", "breakpoint_risk": "C2", "highlight_binding_ref": null }
  ],
  "shots": [
    { "shot_id": "E01S01-SHOT001", "segment_id": "SEG001", "scene_id": "E01S01", "duration_s": 5.5, "time_range_s": [0, 5.5], "timing_events": [], "duration_basis": { "end_event_ids": ["V001"], "duration_s": 5.5 }, "beat_type": "suspense_reveal", "intensity": 3, "spoken_text": "", "camera_family": "axial", "cut_motivation": "eyeline", "causal_role": "establish", "responds_to": null, "establishes": "…（无则 null）", "evidence_visibility": "in_frame" }
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

分镜索引自动检查正文引用、镜头编号、片段对镜头的完整覆盖、相邻片段引用、主要亮点绑定和受众执行落点。`shot_mode` 只能为 `edited|true_one_take`；`true_one_take` 必须且只能引用一个 SHOT，并在导演总控卡说明、顺观看顺序审校没有硬切、隐藏切、遮挡伪切、匹配剪辑或时间跳跃，`one_take_route` 记录连续摄影机路线，以及由观看对象、空间、主体关系、光影/焦点或可见信息形成的实际可读节点（不设数量）。`density_profile` 为可选定性标注，用于区分高密度平台短片、对白/情感、悬疑蓄力、微电影/生活流和自定义节奏；`density_rationale` 可按需记录主导内容负载和排除理由；复杂动作可在正文说明跨镜承接，不另设动作计数表或逐镜自证字段。镜头数量不按精确 15 秒触发硬配额；`opening_event_chain` 仅在规划目标明确采用黄金三秒机制时记录异常/承诺、主体行动/目标和反馈/观看关系变化。`tail_mode` 必须按片段职责选择，`tail_selection_reason` 记录选择依据；中间 SEG 默认 `continuous_motion|cuttable_completion`，使用 `stable_hold` 时填写 `tail_hold_reason`，最终 SEG 默认 `stable_hold`，Loop 使用 `loop_continuation`。`highlight_bindings[].causal_chain` 按触发、变化、反馈、结果记录可观察事实和镜头；变化/兑现映射到 `payoff_shot_ids`，反馈映射到 `reaction_shot_ids`，结果映射到本集 `aftereffect_shot_ids` 或跨集引用。`highlight_bindings` 必须覆盖 `script_contract.highlight_ledger` 中全部 `role=primary` 项；`segment_id` 是亮点兑现所在 SEG，`payoff_shot_ids` 必须属于该 SEG，`reaction_shot_ids` 可落在本集后续 SEG且不得早于兑现镜头。余震在本集发生时填写真实 `aftereffect_shot_ids`，这些镜头不得早于兑现/反应镜头；计划在后续集回收时留空该数组，并把 `deferred_aftereffect_ref` 写成 `{"episode_id":"ep_2","highlight_id":"HL001","binding_id":"HL001-aftereffect"}`。目标集对应绑定必须用相同 `binding_id` 写入 `inherited_aftereffect_bindings[]`，每项结构为 `{"binding_id":"","source_episode_id":"ep_1","source_highlight_id":"HL001","shot_ids":[]}`，形成反向承接。每项还必须填写视觉、表演、声音和视频编译说明。`audience_execution.source_plan_revision` 必须等于当前已确认 `drama_plan.revision`；四项执行合同必须各自填写固定 `source_field` 并逐字继承当前 `audience_plan` 对应值，再绑定到真实场次或镜头，不得在分镜阶段重新画像或更换受众。上述推导字段由主 Agent 按 `storyboard.md` 人工复核；lint 不对其创意质量打分。

`shots[]` 的 `duration_s/time_range_s/timing_events/duration_basis` 来自同一时间内核；`duration_basis` 是结束过程 ID 的结构化追溯，不是字数或节拍发票。`camera_family` 仅为检索标注；真实摄影起点、路径、终点及观看顺序在十五列正文/导演设计中，不按静态比例或路线节点数验收。因果台账、资产状态、受众继承、已确认亮点引用仍按真实源合同核验，不以数量作创意证明。

`beat_coverage` 每个源 event_id 一条处置，`beat_id` 对应源事件；`kept|compressed|moved` 的 `target_shots` 可多镜且必须是真实存在的镜头，镜头时间项须回指 `beat:<ID>`；`dropped` 需当前源版本的真实删戏 confirmation_ref，reason 不能解除覆盖。人声由 line_id → utterance → speech 分片完整承接。

`reference_input_plan` 是每段必填数组（该段无图参考时写 `[]`）：每项含从 1 连续的 `order`、合法 `role`、`planned_source`（形如 `CHR001_v01（名称）`）、`opening_binding`（必须含同序 `<图片N>`/`<IMGN>` 标记）、`adopt` 与 `exclude`。顶层 `asset_usage_plan` 登记资产→片段绑定（`segments` 非空，`["*"]` 表示全部片段），与各段输入计划双向对账：台账绑定但该段未计划传入为 error，计划传入但台账漏登记为 warning。顶层 `inherited_world_facts` 必填，每条含 `fact_id`、`category`（season/festival/date/time_of_day/weather/location_fact/other）、`statement` 和剧本出处 `source`。

`content_review` 是独立观看顺序审校的精简索引：`reviewed_inputs` 由 `full_review_inputs` 计算，绑定源脚本 SHA/revision、分镜设计投影和时间输入文件 SHA；`open_issues` 保存未解决内容问题。不能仅填空数组宣称摄影可达/时间真实/审美成立。设计投影仅排除顶层 review、preflight、confirmations、generation_confirmations、task_id、status、quality_gate、quality_review、output_file、generated_at、validated_at；不递归删除同名语义字段。时间、顺序、正文、摄影路线、道具证据等设计改变后需重新核算/审校，运行事实追加不循环污染设计。

SEG ID 对未变镜头组保持稳定；组内容/摄影/时间变化不继承旧参考、KF、预检和确认。

### rhythm_input_ep_N.json

时间语义输入；先完成事件、观看方式、连续画面与摄影路线，再估计具体过程。核算只保留声明的开始/持续/先后关系，不寻找最短排程。示例仅展示格式，数值不构成动作秒数表。

```json
{
  "episode_id": "ep_1",
  "source_script": { "file": "episodes/ep_1/01_剧本/script_contract_ep_1.json", "revision": 1, "sha256": "当前源文件字节 SHA" },
  "utterances": [],
  "scenes": [ { "scene_id": "E01S01", "shots": [ { "shot_id": "E01S01-SHOT001", "timeline": [ { "event_id": "V001", "kind": "visual", "process": "本次具体可见过程", "source_refs": ["beat:B001"], "start_s": 0, "duration_s": 5.3, "after": [] } ] } ], "beat_groups": [ { "group_id": "G001", "shot_ids": ["E01S01-SHOT001"], "tail_handle": { "mode": "continue_existing_process", "source_event_id": "V001", "description": "末镜既有过程继续，不加戏或拉伸前段" } } ] } ]
}
```

时间最多三位小数，内部整数毫秒；start 非负、duration 正数且有限，拒绝 bool/字符串/NaN/Inf，不舍入。ID 唯一，after 引用已声明 event_id；依赖环、先后冲突、未知引用均阻断，程序不改排程。每镜取过程最大结束时间，按正式镜头顺序累加场次/集；并行按声明区间而非简单相加。

非 speech 的 kind 为 `visual|camera|hold`，需具体 `process`；`source_refs` 解析 `beat:|line:|chain:|asset_state:`，不能引用不存在的事实。speech 只写 `utterance_id/utterance_offset_s/start_s/duration_s/after`，不重复维护台词文本。utterance 结构：`{utterance_id, line_id, speaker_ref, estimated_duration_s, timing_basis}`；依据为 `director_estimate` + 本次演读 note，或 `existing_measurement` + file/sha256/range_s/evidence（本句真实测量，不是音色样音）。同一发声分片完整、无重叠遗漏，跨镜绝对时间连续。跨镜时各 compilation_map.speech_spans 明确 event_id/spoken_text，按 utterance_offset 顺序逐字拼回一次完整源台词，不逐镜重抄整句。跨 SEG 另需 video.speech_bridge 含 implementation、review_ref 及 utterance_spans（每项 utterance_id/event_id/spoken_text），各镜采用同一逐字分片。程序不从秒数猜词，也不证明实际接缝音效自然；无可靠实施应返回导演层。

未知字段报错；不接受 total/target/segment 预算、动作或反应计数、merge、风格时间覆盖。`beat_type/intensity/speech_pace/note` 仅可选注释，时间投影递归排除它们，不影响核算。真实摄影设计仍在阅读正文，不靠标签验收。

`beat_groups` 是明确剪辑边界，不是自动装箱。组按正式顺序完整覆盖所有镜头；内容时间不必整数。请求时间取满足真实 h3.json 能力的最小整数秒，尾差 `tail_handle_s` 仅延续末镜结束处的非 speech 过程；超能力或无合法尾设计就报错，不自动缩短/分镜/换模型。

`allocate --write` 只写派生字段及 episode.planned_content_duration_s，不覆盖规划估时；所有语义/文件/镜头检查在写入前完成。阅读稿时间列同源渲染，缺镜/额外镜/顺序不符不部分写回。`pack --write` 保持稳定身份并按真实设计失效。KF 数来自实际 `keyframe_requests`，不由时长推导。

