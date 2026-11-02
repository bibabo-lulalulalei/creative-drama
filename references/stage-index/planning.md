# Reference 路由 · planning

> 由 `scripts/build_reference_index.py` 从 `references/reference_map.json` 生成；修改索引后重新生成。

查询：`python scripts/read_reference.py --stage planning --mode full`。

正式制作当前阶段前，下列章节是必读依据；局部审阅或修订按当前问题补齐最早受影响阶段的原始方法和必要依赖。同一任务中已读且未变的章节可复用，只补新增或变化的依赖。不要预读无关阶段。路由用于定位，原始教学与合同必须实际加载。

按标题提取会返回完整章节子树及起止行；理解任务需要时可读取完整目标文件与依赖，不设置读取行数、字节或结果数量上限。

## 动作合同（触发时必读）

`full` 文件在其对应动作触发时必须读取；按当前动作定位合同，不要求阶段开始时一次性加载所有文件。

- `references/interaction-ask-video-clarification-ref.md`

## 章节入口

- `references/planning.md`
  - `## 目标`
  - `## 边界`
  - `## 规划流程`
  - `## 交付物`
  - `## drama_plan.json`
  - `## 对话参数确认表：开始写剧本前的强制条件`
  - `## 规划检查`
  - `## 变更与失效`
  - `## 输入与 Reference 路由`
  - `## 创意机制选择算法`
  - `## 画风候选卡`
- `references/control-contracts.md`
  - `## 本 Ref 关键要求`
  - `## 引用与权威边界`
  - `## 2. 阶段状态与确认`
  - `## 4. 跨阶段交接`
  - `## 5. 运行完整性、证据与基础检查`
  - `## 失败、重试与回炉`
  - `## 6. 文件操作与恢复`
  - `## 7. 自动检查与交付`
  - `## 1. 来源与事实锁`
  - `## 非视频生成的阶段迁移确认`
- `references/skill-details.md`
  - `## 全局执行合同`
  - `## 阶段内容硬门`

## 条件入口

条件命中时必须补读对应章节；无法判断时核对当前任务与上游事实，不把条件当作可跳过必要方法的选项。

- `genre_research`：选择、深化或校准题材、受众、亮点、呈现类别或视觉风格时必读；用户已锁定方向时用于核验，不重选主路径。
  - 查询：`python scripts/read_reference.py --stage planning --mode full --condition genre_research`。
  - `references/剧作方法与类型库.md`：`### 使用合同`、`## 第二部分：类型剧作合同`
  - `references/题材亮点与传播库.md`：`## 本 Ref 关键要求`、`### 呈现类别使用合同`、`### 题材发动机使用合同`、`### 五、亮点策略合同`、`### 六、多样性与去同质化检查`
  - `references/题材受众库.md`：`## 本 Ref 关键要求`、`## 使用合同`
  - `references/电影大师风格库.md`：`## 本 Ref 关键要求`、`## 使用合同`、`## 七、AI 短剧风格实现候选`
  - `references/creative-index.md`：`## 规划与剧本的方法入口`、`## 题材发动机定位`
- `project_initialization`：规划已获用户确认，实际建立项目、来源、状态、分集及共享资产入口时必读；确认前不创建项目索引。
  - 查询：`python scripts/read_reference.py --stage planning --mode full --condition project_initialization`。
  - `references/manifests.md`：`### project_manifest.json`、`### source_manifest.json`、`### episode_manifest_ep_N.json`、`### 制作状态.json`、`### 用户确认记录.jsonl`、`### 操作日志.jsonl`、`### asset_registry.json`、`### episode_seams.json`
- `visible_delivery`：保存生成 Prompt、展示阶段产物或请求任何阶段确认前必须读取；阶段内及时展示不扩大确认授权。
  - 查询：`python scripts/read_reference.py --stage planning --mode full --condition visible_delivery`。
  - `references/skill-details.md`：`## Prompt 文件与可见交付`
- `state_update`：修改状态、revision 或正式文件，运行阶段检查、回退或压缩恢复前必须读取。
  - 查询：`python scripts/read_reference.py --stage planning --mode full --condition state_update`。
  - `references/skill-details.md`：`## 状态、文件与自动校验`
