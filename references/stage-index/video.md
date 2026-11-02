# Reference 路由 · video

> 由 `scripts/build_reference_index.py` 从 `references/reference_map.json` 生成；修改索引后重新生成。

查询：`python scripts/read_reference.py --stage video --mode full`。

章节入口为阶段开始必读；动作合同在对应动作触发时整读；条件入口命中时必须补读。已读未变章节可复用，不预读无关阶段。读取总协议见 `SKILL.md`。

## 动作合同（触发时必读）

`full` 文件在其对应动作触发时必须读取；按当前动作定位合同，不要求阶段开始时一次性加载所有文件。

- `references/interaction-ask-video-clarification-ref.md`
- `references/video-batch-confirmation.md`
- `references/local-runtime.md`

## 章节入口

- `references/video.md`
  - `## 权威引用`
  - `## 当前工具链`
  - `## 执行顺序`
  - `## 批次合同`
  - `## 批次确认展示`
  - `## 模型、时长与画幅`
  - `## 入站连续性`
  - `## 图片输入合同`
  - `## 生成质量目标`
  - `## 片段内镜头与运镜执行`
  - `## 镜头密度与片段内切镜`
  - `## 导演交付包（五段式）`
  - `## H3 成稿（提交给模型的文本）`
  - `## 人声与文字合同`
  - `## 动态执行硬门`
  - `## 表演、声音与色彩编译硬门`
  - `## 可选叙事过渡`
  - `## 不同场景类型的交付包侧重点`
  - `## 视频重生成编辑合同`
- `references/assets.md`
  - `## 资产说明记录`
  - `## 当前工具链中的资产使用`
  - `## 关键帧前置关系`
- `references/skill-details.md`
  - `## 全局执行合同`
  - `### video`

## 条件入口

条件命中时必须补读对应章节；无法判断时核对当前任务与上游事实，不把条件当作可跳过必要方法的选项。

- `artifact_write`：预检写回、实际撰写 gen.json 或登记 video/continuity 等正式清单前必读：按最小样例与合同字段写全、绑定冻结后再确认执行。
  - 查询：`python scripts/read_reference.py --stage video --mode full --condition artifact_write`。
  - `references/video.md`：`## 单 SEG gen.json 最小样例`
  - `references/manifests.md`：`### video_manifest_ep_N.json`、`### continuity_ep_N.json`、`### gen_SEGxxx_vNN_ep_N.json`、`### rhythm_input_ep_N.json`
- `post_generation`：SEG 生成完成后必读：抽帧与 FRM/SEAM 记录、输入模态复核、candidate/交付登记；发起视频阶段或拼接确认前同样必读。
  - 查询：`python scripts/read_reference.py --stage video --mode full --condition post_generation`。
  - `references/video.md`：`## 输入模态复核`、`## 生成后交付记录`、`## 第二部分：生成后抽帧与连续性`
- `failure_recovery`：视频生成失败、工具异常，需要重试、换输入或降级前必读；失败编号、重试预算和返回层级以 troubleshooting.md 为准。
  - 查询：`python scripts/read_reference.py --stage video --mode full --condition failure_recovery`。
  - `references/video.md`：`## 视频生成失败处理`
- `collective_cast`：当前阶段涉及需稳定复现的群众、人群或群体角色时必读。
  - 查询：`python scripts/read_reference.py --stage video --mode full --condition collective_cast`。
  - `references/assets.md`：`## 群像/人群类角色资产`
- `visible_delivery`：保存生成 Prompt、展示阶段产物或请求任何阶段确认前必须读取；阶段内及时展示不扩大确认授权。
  - 查询：`python scripts/read_reference.py --stage video --mode full --condition visible_delivery`。
  - `references/skill-details.md`：`## Prompt 文件与可见交付`
- `state_update`：修改状态、revision 或正式文件，运行阶段检查、回退或压缩恢复前必须读取。
  - 查询：`python scripts/read_reference.py --stage video --mode full --condition state_update`。
  - `references/skill-details.md`：`## 状态、文件与自动校验`
- `asset_work`：实际盘点、复用、生成或修改资产、参考图、风格及关键帧前必须读取。
  - 查询：`python scripts/read_reference.py --stage video --mode full --condition asset_work`。
  - `references/skill-details.md`：`## 资产、视觉参考与风格`
- `video_work`：拟定视频方案、设计声音、编译导演包/H3、生成或编辑视频及处理成片媒体前必须读取。
  - 查询：`python scripts/read_reference.py --stage video --mode full --condition video_work`。
  - `references/skill-details.md`：`## 视频、声音与 Prompt`
- `media_execution`：实际执行媒体工具或准备委派包前必须读取；同时遵守原始运行时和委派合同。
  - 查询：`python scripts/read_reference.py --stage video --mode full --condition media_execution`。
  - `references/skill-details.md`：`## 本地工具与执行边界`
