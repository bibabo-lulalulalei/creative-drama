# 视频批次参数与五列分镜确认

## 准备与展示

`prepare_video.py` 从当前段分镜、真实输入和冻结请求生成一份确认证据 JSON 及可直接展示的文本。展示原样使用工具返回的一张参数表和一张五列分镜表；不再由模型重复抄写结构化副本、哈希或台账。

参数表包含任务、交付格式、数量、逐段/总时长、画幅与分辨率、模型、视觉与连续性、声音与字幕、实际参考素材。五列表每 SEG 一行：片段与时长、画面内容、画面过程、声音与完整台词、摄影过程与素材。台词逐字保留，内容只来自当前段已确认分镜；不存在的素材不写成已输入。

## 批次边界

一次确认覆盖当前集连续 1–2 个输入就绪且已冻结的 SEG。默认单段准备；两个独立就绪片段可以合批。依赖未知前段尾帧的 continuous 后段另起下一批，不能预先冻结或授权未知输入。

两个独立段分别准备后，运行 `python scripts/prepare_video.py --project-root <根> --episode ep_N --segment SEG001,SEG002 --combine-evidence`，工具校验两段仍与准备时一致并生成合并两表及一份证据。原样展示其文本，一次确认后用该证据和 `--segments SEG001,SEG002` 登记；不手工拼 JSON。

展示后按 `interaction-ask-video-clarification-ref.md` 取得当前 `generate`。一批只问一次；用户同意后直接登记并执行。数量、时长、模型、画幅、台词、成稿或素材发生变化时重新准备并确认；已确认且未变的参数不额外询问。

## 记录与校验

确认后运行 `stamp_confirmation.py --stage video --video --evidence-file <准备工具返回的JSON> --segments <SEG> --confirmation-id <ID> --user-message <实际回复> --append`，并提供项目根、episode 与 revision。

完整记录只写 `00_制作控制/用户确认记录.jsonl`。工具自动派生快照摘要、数量、范围、时长、attempt 和授权绑定；执行门与 lint 只读这一份记录。重生保留本流程的历次确认，命令自动计算并记录被替代的确认；`--supersedes` 仅在需要显式核对时填写。

写入命令内部完成校验、原子写入和回读，正常执行直接加 `--append`；不要求先运行一遍 dry-run。出现具体错误才定点查看对应合同。
