# Reference 路由 · storyboard

> 由 `scripts/build_reference_index.py` 从 `references/reference_map.json` 生成；修改索引后重新生成。

查询：`python scripts/read_reference.py --stage storyboard --mode full`。

章节入口为阶段开始必读；动作合同在对应动作触发时整读；条件入口命中时必须补读。已读未变章节可复用，不预读无关阶段。读取总协议见 `SKILL.md`。

## 章节入口

- `references/scriptwriter.md`
  - `## 输入门禁`
  - `## 视觉叙事、母题与声音意图`
  - `## 画幅与竖屏写作意图`
  - `## 交接`
- `references/assets.md`
  - `## 目标与输入条件`
  - `## 角色身份与状态追踪`
  - `## 当前工具链中的资产使用`
  - `## 阶段交接`
- `references/storyboard.md`
  - `## 目标`
  - `## 输入条件`
  - `## 分镜产物分层`
  - `## 工作顺序`
  - `## 节奏类型与镜头数量推导算法`
  - `## 节奏设计`
  - `## 每集导演总控卡`
  - `## 导演总控卡字段合同`
  - `## 场次、片段与镜头`
  - `## 片段与时长`
  - `## 高密度剧情与运镜`
  - `## 动态镜头数量`
  - `## 动作桥与观看关系`
  - `## 单镜因果检查`
  - `## 运镜与镜头差异化`
  - `## 对白时长预算`
  - `## 导演总控卡的逐段执行区`
  - `## 开场、转场与角色表演控制`
  - `## 连续性账本与片段衔接卡`
  - `### 镜头到资产与连续性依据映射`
  - `## 参考资料与参考视频`
  - `## 与关键帧和视频阶段的边界`
- `references/control-contracts.md`
  - `## 本 Ref 关键要求`
  - `## 引用与权威边界`
  - `## 2. 阶段状态与确认`
  - `## 4. 跨阶段交接`
  - `## 5. 运行完整性、证据与基础检查`
- `references/skill-details.md`
  - `## 全局执行合同`
  - `### storyboard`

## 条件入口

条件命中时必须补读对应章节；无法判断时核对当前任务与上游事实，不把条件当作可跳过必要方法的选项。

- `artifact_write`：实际撰写或落盘十五列分镜表、片段执行表、资产需求清单或 storyboard/rhythm_input 清单前必读：按合同字段与列结构写全后再跑检查。
  - 查询：`python scripts/read_reference.py --stage storyboard --mode full --condition artifact_write`。
  - `references/storyboard.md`：`## 完整分镜表`、`## 视频片段执行表`、`## 分类资产需求清单`
  - `references/manifests.md`：`### storyboard_ep_N.json`、`### rhythm_input_ep_N.json`
- `pre_confirm_review`：分镜落盘前、五项剧本-分镜对照审校或请求用户确认前必读：执行落盘前检查与阶段确认流程。
  - 查询：`python scripts/read_reference.py --stage storyboard --mode full --condition pre_confirm_review`。
  - `references/storyboard.md`：`## 存储与阶段确认`
- `collective_cast`：当前阶段涉及需稳定复现的群众、人群或群体角色时必读。
  - 查询：`python scripts/read_reference.py --stage storyboard --mode full --condition collective_cast`。
  - `references/assets.md`：`## 群像/人群类角色资产`
- `beat_vocabulary`：需要解释或校准可选 beat_type 词汇、风格节奏档案时读取；不以标签替代导演判断。
  - 查询：`python scripts/read_reference.py --stage storyboard --mode full --condition beat_vocabulary`。
  - `references/节拍类型库.md`：`## §1 使用规则`、`## §2 beat_type 总表`、`## §3 风格节奏档案`
- `visible_delivery`：保存生成 Prompt、渲染分镜阅读稿/摘要、展示阶段产物或请求任何阶段确认前必须读取；阶段内及时展示不扩大确认授权。
  - 查询：`python scripts/read_reference.py --stage storyboard --mode full --condition visible_delivery`。
  - `references/skill-details.md`：`## Prompt 文件与可见交付`
  - `references/storyboard.md`：`## 用户可见分镜阅读稿`
- `state_update`：修改状态、revision 或正式文件，运行阶段检查、回退或压缩恢复前必须读取。
  - 查询：`python scripts/read_reference.py --stage storyboard --mode full --condition state_update`。
  - `references/skill-details.md`：`## 状态、文件与自动校验`
  - `references/control-contracts.md`：`## 失败、重试与回炉`、`## 6. 文件操作与恢复`、`## 7. 自动检查与交付`
- `asset_work`：实际盘点、复用、生成或修改资产、参考图、风格及关键帧前必须读取。
  - 查询：`python scripts/read_reference.py --stage storyboard --mode full --condition asset_work`。
  - `references/skill-details.md`：`## 资产、视觉参考与风格`
