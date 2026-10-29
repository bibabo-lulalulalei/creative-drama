# lint 检查合同 · script 阶段

> 本卡片由 `scripts/build_lint_contract.py` 从 `drama_lint.py` 机读生成，禁止手改。
> 用途：开工前读这张卡知道本阶段 lint 会查什么；报错后按码查修复方向。
> 与源码不一致时以源码为准，并重跑 `python scripts/build_lint_contract.py --check`。

本阶段新增检查项：0。运行命令：`python scripts/drama_lint.py --stage script`（skill 阶段在 skill 根目录运行）。

本阶段同时全量复核以下上游检查（报错时先读对应上游卡）：
- planning 阶段卡 · `check_stage_artifacts` —— script 阶段产物存在性
- planning 阶段卡 · `check_episode_manifest_ids` —— episode_manifest 与 stage 绑定

| 检查码 | 级别 | 查什么（源码原文消息） |
|---|---|---|
