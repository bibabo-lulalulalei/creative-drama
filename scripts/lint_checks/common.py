"""Shared file, JSON, duration, table and issue helpers."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any
from h3_contract import is_url
from .constants import IMAGE_GENERATION_TOOLS, ISO_TIME_PATTERN, STAGES


def issue(level: str, code: str, message: str, path: Path | None = None, hint: str = "") -> dict[str, Any]:
    data: dict[str, Any] = {"level": level, "code": code, "message": message, "hint": hint}
    if path is not None:
        data["path"] = str(path)
    return data


def load_json(path: Path, issues: list[dict[str, Any]], required: bool = True) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if required:
            issues.append(issue("error", "file_missing", "缺少流程所需文件。", path))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.append(issue("error", "json_invalid", f"JSON 无法读取或解析，后续关系无法确认：{exc}", path))
    return None


def relative_file(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    rel = Path(value)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    try:
        target = (root / rel).resolve()
        target.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return target


def file_exists(root: Path, value: Any) -> bool:
    target = relative_file(root, value)
    return target is not None and target.is_file()


def media_location_valid(root: Path, value: Any) -> bool:
    # A URL is a declared reference location, not proof of availability or remote bytes.
    return (isinstance(value, str) and is_url(value)) or file_exists(root, value)


def parse_iso_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not ISO_TIME_PATTERN.fullmatch(text):
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nonempty_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def has_meaningful_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, list):
        return bool(value) and all(has_meaningful_value(item) for item in value)
    if isinstance(value, dict):
        return bool(value) and any(has_meaningful_value(item) for item in value.values())
    return False


def combined_strings(*owners: Any, field: str) -> list[str]:
    values: list[str] = []
    for owner in owners:
        if isinstance(owner, dict):
            values.extend(nonempty_strings(owner.get(field)))
    return values


def check_style_anchor_contract(
    root: Path,
    owner_path: Path,
    owner_label: str,
    tool: Any,
    prompt_path_value: Any,
    style_anchor_refs: list[str],
    terms: list[str],
    adopt: list[str],
    exclude: list[str],
    issues: list[dict[str, Any]],
    visual_reference_decision: Any = None,
) -> None:
    if not style_anchor_refs:
        return
    if tool != "image_edit":
        issues.append(issue("error", "style_anchor_requires_image_edit", f"{owner_label} 使用 style_anchor_reference 时必须走 image_edit。", owner_path))
    if visual_reference_decision == "none_available":
        issues.append(issue("error", "style_anchor_visual_reference_decision_conflict", f"{owner_label} 使用 style_anchor_reference 时 visual_reference_decision 不能写 none_available。", owner_path))
    if not terms:
        issues.append(issue("error", "style_prompt_terms_missing", f"{owner_label} 使用 style_anchor_reference 时 style_prompt_terms 必须是非空字符串数组。", owner_path))
    if not adopt:
        issues.append(issue("error", "style_adopt_missing", f"{owner_label} 使用 style_anchor_reference 时 style_adopt 必须是非空字符串数组。", owner_path))
    if not exclude:
        issues.append(issue("error", "style_exclude_missing", f"{owner_label} 使用 style_anchor_reference 时 style_exclude 必须是非空字符串数组。", owner_path))
    prompt_path = relative_file(root, prompt_path_value)
    if prompt_path is None:
        issues.append(issue("error", "style_prompt_path_missing", f"{owner_label} 使用 style_anchor_reference 时必须登记项目相对 prompt_path。", owner_path))
    elif not prompt_path.is_file():
        issues.append(issue("error", "style_prompt_file_missing", f"{owner_label} style_anchor_reference 对应 Prompt 文件不存在。", prompt_path))


def check_generation_prompt_file(
    root: Path,
    owner_path: Path,
    owner_label: str,
    tool: Any,
    prompt_path_value: Any,
    issues: list[dict[str, Any]],
) -> None:
    if tool not in IMAGE_GENERATION_TOOLS:
        return
    prompt_path = relative_file(root, prompt_path_value)
    if prompt_path is None:
        issues.append(issue("error", "generation_prompt_path_missing", f"{owner_label} 使用 {tool} 生成图片时必须登记项目相对 prompt_path。", owner_path))
    elif not prompt_path.is_file():
        issues.append(issue("error", "generation_prompt_file_missing", f"{owner_label} 生成图片 Prompt 文件不存在。", prompt_path))
    else:
        try:
            prompt_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(issue("error", "generation_prompt_unreadable", f"{owner_label} 生成图片 Prompt 无法读取：{exc}", prompt_path))


def file_inside(root: Path, value: Any, directory: Path) -> bool:
    target = relative_file(root, value)
    if target is None or not target.is_file():
        return False
    try:
        target.relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def expected_duration_display(seconds: int | float) -> str:
    total = int(round(float(seconds)))
    if total <= 60:
        return f"{total}秒"
    minutes, rest = divmod(total, 60)
    return f"{minutes}分钟" if rest == 0 else f"{minutes}分{rest}秒"


def expected_total_duration_display(seconds: int | float) -> str:
    total = int(round(float(seconds)))
    natural = expected_duration_display(total)
    return natural if total <= 60 else f"{total}秒/{natural}"


def check_duration_pair(
    seconds: Any,
    display: Any,
    path: Path,
    label: str,
    issues: list[dict[str, Any]],
    *,
    total_display: bool = False,
) -> None:
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or not math.isfinite(seconds) or seconds < 0:
        issues.append(issue("error", "duration_invalid", f"{label} duration_s 必须是数字。", path))
        return
    if isinstance(display, str) and display.strip():
        expected = expected_total_duration_display(seconds) if total_display else expected_duration_display(seconds)
        if display != expected:
            issues.append(issue("error", "duration_display_invalid", f"{label} duration_display 应为 {expected}。", path))


def check_unique(items: list[Any], field: str, path: Path, issues: list[dict[str, Any]], scope: str) -> set[str]:
    seen: set[str] = set()
    values: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(issue("error", f"{field}_missing", f"{scope} 缺少 {field}。", path))
            continue
        if value in seen:
            issues.append(issue("error", f"{field}_duplicate", f"{scope} 中 {field} 重复：{value}", path))
        seen.add(value)
        values.add(value)
    return values


def manifest_path(root: Path, episode_id: str, stage: str) -> Path | None:
    episode_root = root / "episodes" / episode_id
    paths = {
        "script": episode_root / f"01_剧本/script_contract_{episode_id}.json",
        "assets": episode_root / f"03_资产/asset_usage_{episode_id}.json",
        "storyboard": episode_root / f"02_分镜/storyboard_{episode_id}.json",
        "keyframes": episode_root / f"03_资产/keyframe_manifest_{episode_id}.json",
        "video": episode_root / f"04_视频片段/video_manifest_{episode_id}.json",
        "final": episode_root / f"05_成片/delivery_manifest_{episode_id}.json",
    }
    return paths.get(stage)


def plan_revision(plan: Any, state: dict[str, Any]) -> int | None:
    for source in (state, plan if isinstance(plan, dict) else {}):
        value = source.get("revision") if isinstance(source, dict) else None
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def target_stage(plan: Any) -> str | None:
    objective = plan.get("objective") if isinstance(plan, dict) else None
    value = objective.get("target_stage") if isinstance(objective, dict) else None
    return value if value in STAGES else None


def episode_dirs(root: Path, episode_filter: str | None = None) -> list[tuple[str, Path]]:
    episodes_root = root / "episodes"
    if not episodes_root.is_dir():
        return []
    entries = [
        (child.name, child)
        for child in episodes_root.iterdir()
        if child.is_dir() and re.fullmatch(r"ep_[1-9]\d*", child.name)
        and (episode_filter is None or child.name == episode_filter)
    ]
    return sorted(entries, key=lambda item: int(item[0].split("_", 1)[1]))


def read_text_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def markdown_table_column_counts(text: str) -> list[int]:
    counts: list[int] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped[1:-1].split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            counts.append(len(cells))
    return counts


def dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for item in issues:
        key = (item.get("level"), item.get("code"), item.get("message"), item.get("path"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
