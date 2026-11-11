# 执行层逐文件审查 · 2026-11-11

范围：只审查和修改 Skill 内的请求准备/授权程序及 tools 工具，不读写制作项目、不发起生成或上传。本文为维护记录，不加入 Skill 运行时路由。

| 文件/范围 | 审查记录 | 状态 |
|---|---|---|
| scripts/prepare_video.py | 完整阅读；准备/合批只算媒体指纹不编码；表格按 ID 单元格取行，避免下一镜在描述中引用上一镜时污染摘录；STATE/VOICE索引同步 lint；旧结果保留与真实输入门保留 | 已修复并验证 |
| scripts/h3_contract.py | 完整阅读；prepare_request 新增 encode_media=False 只流式计算相同字节指纹，首次实际提交才装载/编码媒体，既有结构/能力/标记门不变 | 已修复并验证 |
| scripts/video_confirmations.py | 完整阅读；唯一台账来源、逐 SEG 替代和实际输入字节绑定保留；SHA复用共享函数以减少大媒体峰值内存 | 已修复并验证 |
| scripts/stamp_confirmation.py | 完整阅读；冻结/登记确认不编码媒体；非 generate 视频阶段确认写入前核全段真实候选、当前有效生成事实、版本与时间；accepted 不能用 generate 代替用户产物接受，也不能接受时偷换产物或沿用重生前的旧接受 | 已修复并验证 |
| tools/video/h3.py | 完整阅读；结果下载不携带 API 令牌，跨源重定向移除授权头；实际 POST 前单次编码并与原绑定对账；首次提交原本已有 open(x) 独占创建，原疑点不成立，补并发回归验证无双 POST | 已修复并验证 |
| tools/video/ffmpeg_tool.py | 完整阅读；concat 支持单段/无音轨段，补等长静音且保留左右声道，时间戳归零；probe --json 不再附加路径破坏 JSON；无效尺寸不再伪造1920×1080；帧条参数拒绝零/负/非有限间隔 | 已修复并验证 |
| tools/tts/qwen3tts_autodl.py | 完整阅读；新增 --language/逐角色 language，默认 Auto；只下载本 prompt_id 的实际 SaveAudio 输出、并发临时文件隔离；失败退出非零，临时文件清理；空端口/用户名按默认22/root处理 | 已修复并验证 |
| tools/README.md | 完整阅读；修 trim 位置参数示例，补单段/静音拼接和 TTS 语言/失败语义 | 已修复 |
| tools/video/h3.json、tools/image/zhinao_image.json | 已读；能力与部署分离、凭证不入 JSON 保留 | 保留 |
| tools/image/img.py | 完整阅读；比例映射三标准档如实保留；拒绝 NaN/Infinity 比例输入 | 已修复 |
| tools/image/zhinao_image.py | 完整阅读；参考图必须走 edits 的实测非显然约束保留，下载无凭证转发，配置与根.env路由相符 | 保留 |
| tools/search/web_search.py | 完整阅读；实际 httpx 缺失时补明确依赖提示，保留仅文本研究边界 | 已修复 |
| tools/s3/upload.py | 完整阅读；纠正说明中的配置优先级（实际环境优先），URL模式缺httpx给明确提示，保留内容寻址与明确上传入口 | 已修复 |
| .env.example、tools/s3/s3.env.example | 完整阅读；模板只含空值/示例值；S3真实配置忽略问题交root补.gitignore | 已核对 |
| tests/test_h3_runner.py、test_prepare_video.py、test_video_confirmations.py | 完整阅读；保留原端到端离线约束并补媒体编码次数、并发独占、产物接受/拼接边界和摘录引用回归 | 已验证 |
| scripts/drama_lint.py | 本代理完整顺读1500至末尾，生产代理完整读前1500并提供最小复现；去掉反应/余震配额，空world facts合法，不支持分镜擅自dropped；修共享引用空registry漏洞、approved无文件、STATE污染基准版本、分集VOICE复用类别与必传识别 | 已修复并验证 |

## 验证

- H3 runner：20项通过（提交/恢复/候选登记、丢失POST响应不重复提交、并发独占、重生新授权与新版本、跨源凭证边界、本地素材变动失效、实际POST仅编码一次）。
- prepare_video：原14项通过，新增ID单元格摘录测试待集成终跑。
- video_confirmations：12项通过，含真实stamp台账、生成授权不能冒充产物接受、视频目标不创建拼接授权、未完成全集拒绝拼接、重生不能沿用旧接受。
- media_tools：6项通过；含真实本地ffmpeg合成临时素材，验证单段静默/多段混合音轨拼接时长、右声道未丢失、probe JSON可直接解析；TTS请求语言传入实际远程图结构、失败不取旧音频、精确返回文件解析均离线验证。
- lint_contracts：7项通过（空世界事实、空registry伪共享、approved无文件、基准/状态版本独立、分集VOICE跨集复用、锁定事件不可dropped、无额外反应/余震镜头的合法高光）。
- 全部24个Python文件经 ast.parse 语法检查。py_compile 因宿主 PYTHONPYCACHEPREFIX 指向工作区外缓存目录被拒，改用不写缓存的AST检查，无需扩大权限。

以上全部使用临时项目与合成媒体；未发起网络、付费生成、SSH、真实素材上传或制作项目迁移。远端AutoDL/ComfyUI部署可用性、实际模型生成质量仍需真实制作验证。上述性能证据是编码次数/内存路径的确定性减少，不能直接外推视频生成耗时或上下文压缩次数。

## 主审最终集成补记

新增ID单元格摘录回归已通过；主审另补发声块与源台词的顺序、次数及无新增内容核对回归。最终prepare为15项、lint_contracts为8项，全部测试合计70项通过；前述“待集成终跑”已收口。运行时代码此后未再变化。
