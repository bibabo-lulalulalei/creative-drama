#!/usr/bin/env python3
"""Summarize context events and reference route sizes without reading project prose."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any

# python -I（隔离模式）不把脚本目录加入 sys.path，入口必须先自举再走两种导入姿势。
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from scripts import read_reference
except ImportError:  # direct ``python scripts/context_audit.py`` execution
    import read_reference


DEFAULT_TOOL_RESULT_LIMIT = 10_000


def read_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"事件日志第 {line_number} 行不是有效 JSON：{exc}") from exc
        if isinstance(value, dict):
            events.append(value)
    return events


def summarize_events(events: list[dict[str, Any]], tool_limit: int = DEFAULT_TOOL_RESULT_LIMIT) -> dict[str, Any]:
    reference_events = [event for event in events if event.get("kind") == "reference"]
    returned = [event for event in reference_events if event.get("status") == "returned"]
    duplicate_groups: dict[tuple[str, str | None, str], int] = defaultdict(int)
    for event in returned:
        duplicate_groups[(str(event.get("file", "")), event.get("section"), str(event.get("sha256", "")))] += 1
    duplicates = [
        {"file": file_name, "section": section, "sha256": sha, "count": count}
        for (file_name, section, sha), count in duplicate_groups.items()
        if count > 1
    ]
    tool_results = [event for event in events if event.get("kind") == "tool_result"]
    lint_sources = [event for event in events if event.get("kind") == "lint_source"]
    project_reads = [event for event in events if event.get("kind") == "project_read"]
    return {
        "event_count": len(events),
        "observed_kinds": dict(Counter(str(event.get("kind", "unknown")) for event in events)),
        "unobserved_kinds": [kind for kind in ("reference", "project_read", "lint_source", "tool_result")
                             if not any(event.get("kind") == kind for event in events)],
        "reference": {
            "returned_count": len(returned),
            "skipped_count": sum(1 for event in reference_events if event.get("status") == "skipped"),
            "returned_chars": sum(int(event.get("chars", 0) or 0) for event in returned),
            "duplicate_groups": duplicates,
        },
        "project": {
            "read_count": len(project_reads),
            "full_read_count": sum(1 for event in project_reads if event.get("full")),
        },
        "lint_source_read_count": len(lint_sources),
        "tool_results": {
            "count": len(tool_results),
            "over_limit_count": sum(1 for event in tool_results if int(event.get("chars", 0) or 0) > tool_limit),
            "max_chars": max((int(event.get("chars", 0) or 0) for event in tool_results), default=0),
        },
    }


def route_sizes(stages: list[str], mode: str) -> list[dict[str, Any]]:
    result = []
    for stage in stages:
        payload = read_reference.render_route(stage, mode)
        result.append({
            "stage": stage,
            "mode": mode,
            "chars": sum(len(entry["content"]) for entry in payload["entries"]),
            "entries": payload["entry_count"],
        })
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, help="上下文事件 JSONL")
    parser.add_argument("--stage", action="append", dest="stages", help="追加一个阶段路由体积检查")
    parser.add_argument("--mode", choices=("full", "repair"), default="full")
    parser.add_argument("--tool-limit", type=int, default=DEFAULT_TOOL_RESULT_LIMIT)
    parser.add_argument("--json", action="store_true", help="输出 JSON；默认也是 JSON，保留参数便于脚本调用")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.tool_limit < 1:
            raise ValueError("--tool-limit 必须为正数")
        events = read_events(args.events) if args.events else []
        observation_status = ("not_requested" if args.events is None else
                              "missing" if not args.events.exists() else
                              "recorded" if events else "empty")
        payload: dict[str, Any] = {
            "observation": {
                "status": observation_status,
                "events_path": str(args.events) if args.events else None,
                "scope": "instrumented CLI outputs only; direct Read and other host tools are not measured",
            },
            "events": summarize_events(events, args.tool_limit),
            "routes": route_sizes(args.stages, args.mode) if args.stages else [],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
