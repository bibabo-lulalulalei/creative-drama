#!/usr/bin/env python3
"""Read bounded evidence from large project files without returning them whole."""

from __future__ import annotations

import argparse
import hashlib
from itertools import islice
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts import context_ledger
except ImportError:
    import context_ledger


DEFAULT_ID_FIELDS = (
    "id", "shot_id", "segment_id", "beat_id", "event_id", "line_id",
    "asset_id", "fact_id", "chain_id", "seam_id",
)
MAX_OUTPUT_LIMIT = 100_000


def safe_project_file(project_root: Path, file_name: str) -> tuple[Path, str]:
    root = project_root.resolve()
    relative = Path(file_name)
    if not file_name.strip() or relative.is_absolute() or ".." in relative.parts:
        raise ValueError("--file must be a non-empty path relative to --project-root")
    target = (root / relative).resolve()
    try:
        display_path = target.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("--file resolves outside --project-root") from exc
    if not target.is_file():
        raise ValueError(f"project file does not exist: {display_path}")
    return target, display_path


def _pointer_parts(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError(f"invalid JSON Pointer: {pointer!r}")
    parts = pointer[1:].split("/")
    decoded = []
    for part in parts:
        if re.search(r"~(?![01])", part):
            raise ValueError(f"invalid JSON Pointer escape: {pointer!r}")
        decoded.append(part.replace("~1", "/").replace("~0", "~"))
    return decoded


def json_pointer(value: Any, pointer: str) -> Any:
    current = value
    for part in _pointer_parts(pointer):
        if isinstance(current, dict):
            if part not in current:
                raise ValueError(f"JSON Pointer not found: {pointer!r} (missing key {part!r})")
            current = current[part]
        elif isinstance(current, list):
            if not part.isdecimal() or (len(part) > 1 and part.startswith("0")):
                raise ValueError(f"invalid array index in JSON Pointer: {pointer!r}")
            index = int(part)
            if index >= len(current):
                raise ValueError(f"JSON Pointer array index out of range: {pointer!r}")
            current = current[index]
        else:
            raise ValueError(f"JSON Pointer traverses a scalar: {pointer!r}")
    return current


def _iter_objects(value: Any, pointer: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        yield pointer or "/", value
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from _iter_objects(child, f"{pointer}/{escaped}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_objects(child, f"{pointer}/{index}")


def _compact_value(value: Any) -> Any:
    if isinstance(value, str) and len(value) > 240:
        return {"type": "string", "chars": len(value)}
    if isinstance(value, dict):
        return {"type": "object", "keys": len(value)}
    if isinstance(value, list):
        return {"type": "array", "items": len(value)}
    return value


def _project_record(record: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    if fields:
        return {field: record[field] for field in fields if field in record}
    return {key: _compact_value(value) for key, value in record.items()}


def _text_matches(text: str, query: str, context_lines: int, max_matches: int) -> list[dict[str, Any]]:
    lines = text.splitlines()
    windows: list[tuple[int, int]] = []
    hit_indexes = list(islice((index for index, line in enumerate(lines) if query in line), max_matches))
    for index in hit_indexes:
        start = max(0, index - context_lines)
        end = min(len(lines), index + context_lines + 1)
        if windows and start <= windows[-1][1]:
            windows[-1] = (windows[-1][0], end)
        else:
            windows.append((start, end))
    return [
        {
            "line_start": start + 1,
            "line_end": end,
            "text": "\n".join(f"{number + 1}: {lines[number]}" for number in range(start, end)),
        }
        for start, end in windows
    ]


def create_snapshot(
    project_root: Path,
    file_name: str,
    *,
    pointers: list[str] | None = None,
    ids: list[str] | None = None,
    id_fields: list[str] | None = None,
    fields: list[str] | None = None,
    match: str | None = None,
    context_lines: int = 2,
    max_matches: int = 20,
) -> dict[str, Any]:
    target, display_path = safe_project_file(project_root, file_name)
    raw = target.read_bytes()
    payload: dict[str, Any] = {
        "file": display_path,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if match is not None:
        if not match:
            raise ValueError("--match cannot be empty")
        text = raw.decode("utf-8-sig")
        payload["matches"] = _text_matches(text, match, context_lines, max_matches)
        payload["match_count"] = len(payload["matches"])
        return payload

    if not pointers and not ids:
        payload["selection"] = "metadata_only"
        return payload

    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        if pointers or ids:
            raise ValueError(f"selected JSON read requires a UTF-8 JSON file: {exc}") from exc
        payload["selection"] = "metadata_only"
        return payload

    if pointers:
        payload["selection"] = "json_pointer"
        payload["values"] = [{"pointer": pointer, "value": json_pointer(data, pointer)} for pointer in pointers]
    elif ids:
        selected_fields = id_fields or list(DEFAULT_ID_FIELDS)
        payload["selection"] = "id_projection"
        payload["records"] = []
        for identifier in ids:
            found = [
                {"pointer": pointer, "value": _project_record(record, fields or [])}
                for pointer, record in _iter_objects(data)
                if any(record.get(key) is not None and str(record[key]) == identifier for key in selected_fields)
            ]
            if not found:
                raise ValueError(f"ID not found: {identifier}")
            payload["records"].append({"id": identifier, "matches": found})
    else:
        payload["selection"] = "metadata_only"
    return payload


def create_batch_snapshot(
    project_root: Path,
    file_names: list[str],
    *,
    max_files: int = 32,
) -> dict[str, Any]:
    """Return bounded metadata for several project files in one operation.

    Batch mode deliberately returns hashes and byte counts only. Callers can
    follow up with ``create_snapshot`` for a pointer, ID, or text match after
    the changed file has been identified.
    """
    if not file_names:
        raise ValueError("at least one file is required")
    if len(file_names) > max_files:
        raise ValueError(f"at most {max_files} files may be batched")
    files = []
    for file_name in file_names:
        item = create_snapshot(project_root, file_name)
        files.append({
            "file": item["file"],
            "bytes": item["bytes"],
            "sha256": item["sha256"],
        })
    return {"selection": "batch_metadata", "files": files, "count": len(files)}


def format_snapshot(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--file", action="append", required=True,
                        help="path relative to project root; repeat for batch metadata")
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--pointer", action="append", default=[], help="JSON Pointer; repeatable")
    selector.add_argument("--id", action="append", default=[], help="record ID; repeatable")
    selector.add_argument("--match", help="literal text match for line-oriented files")
    parser.add_argument("--id-field", action="append", help="ID field name; repeatable")
    parser.add_argument("--field", action="append", default=[], help="top-level field projected from matched records")
    parser.add_argument("--context-lines", type=int, default=2)
    parser.add_argument("--max-matches", type=int, default=20)
    parser.add_argument("--max-chars", type=int, default=12_000)
    parser.add_argument("--events", type=Path, help="覆盖项目默认上下文事件路径")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.context_lines < 0 or not 1 <= args.max_matches <= 100:
            raise ValueError("context-lines must be nonnegative and max-matches must be 1..100")
        if not 100 <= args.max_chars <= MAX_OUTPUT_LIMIT:
            raise ValueError(f"max-chars must be 100..{MAX_OUTPUT_LIMIT}")
        if len(args.file) > 1 and (args.pointer or args.id or args.match or args.id_field or args.field):
            raise ValueError("selectors may be used with one --file only; batch mode returns metadata")
        if (args.id_field or args.field) and not args.id:
            raise ValueError("--id-field and --field require at least one --id")
        payload = (
            create_batch_snapshot(args.project_root, args.file)
            if len(args.file) > 1 else
            create_snapshot(
                args.project_root,
                args.file[0],
                pointers=args.pointer,
                ids=args.id,
                id_fields=args.id_field,
                fields=args.field,
                match=args.match,
                context_lines=args.context_lines,
                max_matches=args.max_matches,
            )
        )
        output = format_snapshot(payload)
        if len(output) > args.max_chars:
            raise ValueError(
                f"selected output is {len(output)} characters (limit {args.max_chars}); "
                "narrow the pointer/fields/match or raise --max-chars"
            )
        sys.stdout.write(output)
        sys.stdout.flush()
        events = args.events or context_ledger.project_paths(args.project_root)[1]
        for item in payload.get("files", [payload]):
            context_ledger.append_event(events, {
                "kind": "project_read", "file": item["file"], "sha256": item["sha256"],
                "selection": item.get("selection", payload.get("selection", "text_match")),
                "full": bool(args.pointer and "" in args.pointer),
                "chars": len(json.dumps(item, ensure_ascii=False)),
            })
        context_ledger.record_tool_result(events, "project_snapshot", output)
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        sys.stderr.write(f"project_snapshot: {exc}\n")
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
