# lint 合同导航

阶段导航卡与阶段规则卡只说明检查码、级别和源码位置，不替代导演教学；卡片不证明内容可拍或审美合格。压缩恢复协议见 `../recovery.md`。

| 文件 | 何时读 |
|---|---|
| `common.md` 与 `<stage>.md`（阶段导航卡） | 阶段开始的客观检查入口；报错后按码查完整规则 |
| `rules/<stage>.md`（阶段规则卡） | 该阶段检查码、级别、说明和源码位置；按需排错。`rules/final.md` 是增量卡（仅成片自有检查），完整联合视图用 `--rules final` 动态获取 |
| `source-index.md` | 维护校验器时选择模块；函数起止行用 `--module`/`--symbol` 现场查询，不落盘快照 |
| `manifest.json` | 仅供生成器核对；运行 `--check` 获取结果 |

`scripts/drama_lint.py` 保留原命令入口，具体规则按职责放在 `scripts/lint_checks/`。常规创作只读阶段导航卡与所需原始 Ref；维护或排查校验器时，先查询所需位置：

```bash
python scripts/build_lint_contract.py --code file_missing
python scripts/build_lint_contract.py --symbol check_assets
python scripts/build_lint_contract.py --stage video
python scripts/build_lint_contract.py --module assets
python scripts/build_lint_contract.py --rules final
```

查询由程序在进程内解析源码，返回匹配的文件、函数和行范围；`--code` 同时返回完整检查码、级别和规则说明，动态检查码也按源码中的实际有限取值定位，不执行被解析源码。新增无法解析的动态模板会明确报错，避免静默丢失索引。`--offset`、`--limit` 可在结果较多时主动分页，也可以直接读取定位到的完整目标模块。`rules/<stage>.md` 阶段规则卡保留该阶段规则，需要整体理解时可以完整读取，不必为排查单个检查码加载整张阶段规则卡；`--rules <stage>` 直接 stdout 输出该阶段完整规则联合视图（含共享检查），静态 `rules/final.md` 因此只列成片自有检查。

`line` / `end_line` 是函数范围，`issue_line` 是检查码产生位置。先按定位读取相关函数、模块和依赖；为了完整理解一个目标可以读取完整文件，不需要把固定行数限制当作规则。避免无目的地预读全部 lint 源码或所有阶段导航卡/阶段规则卡。

阶段导航卡、模块导航和阶段规则卡由 AST 与实际 `STAGE_CHECKS` 生成；函数起止行不做静态快照，统一由 `--module`/`--symbol` 现场返回。修改检查或移动函数后运行 `python scripts/build_lint_contract.py` 更新；`--check` 核对内容与行号是否漂移。这里不保存包含全部错误码定位的大 JSON 字典。
