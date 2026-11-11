# 工具目录（本地宿主工具）

本目录提供当前 Skill 使用的图片、视频、音色、媒体处理、上传和搜索工具。H3 执行器采用实际调用 `h3-prompt-writing` Skill 返回的模式、输入映射与成稿。

## 权威映射与冻结快照契约

宿主工具映射、工具职责边界和请求快照 schema 以 [`references/local-runtime.md`](../references/local-runtime.md) 为唯一权威。本 README 只维护命令示例、配置和依赖，不复制映射表或 schema。

## 用法示例

```bash
# 生图（统一入口，唯一后端 zhinao；无 --ref=文生图，带 --ref=参考生图）
python tools/image/img.py --ratio 16:9 \
  --prompt-file prompts/char_c01.md --ref refs/c01_key.png --out assets/c01.png

# 当前段取材；H3 成稿完成后，一条命令派生登记、校验、冻结和确认预览
python scripts/prepare_video.py --project-root <project> --episode ep_1 --segment SEG003 --context
python scripts/prepare_video.py --project-root <project> --episode ep_1 --segment SEG003 \
  --request-file takes/S003.snapshot.json --prompt-file takes/S003.h3.md

# 可选：两个独立就绪段合成一份确认预览
python scripts/prepare_video.py --project-root <project> --episode ep_1 --segment SEG003,SEG004 --combine-evidence

# 展示返回的两表，取得真实 generate 后一次登记（不先 dry-run）
python scripts/stamp_confirmation.py --project-root <project> --stage video --video \
  --episode ep_1 --revision 1 --segments SEG003 --confirmation-id CONF-EP1-SEG003-1 \
  --evidence-file <准备工具返回的JSON> --user-message <用户实际回复> --append

# 已授权后直接执行；自动保存 task_id、检查视频并登记 candidate
python tools/video/h3.py --project-root <project> --episode ep_1 --segment SEG003 \
  --out takes/S003.mp4
# 同一命令自动恢复；也可显式 --resume。--submit-only 提交即返回。

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

连续后段另须在编译前用 `ffmpeg_tool.py frame --tail/--at` 从成品提取单个稳定尾帧，作为下段 `previous_tail_as_start_frame` 真实图片输入登记进 video manifest（不建帧注册表、不写连续性 JSON）；最终 `trim <mp4> <out> <start> <end>` 按本段冻结快照的 `content_duration_s/tail_handle_s` 取有效区间（无 lock-cut 子命令、无合同复核参数）。HTTP(S) 文件 URL 原样提交，不下载或编码副本；快照只冻结 URL 字符串，不证明远端内容字节不变。

## 配置与凭证

各工具配置入口不同；环境变量中的凭证优先，不向项目、manifest 或 Prompt 写入真实值。

| 工具 | 凭证变量 | 文件入口 |
|---|---|---|
| image (zhinao) | `XAI_API_KEY`，可选 `GROK_MODELS_BASE_URL` | 自动读 Skill 根 `.env`；`img.py --config` 仅接受后端 JSON，默认 `tools/image/zhinao_image.json` |
| video (h3) | `AUTODL_API_KEY` | 执行时从环境或 Skill 根 `.env` 读取，环境优先；部署配置按下文解析，无 `--config` |
| video (ffmpeg) | 无 | 系统 PATH 需有 ffmpeg/ffprobe；burn 需 libass |
| tts | `AUTODL_SSH_HOST` `AUTODL_SSH_PORT` `AUTODL_SSH_USER` `AUTODL_SSH_PASSWORD` | 可用 `--config <KEY=VALUE 文件>`，无自动 `.env` 加载 |
| s3 | `OSS_ENDPOINT_URL` `OSS_BUCKET_NAME` `OSS_ACCESS_KEY_ID` `OSS_SECRET_KEY_SECRET` `OSS_ANTI_THEFT_CHAIN` | `--config <KEY=VALUE 文件>` 或默认 `tools/s3/s3.env` |
| web_search | `SEARCH_ENGINE_HOST` `SEARCH_ENGINE_SUBSCRIPTION_KEY` | 默认 Skill 根 `.env`，可用 `--config <KEY=VALUE 文件>` 替代 |

[`.env.example`](../.env.example) 与 [s3.env.example](s3/s3.env.example) 仅为键名模板；真实配置不外传、不提交。

## 依赖

- image（zhinao）/video(h3)：仅 Python 标准库；s3 需 `boto3`+`httpx`；search 需 `httpx`；tts 需 `paramiko`+ffmpeg。
- 缺依赖时工具会打印明确安装提示，不静默失败。

H3 部署配置按显式候选请求 > 环境 `H3_WORKFLOW` / `H3_BASE_URL` > Skill 根 `.env` > [`h3.json.deployment`](video/h3.json) 解析。离线预检将实际 workflow/base_url 冻结进 manifest，确认后执行只用冻结值；`--check-only` 不需要令牌，也不探测网络。默认部署值不保证服务当前可用。
