# Reference 路由 · script

> 由 `scripts/build_reference_index.py` 从 `references/reference_map.json` 生成；修改索引后重新生成。

查询：`python scripts/read_reference.py --stage script --mode full`。

章节入口为阶段开始必读；动作合同在对应动作触发时整读；条件入口命中时必须补读。已读未变章节可复用，不预读无关阶段。读取总协议见 `SKILL.md`。

## 章节入口

- `references/scriptwriter.md`
  - `## 输入门禁`
  - `## 边界`
  - `## AI 生成可拍性合同`
  - `## 双层剧本结构`
  - `## 目标`
  - `## 规划继承与澄清`
  - `## 单集创作卡`
  - `## 视觉叙事、母题与声音意图`
  - `## 画幅与竖屏写作意图`
  - `## 类型变体与差异化生成`
  - `## 单集章节结构`
  - `## 输出要求`
  - `## 写作原则与策略路由`
  - `## 题材与受众策略`
- `references/planning.md`
  - `## drama_plan.json`
  - `## 变更与失效`
- `references/control-contracts.md`
  - `## 本 Ref 关键要求`
  - `## 引用与权威边界`
  - `## 2. 阶段状态与确认`
  - `## 4. 跨阶段交接`
  - `## 5. 运行完整性、证据与基础检查`
- `references/skill-details.md`
  - `## 全局执行合同`
  - `### script`

## 条件入口

条件命中时必须补读对应章节；无法判断时核对当前任务与上游事实，不把条件当作可跳过必要方法的选项。

- `artifact_write`：实际撰写或落盘阶段正式产物前必读（剧本成稿、script_contract 与项目级剧本清单等）：按格式规范和合同字段写全后再跑检查。
  - 查询：`python scripts/read_reference.py --stage script --mode full --condition artifact_write`。
  - `references/scriptwriter.md`：`## 专业剧本格式规范`、`## 正式输出约束`
  - `references/manifests.md`：`### script_contract_ep_N.json`、`### 制作状态.json`、`### project_script_manifest.json`、`### project_data_card.json`
- `pre_confirm_review`：剧本完成、自审或请求用户确认前必读：按节内清单逐项人工复核；自动检查通过不代表内容合格。
  - 查询：`python scripts/read_reference.py --stage script --mode full --condition pre_confirm_review`。
  - `references/scriptwriter.md`：`## 剧本内容质量人工评估`
- `genre_research`：选择、深化或校准题材、受众、亮点、呈现类别或视觉风格时必读；用户已锁定方向时用于核验，不重选主路径。
  - 查询：`python scripts/read_reference.py --stage script --mode full --condition genre_research`。
  - `references/剧作方法与类型库.md`：`### 使用合同`、`### 九、分轮改稿`、`## 第二部分：类型剧作合同`
  - `references/题材亮点与传播库.md`：`## 本 Ref 关键要求`、`### 呈现类别使用合同`、`### 题材发动机使用合同`、`### 五、亮点策略合同`、`### 六、多样性与去同质化检查`
  - `references/题材受众库.md`：`## 本 Ref 关键要求`、`## 使用合同`
  - `references/电影大师风格库.md`：`## 本 Ref 关键要求`、`## 使用合同`、`## 七、AI 短剧风格实现候选`
  - `references/creative-index.md`：`## 规划与剧本的方法入口`、`## 题材发动机定位`
- `visible_delivery`：保存生成 Prompt、展示阶段产物或请求任何阶段确认前必须读取；阶段内及时展示不扩大确认授权。
  - 查询：`python scripts/read_reference.py --stage script --mode full --condition visible_delivery`。
  - `references/skill-details.md`：`## Prompt 文件与可见交付`
- `state_update`：修改状态、revision 或正式文件，运行阶段检查、回退或压缩恢复前必须读取。
  - 查询：`python scripts/read_reference.py --stage script --mode full --condition state_update`。
  - `references/skill-details.md`：`## 状态、文件与自动校验`
  - `references/control-contracts.md`：`## 失败、重试与回炉`、`## 6. 文件操作与恢复`、`## 7. 自动检查与交付`
