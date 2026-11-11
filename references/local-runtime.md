# 本地运行时合同（Claude Code 宿主）

本文件是本 Skill 在 Claude Code 环境下工具执行、配置和交付的唯一权威。JSON 中的工具枚举按下表执行；H3 的模式、参考使用方式和成稿必须实际调用 `h3-prompt-writing` Skill 决定。

## 工具映射总表

| 工具枚举或操作 | 本地执行 | 调用方式 |
|---|---|---|
| `image_gen`（文生图） | gpt-image（知脑中转） | `python tools/image/img.py --prompt-file <md> --out <png>` |
| `image_edit`（图生图/修图） | gpt-image（知脑中转） | 同上，加 `--ref <图>`（可多个，顺序即参考顺序） |
| `text_to_video` / `image_to_video` / `media_to_video` | MiniMax H3 | `python tools/video/h3.py --project-root <project> --episode ep_N --segment SEGxxx [--out <mp4>] [--check-only]`；直接执行 manifest 段内冻结快照，mode、成稿与输入映射采用 `h3-prompt-writing` 的实际返回值，枚举本身不用于推断模式 |
| `video_edit`（定点返修） | 无定点编辑能力 | 以原视频为参考槽位经 h3 重生成，Prompt 写明保留人声/音色/口型；语义弱于原工具，返修前向用户说明 |
| `text_to_audio_plus`（TTS 音色） | Qwen3TTS（AutoDL） | `python tools/tts/qwen3tts_autodl.py --role <角色> --instruct <音色描述> --text <样音台词> --out <wav>`；批量用 `--roles-file` |
| `interaction.ask`（确认/询问） | AskUserQuestion | 主 Agent 直接调用；问题/选项结构与原文档相同 |
| mediakit `extract-frames` | ffmpeg | `python tools/video/ffmpeg_tool.py frame <mp4> <png> [--tail|--at S]`；帧条用 `strip` |
| mediakit `probe-video-metadata` | ffprobe | `python tools/video/ffmpeg_tool.py probe <mp4> [--json]` |
| mediakit `trim-video` | ffmpeg | `python tools/video/ffmpeg_tool.py trim <in> <out> --start S --end S` |
| mediakit `concat-video` | ffmpeg | `python tools/video/ffmpeg_tool.py concat <out> <seg1> [seg2 ...]`（片段须带音频流；规格不一时自动 letterbox 统一到首段分辨率） |
| mediakit `add-subtitle-to-video` | ffmpeg（需 libass） | `python tools/video/ffmpeg_tool.py burn <mp4> <srt> <out> [--size 36] [--pos bottom\|lower_third]` |
| mediakit `erase-watermark`（字幕/水印擦除） | ffmpeg delogo | `python tools/video/ffmpeg_tool.py erase <in> <out> --region x,y,w,h`（可重复多区域；固定区域文字/水印插值擦除，输出新 `_vNN` 版本不覆盖原片；移动文字/擦不净走返修重生） |
| mediakit `asr-subtitles` | 无 ASR | 字幕文本从**已锁定剧本台词稿**整理为 SRT（时间轴按成片口播人工/脚本对齐），不做语音识别 |
| `FileBatchUpload`（上传换 URL） | S3 | `python tools/s3/upload.py <文件> --prefix ref/` |
| `design-cli`（画布 Workspace） | 不使用 | 产物保存到项目目录，检查文件存在、非空且可解码；workspace/canvas 字段留空 |
| `present_files` / `file_presents`（交付展示） | 本地文件交付 | 真实文件落盘、非空且可打开/解码，并在对话给出相对路径后才算交付；无单独交付工具调用 |

工具参数细节、各自配置入口和依赖见 `tools/README.md`；凭证不进项目文件。

JSON 里 `tool` / `tool_mode` 这类**字段取值仍是上表左列的枚举原文**
（`image_gen`、`image_edit`、`text_to_video`、`image_to_video`、
`media_to_video`、`video_edit`）：它们是 `drama_lint.py` 的校验枚举，不随本地
执行工具改名。只有面向用户的展示文字、操作日志和正文叙述使用本地工具名。

## 凭证读取（`.env`）

配置入口以 `tools/README.md` 的逐工具表为准：image/search 自动加载 Skill 根 `.env`；H3 从环境或 Skill 根 `.env` 读取指定配置键，环境优先，无 `--config`；TTS/S3 使用各自 KEY=VALUE 配置入口。image 的 `--config` 是后端 JSON，不能传 `.env`。凭证只在执行时读取，不写入项目、manifest、请求快照或 Prompt，不输出真实值。

## 冻结快照契约（`tools/video/h3.py`）

`h3.py` 不接收 gen.json 或 Prompt 路径参数，只按 `--episode/--segment` 读取 `video_manifest_ep_N.json` 段对象内的冻结快照 `request_snapshot` 与 `h3_prompt_file`；快照字段表、冻结命令与客观门只有一份，在 `references/video.md`「请求快照冻结与 stamp 写入面」节（`artifact_write` 条件自动路由，也可 `python scripts/read_reference.py --stage video --condition artifact_write` 读取）。本节只规定部署解析与保留字段合同：

