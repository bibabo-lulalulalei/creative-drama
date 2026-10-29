#!/usr/bin/env python3
"""Build a complete, bounded stage-specific Ref packet without silent truncation."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "references/reference_map.json"
DEFAULT_BUDGET_CHARS = 120000


def force_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def section(text: str, anchor: str, path: str) -> str:
    lines = text.splitlines()
    headings: list[tuple[int, str]] = []
    fence_char: str | None = None
    fence_length = 0
    for i, line in enumerate(lines):
        if fence_char is not None:
            closing = re.match(r"^\s{0,3}(`{3,}|~{3,})[ \t]*$", line)
            if closing and closing.group(1)[0] == fence_char and len(closing.group(1)) >= fence_length:
                fence_char = None
                fence_length = 0
            continue
        opening = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if opening:
            fence_char = opening.group(1)[0]
            fence_length = len(opening.group(1))
            continue
        if re.match(r"^#{1,6}\s", line):
            headings.append((i, line.strip()))
    starts = [i for i, heading in headings if heading == anchor]
    if len(starts) != 1:
        raise ValueError(f"{path}: 章节锚点 {anchor!r} 命中 {len(starts)} 次，要求恰好一次")
    start = starts[0]
    level = len(anchor) - len(anchor.lstrip("#"))
    end = len(lines)
    for i, heading in headings:
        if i <= start:
            continue
        match = re.match(r"^(#{1,6})\s", heading)
        if match and len(match.group(1)) <= level:
            end = i
            break
    return "\n".join(lines[start:end]).rstrip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--condition", action="append", default=[], help="显式命中的条件键，可重复")
    ap.add_argument("--task", default="")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_BUDGET_CHARS)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()
    try:
        mapping = json.loads(MAP.read_text(encoding="utf-8"))
        if args.stage not in mapping["stages"]:
            raise ValueError(f"未知阶段 {args.stage!r}；可选：{', '.join(mapping['stages'])}")
        spec = mapping["stages"][args.stage]
        blocks: list[str] = []
        sources: dict[str, str] = {}
        loaded: set[str] = set()

        def read_file(rel: str) -> str:
            path = (ROOT / rel).resolve()
            if ROOT.resolve() not in path.parents or not path.is_file():
                raise ValueError(f"必需 Ref 不存在或越界：{rel}")
            text = path.read_text(encoding="utf-8")
            sources[rel] = sha(text)
            loaded.add(rel)
            return text

        for rel in spec.get("full", []):
            text = read_file(rel)
            blocks.append(f"<!-- source: {rel} [full] -->\n\n{text}")
        for rel, anchors in spec.get("sections", {}).items():
            text = read_file(rel)
            for anchor in anchors:
                blocks.append(f"<!-- source: {rel} [{anchor}] -->\n\n{section(text, anchor, rel)}")
        conditions = set(args.condition)
        for key in conditions:
            if key not in spec.get("conditional", {}):
                raise ValueError(f"阶段 {args.stage} 没有条件章节 {key!r}；不可静默忽略")
            conditional = spec["conditional"][key]
            if isinstance(conditional, list):
                conditional = {rel: None for rel in conditional}
            if not isinstance(conditional, dict):
                raise ValueError(f"条件章节 {key!r} 必须是文件列表或文件到章节锚点的映射")
            for rel, anchors in conditional.items():
                text = read_file(rel)
                if rel in spec.get("full", []):
                    continue
                if anchors is None:
                    blocks.append(f"<!-- source: {rel} [conditional:{key}, full] -->\n\n{text}")
                elif isinstance(anchors, list) and anchors:
                    for anchor in anchors:
                        blocks.append(f"<!-- source: {rel} [conditional:{key}, {anchor}] -->\n\n{section(text, anchor, rel)}")
                else:
                    raise ValueError(f"条件章节 {key!r} 的 {rel} 必须配置非空锚点数组")
        body = "\n\n---\n\n".join(blocks)
        if len(body) > args.max_chars:
            contributors = sorted(((len(b), b.splitlines()[0]) for b in blocks), reverse=True)
            raise ValueError(f"阅读包 {len(body)} 字符超过预算 {args.max_chars}；未截断。最大章节：{contributors[:8]}")
        manifest = {
            "schema_version": 1,
            "stage": args.stage,
            "task": args.task,
            "conditions": sorted(conditions),
            "required_items": len(spec.get("full", [])) + sum(len(v) for v in spec.get("sections", {}).values()),
            "loaded_files": sorted(loaded),
            "source_sha256": sources,
            "packet_sha256": sha(body),
            "char_count": len(body),
            "built_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        out = Path(args.output).resolve() if args.output else ROOT / ".work" / "reference_packets" / f"{args.stage}_{manifest['packet_sha256'][:12]}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("# Stage Reference Packet\n\n```json\n" + json.dumps(manifest, ensure_ascii=False, indent=2) + "\n```\n\n" + body + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "packet": str(out), "manifest": manifest}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    force_utf8_stdio()
    raise SystemExit(main())
