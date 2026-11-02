#!/usr/bin/env python3
"""Generate small stage navigation pages from the authoritative reference map."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _section_lines(sections: dict[str, list[str]], *, compact: bool = False) -> list[str]:
    lines: list[str] = []
    for path, headings in sections.items():
        if compact:
            lines.append(f"  - `{path}`：" + "、".join(f"`{heading}`" for heading in headings))
        else:
            lines.append(f"- `{path}`")
            lines.extend(f"  - `{heading}`" for heading in headings)
    return lines


def render_stage(stage: str, spec: dict[str, Any]) -> str:
    mode = stage if stage == "repair" else "full"
    query = f"python scripts/read_reference.py --stage {stage} --mode {mode}"
    lines = [
        f"# Reference 路由 · {stage}",
        "",
        "> 由 `scripts/build_reference_index.py` 从 `references/reference_map.json` 生成；修改索引后重新生成。",
        "",
        f"查询：`{query}`。",
        "",
        "正式制作当前阶段前，下列章节是必读依据；局部审阅或修订按当前问题补齐最早受影响阶段的原始方法和必要依赖。同一任务中已读且未变的章节可复用，只补新增或变化的依赖。不要预读无关阶段。路由用于定位，原始教学与合同必须实际加载。",
        "",
        "按标题提取会返回完整章节子树及起止行；理解任务需要时可读取完整目标文件与依赖，不设置读取行数、字节或结果数量上限。",
        "",
    ]
    if stage == "repair":
        lines.extend([
            "返修先定位最早受影响阶段，命中对应 `affected_*` 后补齐该阶段原始创作方法和必要依赖，再修订与审校；修复摘要不能替代原始教学。",
            "",
        ])
    if spec.get("full"):
        lines.extend([
            "## 动作合同（触发时必读）",
            "",
            "`full` 文件在其对应动作触发时必须读取；按当前动作定位合同，不要求阶段开始时一次性加载所有文件。",
            "",
        ])
        lines.extend(f"- `{path}`" for path in spec["full"])
        lines.append("")
    if spec.get("sections"):
        lines.extend(["## 章节入口", ""])
        lines.extend(_section_lines(spec["sections"]))
        lines.append("")
    if spec.get("conditional"):
        lines.extend(["## 条件入口", "", "条件命中时必须补读对应章节；无法判断时核对当前任务与上游事实，不把条件当作可跳过必要方法的选项。", ""])
        triggers = spec.get("condition_triggers") or {}
        for condition, sections in spec["conditional"].items():
            trigger = triggers.get(condition, "当前任务涉及该条件时补读以下章节。")
            lines.extend([
                f"- `{condition}`：{trigger}",
                f"  - 查询：`{query} --condition {condition}`。",
            ])
            lines.extend(_section_lines(sections, compact=True))
        lines.append("")
    return "\n".join(lines)


def build(root: Path = ROOT) -> dict[str, str]:
    data = json.loads((root / "references" / "reference_map.json").read_text(encoding="utf-8"))
    stages = data.get("stages")
    if not isinstance(stages, dict) or not stages:
        raise ValueError("reference_map.json 缺少 stages 对象")
    pages: dict[str, str] = {}
    for stage, spec in stages.items():
        if not isinstance(stage, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", stage):
            raise ValueError(f"无效阶段名称：{stage!r}")
        if not isinstance(spec, dict):
            raise ValueError(f"阶段 {stage} 必须是对象")
        pages[f"{stage}.md"] = render_stage(stage, spec)
    return pages


def check(root: Path, pages: dict[str, str]) -> list[str]:
    directory = root / "references" / "stage-index"
    drift = []
    for name, content in pages.items():
        target = directory / name
        if not target.is_file():
            drift.append(f"missing: references/stage-index/{name}")
        elif target.read_text(encoding="utf-8") != content:
            drift.append(f"changed: references/stage-index/{name}")
    drift.extend(
        f"obsolete: references/stage-index/{target.name}"
        for target in sorted(directory.glob("*.md"))
        if target.name not in pages
    )
    return drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="检查缺失、内容漂移和过时路由页，不写文件")
    args = parser.parse_args(argv)
    try:
        pages = build(ROOT)
        if args.check:
            drift = check(ROOT, pages)
            print(json.dumps({"ok": not drift, "drift": drift}, ensure_ascii=False))
            return int(bool(drift))
        directory = ROOT / "references" / "stage-index"
        directory.mkdir(parents=True, exist_ok=True)
        for name, content in pages.items():
            target = directory / name
            if not target.is_file() or target.read_text(encoding="utf-8") != content:
                target.write_text(content, encoding="utf-8", newline="\n")
        drift = check(ROOT, pages)
        print(json.dumps({"ok": not drift, "generated_count": len(pages), "drift": drift}, ensure_ascii=False))
        return int(bool(drift))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
