# Skill 全面审查记录 · 2026-11-11

范围：只修改 `doubao-creative-drama` Skill，不操作制作项目，不做历史项目兼容，不发起付费生成或真实上传。起点提交：`bcfa34ab576eebee4840dc72dd06c55d2257aaf9`。

方法：逐文件完整阅读，交叉核对入口、路由、阶段 Reference、schema、命令与实际实现；发现问题后记录依据、修复与验证。创作质量用内容判断和独立场景演练核查，程序只检查客观合同。本文及分审记录用于本次维护，不加入生产 Reference 路由。

## 完整覆盖记录

起始受版本管理文件共 **52 个，1,228,135 bytes，全部完成审读**。下表列出全部文件及处理结论；“保留”表示检查后未发现本轮需改的具体问题。新增回归和审计材料另行核查，不计入起始52个文件。

| 文件 | 结论与依据 |
|---|---|
| `.env.example` | 保留空配置模板，不带实际凭证 |
| `.gitignore` | 补忽略真实 `tools/s3/s3.env` |
| `SKILL.md` | 统一适用范围、文字轻路径、确认与质量边界；保留逐句表演，拆镜服从整场观看 |
| `references/control-contracts.md` | 规则未变不重复装载治理包；区分源稿缺陷和已生成候选交付 |
| `references/skill-details.md` | 阶段速记、确认与可见交付和入口一致，移除重复流程 |
| `references/manifests.md` | 当前schema同步KF用途、合法空反应/余震、三种事件去向及工具派生字段 |
| `references/local-runtime.md` | 保留真实本地Claude Code宿主、调用方式和外部工具边界 |
| `references/delegation.md` | 保留按收益选择委派、主Agent负责确认与真实交付 |
| `references/recovery.md` | 压缩后按原任务/授权绑定恢复，不重编未变请求、不重复提交 |
| `references/troubleshooting.md` | 按具体失败定位处置，返修不重启全流程 |
| `references/planning.md` | 修自动重生和强制委派措辞，按具体创作问题研究 |
| `references/scriptwriter.md` | 清机械动作拆分、全员反馈和每句策略配额；逐句具体表演保留且不新建状态；正文不重复创作 |
| `references/creative-index.md` | 小索引定位后窄读原始方法，不默认灌入四库 |
| `references/题材受众库.md` | 清无依据星级、平台人口刻板推断与AI适配排名；画像依实际委托 |
| `references/题材亮点与传播库.md` | 类型方法按需选用，不强迫固定反转、金句、反应或兑现比例 |
| `references/剧作方法与类型库.md` | 场景和人物方法允许克制、复沓、拒答与未决，不把攻防套给所有场面 |
| `references/电影大师风格库.md` | 修作者归类与泛化，以具体风格机制取代署名套壳和固定运镜 |
| `references/节拍类型库.md` | 修3张节拍表列数，消除术语反推拆镜的用法 |
| `references/assets.md` | 入库查看变化图、复用未变版本；状态按可见变化补图；VOICE/真实输入与程序一致 |
| `references/keyframes.md` | 统一高光/状态/构图/风险用途，修静帧、比例和表演密度规则 |
| `references/storyboard.md` | 整场观看决定切点及运镜起停；逐句表演可同镜承接；不为字段强造反应镜 |
| `references/video.md` | H3沿用导演决定及逐句表演；实际调用一次编写成稿；准备工具派生元数据 |
| `references/delivery.md` | 冻结区间不被任意剪点覆盖；减少重复probe、lint及逐字幕抽帧；默认样式可被明确覆盖 |
| `references/video-batch-confirmation.md` | 实际当前批一次确认；已知源稿缺陷在生成前处理 |
| `references/interaction-ask-video-clarification-ref.md` | 确认范围、定点澄清和未变原任务恢复统一 |
| `references/reference_map.json` | 增writing路由；研究、返修按条件窄读；不装入维护报告 |
| `scripts/read_reference.py` | 保留完整标题子树、条件独立补读和去重；全部当前路由另做渲染检查 |
| `scripts/build_reference_index.py` | beat词库元数据来源与实际内联构建逻辑一致 |
| `scripts/beat_types.json` | 修已不存在的生成脚本来源说明，词汇保留 |
| `scripts/rhythm_engine.py` | Unicode台词键、SHA流式和分组索引复用；去旧布局/别名兼容及dropped捷径 |
| `scripts/drama_lint.py` | 修空清单/引用/版本/VOICE误判；发声块逐字次序和次数核对；不以反应配额评判创作 |
| `scripts/drama_rollback.py` | 保留按现有依赖失效，未新增历史项目迁移 |
| `scripts/stamp_review.py` | 保留真实审查来源与当前版本绑定 |
| `scripts/h3_contract.py` | 准备阶段流式指纹，不重复base64；实际POST才编码 |
| `scripts/prepare_video.py` | 不重复编码；只按镜头ID单元格摘录；资产索引与lint一致 |
| `scripts/video_confirmations.py` | 当前唯一确认来源和字节绑定保留，复用流式SHA |
| `scripts/stamp_confirmation.py` | 接受来自真实当前产物；生成授权不冒充接受，未完成本集不能提前确认拼接 |
| `tools/README.md` | 命令示例、拼接音轨和TTS语言/失败语义与实现一致 |
| `tools/image/img.py` | 拒绝非有限比例，标准尺寸档如实保留 |
| `tools/image/zhinao_image.py` | 保留真实参考图edits入口、配置路由与下载凭证边界 |
| `tools/image/zhinao_image.json` | 保留能力配置与部署/凭证分离 |
| `tools/s3/s3.env.example` | 保留空值与示例值模板 |
| `tools/s3/upload.py` | 配置优先级说明对齐实际行为，缺依赖时报清楚 |
| `tools/search/web_search.py` | 缺httpx时明确依赖提示，保留文本研究范围 |
| `tools/tts/qwen3tts_autodl.py` | 实际项目语言、当前prompt_id精确输出、任务隔离和失败非零退出 |
| `tools/video/ffmpeg_tool.py` | 单段/静音/混合音轨拼接、保留立体声、归零时间戳及有效JSON输出 |
| `tools/video/h3.json` | 保留实际模式/能力与配置分离 |
| `tools/video/h3.py` | 下载和跨源重定向不泄露API令牌；提交前重核绑定并仅编码一次 |
| `tests/test_h3_runner.py` | 完整审读并补编码次数、跨源凭证和并发独占回归 |
| `tests/test_prepare_video.py` | 完整审读并补精确镜头摘录和准备行为回归 |
| `tests/test_read_reference.py` | 保留完整子树、去重与条件路由回归 |
| `tests/test_video_confirmations.py` | 完整审读并补实际产物接受、失效授权和拼接边界回归 |

