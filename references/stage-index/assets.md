# Reference 路由 · assets

> 由 `scripts/build_reference_index.py` 从 `references/reference_map.json` 生成；修改索引后重新生成。

查询：`python scripts/read_reference.py --stage assets --mode full`。

章节入口为阶段开始必读；动作合同在对应动作触发时整读；条件入口命中时必须补读。已读未变章节可复用，不预读无关阶段。读取总协议见 `SKILL.md`。

## 章节入口

- `references/assets.md`
  - `## 目标与输入条件`
  - `## 生图工具路由`
  - `## 分类目录与命名`
  - `## 资产说明记录`
  - `## 场景参考与全局风格资产`
  - `## 角色资产`
  - `## 角色身份与状态追踪`
  - `## 道具资产`
  - `## 专属音色（qwen3tts_autodl）`
  - `## 图片 Prompt 与参考图引用`
  - `## 当前工具链中的资产使用`
  - `## 关键帧前置关系`
  - `## 资产 JSON 登记`
  - `## 资产版本管理`
  - `## 阶段交接`
- `references/control-contracts.md`
  - `## 本 Ref 关键要求`
  - `## 引用与权威边界`
  - `## 2. 阶段状态与确认`
  - `## 4. 跨阶段交接`
  - `## 5. 运行完整性、证据与基础检查`
- `references/skill-details.md`
  - `## 全局执行合同`
  - `### assets`

## 条件入口

条件命中时必须补读对应章节；无法判断时核对当前任务与上游事实，不把条件当作可跳过必要方法的选项。

- `artifact_write`：实际登记或落盘 asset_registry/asset_usage 等正式产物前必读：按合同字段写全后再跑检查。
  - 查询：`python scripts/read_reference.py --stage assets --mode full --condition artifact_write`。
  - `references/manifests.md`：`### asset_registry.json`、`### asset_usage_ep_N.json`
- `pre_confirm_review`：资产生成完成、人工验收或请求用户确认前必读：逐项核对身份与状态、可打开/可试听和复用判定。
  - 查询：`python scripts/read_reference.py --stage assets --mode full --condition pre_confirm_review`。
  - `references/assets.md`：`## 资产人工验收`
- `failure_recovery`：生图失败、工具异常，需要重试、换输入或降级前必读；失败编号与重试预算以 troubleshooting.md 为准。
  - 查询：`python scripts/read_reference.py --stage assets --mode full --condition failure_recovery`。
  - `references/assets.md`：`## 资产生成失败处理`
- `collective_cast`：当前阶段涉及需稳定复现的群众、人群或群体角色时必读。
  - 查询：`python scripts/read_reference.py --stage assets --mode full --condition collective_cast`。
  - `references/assets.md`：`## 群像/人群类角色资产`
- `style_gap`：资产制作缺少可执行风格依据或发现风格冲突时必读，不擅自更改已确认风格。
  - 查询：`python scripts/read_reference.py --stage assets --mode full --condition style_gap`。
  - `references/电影大师风格库.md`：`## 使用合同`、`## 一、风格选择逻辑`
- `visible_delivery`：保存生成 Prompt、展示阶段产物或请求任何阶段确认前必须读取；阶段内及时展示不扩大确认授权。
  - 查询：`python scripts/read_reference.py --stage assets --mode full --condition visible_delivery`。
  - `references/skill-details.md`：`## Prompt 文件与可见交付`
- `state_update`：修改状态、revision 或正式文件，运行阶段检查、回退或压缩恢复前必须读取。
  - 查询：`python scripts/read_reference.py --stage assets --mode full --condition state_update`。
  - `references/skill-details.md`：`## 状态、文件与自动校验`
  - `references/control-contracts.md`：`## 失败、重试与回炉`、`## 6. 文件操作与恢复`、`## 7. 自动检查与交付`
- `asset_work`：实际盘点、复用、生成或修改资产、参考图、风格及关键帧前必须读取。
  - 查询：`python scripts/read_reference.py --stage assets --mode full --condition asset_work`。
  - `references/skill-details.md`：`## 资产、视觉参考与风格`
- `media_execution`：实际执行媒体工具或准备委派包前必须读取；同时遵守原始运行时和委派合同。
  - 查询：`python scripts/read_reference.py --stage assets --mode full --condition media_execution`。
  - `references/skill-details.md`：`## 本地工具与执行边界`
