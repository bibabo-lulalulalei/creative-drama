# Reference 读取入口

进入阶段先读对应的阶段路由页，再按其中的文件和标题读取原始章节；不要为选章节通读 `reference_map.json`。

| 阶段 | 路由页 |
|---|---|
| planning | `stage-index/planning.md` |
| script | `stage-index/script.md` |
| assets | `stage-index/assets.md` |
| storyboard | `stage-index/storyboard.md` |
| keyframes | `stage-index/keyframes.md` |
| video | `stage-index/video.md` |
| delivery | `stage-index/delivery.md` |
| repair | `stage-index/repair.md` |

```bash
python scripts/read_reference.py --stage storyboard --mode full
python scripts/read_reference.py --file references/storyboard.md --section "## 运镜与镜头差异化"
```

读取协议（章节必读、动作触发、条件补读、返修、压缩恢复）统一见 `SKILL.md`「Reference 读取协议」；创作方法小入口见 `creative-index.md`。路由页只负责定位，不替代原始教学。
