# 本地运行时合同（Claude Code 宿主）

本文件是本 skill 在 Claude Code 环境下执行时，所有宿主工具调用的**唯一权威**。
其他文档中出现豆包宿主工具名（`image_gen`、`text_to_video`、`interaction.ask`、
mediakit、`design-cli`、`present_files`、`FileBatchUpload` 等）时，含义一律以本
文件的本地映射为准；各文档只保留流程与合同语义，不再描述平台工具参数。

## 工具映射总表

| 文档中的豆包工具名 | 本地执行 | 调用方式 |
|---|---|---|
| `image_gen`（文生图） | gpt-image（知脑中转） | `python tools/image/img.py --prompt-file <md> --out <png>` |
| `image_edit`（图生图/修图） | gpt-image（知脑中转） | 同上，加 `--ref <图>`（可多个，顺序即参考顺序） |
| `text_to_video` | MiniMax H3 | `python tools/video/h3.py --gen <gen.json> --prompt <md> --out <mp4>`，gen.json `inputs` 为空、`mode: T2VA` |
| `image_to_video` | MiniMax H3 | 同上，`inputs` 含图片槽位、`mode: I2VA/FL2VA/L2VA` |
| `media_to_video` | MiniMax H3 | 同上，`inputs` 含视频/音频槽位、`mode: Ref2VA` |
| `video_edit`（定点返修） | 无定点编辑能力 | 以原视频为参考槽位经 h3 重生成，Prompt 写明保留人声/音色/口型；语义弱于原工具，返修前向用户说明 |
| `text_to_audio_plus`（TTS 音色） | Qwen3TTS（AutoDL） | `python tools/tts/qwen3tts_autodl.py --role <角色> --instruct <音色描述> --text <样音台词> --out <wav>`；批量用 `--roles-file` |
| `interaction.ask`（确认/询问） | AskUserQuestion | 主 Agent 直接调用；问题/选项结构与原文档相同 |
| mediakit `extract-frames` | ffmpeg | `python tools/video/ffmpeg_tool.py frame <mp4> <png> [--tail|--at S]`；帧条用 `strip` |
| mediakit `probe-video-metadata` | ffprobe | `python tools/video/ffmpeg_tool.py probe <mp4> [--json]` |
| mediakit `trim-video` | ffmpeg | `python tools/video/ffmpeg_tool.py trim <in> <out> --start S --end S` |
| mediakit `concat-video` | ffmpeg | `python tools/video/ffmpeg_tool.py concat <out> <seg1> [seg2 ...]`（片段须带音频流；规格不一时自动 letterbox 统一到首段分辨率） |
| mediakit `add-subtitle-to-video` | ffmpeg（需 libass） | `python tools/video/ffmpeg_tool.py burn <mp4> <srt> <out> [--size 36] [--pos bottom\|lower_third]` |
| mediakit `asr-subtitles` | 无 ASR | 字幕文本从**已锁定剧本台词稿**整理为 SRT（时间轴按成片口播人工/脚本对齐），不做语音识别 |
| `FileBatchUpload`（上传换 URL） | S3 | `python tools/s3/upload.py <文件> --prefix ref/` |
| `design-cli`（画布 Workspace） | 不使用 | 本地无画布；产物直接落项目目录即视为「上画布」，对应回读动作改为检查文件存在且可解码 |
| `present_files` / `file_presents`（交付展示） | 文件落盘即交付 | 最终成片路径写入交付说明并在对话中给出；无单独交付工具调用 |

工具参数细节、环境变量与依赖见 `tools/README.md`；凭证只走环境变量或
`--config` 文件，不进项目文件。

JSON 里 `tool` / `tool_mode` 这类**字段取值仍是上表左列的枚举原文**
（`image_gen`、`image_edit`、`text_to_video`、`image_to_video`、
`media_to_video`、`video_edit`）：它们是 `drama_lint.py` 的校验枚举，不随本地
执行工具改名。只有面向用户的展示文字、操作日志和正文叙述使用本地工具名。

## 凭证读取（`.env`）

工具凭证缺省读 skill 根目录的 `.env`（模板 `.env.example`，含全部键名，值留空）；
也可用 `--config <KEY=VALUE 文件>` 指向别处，或先放进系统环境变量——**环境变量优先**。
`tools/search/web_search.py` 已按「脚本上溯三级」自动定位 skill 根 `.env`；其余工具
用 `--config <skill 根>/.env` 指向同一文件即可。凭证不进项目目录、不进 manifest、
不写进 Prompt。S3 仍可单独放 `tools/s3/s3.env`（模板 `s3.env.example`）。

## gen.json 契约（`tools/video/h3.py`）

`h3.py` 必读 `--gen <gen.json>`，最小结构：

