# 工具目录（本地宿主工具）

本 skill 原为豆包宿主编写，文档里的 `image_gen`、`text_to_video`、`interaction.ask`、
mediakit、`design-cli`、`present_files` 等均为豆包平台自带工具。本目录是这些能力
在 Claude Code 环境下的**本地等价物**——从 ai-film-production skill 拷入并扩展，
独立成册，两个 skill 互不依赖。

## 豆包工具 → 本地工具映射

| 豆包宿主工具 | 本地等价 | 说明 |
|---|---|---|
| `image_gen`（文生图） | [`image/img.py`](image/img.py) 不传 `--ref` | **统一入口**，唯一后端 zhinao（知脑中转 gpt-image） |
| `image_edit`（图生图/参考生图） | [`image/img.py`](image/img.py) 传 `--ref`（可多个） | 同上；`--ratio` 由工具转成后端参数 |
| —（后端实现） | [`image/zhinao_image.py`](image/zhinao_image.py) | 直接调用也可，但文档一律走 `img.py` |
| `text_to_video` | [`video/h3.py`](video/h3.py)，gen.json 不带 inputs | MiniMax H3（AutoDL ComfyUI） |
| `image_to_video` | [`video/h3.py`](video/h3.py)，inputs 带图片槽位 | |
| `media_to_video` | [`video/h3.py`](video/h3.py)，inputs 带视频/音频槽位 | 槽位顺序即 inputs 数组顺序 |
| `video_edit`（定点返修） | 无定点编辑；用 h3 以原视频为参考槽位重生成 | 能力缺口，注意返修语义不同 |
| `text_to_audio_plus`（TTS 音色） | [`tts/qwen3tts_autodl.py`](tts/qwen3tts_autodl.py) | 无参考音、音色由文字描述 |
| `interaction.ask`（封闭确认） | Claude Code 原生 AskUserQuestion | 选项式确认，等价 proceed/generate 三类 |
| mediakit `extract-frames` | [`video/ffmpeg_tool.py`](video/ffmpeg_tool.py) `frame` / `strip` | |
| mediakit `probe-video-metadata` | `ffmpeg_tool.py probe`（`--json` 出原始 ffprobe） | |
| mediakit `trim-video` | `ffmpeg_tool.py trim --start S --end S` | 重编码保证切点精确 |
| mediakit `concat-video` | `ffmpeg_tool.py concat` | 片段须带音频流；规格不一自动 letterbox 统一到首段分辨率 |
| mediakit `add-subtitle-to-video` | `ffmpeg_tool.py burn`（需 ffmpeg 带 libass） | **字幕文本来自剧本台词稿整理成 SRT，不做 ASR** |
| mediakit `asr-subtitles` | 无 | 能力缺口：台词稿→SRT 由剧本文本人工/脚本对齐 |
| `FileBatchUpload`（上传换 URL） | [`s3/upload.py`](s3/upload.py) | 返回 CDN URL，幂等 |
| `design-cli`（画布）/ `present_files`（交付） | 不需要 | 本地文件系统即画布与交付；产物直接落项目目录 |
| `mediakit` 字幕擦除/混音/封装 | 无（ffmpeg 可临时手写） | 低频，未封装 |

辅助工具（豆包版没有，本地增强）：[`search/web_search.py`](search/web_search.py)
文本调研（**用于事实核验，不用于画风选择**）。

`h3.py` 的 `--prompt` 文件由平行 skill `h3-prompt-writing` 产出，本目录只负责提交。

校验/回退脚本 `scripts/drama_lint.py`、`scripts/drama_rollback.py` 为纯标准库，
本地可直接跑：`python scripts/drama_lint.py --project-root <项目根> --stage <阶段>`。

## gen.json 契约（`video/h3.py`）

```json
{
  "model": "MiniMax H3",
  "duration_s": 12,
  "seed": 0,
  "mode": "I2VA",
  "inputs": [{"kind": "image", "path": "assets/c01.png", "role": "identity_reference"}],
  "extra": {"workflow": "<AutoDL workflow id>", "base_url": "https://autodl.art",
            "resolution": "768p横", "options": {}, "poll_interval_s": 10, "timeout_s": 1800}
}
```

- **`extra.workflow` 必填**：AutoDL 上部署的 ComfyUI workflow id，缺失即 `BackendError`
  退出。它是部署侧事实，按实际接入填写，不由本目录提供默认值。
- `inputs[]` 按 `kind`（`image`/`video`/`audio`）分组成 `ref_<kind>_N` 槽位，
  **数组顺序即槽位顺序**；`label`/`role` 只作登记，标签与正文的对应由 prompt 文件承担。
- `mode` 是每镜经 `h3-prompt-writing` 判定的模式（T2VA/I2VA/FL2VA/L2VA/Ref2VA）。
- `extra.options` 为 workflow 私有字段直通口；`prompt`/`duration`/`seed`/`resolution`
  等已知键随后覆盖，显式字段优先。
- `inputs[].path` 相对路径按**当前工作目录（项目根）**解析；http(s) URL 原样直传。
- 成功后 stdout 末行打印 `{"task_id","seed","workflow","model"}`，供 provenance 记录。

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
