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

# 视频先离线预检：导演包与纯 H3 成稿独立保存，按当前 SEG 写回绑定
python scripts/preflight_video.py --project-root <project> --episode ep_1 --segment SEG003 --write
python tools/video/h3.py --project-root <project> --gen takes/S003.gen.json --prompt takes/S003.h3.md --check-only

# 取得同一 binding_id 的真实 generate 授权后由受控执行者提交
python tools/video/h3.py --project-root <project> --gen takes/S003.gen.json --prompt takes/S003.h3.md \
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

连续后段另须在编译前用 `ffmpeg_tool.py lock-cut` 锁定实际采用出点和对应帧，最终 `trim` 以同一 `--adopted-cut-file/--adopted-cut-id` 复核；参数见 `python tools/video/ffmpeg_tool.py lock-cut --help`。HTTP(S) 文件 URL 原样提交，不下载或编码副本；绑定只冻结 URL 字符串，不证明远端内容字节不变。

## 配置与凭证

各工具配置入口不同；环境变量中的凭证优先，不向项目、manifest 或 Prompt 写入真实值。

| 工具 | 凭证变量 | 文件入口 |
|---|---|---|
| image (zhinao) | `XAI_API_KEY`，可选 `GROK_MODELS_BASE_URL` | 自动读 Skill 根 `.env`；`img.py --config` 仅接受后端 JSON，默认 `tools/image/zhinao_image.json` |
| video (h3) | `AUTODL_API_KEY` | 只读环境变量，无 `--config`，不自动加载 `.env`；运行前由宿主注入 |
| video (ffmpeg) | 无 | 系统 PATH 需有 ffmpeg/ffprobe；burn 需 libass |
| tts | `AUTODL_SSH_HOST` `AUTODL_SSH_PORT` `AUTODL_SSH_USER` `AUTODL_SSH_PASSWORD` | 可用 `--config <KEY=VALUE 文件>`，无自动 `.env` 加载 |
| s3 | `OSS_ENDPOINT_URL` `OSS_BUCKET_NAME` `OSS_ACCESS_KEY_ID` `OSS_SECRET_KEY_SECRET` `OSS_ANTI_THEFT_CHAIN` | `--config <KEY=VALUE 文件>` 或默认 `tools/s3/s3.env` |
| web_search | `SEARCH_ENGINE_HOST` `SEARCH_ENGINE_SUBSCRIPTION_KEY` | 默认 Skill 根 `.env`，可用 `--config <KEY=VALUE 文件>` 替代 |

[`.env.example`](../.env.example) 与 [s3.env.example](s3/s3.env.example) 仅为键名模板；真实配置不外传、不提交。

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