生产逐项证据见 [production-review-2026-11-11.md](production-review-2026-11-11.md)，含30组生产问题及lint前1500行的7项实证；执行层逐文件证据见 [execution-review-2026-11-11.md](execution-review-2026-11-11.md)。独立评估在未读其他审计结论的情况下完成，范围和限制见 [scenario-review-2026-11-11.md](scenario-review-2026-11-11.md)。创作8份文档完整审读结果已汇入上表与下列流水。

## 问题与处理流水

| ID | 原问题与影响 | 已完成处理 |
|---|---|---|
| A01 | 所有确认都用AskUserQuestion与普通阶段整句接受冲突 | 普通阶段用真实明确回复；关键选型、实际生成/拼接按各自合同，不重复询问 |
| A02 | 普通展示、确认、状态更新均重读完整治理包 | 已读未变复用；规则缺失/变化才补对应节 |
| A03 | 将生成后观察不阻断泛化到已知源稿缺陷 | 源稿实质断点先修；已生成候选真实交付，不能自动重生 |
| A04 | 强制委派并暗含自动返修重生 | 主Agent可直接执行，必要才最小委派；新生成仍依实际请求确认 |
| A05 | 研究默认加载整组矩阵，动作/反应拆镜及固定慢推污染上游 | 小索引后窄读；整场注意力、人物关系和情绪决定切点及摄影起停 |
| A06 | 纯文字剧本/评阅被要求建生产包、选模型、多轮确认 | 新增writing轻路径，按委托成果结束；生产合同仍适用实际媒体任务 |
| A07 | 删机械反应规则时可能连人物具体表演一并丢失 | 按用户最新要求保留原句“每句对白后接表情、反应或小动作”，贯穿剧本→分镜→H3画面描述 |
| A08 | 入口所有场面强制目标/代价/立即行动，与观察性创作冲突 | 行动故事厘清目标阻碍；生活流/观察场面从处境、相处及观看期待组织，不补危机或钩子 |
| A09 | 表情和视线被列入服装等状态变更，逐句可能新增state_id | 表情、视线、小动作为场面表演，不逐句注册角色状态 |
| A10 | KF一处允许状态/构图/风险，另一处只许剧情峰值 | 用途全文统一，保留机器highlight通道名及必要输入 |
| A11 | 无独立反应/余震镜头被判不完整，倒逼补镜和跨集回收 | 对应引用可空；源稿已有逐句表演仍须保留，可同镜完成 |
| A12 | 已确认事件可凭一般剧本确认登记dropped | 删除该路径；删戏先改源剧本版本并重新确认，再按新源建覆盖表 |
| A13 | substring台词检查漏过重复句漏说、倒序和新增台词 | Unicode NFC与字母数字/组合符键；实际发声块拼接与源串顺序、次数一致，允许跨镜拆块 |
| A14 | 空world facts逼补事实，空registry引用假通过，approved图片无files | 区分合法空列表与缺字段；引用必解析，approved媒体必有资源 |
| A15 | STATE版本污染基准CHR latest，合法分集VOICE缺category误判 | 基准/状态独立索引；按当前schema追溯真实批准来源与必传音色 |
| A16 | 准备、确认、恢复重复base64，大文件哈希整块入内存 | 流式SHA、指纹复用，实际首次POST才编码一次并重核绑定 |
| A17 | H3下载及跨源重定向可能带API令牌 | 结果下载无API令牌，跨源移除授权头，并有离线回归 |
| A18 | 生成授权冒充接受，重生沿用旧接受，未完成即确认拼接 | 接受绑定当前真实产物、版本与时间；全部完成后才可确认本集拼接 |
| A19 | ffmpeg不支持单段/无声段且可能丢右声道，JSON附文字 | 实际本地合成媒体验证静音补齐、混合音轨、立体声、时长和JSON |
| A20 | TTS硬编码Chinese、glob旧音频且失败看似成功 | 默认Auto或实际指定语言，仅取当前prompt_id输出；任务隔离、失败非零退出 |
| A21 | 重复手填派生字段、重复探测、逐字幕固定抽帧 | prepare自动派生，同一未变输出检查一次；听看对齐，具体风险才定点抽帧 |
| A22 | 固定比例/金句/受众星级、大师泛化和示例因果断裂 | 修专业表述与例子，方法依作品采用；三张节拍表修列数 |

