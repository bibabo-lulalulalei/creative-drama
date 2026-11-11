#!/usr/bin/env python3
"""Route and read reference sections without making the model read the route table."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROFILE_NAMES = {"full", "repair"}
# lint 阶段枚举使用 final，成片路由键为 delivery；别名只在此处归一。
STAGE_ALIASES = {"final": "delivery"}


class ReferenceError(ValueError):
    """A caller supplied path, stage, mode, condition or heading is invalid."""


def load_map(root: Path = ROOT) -> dict[str, Any]:
    try:
        data = json.loads((root / "references" / "reference_map.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReferenceError(f"无法读取 reference_map.json：{exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("stages"), dict):
        raise ReferenceError("reference_map.json 缺少 stages 对象")
    return data


def _safe_reference_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ReferenceError("文件路径不能为空")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != "references":
        raise ReferenceError("只能读取 references/ 下的相对路径")
    target = (root / relative).resolve()
    try:
        target.relative_to((root / "references").resolve())
    except ValueError as exc:
        raise ReferenceError("文件路径越出 references/") from exc
    if not target.is_file():
        raise ReferenceError(f"文件不存在：{value}")
    return target


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def full_tier_files(root: Path = ROOT) -> set[str]:
    """Files legitimately read whole: only files listed in some stage's full tier."""
    data = load_map(root)
    return {
        path
        for spec in data["stages"].values()
        for path in _as_list(spec.get("full"))
    }