```json
{
  "model": "MiniMax H3",
  "duration_s": 12,
  "seed": 0,
  "mode": "I2VA",
  "inputs": [{"kind": "image", "path": "<项目相对路径或 http(s) URL>", "role": "identity_reference"}],
  "extra": {"workflow": "<AutoDL workflow id>", "base_url": "https://autodl.art",
            "resolution": "768p横", "options": {}, "poll_interval_s": 10, "timeout_s": 1800}
}
```

- **`extra.workflow` 必填**，是部署侧事实（AutoDL 上部署的 ComfyUI workflow id），
  缺失时 `h3.py` 直接 `BackendError` 退出；本地文档无法代为指定，按实际接入填写。
- `inputs[]` 按 `kind`（`image`/`video`/`audio`）分组成 `ref_<kind>_N` 槽位，**数组序即槽位序**；
  `mode` 是每镜经 `h3-prompt-writing` 判定的结果；`duration_s` 与交付包/成稿时间轴一致且 ≤15s。
- `extra.options` 是 workflow 私有字段直通口（分辨率/时长档位名随 workflow 而异），
  已知键（`prompt`/`duration`/`seed`/`resolution`）随后覆盖，保证显式字段优先。
- `inputs[].path` 相对路径按**项目根**（运行时 cwd）解析；命中 SEG 的 gen.json 路径登记为
  `segments[].gen_file`，每个 SEG 一份。

## 每 SEG 两份 Prompt

视频阶段每个 `SEGxxx` 产出两份 Prompt 文件，**同一 `_vNN` 版本**：

| 文件 | 角色 | 提交给模型？ |
|---|---|---|
| `提示词_SEGxxx_vNN_ep_N.md` | 五段式**导演交付包**（`video.md` 定义），含表演/色彩/声音硬门、切点、尾态、禁区等导演级信息 | 否，是内部输入包 |
| `提示词_SEGxxx_vNN_ep_N.h3.md` | 经平行 skill `h3-prompt-writing` 转出的 **H3 成稿** | 是，`h3.py --prompt` 的唯一输入 |

导演交付包信息一字不减地落到成稿对应位置；成稿的字段结构、参考标记、时间写法以
`h3-prompt-writing` skill 为准，本仓不复述。`drama_lint.py` 对交付包查五段/标记/台词，
对成稿只核「存在 + 非空 + `h3_prompt_sha256` 一致」。

## 用户可见模型名

- 生图模型：**gpt-image（知脑中转）**。本地无「会员模型」分层，参数确认表不再出现
  会员/额度提示；`drama_plan.json` 与 manifest 中生图模型字段写 `gpt-image`。
- 视频模型：**MiniMax H3**。能力档案以 `tools/video/h3.json` 为准：单段 4–15 秒、
  24fps、参考图 ≤9、参考音频 ≤3。文档中 `seedance 2.0 fast`（默认、SEG ≤15s）
  按 H3 执行；`seedance 2.5`（30s、会员提示）本地无对应物，规划时不可选，
  lint 中 seedance 2.5 相关校验自然不触发。
- SEG 时长上限沿用 15 秒合同不变。

## interaction.ask → AskUserQuestion 的执行约定

原文档三类确认（`proceed_project` / `generate` / `proceed_assembly`）与唯一素材
询问例外全部以 AskUserQuestion 执行，问题与选项文案结构不变。确认记录写入
`用户确认记录.jsonl` 时字段沿用原 schema，`interaction_ask_call_id` 填本地约定
值 `auq-<UTC ISO8601 时间戳>`（如 `auq-2026-10-15T08:30:00Z`），保证非空且
唯一，lint 校验逻辑不变。

## 画风候选卡

`planning.md`「画风候选卡」是本 skill 唯一允许用户挑选创意选项的位置。本地宿主
不改变该机制：候选卡随规划阶段参数确认表一次性呈现 `3-5` 个画风候选，用户选定后
写入 `drama_plan.json.style_contract`，此后所有生图与视频 Prompt 首句统一带该
`project_visual_mode` 风格词。除这一次选择外，视频方案确认仍不得携带创意选项。

## 画布与交付的本地语义

- 原「非 Mobile 上画布 + 回读」改为：每个图片/视频产物生成后检查文件存在、
  大小非零、可被 ffprobe/图片解码，即视为完成展示与回读。
- 原 `present_files` 交付改为：产物已在项目目录对应位置落盘，并在对话中给出
  相对路径清单。
- `references/cli/` 整套 design-cli 文档本地不适用，已移除；manifest 中
  workspace/canvas 相关字段留空即可。

## 操作日志用语

操作日志登记媒体处理动作时写本地工具名（如 `ffmpeg_tool concat`），不再出现
mediakit 字样；lint 的禁用词为 `text_to_image`（正确工具名是 `img`）。