- `workflow` / `base_url` 在快照缺省时依次取：环境 `H3_WORKFLOW` / `H3_BASE_URL` > Skill 根 `.env` 同名项 > `tools/video/h3.json.deployment`，解析结果在冻结时补进快照；执行只使用冻结值，不从环境临时补选。配置缺失、空值或无效时离线报出具体项。默认配置不等于已验证服务可用。
- `inputs[]` 按 `kind`（`image`/`video`/`audio`）分组成 `ref_<kind>_N` 槽位，**数组序即槽位序**；
  `mode` 是实际调用 `h3-prompt-writing` 返回的结果，不在此根据媒体种类派生；`duration_s` 与源分镜/成稿时间轴一致，为 4–15s 整数（区间读 `tools/video/h3.json` capabilities）。
- `options` 是 workflow 私有字段直通口（分辨率/时长档位名随 workflow 而异），
  保留键（prompt/duration/seed/resolution/媒体槽位等）不得通过 options 覆盖，冲突报错。
- `inputs[].path` 相对路径按**项目根**（显式 --project-root）解析；每个 SEG 的冻结请求就是段对象内一份 `request_snapshot`，不再有外部 gen 文件。

## 导演源信息与唯一模型 Prompt

当前段已确认分镜与导演卡直接作为 H3 编写依据；独立导演包仅按需补充。`h3_prompt_file` 是唯一提交文本，保持纯净；`compiled_prompt_file` 指向源导演卡或可选交付包。

`prepare_video.py` 一次派生登记并冻结真实请求与 Prompt SHA。视频确认只完整保存于用户确认台账，执行门和 lint 共享同源读取器，不读取其他格式的确认副本。

HTTP(S) 输入原样直传，仅绑定 URL 字符串；本地输入读取实际 bytes 并绑定指纹。参数、Prompt 或本地输入变化重新确认。正常执行直接使用准备和生成命令，无额外 dry-run 或 check-only；这些只用于定位具体问题。

h3.py 在提交后立即保存 task_id，支持 --submit-only、--resume 与同命令恢复；自动下载、可解码检查和 candidate 登记。任务中断按原任务恢复，不凭等待超时重复提交。

## 用户可见模型名

- 生图模型：**gpt-image（知脑中转）**。本地无「会员模型」分层，参数确认表不再出现
  会员/额度提示；`drama_plan.json` 与 manifest 中生图模型字段写 `gpt-image`。
- 视频模型：**MiniMax H3**。能力档案以 `tools/video/h3.json` 为准：单段 4–15 秒读
  `capabilities`，各模式参考数量、单文件/总时长读 `mode_ref_limits`，不保留旧模型特例；
  各模式首帧/尾帧语义以 `h3-prompt-writing` 的模式指南为准；拼接统一 24fps 由 ffmpeg 链路固定。
- SEG 单段时长沿用 `tools/video/h3.json` capabilities 的 4–15 秒整数区间，上下限与整数约束均以能力档案为准。

## interaction.ask → AskUserQuestion 的执行约定

原文档三类确认（`proceed_project` / `generate` / `proceed_assembly`）与唯一素材
询问例外全部以 AskUserQuestion 执行，问题与选项文案结构不变。确认记录由
`stamp_confirmation.py` 写入 `用户确认记录.jsonl`，字段沿用原 schema；
`interaction_ask_call_id` 由命令按本地约定值 `auq-<UTC ISO8601 时间戳>`
（如 `auq-2026-10-15T08:30:00Z`）自动生成，保证非空且唯一，lint 校验逻辑不变。

## 画风候选卡

呈现形态门是项目级根决策：用户种子未含呈现形态（真人/动画/漫剧等）时，规划必须先按 `planning.md`「呈现形态门与画风候选卡」让用户选定形态，再出全套方案；形态内的画风候选有决策价值才提供，无固定数量门，不让生成确认兼任选择。用户修改方案后更新绑定、重预检并重新确认。

## 画布与交付的本地语义

- 每个图片/视频产物保存后检查文件存在、大小非零、可被 ffprobe/图片解码，并在对话给出相对路径；完成这些动作才算交付展示。
- 技术可打开不代表已完成看图、试听或观看顺序内容审查；按各阶段 Ref 执行。
- manifest 中 workspace/canvas 字段留空。

**落盘检查**：产物已写入项目目录对应位置、文件存在且大小非零、可被 ffprobe/图片解码器打开（视频另含可渲染视频流检查），并在对话中给出相对路径。通过即视为完成展示与回读；未通过不得继续下一个生成任务、不得宣布已交付。

## 操作日志用语

操作日志登记媒体处理动作时写本地工具名（如 `ffmpeg_tool concat`），不再出现
mediakit 字样；lint 的禁用词为 `text_to_image`（正确工具名是 `img`）。
