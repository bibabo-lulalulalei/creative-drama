# Manifest 分册 · 视频生成与连续性

> 由 manifests.md 物理拆分：本分册只含具体 JSON schema；设计原则、统一目录、状态失效拓扑与「不进入 JSON 的内容」保留在 [../manifests.md](../manifests.md)。
> 需要哪个 schema 读对应小节（read_reference 可按阶段/条件路由到本节），不整篇通读本分册。

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
      "reference_inputs": [ {"order": 1, "source_type": "asset", "source_id": "CHR001_v01", "file": "shared/03_资产/角色/角色_CHR001_林远_基准状态_v01.png", "role": "identity_reference"} ],
      "required_reference_roles": ["identity_reference"],
      "audio_input_supported": false, "audio_inputs": [], "video_inputs": [], "voice_inputs": [],
      "native_audio_supported": true, "speech_mode": "native_required",
      "speech_lines": [ {"speaker": "", "voice_id": "VOICE001", "voice_anchor": "", "type": "on_screen_dialogue", "source_text": "", "display_text": "", "spoken_text": "", "delivery_intent": "", "pause_plan": "", "emotion": "", "emphasis_words": []} ],
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
| `segments[].h3_mode` | `T2VA`（纯文本）/ `I2VA`（图生视频）/ `Ref2VA`（多媒体）；逐 SEG 记录 `h3-prompt-writing` 实际返回模式，同批次内可不同 |
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

`reference_inputs` / `video_inputs` / `audio_inputs` 只登记实际提交媒体，mode 与参考用法采用 `h3-prompt-writing` 的实际返回值，不通过媒体种类反推。视频重生成的制作目标必须有一个真实待修改源视频，登记在 `video_inputs` 中（含资源编号和文件路径）；重生片段沿用同一 SEG 的已确认时长与画幅参数，由冻结快照对账，不另设保持性登记对象。

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

