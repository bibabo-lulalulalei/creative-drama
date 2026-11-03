#!/usr/bin/env python3
"""Render stage navigation pages from the authoritative reference map (stdout only)."""

from __future__ import annotations

import argparse
import json
import re
import sys
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
    render_query = f"python scripts/read_reference.py --stage {stage} --mode {mode} --render"
    lines = [
        f"# Reference 路由 · {stage}",
        "",
        "> 由 `scripts/build_reference_index.py --stdout` 从 `references/reference_map.json` 现场生成，不入库；修改索引后下次查询自动生效。",
        "",
        f"取本阶段必读正文（推荐，一次取齐下方全部章节子树）：`{render_query}`；命中条件时追加 `--condition <条件> --render`，可重复。",
        f"只查路由锚点（导航 JSON）：`{query}`。",
        "",
        "章节入口为阶段开始必读，用 `--render` 取正文，不要为装载必读章节整文件 Read（任务确实依赖章节子树之外的全文时除外）；动作合同在对应动作触发时用 `--file` 整读；条件入口命中时必须补读。已读未变章节可复用，不预读无关阶段。读取总协议见 `SKILL.md`。",
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
        base_keys = {
            (path, heading)
            for path, headings in (spec.get("sections") or {}).items()
            for heading in headings
        }
        for condition, sections in spec["conditional"].items():
            trigger = triggers.get(condition, "当前任务涉及该条件时补读以下章节。")
            lines.extend([
                f"- `{condition}`：{trigger}",
                f"  - 补读正文：`{render_query} --condition {condition}`；只查锚点：`{query} --condition {condition}`。",
            ])
            extra = {
                path: [heading for heading in headings if (path, heading) not in base_keys]
                for path, headings in sections.items()
            }
            extra = {path: headings for path, headings in extra.items() if headings}
            if extra:
                lines.extend(_section_lines(extra, compact=True))
            else:
                lines.append("  - 锚点均已在上方「章节入口」装载，条件查询时不重复返回。")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdout", action="store_true",
                        help="把指定阶段路由页渲染到 stdout（路由页已改为现场生成，不入库）")
    parser.add_argument("--stage", help="配合 --stdout：阶段名（如 planning、repair）")
    args = parser.parse_args(argv)
    try:
        if not args.stdout or not args.stage:
            parser.error("路由页现场生成不入库：使用 --stdout --stage <stage>")
        pages = build(ROOT)
        name = f"{args.stage}.md"
        if name not in pages:
            parser.error(f"未知阶段 {args.stage!r}；可选：{sorted(Path(item).stem for item in pages)}")
        sys.stdout.write(pages[name])
        return 0
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
