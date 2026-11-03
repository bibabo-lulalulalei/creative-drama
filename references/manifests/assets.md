# Manifest 分册 · 共享与分集资产

> 由 manifests.md 物理拆分：本分册只含具体 JSON schema；设计原则、统一目录、状态失效拓扑与「不进入 JSON 的内容」保留在 [../manifests.md](../manifests.md)。
> 需要哪个 schema 读对应小节（read_reference 可按阶段/条件路由到本节），不整篇通读本分册。

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

