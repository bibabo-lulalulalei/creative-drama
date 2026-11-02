# Reference 路由 · delivery

> 由 `scripts/build_reference_index.py` 从 `references/reference_map.json` 生成；修改索引后重新生成。

查询：`python scripts/read_reference.py --stage delivery --mode full`。

正式制作当前阶段前，下列章节是必读依据；局部审阅或修订按当前问题补齐最早受影响阶段的原始方法和必要依赖。同一任务中已读且未变的章节可复用，只补新增或变化的依赖。不要预读无关阶段。路由用于定位，原始教学与合同必须实际加载。

按标题提取会返回完整章节子树及起止行；理解任务需要时可读取完整目标文件与依赖，不设置读取行数、字节或结果数量上限。

## 动作合同（触发时必读）

`full` 文件在其对应动作触发时必须读取；按当前动作定位合同，不要求阶段开始时一次性加载所有文件。

- `references/interaction-ask-video-clarification-ref.md`
- `references/local-runtime.md`

## 章节入口

- `references/delivery.md`
  - `## 第一部分：成片拼接、最终音轨与交付`
  - `## 第二部分：字幕生成与烧录`
- `references/manifests.md`
  - `### delivery_manifest_ep_N.json`
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

- `visible_delivery`：保存生成 Prompt、展示阶段产物或请求任何阶段确认前必须读取；阶段内及时展示不扩大确认授权。
  - 查询：`python scripts/read_reference.py --stage delivery --mode full --condition visible_delivery`。
  - `references/skill-details.md`：`## Prompt 文件与可见交付`
- `state_update`：修改状态、revision 或正式文件，运行阶段检查、回退或压缩恢复前必须读取。
  - 查询：`python scripts/read_reference.py --stage delivery --mode full --condition state_update`。
  - `references/skill-details.md`：`## 状态、文件与自动校验`
- `video_work`：拟定视频方案、设计声音、编译导演包/H3、生成或编辑视频及处理成片媒体前必须读取。
  - 查询：`python scripts/read_reference.py --stage delivery --mode full --condition video_work`。
  - `references/skill-details.md`：`## 视频、声音与 Prompt`
- `media_execution`：实际执行媒体工具或准备委派包前必须读取；同时遵守原始运行时和委派合同。
  - 查询：`python scripts/read_reference.py --stage delivery --mode full --condition media_execution`。
  - `references/skill-details.md`：`## 本地工具与执行边界`
