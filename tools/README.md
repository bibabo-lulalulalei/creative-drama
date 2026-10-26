# 工具目录（本地宿主工具）

本 skill 原为豆包宿主编写，文档里的 `image_gen`、`text_to_video`、`interaction.ask`、
mediakit、`design-cli`、`present_files` 等均为豆包平台自带工具。本目录是这些能力
在 Claude Code 环境下的**本地等价物**——从 ai-film-production skill 拷入并扩展，
独立成册，两个 skill 互不依赖。

## 权威映射与 gen.json 契约

宿主工具映射、工具职责边界和 `gen.json` schema 以 [`references/local-runtime.md`](../references/local-runtime.md) 为唯一权威。本 README 只维护命令示例、配置和依赖，不复制映射表或 schema。

## 用法示例

```bash
# 生图（统一入口，唯一后端 zhinao；无 --ref=文生图，带 --ref=参考生图）
python tools/image/img.py --ratio 16:9 \
  --prompt-file prompts/char_c01.md --ref refs/c01_key.png --out assets/c01.png

# 生视频（成功后末行打印结果 JSON：task_id/seed/workflow/model）
python tools/video/h3.py --gen takes/S003.gen.json --prompt takes/S003.h3.md \
  --out takes/S003.mp4

# 成片后处理链
python tools/video/ffmpeg_tool.py probe takes/S003.mp4
python tools/video/ffmpeg_tool.py trim takes/S003.mp4 takes/S003_cut.mp4 --start 0.5 --end 8.0
python tools/video/ffmpeg_tool.py concat delivery/ep01_master.mp4 takes/S001.mp4 takes/S002.mp4 takes/S003_cut.mp4
python tools/video/ffmpeg_tool.py burn delivery/ep01_master.mp4 delivery/ep01.srt delivery/ep01_sub.mp4 --pos lower_third

# TTS（多角色批量）
python tools/tts/qwen3tts_autodl.py --roles-file voices.json

# 上传换 URL
python tools/s3/upload.py assets/c01.png --prefix ref/
```

## 配置（凭证不进 skill）

每个工具从**环境变量**读配置，也支持 `--config <KEY=VALUE 文件>`；S3 还会自动
读 `tools/s3/s3.env`（模板 [s3/s3.env.example](s3/s3.env.example)，需自行填）：

| 工具 | 变量 |
|---|---|
| image (zhinao) | `XAI_API_KEY`（知脑中转令牌）+ 可选 `GROK_MODELS_BASE_URL` |
| video (h3) | `AUTODL_API_KEY`（AutoDL 令牌，分组选 ComfyUI） |
| video (ffmpeg) | 无，仅需系统 PATH 有 ffmpeg/ffprobe（burn 需 libass 构建） |
| tts | `AUTODL_SSH_HOST` `AUTODL_SSH_PORT` `AUTODL_SSH_USER` `AUTODL_SSH_PASSWORD` |
| s3 | `OSS_ENDPOINT_URL` `OSS_BUCKET_NAME` `OSS_ACCESS_KEY_ID` `OSS_SECRET_KEY_SECRET` `OSS_ANTI_THEFT_CHAIN` |
| web_search | `SEARCH_ENGINE_HOST` `SEARCH_ENGINE_SUBSCRIPTION_KEY` |

本 skill 根目录放有一个 `.env`（模板 [`.env.example`](../.env.example)，只有键名、
值留空）汇总以上全部变量。`web_search.py` 已自动读它（脚本上溯三级即 skill 根）；
其余工具用 `--config <skill 根>/.env` 指向同一文件，或直接把变量放进系统环境变量
（**环境变量优先**）。`.env` 含真实凭证，不得外传、不得提交到任何仓库。

## 依赖

- image（zhinao）/video(h3)：仅 Python 标准库；s3 需 `boto3`+`httpx`；search 需 `httpx`；tts 需 `paramiko`+ffmpeg。
- 缺依赖时工具会打印明确安装提示，不静默失败。

## 与豆包原文档的冲突须知

原 skill 文档明令「禁止 ffmpeg」「mediakit 缺失时停止」。在本目录落地后，凡文档
提到 mediakit 的环节（抽帧/探测/裁剪/拼接/字幕烧录）即以 `ffmpeg_tool.py` 对应
子命令执行为准；`interaction.ask` 一律以 AskUserQuestion 执行；`design-cli` 与
`present_files` 环节跳过（文件落盘即交付）。其余合同（阶段硬门、manifest、lint）
不变，`drama_lint.py` 的 ffmpeg 禁用词校验针对的是**操作日志话术**，不影响本
工具链的实际执行。
