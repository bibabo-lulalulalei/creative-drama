#!/usr/bin/env python3
"""Build a small, evidence-backed recovery checkpoint for a project.

The checkpoint is a locator, not a second state store.  State, confirmations,
manifests, and lint reports remain authoritative and are hashed here so a
compressed session can decide what needs to be read again.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable

try:
    from scripts import context_ledger
except ImportError:
    import context_ledger


DEFAULT_MAX_CHARS = 4_000
DEFAULT_CONFIRMATION_LIMIT = 8
DEFAULT_OPERATION_LIMIT = 20
STAGES = ("planning", "script", "assets", "storyboard", "keyframes", "video", "final")


def _display_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _safe_path(root: Path, relative: str) -> tuple[Path, str]:
    candidate = Path(relative)
    if not relative or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"invalid project-relative path: {relative!r}")
    path = (root / candidate).resolve()
    try:
        display = path.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {relative!r}") from exc
    return path, display


def _file_meta(root: Path, relative: str, data: Any | None = None) -> dict[str, Any]:
    path, display = _safe_path(root, relative)
    raw = path.read_bytes()
    item: dict[str, Any] = {
        "path": display,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if isinstance(data, dict) and isinstance(data.get("revision"), int) and not isinstance(data["revision"], bool):
        item["revision"] = data["revision"]
    return item


def _read_json(root: Path, relative: str, errors: list[str]) -> tuple[Any | None, dict[str, Any] | None]:
    try:
        path, display = _safe_path(root, relative)
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8-sig"))
        return data, {
            "path": display,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            **({"revision": data["revision"]} if isinstance(data, dict)
               and isinstance(data.get("revision"), int) and not isinstance(data["revision"], bool) else {}),
        }
    except FileNotFoundError:
        errors.append(f"missing:{relative}")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"unreadable:{relative}:{exc}")
    return None, None


def _read_jsonl(root: Path, relative: str, errors: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    try:
        path, display = _safe_path(root, relative)
        raw = path.read_bytes()
    except FileNotFoundError:
        errors.append(f"missing:{relative}")
        return [], None
    except (OSError, ValueError) as exc:
        errors.append(f"unreadable:{relative}:{exc}")
        return [], None

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        errors.append(f"invalid_encoding:{relative}:{exc}")
        return [], {
            "path": display,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }

    records: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid_jsonl:{relative}:{number}:{exc.msg}")
            continue
        if isinstance(value, dict):
            records.append(value)
    return records, {
        "path": display,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _confirmed_ids(
    records: Iterable[dict[str, Any]],
    current_stage: str,
    current_episode: str | None,
    *,
    limit: int = DEFAULT_CONFIRMATION_LIMIT,
) -> list[dict[str, Any]]:
    """Keep only real confirmed records relevant to the current recovery."""
    selected: list[dict[str, Any]] = []
    for record in records:
        identifier = record.get("confirmation_id")
        if record.get("decision") != "confirmed" or not isinstance(identifier, str) or not identifier:
            continue
        stage = record.get("stage")
        episode = record.get("episode_id") or None
        relevant = (stage == "planning" and episode is None) or (
            stage == current_stage and episode == current_episode
        )
        if not relevant:
            continue
        selected.append({
            "id": identifier,
            "stage": stage,
            "episode_id": episode,
            **({"revision": record["revision"]} if isinstance(record.get("revision"), int) else {}),
        })
    # The source is append-only; newest records are the useful recovery facts.
    return list(reversed(selected[-limit:]))


def _handoff_confirmation(
    records: Iterable[dict[str, Any]],
    current_stage: str,
    current_episode: str | None,
) -> dict[str, Any] | None:
    """Link the current stage to its immediately preceding confirmed scope."""
    if current_stage == "planning" or current_stage not in STAGES:
        return None
    if current_stage == "script":
        previous_stage, previous_episode = ("script", None) if current_episode else ("planning", None)
    else:
        previous_stage = STAGES[STAGES.index(current_stage) - 1]
        previous_episode = current_episode

    for record in reversed(list(records)):
        confirmation_id = record.get("confirmation_id")
        if (
            record.get("decision") != "confirmed"
            or record.get("valid", True) is False
            or not isinstance(confirmation_id, str)
            or not confirmation_id
            or record.get("stage") != previous_stage
            or (record.get("episode_id") or None) != previous_episode
        ):
            continue
        handoff: dict[str, Any] = {
            "from_stage": previous_stage,
            "from_episode_id": previous_episode,
            "confirmation_id": confirmation_id,
            "to_stage": current_stage,
            "to_episode_id": current_episode,
        }
        revision = record.get("revision")
        if isinstance(revision, int) and not isinstance(revision, bool):
            handoff["revision"] = revision
        return handoff
    return None


def _latest_operation(records: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    for record in reversed(list(records)[-DEFAULT_OPERATION_LIMIT:]):
        if not isinstance(record, dict):
            continue
        return {
            key: record[key]
            for key in ("operation_id", "stage", "status", "timestamp", "recovery_action")
            if record.get(key) not in (None, "", [])
        }
    return None


def _lint_summary(root: Path, relative: str | None, errors: list[str]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if not relative:
        return {"error_codes": [], "release_ready": None}, None
    report, meta = _read_json(root, relative, errors)
    if not isinstance(report, dict):
        return {"path": relative, "error_codes": [], "release_ready": None}, meta
    lint = report.get("lint") if isinstance(report.get("lint"), dict) else report
    issues = lint.get("issues", []) if isinstance(lint, dict) else []
    codes: list[str] = []
    if isinstance(issues, list):
        for item in issues:
            if not isinstance(item, dict) or item.get("level") != "error":
                continue
            code = item.get("code")
            if isinstance(code, str) and code and code not in codes:
                codes.append(code)
    release_ready = None
    if isinstance(lint, dict):
        value = lint.get("release_ready", lint.get("ok"))
        if isinstance(value, bool):
            release_ready = value
    summary: dict[str, Any] = {
        "path": relative,
        "error_codes": codes[:32],
        "release_ready": release_ready,
    }
    return summary, meta


def _phase(state: dict[str, Any], stage: str, episode: str | None) -> str | None:
    if episode:
        item = state.get("episodes", {}).get(episode, {})
        if isinstance(item, dict):
            value = item.get("stage_status", {}).get(stage)
            if isinstance(value, str):
                return value
    value = state.get("phases", {}).get(stage)
    return value if isinstance(value, str) else None


def _next_action(stage: str, phase: str | None, error_codes: list[str], target_stage: str) -> tuple[str, str]:
    if error_codes:
        codes = ", ".join(error_codes[:5])
        suffix = " 等" if len(error_codes) > 5 else ""
        return (
            f"修复 {codes}{suffix}，然后重新运行 {stage} lint",
            "无需用户动作；先完成错误修复并复检",
        )
    if phase == "awaiting_confirmation":
        return f"展示 {stage} 阶段正式产物并等待用户确认", f"需要用户确认 {stage} 阶段产物"
    if phase == "confirmed":
        if stage == target_stage:
            return "核对目标阶段交付条件并结束当前任务", "无"
        return f"按阶段顺序进入 {target_stage} 之前的下一阶段", "无"
    if phase == "blocked":
        return f"定位 {stage} 阶段阻断原因并按错误码修复", "无"
    if phase == "pending":
        return f"开始 {stage} 阶段固定作业并运行 lint", "无"
    return f"继续 {stage} 阶段固定作业并运行 lint", "无"


def _manifest_path(root: Path, state: dict[str, Any], stage: str, episode: str | None, errors: list[str]) -> str | None:
    if stage == "planning":
        return "00_制作控制/drama_plan.json"
    if episode:
        episode_state = state.get("episodes", {}).get(episode, {})
        if isinstance(episode_state, dict) and isinstance(episode_state.get("manifest"), str):
            episode_manifest = episode_state["manifest"]
            manifest, _ = _read_json(root, episode_manifest, errors)
            if isinstance(manifest, dict):
                paths = manifest.get("stage_manifests", {})
                if isinstance(paths, dict):
                    selected = paths.get(stage)
                    if stage == "final" and not selected:
                        selected = paths.get("delivery")
                    if isinstance(selected, str):
                        return selected
    # Project-level recovery can still identify the current story index.
    if stage == "script":
        for candidate in ("01_剧本/project_script_manifest.json", "01_剧本/project_manifest.json"):
            if (root / candidate).is_file():
                return candidate
    return None


def _compare_previous(current: list[dict[str, Any]], previous: dict[str, Any] | None) -> list[dict[str, str]]:
    if not isinstance(previous, dict):
        return []
    old_items = previous.get("artifacts", [])
    old = {item.get("path"): item.get("sha256") for item in old_items if isinstance(item, dict)}
    changes = []
    for item in current:
        path, digest = item.get("path"), item.get("sha256")
        if path in old and old[path] != digest:
            changes.append({
                "path": path,
                "reason": "hash_changed",
                "action": "重新读取该文件的受影响字段，并检查下游失效范围",
            })
    return changes


def build_checkpoint(
    project_root: Path,
    *,
    lint_report: str | None = None,
    previous: dict[str, Any] | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> dict[str, Any]:
    root = project_root.resolve()
    errors: list[str] = []
    state, state_meta = _read_json(root, "00_制作控制/制作状态.json", errors)
    plan, plan_meta = _read_json(root, "00_制作控制/drama_plan.json", errors)
    confirmations, confirmations_meta = _read_jsonl(root, "00_制作控制/用户确认记录.jsonl", errors)
    operations, operations_meta = _read_jsonl(root, "00_制作控制/操作日志.jsonl", errors)
    state = state if isinstance(state, dict) else {}
    plan = plan if isinstance(plan, dict) else {}
    current_stage = state.get("current_stage") if isinstance(state.get("current_stage"), str) else "unknown"
    current_episode = state.get("current_episode")
    if not isinstance(current_episode, str) or not current_episode:
        current_episode = None
    target_stage = plan.get("objective", {}).get("target_stage") if isinstance(plan.get("objective"), dict) else None
    if not isinstance(target_stage, str) or target_stage not in STAGES:
        target_stage = current_stage if current_stage in STAGES else "unknown"
    phase = _phase(state, current_stage, current_episode)

    artifacts = [meta for meta in (state_meta, plan_meta, confirmations_meta, operations_meta) if meta]
    handoff = _handoff_confirmation(confirmations, current_stage, current_episode)
    if handoff:
        previous_manifest_path = _manifest_path(
            root, state, handoff["from_stage"], handoff["from_episode_id"], errors
        )
        if previous_manifest_path:
            _, previous_manifest_meta = _read_json(root, previous_manifest_path, errors)
            if previous_manifest_meta:
                handoff["artifact"] = previous_manifest_meta
                if not any(item.get("path") == previous_manifest_meta["path"] for item in artifacts):
                    artifacts.append(previous_manifest_meta)
    manifest_path = _manifest_path(root, state, current_stage, current_episode, errors)
    if manifest_path:
        manifest, manifest_meta = _read_json(root, manifest_path, errors)
        if manifest_meta:
            artifacts.append(manifest_meta)
    lint, lint_meta = _lint_summary(root, lint_report, errors)
    if lint_meta:
        artifacts.append(lint_meta)

    next_action, required_user_action = _next_action(current_stage, phase, lint["error_codes"], target_stage)
    checkpoint: dict[str, Any] = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "context": {"ledger": context_ledger.PROJECT_LEDGER, "events": context_ledger.PROJECT_EVENTS},
        "project_id": state.get("project_id") or plan.get("project_id"),
        "current_stage": current_stage,
        "current_episode": current_episode,
        "target_stage": target_stage,
        "phase": phase,
        "handoff": handoff,
        "authorization_ids": _confirmed_ids(confirmations, current_stage, current_episode),
        "artifacts": artifacts,
        "lint": lint,
        "last_successful_operation": state.get("last_successful_operation") or None,
        "last_operation": _latest_operation(operations),
        "changes": _compare_previous(artifacts, previous),
        "next_action": next_action,
        "required_user_action": required_user_action,
    }
    if errors:
        checkpoint["read_warnings"] = errors[:16]

    encoded = json.dumps(checkpoint, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) > max_chars:
        # Keep the facts needed to recover; omit optional diagnostics before failing.
        checkpoint["authorization_ids"] = checkpoint["authorization_ids"][:4]
        checkpoint["changes"] = checkpoint["changes"][:4]
        checkpoint["read_warnings"] = checkpoint.get("read_warnings", [])[:4]
        encoded = json.dumps(checkpoint, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) > max_chars:
        raise ValueError(f"checkpoint is {len(encoded)} characters (limit {max_chars})")
    return checkpoint


def format_checkpoint(checkpoint: dict[str, Any]) -> str:
    return json.dumps(checkpoint, ensure_ascii=False, separators=(",", ":")) + "\n"


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--lint-report", help="optional project-relative lint JSON report")
    parser.add_argument("--previous-checkpoint", type=Path, help="optional prior checkpoint for hash change detection")
    parser.add_argument("--output", type=Path, help="write the checkpoint atomically to this path")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    args = parser.parse_args(argv)
    try:
        if not 512 <= args.max_chars <= 20_000:
            raise ValueError("max-chars must be 512..20000")
        previous = None
        if args.previous_checkpoint:
            previous = json.loads(args.previous_checkpoint.read_text(encoding="utf-8-sig"))
        checkpoint = build_checkpoint(
            args.project_root,
            lint_report=args.lint_report,
            previous=previous,
            max_chars=args.max_chars,
        )
        output = format_checkpoint(checkpoint)
        if args.output:
            write_atomic(args.output, output)
        print(output, end="")
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
