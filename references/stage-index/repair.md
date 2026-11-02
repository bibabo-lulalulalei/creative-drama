# Reference 路由 · repair

> 由 `scripts/build_reference_index.py` 从 `references/reference_map.json` 生成；修改索引后重新生成。

查询：`python scripts/read_reference.py --stage repair --mode repair`。

正式制作当前阶段前，下列章节是必读依据；局部审阅或修订按当前问题补齐最早受影响阶段的原始方法和必要依赖。同一任务中已读且未变的章节可复用，只补新增或变化的依赖。不要预读无关阶段。路由用于定位，原始教学与合同必须实际加载。

按标题提取会返回完整章节子树及起止行；理解任务需要时可读取完整目标文件与依赖，不设置读取行数、字节或结果数量上限。

返修先定位最早受影响阶段，命中对应 `affected_*` 后补齐该阶段原始创作方法和必要依赖，再修订与审校；修复摘要不能替代原始教学。

## 动作合同（触发时必读）

`full` 文件在其对应动作触发时必须读取；按当前动作定位合同，不要求阶段开始时一次性加载所有文件。

- `references/troubleshooting.md`

## 章节入口

- `references/control-contracts.md`
  - `## 本 Ref 关键要求`
  - `## 引用与权威边界`
  - `## 1. 来源与事实锁`
  - `## 2. 阶段状态与确认`
  - `## 非视频生成的阶段迁移确认`
  - `## 4. 跨阶段交接`
  - `## 5. 运行完整性、证据与基础检查`
  - `## 失败、重试与回炉`
  - `## 6. 文件操作与恢复`
  - `## 7. 自动检查与交付`
- `references/skill-details.md`
  - `## 全局执行合同`
  - `## 阶段内容硬门`

## 条件入口

条件命中时必须补读对应章节；无法判断时核对当前任务与上游事实，不把条件当作可跳过必要方法的选项。

- `affected_planning`：最早受影响阶段为 planning 时必读；并补齐该阶段原始方法及必要依赖。
  - 查询：`python scripts/read_reference.py --stage repair --mode repair --condition affected_planning`。
  - `references/planning.md`：`## 目标`、`## 规划流程`、`## 交付物`、`## drama_plan.json`、`## 规划检查`
  - `references/manifests.md`：`### project_manifest.json`、`### source_manifest.json`、`### episode_manifest_ep_N.json`、`### 制作状态.json`、`### 用户确认记录.jsonl`、`### 操作日志.jsonl`、`### asset_registry.json`、`### episode_seams.json`
- `affected_script`：最早受影响阶段为 script 时必读；并补齐该阶段原始方法及必要依赖。
  - 查询：`python scripts/read_reference.py --stage repair --mode repair --condition affected_script`。
  - `references/scriptwriter.md`：`## 输入门禁`、`## 视觉叙事、母题与声音意图`、`## 画幅与竖屏写作意图`、`## 类型变体与差异化生成`、`## 写作原则与策略路由`、`## 剧本内容质量人工评估`、`## 正式输出约束`
  - `references/manifests.md`：`### script_contract_ep_N.json`、`### project_script_manifest.json`、`### project_data_card.json`
- `affected_assets`：最早受影响阶段为 assets 时必读；并补齐该阶段原始方法及必要依赖。
  - 查询：`python scripts/read_reference.py --stage repair --mode repair --condition affected_assets`。
  - `references/assets.md`：`## 目标与输入条件`、`## 生图工具路由`、`## 角色资产`、`## 道具资产`、`## 专属音色（qwen3tts_autodl）`、`## 图片 Prompt 与参考图引用`、`## 资产 JSON 登记`、`## 资产版本管理`、`## 资产人工验收`、`## 资产生成失败处理`
  - `references/manifests.md`：`### asset_registry.json`、`### asset_usage_ep_N.json`
  - `references/skill-details.md`：`## 资产、视觉参考与风格`
- `affected_storyboard`：最早受影响阶段为 storyboard 时必读；并补齐该阶段原始方法及必要依赖。
  - 查询：`python scripts/read_reference.py --stage repair --mode repair --condition affected_storyboard`。
  - `references/storyboard.md`：`## 工作顺序`、`## 动作桥与观看关系`、`## 运镜与镜头差异化`、`## 对白时长预算`、`## 完整分镜表`、`## 片段与时长`、`## 连续性账本与片段衔接卡`、`### 分镜内容人工复核`
  - `references/manifests.md`：`### storyboard_ep_N.json`、`### rhythm_input_ep_N.json`
  - `references/skill-details.md`：`## 资产、视觉参考与风格`
- `affected_keyframes`：最早受影响阶段为 keyframes 时必读；并补齐该阶段原始方法及必要依赖。
  - 查询：`python scripts/read_reference.py --stage repair --mode repair --condition affected_keyframes`。
  - `references/keyframes.md`：`## 数量与职责`、`## 生成合同`、`## 登记与验收`
  - `references/manifests.md`：`### keyframe_manifest_ep_N.json`
  - `references/skill-details.md`：`## 资产、视觉参考与风格`
- `affected_video`：最早受影响阶段为 video 时必读；并补齐该阶段原始方法及必要依赖。
  - 查询：`python scripts/read_reference.py --stage repair --mode repair --condition affected_video`。
  - `references/video.md`：`## 执行顺序`、`## 批次合同`、`## 入站连续性`、`## 图片输入合同`、`## 导演交付包（五段式）`、`## H3 成稿（提交给模型的文本）`、`## 人声与文字合同`、`## 可选叙事过渡`、`## 不同场景类型的交付包侧重点`、`## 单 SEG gen.json 最小样例`、`## 输入模态复核`、`## 生成后交付记录`、`## 第二部分：生成后抽帧与连续性`
  - `references/manifests.md`：`### video_manifest_ep_N.json`、`### continuity_ep_N.json`、`### gen_SEGxxx_vNN_ep_N.json`、`### rhythm_input_ep_N.json`
  - `references/local-runtime.md`：`# 本地运行时合同（Claude Code 宿主）`
  - `references/skill-details.md`：`## 视频、声音与 Prompt`、`## 本地工具与执行边界`
- `affected_delivery`：最早受影响阶段为 delivery 时必读；并补齐该阶段原始方法及必要依赖。
  - 查询：`python scripts/read_reference.py --stage repair --mode repair --condition affected_delivery`。
  - `references/delivery.md`：`### 拼接与最终音轨`、`### 基础可交付检查`、`### 最终状态`、`## 第二部分：字幕生成与烧录`
  - `references/manifests.md`：`### delivery_manifest_ep_N.json`
  - `references/skill-details.md`：`## 视频、声音与 Prompt`、`## 本地工具与执行边界`
- `visible_delivery`：保存生成 Prompt、展示阶段产物或请求任何阶段确认前必须读取；阶段内及时展示不扩大确认授权。
  - 查询：`python scripts/read_reference.py --stage repair --mode repair --condition visible_delivery`。
  - `references/skill-details.md`：`## Prompt 文件与可见交付`
- `state_update`：修改状态、revision 或正式文件，运行阶段检查、回退或压缩恢复前必须读取。
  - 查询：`python scripts/read_reference.py --stage repair --mode repair --condition state_update`。
  - `references/skill-details.md`：`## 状态、文件与自动校验`
