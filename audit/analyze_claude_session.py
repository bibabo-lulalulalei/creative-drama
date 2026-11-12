#!/usr/bin/env python3
"""Read a Claude Code JSONL snapshot and emit aggregate context evidence as JSON.

Does not emit message bodies, shell commands, API blobs, or image payloads.
Character counts are measured text, never an estimate of model tokens.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


def fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def content_sizes(content: Any) -> dict[str, int]:
    """Count decoded text separately from serialized base64 image data."""
    result = {"text_chars": 0, "image_blocks": 0, "image_base64_chars": 0}
    if isinstance(content, str):
        result["text_chars"] = len(content)
        return result
    if not isinstance(content, list):
        return result
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            result["text_chars"] += len(block.get("text", ""))
        elif block.get("type") == "image":
            result["image_blocks"] += 1
            source = block.get("source", {})
            if isinstance(source, dict) and source.get("type") == "base64":
                result["image_base64_chars"] += len(source.get("data", ""))
    return result


def timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def read_category(path: str) -> str:
    normalized = path.replace("\\", "/")
    if "/scripts/" in normalized and normalized.endswith(".py"):
        return "script_source"
    if "/references/" in normalized:
        return "reference"
    if "/artifacts/" in normalized:
        return "project_file"
    return "other"


def analyze(path: Path) -> dict[str, Any]:
    stat_before = path.stat()
    raw = path.read_bytes()
    stat_after = path.stat()
    lines = raw.decode("utf-8-sig").splitlines()
    records = []
    incomplete_final_line = False
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            if line_number == len(lines) and not raw.endswith(b"\n"):
                incomplete_final_line = True
                continue
            raise ValueError(f"Invalid JSON at line {line_number}") from None
        records.append((line_number, record))

    calls: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    result_hashes: dict[str, set[str]] = defaultdict(set)
    assistant_blocks = []
    assistant_seen = set()
    assistant_response_ids = set()
    seen_message_uuids = set()
    response_usage: dict[str, dict[str, Any]] = {}
    duplicate_message_uuids = 0
    duplicate_calls = 0
    result_block_count = 0
    assistant_block_duplicates = 0
    summaries = []
    compactions = []
    shapes = []
    request_policies = Counter()
    archived_result_blocks = 0
    archived_result_ids = set()

    for line_number, record in records:
        kind = record.get("type")
        if kind == "api-request":
            params = record.get("params", {})
            policy = {
                "effort": params.get("output_config", {}).get("effort"),
                "thinking_retention": [
                    edit.get("keep")
                    for edit in params.get("context_management", {}).get("edits", [])
                    if str(edit.get("type", "")).startswith("clear_thinking_")
                ],
            }
            request_policies[json.dumps(policy, sort_keys=True)] += 1
        if kind == "api-request-blob":
            archived_content = record.get("message", {}).get("content", [])
            if isinstance(archived_content, list):
                for block in archived_content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        archived_result_blocks += 1
                        archived_result_ids.add(block.get("tool_use_id"))
        if record.get("subtype") == "compact_boundary":
            metadata = record.get("compactMetadata", {})
            compactions.append({
                "line": line_number,
                "timestamp_utc": record.get("timestamp"),
                "trigger": metadata.get("trigger"),
                "pre_tokens": metadata.get("preTokens"),
                "post_tokens": metadata.get("postTokens"),
                "cumulative_dropped_tokens": metadata.get("cumulativeDroppedTokens"),
                "duration_ms": metadata.get("durationMs"),
            })
        if kind == "api-request-shape":
            shape = record.get("shape", {})
            shapes.append({
                "line": line_number,
                "shape_hash": record.get("shapeHash"),
                "system_json_chars": len(json.dumps(shape.get("system", []), ensure_ascii=False)),
                "tool_schema_json_chars": len(json.dumps(shape.get("tools", []), ensure_ascii=False)),
                "tool_count": len(shape.get("tools", [])),
            })
        if kind not in {"assistant", "user"}:
            continue
        uuid = record.get("uuid")
        if uuid and uuid in seen_message_uuids:
            duplicate_message_uuids += 1
            continue
        if uuid:
            seen_message_uuids.add(uuid)
        message = record.get("message", {})
        content = message.get("content", [])
        response_id = message.get("id")
        if kind == "assistant":
            assistant_response_ids.add(response_id or f"line:{line_number}")
            usage = message.get("usage")
            if response_id and isinstance(usage, dict):
                first_line = response_usage.get(response_id, {}).get("line", line_number)
                response_usage[response_id] = {"line": first_line, **usage}
        if isinstance(content, str):
            if kind == "user" and content.startswith("This session is being continued from a previous conversation"):
                summaries.append({"line": line_number, "text_chars": len(content)})
            continue
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if kind == "assistant":
                key = (response_id or uuid or line_number, fingerprint(block))
                if key in assistant_seen:
                    assistant_block_duplicates += 1
                    continue
                assistant_seen.add(key)
                if block_type in {"text", "thinking"}:
                    value = block.get("text", "") if block_type == "text" else block.get("thinking", "")
                    assistant_blocks.append({"line": line_number, "type": block_type, "chars": len(value)})
            if block_type == "tool_use":
                tool_id = block.get("id")
                if not tool_id:
                    continue
                if tool_id in calls:
                    duplicate_calls += 1
                    continue
                inputs = block.get("input", {})
                calls[tool_id] = {
                    "line": line_number,
                    "name": block.get("name", "unknown"),
                    "path": inputs.get("file_path"),
                    "input_json_chars": len(json.dumps(inputs, ensure_ascii=False)),
                    "has_offset": "offset" in inputs,
                    "has_limit": "limit" in inputs,
                }
            elif block_type == "tool_result":
                result_block_count += 1
                tool_id = block.get("tool_use_id")
                if not tool_id:
                    continue
                result_hashes[tool_id].add(fingerprint(block))
                if tool_id not in results:
                    results[tool_id] = {"line": line_number, **content_sizes(block.get("content", ""))}

    previous = None
    for boundary in compactions:
        current = timestamp(boundary["timestamp_utc"])
        boundary["minutes_since_previous_compaction"] = (
            round((current - previous).total_seconds() / 60, 3)
            if previous and current else None
        )
        previous = current
        after = sorted(
            (usage for usage in response_usage.values() if usage["line"] > boundary["line"]),
            key=lambda value: value["line"],
        )
        if after:
            usage = after[0]
            boundary["first_response_after_compaction"] = {
                "line": usage["line"],
                "input_tokens": usage.get("input_tokens", 0),
                "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
            }

    read_files: dict[str, dict[str, Any]] = {}
    for tool_id, call in calls.items():
        if call["name"] != "Read" or not call["path"]:
            continue
        entry = read_files.setdefault(call["path"], {
            "path": call["path"], "category": read_category(call["path"]),
            "calls": 0, "full_read_calls": 0, "text_chars": 0,
            "image_blocks": 0, "image_base64_chars": 0, "call_lines": [],
        })
        entry["calls"] += 1
        entry["full_read_calls"] += not call["has_offset"] and not call["has_limit"]
        entry["call_lines"].append(call["line"])
        if tool_id in results:
            for field in ("text_chars", "image_blocks", "image_base64_chars"):
                entry[field] += results[tool_id][field]

    periods = []
    period_start = 1
    period_ends = [boundary["line"] for boundary in compactions] + [len(lines)]
    for period_index, period_end in enumerate(period_ends, 1):
        selected_calls = {key: value for key, value in calls.items() if period_start <= value["line"] <= period_end}
        selected_results = {key: value for key, value in results.items() if period_start <= value["line"] <= period_end}
        selected_blocks = [value for value in assistant_blocks if period_start <= value["line"] <= period_end]
        counts = Counter(value["name"] for value in selected_calls.values())
        periods.append({
            "period": period_index, "start_line": period_start, "end_line": period_end,
            "unique_tool_calls": len(selected_calls), "unique_tool_results_first_observed": len(selected_results),
            "calls_by_tool": dict(sorted(counts.items())),
            "read_calls": counts["Read"],
            "write_or_edit_calls": counts["Write"] + counts["Edit"],
            "command_execution_calls": counts["Bash"] + counts["PowerShell"],
            "tool_result_text_chars": sum(value["text_chars"] for value in selected_results.values()),
            "tool_input_json_chars": sum(value["input_json_chars"] for value in selected_calls.values()),
            "assistant_chars_by_type": {
                name: sum(value["chars"] for value in selected_blocks if value["type"] == name)
                for name in ("text", "thinking")
            },
            "write_or_edit_lines": [value["line"] for value in selected_calls.values() if value["name"] in {"Write", "Edit"}],
        })
        period_start = period_end + 1

    return {
        "snapshot": {
            "source_path": str(path.resolve()),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes_read": len(raw), "line_count": len(lines), "parsed_records": len(records),
            "source_mtime_utc": datetime.fromtimestamp(stat_after.st_mtime, timezone.utc).isoformat(),
            "analysis_time_utc": datetime.now(timezone.utc).isoformat(),
            "source_changed_during_read": (stat_before.st_size, stat_before.st_mtime_ns) != (stat_after.st_size, stat_after.st_mtime_ns),
            "incomplete_final_line_skipped": incomplete_final_line,
        },
        "method": {
            "deduplication": "Only actual assistant/user records count toward message statistics; api-request-blob mirrors and api-request-shape schemas are excluded. Message UUID duplicates are skipped; assistant blocks deduplicate by response ID and full-block hash, retaining distinct streaming blocks. Tool calls and results deduplicate by tool ID at their earliest observed line. Conflicting result variants are reported, never silently counted twice.",
            "token_evidence": "Only compactMetadata and provider usage fields are reported as tokens. Character/base64 counts are not converted to tokens. Repeated response usage is retained once per response ID; prompt token counts are not summed as unique context.",
            "period_assignment": "Tool calls use the first tool_use line; results use the first tool_result line. Preserved records can cross a compact boundary, so period call/result counts need not match.",
            "privacy": "No message bodies, commands, API blobs, environment values, or media payloads are emitted. File paths are included for reproducible Read attribution.",
        },
        "record_types": dict(Counter(record.get("type", "unknown") for _, record in records)),
        "totals": {
            "unique_tool_calls": len(calls), "calls_by_tool": dict(Counter(call["name"] for call in calls.values())),
            "tool_result_blocks_in_log": result_block_count, "unique_tool_results": len(results),
            "api_blob_result_blocks_excluded": archived_result_blocks,
            "api_blob_result_ids_matching_conversation": len(archived_result_ids.intersection(results)),
            "duplicate_tool_results": result_block_count - len(results),
            "conflicting_tool_result_ids": sum(len(values) > 1 for values in result_hashes.values()),
            "duplicate_tool_calls": duplicate_calls, "duplicate_message_uuids": duplicate_message_uuids,
            "duplicate_assistant_blocks": assistant_block_duplicates,
            "unique_assistant_responses": len(assistant_response_ids),
            "response_ids_with_usage": len(response_usage),
            "tool_result_text_chars": sum(result["text_chars"] for result in results.values()),
            "tool_result_image_blocks": sum(result["image_blocks"] for result in results.values()),
            "tool_result_image_base64_chars": sum(result["image_base64_chars"] for result in results.values()),
            "assistant_chars_by_type": {
                name: sum(block["chars"] for block in assistant_blocks if block["type"] == name)
                for name in ("text", "thinking")
            },
            "compaction_duration_ms": sum(boundary.get("duration_ms") or 0 for boundary in compactions),
        },
        "compactions": compactions,
        "periods": periods,
        "read_files": sorted(read_files.values(), key=lambda value: (-value["text_chars"], value["path"])),
        "compaction_summaries": summaries,
        "api_request_shapes": shapes,
        "api_request_policies": [dict(json.loads(policy), requests=count)
                                 for policy, count in sorted(request_policies.items())],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_jsonl", type=Path)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        report = analyze(args.session_jsonl)
    except (OSError, UnicodeError, ValueError) as exc:
        parser.exit(1, f"Cannot analyze session: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