def _section_entries(spec: dict[str, Any]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path, headings in (spec.get("sections") or {}).items():
        if not isinstance(path, str) or not isinstance(headings, list):
            continue
        for heading in headings:
            if isinstance(heading, str):
                entries.append({"file": path, "section": heading})
    return entries


def _condition_entries(spec: dict[str, Any], conditions: list[str]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    conditional = spec.get("conditional") or {}
    for condition in conditions:
        group = conditional.get(condition)
        if group is None:
            raise ReferenceError(f"条件 {condition!r} 不存在；可选值：{', '.join(sorted(conditional)) or '无'}")
        if not isinstance(group, dict):
            continue
        entries.extend(_section_entries({"sections": group}))
    return entries


def resolve_route(
    stage: str,
    mode: str = "full",
    conditions: list[str] | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Return all navigation without prose."""
    data = load_map(root)
    stages = data["stages"]
    stage = STAGE_ALIASES.get(stage, stage)
    if stage not in stages:
        available = ", ".join(sorted([*sorted(stages), *sorted(STAGE_ALIASES)]))
        raise ReferenceError(f"阶段 {stage!r} 不存在；可选值：{available}")
    if mode not in PROFILE_NAMES:
        raise ReferenceError(f"模式必须是 full 或 repair：{mode}")

    if mode == "full":
        spec = stages[stage]
        selected_conditions = list(conditions or [])
        source_stage = stage
    elif stage == "repair":
        # repair 是独立路由页，不对应具体生产阶段。
        spec = stages["repair"]
        selected_conditions = list(conditions or [])
        source_stage = "repair"
    else:
        source_stage = "repair"
        spec = stages["repair"]
        selected_conditions = list(conditions or [])
        if not any(condition.startswith("affected_") for condition in selected_conditions):
            default_condition = f"affected_{stage}"
            if default_condition in (spec.get("conditional") or {}):
                selected_conditions.insert(0, default_condition)

    full = [{"file": path, "kind": "full"} for path in _as_list(spec.get("full"))]
    sections = _section_entries(spec)
    conditional = _condition_entries(spec, selected_conditions)
    # 治理包等条件可能与章节入口指向同一锚点（如 governance_reload）：
    # 同一锚点在一次路由结果中只出现一次，章节入口优先。
    section_keys = {(item["file"], item["section"]) for item in sections}
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for item in conditional:
        key = (item["file"], item["section"])
        if key in section_keys or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    conditional = deduped
    available_conditions = {
        condition: {
            "trigger": (spec.get("condition_triggers") or {}).get(condition, ""),
            "sections": _section_entries({"sections": group}),
        }
        for condition, group in (spec.get("conditional") or {}).items()
        if isinstance(group, dict)
    }
    all_files = sorted({item["file"] for item in [*full, *sections, *conditional]})
    for path in all_files:
        _safe_reference_path(root, path)
    result = {
        "stage": stage,
        "mode": mode,
        "source_map_entry": source_stage,
        "conditions": selected_conditions,
        "full": full,
        "section_count": len(sections),
        "sections": sections,
        "available_conditions": available_conditions,
        "conditional_sections": conditional,
        "files": all_files,
    }
    return result


def render_route(
    stage: str,
    mode: str = "full",
    conditions: list[str] | None = None,
    *,
    include_full: bool = False,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Resolve the route and return required subtree bodies.

    无条件：一次取齐阶段 sections 子树。带条件（full 模式）：只返回条件增量
    子树——阶段基线已在入口装载，条件调用不重复计费；repair 模式基线仅 90 秒
    恢复一节，仍与 affected_* 合并返回。full 动作合同仅在 include_full 时整读。
    """
    route = resolve_route(stage, mode, conditions, root)
    condition_only = bool(route["conditions"]) and mode == "full"
    entries: list[dict[str, Any]] = []
    if include_full:
        for item in route["full"]:
            path = item["file"]
            target = _safe_reference_path(root, path)
            content = target.read_text(encoding="utf-8")
            entries.append({
                "file": path,
                "section": None,
                "start_line": 1,
                "end_line": len(content.splitlines()),
                "content": content,
            })
    if condition_only:
        # 条件单发返回该条件声明的完整子树集合（含与基线重叠的锚点，如
        # governance_reload），只在条件集合内部去重；不再套用基线去重。
        spec = load_map(root)["stages"][route["stage"]]
        picked = _condition_entries(spec, route["conditions"])
    else:
        picked = [*route["sections"], *route["conditional_sections"]]
    seen: set[tuple[str, str]] = set()
    for item in picked:
        key = (item["file"], item["section"])
        if key in seen:
            continue
        seen.add(key)
        extracted = extract_section(item["file"], item["section"], root)
        entries.append({
            "file": extracted["file"],
            "section": item["section"],
            "start_line": extracted["start_line"],
            "end_line": extracted["end_line"],
            "content": extracted["content"],
        })
    # A parent section already contains its descendants verbatim. A full-file
    # action contract similarly contains every selected section in that file.
    # Deduplicate by actual source ranges, including a parent selected later,
    # while preserving every word of the retained teaching subtree.
    entries = [entry for index, entry in enumerate(entries) if not any(
        other["file"] == entry["file"]
        and other["start_line"] <= entry["start_line"]
        and other["end_line"] >= entry["end_line"]
        and ((other["start_line"], other["end_line"]) != (entry["start_line"], entry["end_line"])
             or other_index < index)
        for other_index, other in enumerate(entries)
    )]
    return {
        "stage": route["stage"],
        "mode": mode,
        "conditions": route["conditions"],
        "condition_only": condition_only,
        "include_full": include_full,
        "entry_count": len(entries),
        "entries": entries,
    }


def format_rendered(payload: dict[str, Any]) -> str:
    """Human-readable rendering: one block per file/section with line locators."""
    lines = [f"# Rendered sections · {payload['stage']} ({payload['mode']})", ""]
    if payload.get("condition_only"):
        lines.append(f"conditions-only: {', '.join(payload['conditions'])}（仅条件增量子树；阶段基线用不带 --condition 的 --render 另取）")
        lines.append("")
    elif payload["conditions"]:
        lines.append(f"conditions: {', '.join(payload['conditions'])}")
        lines.append("")
    current: str | None = None
    for entry in payload["entries"]:
        if entry["file"] != current:
            current = entry["file"]
            lines.extend([f"## {current}", ""])
        if entry["section"]:
            lines.append(f"### L{entry['start_line']}-{entry['end_line']} {entry['section']}")
            lines.append("")
        lines.append(entry["content"].rstrip("\n"))
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def _markdown_headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """Find ATX headings outside backtick and tilde fenced code blocks."""
    headings: list[tuple[int, int, str]] = []
    fence: str | None = None
    for number, line in enumerate(lines):
        text = line.rstrip("\r\n")
        if fence is not None:
            closing = re.match(r"^ {0,3}(`{3,}|~{3,})[ \t]*$", text)
            if closing and closing[1][0] == fence[0] and len(closing[1]) >= len(fence):
                fence = None
            continue
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", text)
        if opening and not (opening[1][0] == "`" and "`" in opening[2]):
            fence = opening[1]
            continue
        match = re.match(r"^ {0,3}(#{1,6})[ \t]+(.+?)\s*$", text)
        if match:
            headings.append((number, len(match[1]), match[2].strip()))
    return headings


def extract_section(path: str, heading: str, root: Path = ROOT) -> dict[str, Any]:
    """Return one complete Markdown heading subtree, including nested headings."""
    target = _safe_reference_path(root, path)
    wanted = heading.strip()
    if not wanted:
        raise ReferenceError("章节标题不能为空")
    lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    headings = _markdown_headings(lines)
    explicit = re.fullmatch(r"(#{1,6})[ \t]+(.+)", wanted)
    if explicit:
        matches = [
            (number, level)
            for number, level, title in headings
            if level == len(explicit[1]) and title == explicit[2].strip()
        ]
    else:
        matches = [(number, level) for number, level, title in headings if title == wanted]
    if not matches:
        raise ReferenceError(f"在 {path} 中找不到章节：{heading}")
    if len(matches) != 1:
        hint = "请使用唯一的同级标题" if explicit else "请使用带层级的完整标题"
        raise ReferenceError(f"章节标题在 {path} 中命中 {len(matches)} 次，{hint}")
    start, level = matches[0]
    end = len(lines)
    for number, next_level, _title in headings:
        if number > start and next_level <= level:
            end = number
            break
    return {
        "file": path,
        "section": lines[start].strip(),
        "start_line": start + 1,
        "end_line": end,
        "content": "".join(lines[start:end]),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", help="查询阶段路由")
    parser.add_argument("--mode", choices=sorted(PROFILE_NAMES), default="full")
    parser.add_argument("--condition", action="append", default=[], help="补读一个条件，可重复")
    parser.add_argument("--file", help="读取 references/ 下的 Markdown（裸读仅限 map 的 full 动作合同）")
    parser.add_argument("--section", help="与 --file 一起使用，读取一个完整标题子树（常规读取方式）")
    parser.add_argument("--render", action="store_true",
                        help="一次输出本阶段全部必读章节子树正文（含已给 --condition），不要为装载必读章节整文件 Read")
    parser.add_argument("--include-full", action="store_true",
                        help="与 --render 一起使用：同时整读 full 动作合同（仅在对应动作触发时）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出路由或章节结果")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.file:
            if args.stage or args.condition or args.mode != "full" or args.render or args.include_full:
                raise ReferenceError("--file 模式不能和 --stage/--mode/--condition/--render 混用")
            if args.section:
                result: Any = extract_section(args.file, args.section)
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print(f"{result['file']}:{result['start_line']}-{result['end_line']} {result['section']}")
                    print(result["content"], end="" if result["content"].endswith("\n") else "\n")
            else:
                path = _safe_reference_path(ROOT, args.file)
                if args.file not in full_tier_files():
                    raise ReferenceError(
                        f"{args.file} 不是 full 动作合同，禁止整文件读取："
                        "加 --section 取标题子树，或用 --stage <stage> --render 取阶段必读"
                    )
                content = path.read_text(encoding="utf-8")
                if args.json:
                    print(json.dumps({"file": args.file, "content": content}, ensure_ascii=False))
                else:
                    print(content, end="" if content.endswith("\n") else "\n")
            return 0
        if not args.stage:
            raise ReferenceError("请提供 --stage，或使用 --file --section")
        if args.include_full and not args.render:
            raise ReferenceError("--include-full 只能与 --render 一起使用")
        if args.render:
            payload = render_route(
                args.stage, args.mode, args.condition, include_full=args.include_full
            )
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(format_rendered(payload), end="")
            return 0
        result = resolve_route(args.stage, args.mode, args.condition)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ReferenceError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    # Windows 管道默认 GBK，不重配会让中文路由/章节输出在模型侧变成乱码。
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