**逐句表演的最终决策。** 每句对白后必须接一句具体、可演的表情、反应或小动作，来自人物处境、已有行为与前后情绪，可由说话人或听者承接；克制或拒答要写成可观察状态。不能重复皱眉握拳填空，也不能逐句切镜、启动运镜、固定停顿或让全员轮流反应。提示不混进 `source_text` 或H3 `<d>` 口播，但须进入后续画面/表演描述。本轮采用跨阶段内容核对，不为这一可逆文字调整新增措辞匹配测试。

**更正已排除疑点。** H3首次提交原有 `open("x")` 独占声明，最初“并发双POST”猜测不成立；本轮保留实现并补并发回归，不能宣称修复了已有双提交漏洞。beat词库 `_generated_by` 原指向不存在脚本，本轮对齐内联构建来源，未虚构新生成器。

## 提速证据

复现：`python -B -X utf8 audit/measure_reference_load.py`。基线取上述起点的references，前后均使用同一当前renderer；统计UTF-8正文bytes，不含导航包装。负“减少”表示为补清质量与边界而略增。

| 路由 | 起点bytes | 当前bytes | 减少 |
|---|---:|---:|---:|
| planning基线 | 18,676 | 18,722 | -0.2% |
| script基线 | 23,779 | 24,436 | -2.8% |
| assets基线 | 17,439 | 17,843 | -2.3% |
| storyboard基线 | 5,736 | 5,807 | -1.2% |
| keyframes基线 | 15,309 | 13,932 | 9.0% |
| video基线 | 4,305 | 4,305 | 0% |
| delivery基线 | 14,281 | 14,910 | -4.4% |
| repair基线 | 1,710 | 1,710 | 0% |
| planning/genre_research | 32,234 | 5,260 | 83.7% |
| script/genre_research | 32,746 | 5,260 | 83.9% |
| repair/affected_script | 36,953 | 7,884 | 78.7% |
| repair/affected_assets | 54,602 | 2,677 | 95.1% |
| repair/affected_video | 36,398 | 2,837 | 92.2% |
| repair/affected_delivery | 23,404 | 2,316 | 90.1% |

新writing基线为9,776 bytes。题材入口之后实际选中的原始方法另计，不能把入口缩减解释为删去全部创作方法。常规基线并非全面变短；主要收益来自避免无关条件包、重复载入、重复读图/手填/探测与重复媒体编码。本文不把bytes当token，不外推为整体出片快84%、压缩次数已下降或模型生成耗时下降。前一轮分镜载入量缩减也不算成本轮新增效果。

## 验证与质量边界

- **70项回归通过**，最近完整运行3.431秒：H3 runner 20、prepare 15、video confirmations 12、media tools 6、lint contracts 8、read_reference 5、rhythm_source 4。其后只改文档与测量脚本，运行时代码未再变化。
- `python -B scripts/drama_lint.py --stage skill`：0 error、0 warning；`quick_validate.py .`：Skill is valid。提交前已检查9个阶段、151个不同文件/标题锚点、4个全文动作合同及98组阶段/条件/返修渲染，0错误；25个Python文件AST解析及 `git -c core.autocrlf=false diff --check` 均通过。
- 审计覆盖表已对照起点git清单逐项核验，52/52无遗漏；待提交41个修改文件与8个新文件均为Skill实现、Reference、测试或维护记录，不含制作媒体、真实.env或制作项目。
- 三个独立无外部副作用场景：纯文字剧本走轻路径；continuous后段等真实尾帧后另批；压缩后未变原任务直接resume。最新逐句表演要求由主审集成补记，不伪称早先独立探针已覆盖该要求。
- 回归使用临时JSON/项目与本地合成媒体。ffmpeg音轨等有真实本地执行证据；TTS、供应商轮询/下载与授权分支为离线验证，未做真实付费成片、SSH或上传。
- 保留真实媒体查看、批准身份/状态、required输入、逐字台词、已确认切点/运镜及真实请求授权；未用静态lint代替人物表演、衔接和整体审美判断。
- 实际成片是否自然、是否有情绪，需要真实制作后顺看判断。本轮修其上游规则和客观实现，不能据此保证模型每次都生成有感染力的画面。
