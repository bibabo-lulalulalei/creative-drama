# Reference 读取入口

先按当前任务选择阶段和模式，再读取对应的阶段路由；不要为了选择章节全文读取 `reference_map.json`。

```bash
python scripts/read_reference.py --stage storyboard --mode full
python scripts/read_reference.py --stage video --mode full
python scripts/read_reference.py --stage storyboard --mode repair
python scripts/read_reference.py --stage assets --mode full --condition collective_cast
python scripts/read_reference.py --file references/storyboard.md --section "## 运镜与镜头差异化"
```

阶段查询默认返回章节锚点、可选条件及其触发说明，不复制 Reference 正文。正式执行阶段制作前，必须读取该阶段章节入口中的原始依据，已读且未变化的章节可复用；`full` 中的文件在对应动作触发时必须读，不要求阶段开始一次性读入所有动作合同。局部审阅与返修按当前问题补齐最早受影响阶段的原始方法和必要依赖，不能把修复路由当作原始教学的替代。

使用 `--file --section` 返回该标题、真实起止行及嵌套子节的完整原文；任务确实需要时，可以读取完整目标文件。创作方法的小型入口在 `creative-index.md`，必须按实际创作动作读取其中指向的原始章节。

八个阶段路由页由 `python scripts/build_reference_index.py` 从 `reference_map.json` 生成，修改路由后重新生成；`python scripts/build_reference_index.py --check` 检查页面漂移。机器路由和页面只维护定位与触发，不复制教学合同。

| 阶段 | 路由重点 |
|---|---|
| planning | `stage-index/planning.md` |
| script | `stage-index/script.md` |
| assets | `stage-index/assets.md` |
| storyboard | `stage-index/storyboard.md` |
| keyframes | `stage-index/keyframes.md` |
| video | `stage-index/video.md` |
| delivery | `stage-index/delivery.md` |
| repair | `stage-index/repair.md` |

创作方法仍以原始 Reference 为准；路由页和 lint 导航只负责定位，不能替代原始教学章节。
