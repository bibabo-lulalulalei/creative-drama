# Manifest 分册 · 成片交付

> 由 manifests.md 物理拆分：本分册只含具体 JSON schema；设计原则、统一目录、状态失效拓扑与「不进入 JSON 的内容」保留在 [../manifests.md](../manifests.md)。
> 需要哪个 schema 读对应小节（read_reference 可按阶段/条件路由到本节），不整篇通读本分册。

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

