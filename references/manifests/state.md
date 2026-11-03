# Manifest 分册 · 状态、确认与操作日志

> 由 manifests.md 物理拆分：本分册只含具体 JSON schema；设计原则、统一目录、状态失效拓扑与「不进入 JSON 的内容」保留在 [../manifests.md](../manifests.md)。
> 需要哪个 schema 读对应小节（read_reference 可按阶段/条件路由到本节），不整篇通读本分册。

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

