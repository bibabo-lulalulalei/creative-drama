#!/usr/bin/env python3
"""只读流程检查：结构、算术、依赖、源版本与授权；不证明摄影可达或审美。

本文件由原 lint_checks 包 15 模块合并，横幅注释保留模块边界；issue 的
message/path 就地定位，创作路径不读本文件。兄弟模块依赖
rhythm_engine（时间核算与源对账）、video_confirmations、
h3_contract，均在本目录平级导入。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# python -I（隔离模式）不把脚本目录加入 sys.path，入口一次性自举本目录兄弟模块。
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# ===== 原 lint_checks/constants.py =====

import re


STAGES = ("planning", "script", "assets", "storyboard", "keyframes", "video", "final")

EPISODE_STAGES = set(STAGES[1:])

STATUS_VALUES = {"pending", "in_progress", "awaiting_confirmation", "confirmed", "invalidated", "blocked"}

ASSET_STATUS_VALUES = {"draft", "reviewed", "approved", "rejected", "superseded"}

VISUAL_REFERENCE_DECISIONS = {"used", "none_available", "explicit_user_override"}

PROJECT_VISUAL_MODES = {"live_action", "photoreal", "2d_comic", "anime", "ink_animation", "illustration", "stylized_3d", "mixed_with_explicit_scope"}

VIDEO_STATUS_VALUES = {"candidate", "accepted", "rejected", "blocked"}

VIDEO_TOOL_MODES = {"text_to_video", "media_to_video", "image_to_video", "video_edit"}

IMAGE_GENERATION_TOOLS = {"image_gen", "image_edit"}

FORBIDDEN_TOOL_TERMS = ("text_to_image",)

BEAT_LIBRARY_JSON_PATH = SCRIPT_DIR / "beat_types.json"

BEAT_LIBRARY_MD_PATH = SCRIPT_DIR.parent / "references" / "节拍类型库.md"

H3_CAPABILITY_PATH = SCRIPT_DIR.parent / "tools" / "video" / "h3.json"

CUT_MOTIVATIONS = {"match_on_action", "eyeline", "sound_bridge", "occlusion", "reaction", "spatial", "information", "motivated_hard_cut"}

REFERENCE_ROLES = {
    "previous_tail_as_start_frame",
    "previous_scene_anchor_reference",
    "previous_character_state_reference",
    "previous_prop_state_reference",
    "segment_highlight_reference",
    "identity_reference",
    "character_state_reference",
    "scene_layout",
    "prop_structure",
    "prop_state_reference",
    "style_reference",
}

VIDEO_INPUT_ROLES = {
    "previous_segment_video_reference",
    "style_video_reference",
    "character_video_reference",
    "scene_video_reference",
    "source_video_for_edit",
}

AUDIO_INPUT_ROLES = {
    "voice_audio_reference",
    "music_reference",
    "sound_effect_reference",
    "ambient_reference",
}

STATE_REFERENCE_ROLES = {"character_state_reference", "prop_state_reference"}

CURRENT_STAGE_ACTIVE_VALUES = {"in_progress", "awaiting_confirmation", "invalidated", "blocked"}

CONFIRMATION_MODES = {"full", "incremental"}

ISO_TIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})")

ASSET_ID_PATTERN = re.compile(r"^((?:CHR|SCN|PROP|STYLE)\d+)(?:[_:]v?(\d+))?")

ASSET_ROLE_COMPATIBILITY = {
    "CHR": {"identity_reference", "character_state_reference", "previous_character_state_reference"},
    "SCN": {"scene_layout", "previous_scene_anchor_reference"},
    "PROP": {"prop_structure", "prop_state_reference", "previous_prop_state_reference"},
    "STYLE": {"style_reference"},
}

WORLD_FACT_CATEGORIES = {"season", "festival", "date", "time_of_day", "weather", "location_fact", "other"}

BEAT_DISPOSITIONS = {"kept", "compressed", "moved", "dropped"}

# ===== 原 lint_checks/common.py =====

from datetime import datetime
import hashlib
import math
from h3_contract import is_url


def issue(level: str, code: str, message: str, path: Path | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {"level": level, "code": code, "message": message}
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

# ===== 原 lint_checks/state.py =====



def load_confirmation_records(
    root: Path,
    issues: list[dict[str, Any]],
    required: bool,
    require_planning_interaction: bool = False,
) -> list[dict[str, Any]]:
    path = root / "00_制作控制/用户确认记录.jsonl"
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if required:
            issues.append(issue("error", "confirmation_log_missing", "阶段已确认或推进到后续阶段时必须存在用户确认记录。", path))
        return []
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "confirmation_log_unreadable", f"用户确认记录无法读取：{exc}", path))
        return []

    records: list[dict[str, Any]] = []
    full_revisions_by_scope: dict[tuple[str, str], set[int]] = {}
    interaction_call_ids: dict[str, tuple[str, str, str]] = {}
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            issues.append(issue("error", "confirmation_log_blank_line", f"用户确认记录第 {line_number} 行为空行。", path))
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(issue("error", "confirmation_log_json_invalid", f"用户确认记录第 {line_number} 行不是有效 JSON：{exc}", path))
            continue
        if not isinstance(data, dict):
            issues.append(issue("error", "confirmation_log_row_invalid", f"用户确认记录第 {line_number} 行必须是对象。", path))
            continue
        stage = data.get("stage")
        if stage not in STAGES:
            issues.append(issue("error", "confirmation_stage_invalid", f"用户确认记录第 {line_number} 行 stage 无效。", path))
        episode_id = str(data.get("episode_id") or "")
        if episode_id and not re.fullmatch(r"ep_[1-9]\d*", episode_id):
            issues.append(issue("error", "confirmation_episode_id_invalid", f"用户确认记录第 {line_number} 行 episode_id 无效。", path))
        if stage == "planning" and episode_id:
            issues.append(issue("error", "project_confirmation_has_episode", f"用户确认记录第 {line_number} 行 planning 阶段不得填写 episode_id。", path))
        if stage in EPISODE_STAGES - {"script"} and not episode_id:
            issues.append(issue("error", "episode_confirmation_missing_episode_id", f"用户确认记录第 {line_number} 行 {stage} 阶段必须填写 episode_id。", path))
        if data.get("decision") != "confirmed":
            issues.append(issue("error", "confirmation_decision_invalid", f"用户确认记录第 {line_number} 行 decision 必须是 confirmed。", path))
        if data.get("confirmation_mode") not in CONFIRMATION_MODES:
            issues.append(issue("error", "confirmation_mode_invalid", f"用户确认记录第 {line_number} 行 confirmation_mode 无效。", path))
        if not isinstance(data.get("revision"), int) or isinstance(data.get("revision"), bool):
            issues.append(issue("error", "confirmation_revision_invalid", f"用户确认记录第 {line_number} 行 revision 必须是整数。", path))
        if not str(data.get("user_message") or "").strip():
            issues.append(issue("error", "confirmation_user_message_missing", f"用户确认记录第 {line_number} 行 user_message 不能为空。", path))
        confirmed_at = str(data.get("confirmed_at") or "")
        if parse_iso_time(confirmed_at) is None:
            issues.append(issue("error", "confirmation_time_invalid", f"用户确认记录第 {line_number} 行 confirmed_at 必须是带时区 ISO-8601 时间。", path))
        call_id = str(data.get("interaction_ask_call_id") or "").strip()
        if call_id:
            purpose_key = (str(data.get("confirmation_purpose") or ""), str(data.get("interaction_ask_result") or ""), f"{stage}:{episode_id}")
            previous_purpose = interaction_call_ids.get(call_id)
            if previous_purpose is not None and previous_purpose != purpose_key:
                issues.append(issue("error", "interaction_call_id_reused", f"用户确认记录第 {line_number} 行 interaction_ask_call_id 已被其他用途使用。", path))
            interaction_call_ids[call_id] = purpose_key
        if data.get("confirmation_mode") == "incremental":
            base_revision = data.get("base_revision")
            if not isinstance(base_revision, int) or isinstance(base_revision, bool):
                issues.append(issue("error", "confirmation_base_revision_invalid", f"用户确认记录第 {line_number} 行 incremental 必须填写整数 base_revision。", path))
            elif base_revision not in full_revisions_by_scope.get((str(stage), episode_id), set()):
                issues.append(issue("error", "confirmation_base_revision_missing", f"用户确认记录第 {line_number} 行找不到同阶段对应的全量确认 base_revision。", path))
            if not isinstance(data.get("changed_artifacts"), list) or not data.get("changed_artifacts"):
                issues.append(issue("error", "confirmation_changed_artifacts_missing", f"用户确认记录第 {line_number} 行 incremental 必须填写 changed_artifacts。", path))
            if not isinstance(data.get("impact_scope"), list) or not data.get("impact_scope"):
                issues.append(issue("error", "confirmation_impact_scope_missing", f"用户确认记录第 {line_number} 行 incremental 必须填写 impact_scope。", path))
        elif data.get("confirmation_mode") == "full" and isinstance(data.get("revision"), int) and not isinstance(data.get("revision"), bool):
            full_revisions_by_scope.setdefault((str(stage), episode_id), set()).add(data["revision"])
        records.append(data)
    if require_planning_interaction:
        planning_records = [record for record in records if record.get("stage") == "planning"]
        latest_revision = max(
            (
                record.get("revision")
                for record in planning_records
                if isinstance(record.get("revision"), int) and not isinstance(record.get("revision"), bool)
            ),
            default=None,
        )
        latest_records = [record for record in planning_records if record.get("revision") == latest_revision]
        expected_purpose = "project_execution"
        expected_result = "proceed_project"
        if not any(
            record.get("confirmation_purpose") == expected_purpose
            and str(record.get("interaction_ask_call_id") or "").strip()
            and record.get("interaction_ask_result") == expected_result
            for record in latest_records
        ):
            issues.append(issue("error", "planning_interaction_confirmation_missing", f"最新 planning 确认必须记录 {expected_purpose}、真实 interaction_ask_call_id 和 {expected_result}。", path))
    return records


def check_operation_log_tools(root: Path, issues: list[dict[str, Any]]) -> None:
    path = root / "00_制作控制/操作日志.jsonl"
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "operation_log_unreadable", f"操作日志无法读取：{exc}", path))
        return
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        tool_name = str(data.get("tool") or "").strip().lower()
        if tool_name in FORBIDDEN_TOOL_TERMS:
            issues.append(issue("error", "forbidden_media_tool_used", f"操作日志第 {line_number} 行登记了禁用工具 {tool_name}；媒体处理必须使用 tools/video/ffmpeg_tool.py 本地链路。", path))


def has_confirmation(
    records: list[dict[str, Any]],
    stage: str,
    revision: int | None,
    episode_id: str | None = None,
) -> bool:
    for record in records:
        if record.get("stage") != stage or record.get("decision") != "confirmed":
            continue
        if revision is not None and record.get("revision") != revision:
            continue
        record_episode = str(record.get("episode_id") or "")
        if episode_id is not None and record_episode != episode_id:
            continue
        if episode_id is None and record_episode:
            continue
        if str(record.get("user_message") or "").strip():
            return True
    return False


def check_state(root: Path, plan: Any, issues: list[dict[str, Any]]) -> None:
    state_path = root / "00_制作控制/制作状态.json"
    state = load_json(state_path, issues, required=False)
    if not isinstance(state, dict):
        return
    current = state.get("current_stage")
    current_episode = state.get("current_episode")
    phases = state.get("phases")
    if current not in STAGES:
        issues.append(issue("error", "current_stage_invalid", "current_stage 不是有效阶段。", state_path))
    if not isinstance(phases, dict):
        issues.append(issue("error", "phases_invalid", "phases 必须是对象。", state_path))
        return
    revision = plan_revision(plan, state)
    target = target_stage(plan)
    # objective.target_stage 合法性由随各阶段运行的 check_plan_durations 统一上报，此处不重复。
    episode_ids = [episode_id for episode_id, _ in episode_dirs(root)]
    needs_confirmations = False
    for stage in STAGES:
        value = phases.get(stage)
        if value not in STATUS_VALUES:
            issues.append(issue("error", "phase_status_invalid", f"{stage} 状态无效。", state_path))
        if value == "confirmed":
            needs_confirmations = True
    project_level_stage = current == "planning" or (current == "script" and current_episode in {None, ""})
    if project_level_stage:
        if current_episode not in {None, ""}:
            issues.append(issue("error", "current_episode_must_be_empty", f"current_stage={current} 时 current_episode 必须为空。", state_path))
        current_index = STAGES.index(current)
        for index, stage in enumerate(STAGES):
            value = phases.get(stage)
            if index < current_index and value != "confirmed":
                issues.append(issue("error", "phase_order_invalid", f"{stage} 应先完成后再进入 {current}。", state_path))
            if index > current_index and value not in {"pending", "invalidated"}:
                issues.append(issue("error", "future_phase_status_invalid", f"{stage} 晚于 current_stage={current}，只能是 pending 或 invalidated。", state_path))
            if index == current_index:
                allowed_current = set(CURRENT_STAGE_ACTIVE_VALUES)
                if current == "final" or current == target:
                    allowed_current.add("confirmed")
                if value not in allowed_current:
                    issues.append(issue("error", "current_phase_status_invalid", f"{stage} 是 current_stage，状态不能是 {value}。", state_path))
        if current_index > 0:
            needs_confirmations = True
    elif current in EPISODE_STAGES:
        if current_episode not in episode_ids:
            issues.append(issue("error", "current_episode_invalid", "逐集生产阶段必须把 current_episode 指向计划内分集。", state_path))
        if target in STAGES and STAGES.index(current) > STAGES.index(target):
            issues.append(issue("error", "current_stage_beyond_target", f"current_stage={current} 不得晚于 objective.target_stage={target}。", state_path))
        if phases.get("planning") != "confirmed":
            issues.append(issue("error", "project_prerequisite_not_confirmed", "进入逐集生产前 phases.planning 必须为 confirmed。", state_path))
        if phases.get("script") != "confirmed":
            issues.append(issue("error", "project_prerequisite_not_confirmed", "进入逐集生产前项目级 phases.script 必须为 confirmed。", state_path))
        needs_confirmations = True
    confirmations = load_confirmation_records(
        root,
        issues,
        needs_confirmations,
        require_planning_interaction=target in {"video", "final"},
    )
    for stage in ("planning", "script"):
        value = phases.get(stage)
        required_revision = revision if stage == current and current_episode in {None, ""} else None
        if value == "confirmed" and not has_confirmation(confirmations, stage, required_revision):
            detail = "同阶段、同 revision" if stage == current else "同阶段"
            issues.append(issue("error", "phase_confirmation_missing", f"{stage} 已 confirmed，但缺少{detail}的有效用户确认记录。", state_path))
    episodes = state.get("episodes")
    if not isinstance(episodes, dict):
        issues.append(issue("error", "episode_states_invalid", "制作状态.json.episodes 必须是对象并覆盖全部计划分集。", state_path))
        return
    state_episode_ids = set(episodes)
    expected_episode_ids = set(episode_ids)
    if state_episode_ids != expected_episode_ids:
        missing = sorted(expected_episode_ids - state_episode_ids)
        extra = sorted(state_episode_ids - expected_episode_ids)
        if missing:
            issues.append(issue("error", "episode_states_missing", f"制作状态.json.episodes 缺少计划分集：{missing}", state_path))
        if extra:
            issues.append(issue("error", "episode_states_unplanned", f"制作状态.json.episodes 包含计划外分集：{extra}", state_path))
    if isinstance(episodes, dict):
        for episode_id, episode_state in episodes.items():
            if not re.fullmatch(r"ep_[1-9]\d*", str(episode_id)):
                issues.append(issue("error", "episode_id_invalid", f"分集 ID 无效：{episode_id}", state_path))
            statuses = episode_state.get("stage_status") if isinstance(episode_state, dict) else None
            if not isinstance(statuses, dict):
                issues.append(issue("error", "episode_stage_statuses_invalid", f"{episode_id}.stage_status 必须是对象。", state_path))
                continue
            missing_stages = [stage for stage in EPISODE_STAGES if stage not in statuses]
            if missing_stages:
                issues.append(issue("error", "episode_stage_statuses_missing", f"{episode_id}.stage_status 缺少阶段：{missing_stages}", state_path))
            if isinstance(statuses, dict):
                for stage, value in statuses.items():
                    if stage in EPISODE_STAGES and value not in STATUS_VALUES:
                        issues.append(issue("error", "episode_stage_status_invalid", f"{episode_id}.{stage} 状态无效。", state_path))
                if current == "planning":
                    for stage in EPISODE_STAGES:
                        value = statuses.get(stage)
                        if value is not None and value not in {"pending", "invalidated"}:
                            issues.append(issue("error", "episode_stage_before_planning_confirmed", f"项目仍在 planning，{episode_id}.{stage} 只能是 pending 或 invalidated。", state_path))
                elif current == "script" and current_episode in {None, ""}:
                    script_value = statuses.get("script")
                    if script_value not in {"pending", "invalidated"}:
                        issues.append(issue("error", "episode_script_started_before_global_confirmation", f"{episode_id}.script 在项目级故事包确认前只能是 pending 或 invalidated。", state_path))
                    for stage in STAGES[2:]:
                        value = statuses.get(stage)
                        if value is not None and value not in {"pending", "invalidated"}:
                            issues.append(issue("error", "episode_stage_before_script_confirmed", f"项目级故事包尚未确认，{episode_id}.{stage} 只能是 pending 或 invalidated。", state_path))
                elif current in EPISODE_STAGES and current_episode in episode_ids:
                    episode_position = episode_ids.index(episode_id) if episode_id in episode_ids else -1
                    active_position = episode_ids.index(str(current_episode))
                    if episode_position < active_position:
                        completed_through = STAGES.index(target) if target in EPISODE_STAGES else STAGES.index("final")
                        for stage in EPISODE_STAGES:
                            stage_index = STAGES.index(stage)
                            if stage_index <= completed_through:
                                if statuses.get(stage) != "confirmed":
                                    issues.append(issue("error", "previous_episode_incomplete", f"{episode_id}.{stage} 必须完成后才能推进 {current_episode}。", state_path))
                            elif statuses.get(stage) not in {"pending", "invalidated"}:
                                issues.append(issue("error", "previous_episode_beyond_target", f"{episode_id}.{stage} 超出 target_stage={target}，只能是 pending 或 invalidated。", state_path))
                    elif episode_position > active_position:
                        if statuses.get("script") not in {"pending", "invalidated"}:
                            issues.append(issue("error", "future_episode_script_started_early", f"{episode_id}.script 在该集开始制作前只能是 pending 或 invalidated。", state_path))
                        for stage in STAGES[2:]:
                            if statuses.get(stage) not in {"pending", "invalidated"}:
                                issues.append(issue("error", "future_episode_started_early", f"{episode_id}.{stage} 在 {current_episode} 达到目标前只能是 pending 或 invalidated。", state_path))
                    else:
                        current_episode_index = STAGES.index(current)
                        if current != "script" and statuses.get("script") != "confirmed":
                            issues.append(issue("error", "current_episode_script_incomplete", f"{episode_id}.script 必须在后续生产前确认为 confirmed。", state_path))
                        for stage in EPISODE_STAGES:
                            value = statuses.get(stage)
                            index = STAGES.index(stage)
                            if index < current_episode_index and value != "confirmed":
                                issues.append(issue("error", "episode_phase_order_invalid", f"{episode_id}.{stage} 应先完成后再进入 {current}。", state_path))
                            if index > current_episode_index and value not in {"pending", "invalidated"}:
                                issues.append(issue("error", "episode_future_phase_status_invalid", f"{episode_id}.{stage} 晚于当前集 current_stage={current}，只能是 pending 或 invalidated。", state_path))
                            if index == current_episode_index:
                                allowed_current = set(CURRENT_STAGE_ACTIVE_VALUES)
                                current_is_last_episode = episode_position == len(episode_ids) - 1
                                if current_is_last_episode and current in {"final", target}:
                                    allowed_current.add("confirmed")
                                if value not in allowed_current:
                                    issues.append(issue("error", "episode_current_phase_status_invalid", f"{episode_id}.{stage} 是当前集阶段，状态不能是 {value}。", state_path))
                for stage in EPISODE_STAGES:
                    if statuses.get(stage) != "confirmed":
                        continue
                    if stage == "script":
                        if not has_confirmation(confirmations, "script", None, episode_id):
                            issues.append(issue("error", "episode_script_confirmation_missing", f"{episode_id}.script 已 confirmed，但缺少绑定该集的详细剧本确认记录。", state_path))
                        continue
                    required_revision = revision if episode_id == current_episode and stage == current else None
                    if not has_confirmation(
                        confirmations,
                        stage,
                        required_revision,
                        episode_id,
                    ):
                        issues.append(issue("error", "episode_confirmation_missing", f"{episode_id}.{stage} 已 confirmed，但缺少绑定该集的有效确认记录。", state_path))
        for stage in STAGES[2:]:
            if phases.get(stage) != "confirmed":
                continue
            stage_values = [
                episode_state.get("stage_status", {}).get(stage)
                for episode_state in episodes.values()
                if isinstance(episode_state, dict) and isinstance(episode_state.get("stage_status"), dict)
            ]
            if not stage_values or any(value != "confirmed" for value in stage_values):
                issues.append(issue("error", "aggregate_phase_confirmed_early", f"phases.{stage} 只有在全部分集该阶段完成后才能写 confirmed。", state_path))
        if current in EPISODE_STAGES and current_episode in episodes:
            current_statuses = episodes[current_episode].get("stage_status") if isinstance(episodes[current_episode], dict) else {}
            current_index = STAGES.index(current)
            for stage in STAGES[2:]:
                phase_value = phases.get(stage)
                stage_index = STAGES.index(stage)
                completed_values = {"confirmed"}
                all_completed = all(
                    isinstance(episode_state, dict)
                    and isinstance(episode_state.get("stage_status"), dict)
                    and episode_state["stage_status"].get(stage) in completed_values
                    for episode_state in episodes.values()
                )
                any_completed = any(
                    isinstance(episode_state, dict)
                    and isinstance(episode_state.get("stage_status"), dict)
                    and episode_state["stage_status"].get(stage) in completed_values
                    for episode_state in episodes.values()
                )
                if all_completed:
                    if phase_value != "confirmed":
                        issues.append(issue("error", "aggregate_phase_status_mismatch", f"phases.{stage} 必须反映全部分集已完成。", state_path))
                elif stage == current:
                    current_value = current_statuses.get(stage) if isinstance(current_statuses, dict) else None
                    if phase_value != current_value:
                        issues.append(issue("error", "aggregate_current_phase_mismatch", f"phases.{stage} 必须与 {current_episode}.{stage} 当前活动状态一致。", state_path))
                elif stage_index > current_index and phase_value not in ({"pending", "invalidated", "in_progress"} if any_completed else {"pending", "invalidated"}):
                    issues.append(issue("error", "aggregate_future_phase_started", f"phases.{stage} 与已完成分集的聚合状态不一致。", state_path))
                elif stage_index < current_index and phase_value not in {"in_progress", "confirmed"}:
                    issues.append(issue("error", "aggregate_previous_phase_invalid", f"phases.{stage} 已有分集完成但尚未全量完成，必须保持 in_progress 或合法完成态。", state_path))

# ===== 原 lint_checks/causal.py =====



def check_world_facts(data: dict[str, Any], path: Path, issues: list[dict[str, Any]]) -> None:
    """inherited_world_facts 的结构检查：强制世界事实被显式登记并注明剧本出处。

    语义矛盾（如霜气 vs 中元节）不属于 lint 职责，由剧本-分镜对照审校步骤处理；
    本检查的意义是让审校有对照表可查。
    """
    facts = data.get("inherited_world_facts")
    if not isinstance(facts, list) or not facts:
        issues.append(issue("error", "world_facts_missing", "storyboard 必须登记 inherited_world_facts：从剧本继承的季节/节日/时辰/天气等世界事实。", path, ))
        return
    check_unique(facts, "fact_id", path, issues, "inherited_world_facts")
    for index, fact in enumerate(facts, start=1):
        if not isinstance(fact, dict):
            issues.append(issue("error", "world_fact_invalid", f"第 {index} 条世界事实必须是对象。", path))
            continue
        if fact.get("category") not in WORLD_FACT_CATEGORIES:
            issues.append(issue("error", "world_fact_category_invalid", f"第 {index} 条世界事实 category 无效：{fact.get('category')}", path))
        if not str(fact.get("statement") or "").strip() or not str(fact.get("source") or "").strip():
            issues.append(issue("error", "world_fact_incomplete", f"第 {index} 条世界事实缺少 statement 或 source（剧本出处）。", path))


def check_beat_coverage(
    data: dict[str, Any],
    shot_ids: set[str],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    """beat_coverage 台账的结构检查：剧本每条动作/事件必须登记去向。

    dropped 必须给理由；kept/compressed/moved 必须落到真实存在的镜头。
    剧本 beat 的提取是语义工作，由分镜作者完成；lint 验证台账完整性与引用有效性。
    """
    beats = data.get("beat_coverage")
    if not isinstance(beats, list):
        issues.append(issue("error", "beat_coverage_missing", "storyboard 必须登记 beat_coverage：剧本每条动作/事件的去向台账。", path, ))
        return
    check_unique(beats, "beat_id", path, issues, "beat_coverage")
    for index, beat in enumerate(beats, start=1):
        if not isinstance(beat, dict):
            issues.append(issue("error", "beat_invalid", f"第 {index} 条 beat 必须是对象。", path))
            continue
        label = beat.get("beat_id") or f"第 {index} 条"
        disposition = beat.get("disposition", beat.get("status"))
        if disposition not in BEAT_DISPOSITIONS:
            issues.append(issue("error", "beat_disposition_invalid", f"{label} disposition 无效。", path))
            continue
        if not str(beat.get("summary") or "").strip() or not str(beat.get("scene") or "").strip():
            issues.append(issue("error", "beat_incomplete", f"{label} 缺少 scene 或 summary。", path))
        targets = beat.get("target_shots")
        if disposition == "dropped":
            if not str(beat.get("reason") or "").strip():
                issues.append(issue("error", "beat_drop_reason_missing", f"{label} 被 dropped 但未给理由。", path))
        else:
            if not isinstance(targets, list) or not targets:
                issues.append(issue("error", "beat_target_missing", f"{label} disposition={disposition} 时 target_shots 必须非空。", path))
            else:
                unknown = [t for t in targets if t not in shot_ids]
                if unknown:
                    issues.append(issue("error", "beat_unknown_shot", f"{label} 引用了不存在的镜头：{unknown}", path))


def validate_collective_profiles(root: Path, issues: list[dict[str, Any]]) -> set[str]:
    """Validate the explicit visual profile contract for collective CHR records."""
    path = root / "00_制作控制/project_data_card.json"
    card = load_json(path, issues, required=False)
    collective_ids: set[str] = set()
    if not isinstance(card, dict):
        return collective_ids
    for index, item in enumerate(card.get("characters") or []):
        if not isinstance(item, dict):
            continue
        scope = item.get("entity_scope", "individual")
        if scope not in {"individual", "collective"}:
            issues.append(issue("error", "character_entity_scope_invalid", f"characters[{index}].entity_scope 必须为 individual 或 collective。", path))
            continue
        if scope != "collective":
            continue
        asset_id = str(item.get("character_id") or "")
        if not re.fullmatch(r"CHR\d+", asset_id):
            issues.append(issue("error", "collective_character_id_invalid", f"characters[{index}] 群像必须使用 CHR ID。", path))
        else:
            collective_ids.add(asset_id)
        profile = item.get("collective_profile")
        if not isinstance(profile, dict):
            issues.append(issue("error", "collective_profile_missing", f"{asset_id or f'characters[{index}]'} 必须填写 collective_profile。", path))
            continue
        if not str(profile.get("group_type") or "").strip():
            issues.append(issue("error", "collective_group_type_missing", f"{asset_id} collective_profile.group_type 不能为空。", path))
        count_range = profile.get("count_range")
        if not isinstance(count_range, dict):
            issues.append(issue("error", "collective_count_range_missing", f"{asset_id} collective_profile.count_range 必须包含 min/max。", path))
        else:
            minimum, maximum = count_range.get("min"), count_range.get("max")
            valid_ints = all(isinstance(value, int) and not isinstance(value, bool) for value in (minimum, maximum))
            if not valid_ints or minimum < 1 or maximum < minimum:
                issues.append(issue("error", "collective_count_range_invalid", f"{asset_id} collective_profile.count_range 必须满足 1 <= min <= max。", path))
        for field in ("age_and_gender_mix", "role_or_faction_mix", "wardrobe_palette_distribution", "silhouette_distinction_keys"):
            value = profile.get(field)
            if not isinstance(value, list) or not any(str(entry).strip() for entry in value):
                issues.append(issue("error", "collective_profile_field_missing", f"{asset_id} collective_profile.{field} 必须是非空数组。", path))
        for field in ("shared_props", "forbidden_features"):
            if not isinstance(profile.get(field), list):
                issues.append(issue("error", "collective_profile_field_invalid", f"{asset_id} collective_profile.{field} 必须是数组；无内容时填空数组。", path))
        if profile.get("voice_mode") not in {"none", "collective_ambience"}:
            issues.append(issue("error", "collective_voice_mode_invalid", f"{asset_id} collective_profile.voice_mode 必须为 none 或 collective_ambience。", path))
        refs = item.get("asset_refs") if isinstance(item.get("asset_refs"), dict) else {}
        if refs.get("collective_profile") != asset_id:
            issues.append(issue("error", "collective_asset_ref_mismatch", f"{asset_id} asset_refs.collective_profile 必须指向该群像 CHR。", path))
        identity = item.get("identity_locked")
        if isinstance(identity, dict) and str(identity.get("voice_id") or "").strip():
            issues.append(issue("error", "collective_individual_voice_invalid", f"{asset_id} 群像不能绑定单人 identity_locked.voice_id。", path))
    return collective_ids


# ===== 原 lint_checks/assets.py =====

import subprocess
import wave


def asset_version_key(asset_id: str, version: str, separator: str = "_") -> str:
    return f"{asset_id}{separator}{version}"


def version_rank(version: str) -> int:
    match = re.search(r"\d+", version)
    return int(match.group()) if match else -1


def split_asset_version_ref(ref: Any) -> tuple[str, str] | None:
    if not isinstance(ref, str):
        return None
    for separator in ("_", ":"):
        head, sep, tail = ref.rpartition(separator)
        if sep and head and re.fullmatch(r"v\d+", tail, flags=re.I):
            return head, tail
    return None


def blank_asset_index() -> dict[str, Any]:
    return {
        "known_asset_ids": set(),
        "known_version_refs": set(),
        "approved_version_refs": set(),
        "approved_versions_by_asset": {},
        "latest_approved_version": {},
        "known_state_refs": set(),
        "approved_state_refs": set(),
        # registry 中 category=voice、status=approved 的 asset_id 集合（即存在可用 approved 样音的声部）。
        "approved_voice_ids": set(),
    }


def remember_asset_version(index: dict[str, Any], asset_id: str, version: str, status: Any) -> None:
    index["known_asset_ids"].add(asset_id)
    if version:
        underscore_ref = asset_version_key(asset_id, version, "_")
        colon_ref = asset_version_key(asset_id, version, ":")
        index["known_version_refs"].add(underscore_ref)
        index["known_version_refs"].add(colon_ref)
        if status == "approved":
            index["approved_version_refs"].add(underscore_ref)
            index["approved_version_refs"].add(colon_ref)
            approved = index["approved_versions_by_asset"].setdefault(asset_id, set())
            approved.add(version)
            latest = index["latest_approved_version"].get(asset_id)
            if latest is None or version_rank(version) > version_rank(latest):
                index["latest_approved_version"][asset_id] = version


def state_ref_keys(asset_id: str, state_id: str, version: str = "") -> set[str]:
    refs = {f"{asset_id}:{state_id}"}
    if version:
        refs.add(f"{asset_id}:{state_id}_{version}")
        refs.add(f"{asset_id}:{state_id}:{version}")
    return refs


def remember_state_version(index: dict[str, Any], asset_id: str, state_id: str, version: str, status: Any) -> None:
    refs = state_ref_keys(asset_id, state_id, version)
    index["known_state_refs"].update(refs)
    if status == "approved":
        index["approved_state_refs"].update(refs)


def check_stale_asset_version(ref: Any, index: dict[str, Any], path: Path, issues: list[dict[str, Any]], owner: str) -> None:
    parsed = split_asset_version_ref(ref)
    if parsed is None:
        return
    asset_id, version = parsed
    latest = index["latest_approved_version"].get(asset_id)
    if latest and version_rank(version) < version_rank(latest):
        issues.append(issue("error", "downstream_asset_version_stale", f"{owner} 仍引用旧资产版本 {ref}；最新 approved 版本是 {asset_version_key(asset_id, latest)}。", path))


def check_voice_sample(root, asset, path, issues):
    if asset.get("category") != "voice" or asset.get("status") != "approved":
        return
    label = asset.get("asset_id") or "VOICE"
    files = asset.get("files")
    value = asset.get("file") or (files[0] if isinstance(files, list) and len(files) == 1 else None)
    try:
        if files and (not isinstance(files, list) or files != [value]):
            raise ValueError("音色必须指向唯一真实样音，file/files 不得冲突")
        if isinstance(value, str) and is_url(value):
            # URL identity remains the original string; never fetch it for lint.
            duration = asset.get("duration_s")
        else:
            audio = relative_file(root, value)
            if audio is None or not audio.is_file():
                raise ValueError("缺真实音色文件或有效 HTTP(S) URL")
            if audio.suffix.lower() == ".wav":
                with wave.open(str(audio), "rb") as sample:
                    if sample.getframerate() <= 0:
                        raise ValueError("WAV 采样率无效")
                    duration = sample.getnframes() / sample.getframerate()
            else:
                result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                    "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(audio)],
                    capture_output=True, text=True, encoding="utf-8", timeout=30)
                metadata = json.loads(result.stdout)
                if result.returncode or not metadata.get("streams"):
                    raise ValueError("未探测到可用音频流")
                duration = float(metadata["format"]["duration"])
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
            raise ValueError("需有效音频时长；URL 从已知媒体事实登记 duration_s，lint 不下载")
        if "duration_s" in asset and (isinstance(asset["duration_s"], bool)
                or not isinstance(asset["duration_s"], (int, float))
                or not math.isfinite(asset["duration_s"]) or abs(asset["duration_s"] - duration) > .001):
            issues.append(issue("error", "voice_sample_duration_mismatch", f"{label} 登记时长与本地音频实测不同。", path))
    except (OSError, ValueError, TypeError, KeyError, wave.Error, EOFError, subprocess.TimeoutExpired) as exc:
        issues.append(issue("error", "voice_sample_invalid", f"{label} 音色技术核验失败：{exc}", path))


def check_reused_voice_sample(root, asset, source_episode, cache, issues):
    """Resolve a current episode's VOICE to its original approved record, without copying it."""
    asset_id = str(asset.get("asset_id") or "")
    if not asset_id.startswith("VOICE"):
        return
    origin = source_episode
    record = asset
    while record.get("source_episode_id"):
        previous = record["source_episode_id"]
        path = root / f"episodes/{origin}/03_资产/asset_usage_{origin}.json"
        if (not isinstance(previous, str) or not re.fullmatch(r"ep_[1-9]\d*", previous)
                or int(previous.split("_")[1]) >= int(origin.split("_")[1])):
            issues.append(issue("error", "voice_sample_source_invalid", f"{asset_id} 音色复用来源必须指向更早分集。", path))
            return
        if previous not in cache:
            source_path = root / f"episodes/{previous}/03_资产/asset_usage_{previous}.json"
            cache[previous] = load_json(source_path, issues, required=False)
        source = cache[previous]
        candidates = []
        if isinstance(source, dict):
            for field in ("episode_assets", "reused_episode_assets"):
                rows = source.get(field)
                if isinstance(rows, list):
                    candidates.extend(row for row in rows if isinstance(row, dict)
                        and row.get("asset_id") == asset_id and row.get("status") == "approved"
                        and str(row.get("state_id") or "") == str(record.get("state_id") or "")
                        and row.get("version") == record.get("version"))
        if len(candidates) != 1 or candidates[0].get("files", []) != record.get("files", []):
            issues.append(issue("error", "voice_sample_source_invalid", f"{asset_id} 音色复用链缺唯一、文件一致的 approved 来源。", path))
            return
        record, origin = candidates[0], previous
    path = root / f"episodes/{origin}/03_资产/asset_usage_{origin}.json"
    if record.get("category") != "voice":
        issues.append(issue("error", "voice_sample_source_invalid", f"{asset_id} 原批准记录未登记为 voice。", path))
        return
    check_voice_sample(root, record, path, issues)


def check_assets(root: Path, issues: list[dict[str, Any]], episode_filter: str | None = None) -> dict[str, Any]:
    registry_path = root / "shared/03_资产/asset_registry.json"
    registry = load_json(registry_path, issues, required=False)
    collective_ids = validate_collective_profiles(root, issues)
    index = blank_asset_index()
    source_usage_cache: dict[str, dict[str, Any] | None] = {}
    if isinstance(registry, dict):
        assets = registry.get("assets")
        if isinstance(assets, list):
            version_keys: set[tuple[str, str]] = set()
            for asset in assets:
                if not isinstance(asset, dict):
                    continue
                asset_id = asset.get("asset_id")
                category = asset.get("category")
                entity_scope = asset.get("entity_scope", "individual")
                version = str(asset.get("version") or "")
                if category == "character":
                    if entity_scope not in {"individual", "collective"}:
                        issues.append(issue("error", "asset_entity_scope_invalid", f"{asset_id or '角色资产'} entity_scope 必须为 individual 或 collective。", registry_path))
                    elif isinstance(asset_id, str) and asset_id in collective_ids and entity_scope != "collective":
                        issues.append(issue("error", "collective_asset_scope_mismatch", f"{asset_id} 在项目数据卡中是群像，registry 必须登记 entity_scope=collective。", registry_path))
                    elif entity_scope == "collective" and asset_id not in collective_ids:
                        issues.append(issue("error", "collective_asset_data_card_missing", f"{asset_id or '群像资产'} 登记为 collective，但项目数据卡没有对应群像角色记录。", registry_path))
                elif "entity_scope" in asset:
                    issues.append(issue("error", "asset_entity_scope_not_character", f"{asset_id or '资产'} 只有 character 类资产可填写 entity_scope。", registry_path))
                if isinstance(asset_id, str) and asset_id.strip():
                    remember_asset_version(index, asset_id, version, asset.get("status"))
                    key = (asset_id, version)
                    if key in version_keys:
                        issues.append(issue("error", "asset_version_duplicate", f"asset_id + version 重复：{asset_id} {version}", registry_path))
                    version_keys.add(key)
                else:
                    issues.append(issue("error", "asset_id_missing", "资产缺少 asset_id。", registry_path))
                status = asset.get("status")
                check_voice_sample(root, asset, registry_path, issues)
                if category == "voice" and status == "approved" and isinstance(asset_id, str) and asset_id.strip():
                    # 技术核验由 check_voice_sample 独立报错；此处只回答「该声部有没有 approved 样音」。
                    index["approved_voice_ids"].add(asset_id.strip())
                if status is not None and status not in ASSET_STATUS_VALUES:
                    issues.append(issue("error", "asset_status_invalid", f"资产状态无效：{status}", registry_path))
                state_id = str(asset.get("state_id") or "")
                if isinstance(asset_id, str) and asset_id.strip() and state_id:
                    remember_state_version(index, asset_id, state_id, version, status)
                for file_value in asset.get("files") or []:
                    if not media_location_valid(root, file_value):
                        issues.append(issue("error", "asset_file_missing", f"资产缺本地文件或有效 HTTP(S) 引用：{file_value}", registry_path))
                generation = asset.get("generation") if isinstance(asset.get("generation"), dict) else {}
                tool = generation.get("tool")
                refs = [*asset.get("reference_asset_ids", [])] if isinstance(asset.get("reference_asset_ids"), list) else []
                available_visual_refs = []
                for field_owner in (asset, generation):
                    value = field_owner.get("available_visual_reference_ids") if isinstance(field_owner, dict) else None
                    if isinstance(value, list):
                        available_visual_refs.extend(item for item in value if isinstance(item, str) and item.strip())
                visual_reference_decision = asset.get("visual_reference_decision") or generation.get("visual_reference_decision")
                if visual_reference_decision is not None and visual_reference_decision not in VISUAL_REFERENCE_DECISIONS:
                    issues.append(issue("error", "visual_reference_decision_invalid", f"{asset_id} visual_reference_decision 无效：{visual_reference_decision}", registry_path))
                visual_inputs = []
                for field in ("reference_inputs", "input_files", "input_images"):
                    value = generation.get(field)
                    if isinstance(value, list):
                        visual_inputs.extend(value)
                style_anchor_refs = combined_strings(asset, generation, field="style_anchor_reference_ids")
                style_terms = combined_strings(asset, generation, field="style_prompt_terms")
                project_visual_mode = asset.get("project_visual_mode") or generation.get("project_visual_mode")
                if category in {"character", "scene", "prop", "style"} and status == "approved":
                    if project_visual_mode not in PROJECT_VISUAL_MODES:
                        issues.append(issue("error", "project_visual_mode_missing_or_invalid", f"{asset_id or '资产'} approved 图片资产必须登记有效 project_visual_mode。", registry_path))
                if tool == "image_gen" and (refs or visual_inputs):
                    issues.append(issue("error", "image_gen_should_not_have_visual_inputs", f"{asset_id} 使用 image_gen 时不应登记图片参考输入。", registry_path))
                if tool == "image_gen" and available_visual_refs and visual_reference_decision != "explicit_user_override":
                    issues.append(issue("error", "image_gen_visual_reference_available", f"{asset_id} 已登记可用视觉参考，必须使用 image_edit；除非用户明确要求不参考并记录 explicit_user_override。", registry_path))
                if tool == "image_gen" and visual_reference_decision == "used":
                    issues.append(issue("error", "image_gen_visual_reference_decision_conflict", f"{asset_id} visual_reference_decision=used 时不能使用 image_gen。", registry_path))
                if tool == "image_edit" and not (refs or visual_inputs or style_anchor_refs):
                    issues.append(issue("error", "image_edit_reference_missing", f"{asset_id} 使用 image_edit 时必须登记实际参考来源。", registry_path))
                if tool == "image_edit" and visual_reference_decision == "none_available":
                    issues.append(issue("error", "image_edit_visual_reference_decision_conflict", f"{asset_id} 使用 image_edit 时 visual_reference_decision 不能写 none_available。", registry_path))
                if category == "character" and state_id and tool == "image_gen" and visual_reference_decision != "explicit_user_override":
                    issues.append(issue("error", "character_state_asset_requires_image_edit", f"{asset_id or '角色状态资产'} 是人物状态资产时必须基于已批准人物图使用 image_edit；除非用户明确要求重做并记录 explicit_user_override。", registry_path))
                check_generation_prompt_file(root, registry_path, str(asset_id or "资产"), tool, generation.get("prompt_path"), issues)
                check_style_anchor_contract(
                    root,
                    registry_path,
                    str(asset_id or "资产"),
                    tool,
                    generation.get("prompt_path"),
                    style_anchor_refs,
                    style_terms,
                    combined_strings(asset, generation, field="style_adopt"),
                    combined_strings(asset, generation, field="style_exclude"),
                    issues,
                    visual_reference_decision,
                )
        elif assets is not None:
            issues.append(issue("error", "assets_invalid", "asset_registry.assets 必须是数组。", registry_path))
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"03_资产/asset_usage_{episode_id}.json"
        usage = load_json(path, issues, required=False)
        if not isinstance(usage, dict):
            continue
        shared = usage.get("shared_assets")
        reused_episode_assets = usage.get("reused_episode_assets")
        episode_assets = usage.get("episode_assets")
        for field in ("shared_assets", "episode_assets", "reused_episode_assets"):
            values = usage.get(field)
            if not isinstance(values, list):
                continue
            for item in values:
                if not isinstance(item, dict):
                    continue
                asset_id = str(item.get("asset_id") or "")
                if asset_id in collective_ids and item.get("entity_scope") != "collective":
                    issues.append(issue("error", "collective_usage_scope_mismatch", f"{episode_id} 的 {asset_id} 必须以 entity_scope=collective 登记。", path))
        if isinstance(shared, list):
            seen_shared: set[tuple[str, str]] = set()
            for item in shared:
                if not isinstance(item, dict):
                    continue
                asset_id = item.get("asset_id")
                version = str(item.get("version") or "")
                if isinstance(asset_id, str):
                    if index["known_asset_ids"] and asset_id not in index["known_asset_ids"]:
                        issues.append(issue("error", "asset_usage_unknown_shared_asset", f"{episode_id} 引用了 registry 中不存在的共享资产：{asset_id}", path))
                    if not version:
                        issues.append(issue("error", "asset_usage_shared_version_missing", f"{episode_id} 共享资产必须填写 version：{asset_id}", path))
                    else:
                        refs = {asset_version_key(asset_id, version, "_"), asset_version_key(asset_id, version, ":")}
                        if index["known_version_refs"] and not (refs & index["known_version_refs"]):
                            issues.append(issue("error", "asset_usage_unknown_shared_version", f"{episode_id} 引用了 registry 中不存在的共享资产版本：{asset_id} {version}", path))
                        elif index["known_version_refs"] and not (refs & index["approved_version_refs"]):
                            issues.append(issue("error", "asset_usage_shared_not_approved", f"{episode_id} 只能引用 registry 中 approved 的共享资产版本：{asset_id} {version}", path))
                    key = (asset_id, version)
                    if key in seen_shared:
                        issues.append(issue("error", "asset_usage_duplicate", f"{episode_id} 共享资产重复：{asset_id} {version}", path))
                    seen_shared.add(key)
        if reused_episode_assets is not None and not isinstance(reused_episode_assets, list):
            issues.append(issue("error", "reused_episode_assets_invalid", f"{episode_id} reused_episode_assets 必须是数组。", path))
        if isinstance(reused_episode_assets, list):
            seen_reused: set[tuple[str, str, str, str]] = set()
            for item in reused_episode_assets:
                if not isinstance(item, dict):
                    issues.append(issue("error", "reused_episode_asset_invalid", f"{episode_id} reused_episode_assets 每项必须是对象。", path))
                    continue
                source_episode_id = str(item.get("source_episode_id") or "")
                asset_id = str(item.get("asset_id") or "")
                state_id = str(item.get("state_id") or "")
                version = str(item.get("version") or "")
                status = item.get("status")
                source_valid = True
                if not source_episode_id:
                    issues.append(issue("error", "reused_episode_source_missing", f"{episode_id} 复用分集资产必须填写 source_episode_id。", path))
                    source_valid = False
                elif not re.fullmatch(r"ep_[1-9]\d*", source_episode_id) or int(source_episode_id.split("_", 1)[1]) >= int(episode_id.split("_", 1)[1]):
                    issues.append(issue("error", "reused_episode_source_invalid", f"{episode_id} 只能复用更早分集的 approved 资产：{source_episode_id}", path))
                    source_valid = False
                if not asset_id or not version:
                    issues.append(issue("error", "reused_episode_asset_ref_missing", f"{episode_id} 复用分集资产必须填写 asset_id 和 version。", path))
                    source_valid = False
                if status != "approved":
                    issues.append(issue("error", "reused_episode_asset_not_approved", f"{episode_id} 只能复用 approved 分集资产：{asset_id} {state_id} {version}", path))
                    source_valid = False
                if source_valid:
                    if source_episode_id not in source_usage_cache:
                        source_path = root / f"episodes/{source_episode_id}/03_资产/asset_usage_{source_episode_id}.json"
                        source_usage = load_json(source_path, issues, required=False)
                        source_usage_cache[source_episode_id] = source_usage if isinstance(source_usage, dict) else None
                    source_usage = source_usage_cache[source_episode_id]
                    source_candidates = []
                    if isinstance(source_usage, dict):
                        for field in ("episode_assets", "reused_episode_assets"):
                            values = source_usage.get(field)
                            if isinstance(values, list):
                                source_candidates.extend(candidate for candidate in values if isinstance(candidate, dict))
                    matching_source = next(
                        (
                            candidate
                            for candidate in source_candidates
                            if str(candidate.get("asset_id") or "") == asset_id
                            and str(candidate.get("state_id") or "") == state_id
                            and str(candidate.get("version") or "") == version
                            and candidate.get("status") == "approved"
                        ),
                        None,
                    )
                    if matching_source is None:
                        issues.append(issue("error", "reused_episode_asset_source_not_found", f"{episode_id} 复用资产在 {source_episode_id} 中找不到一致的 approved 来源：{asset_id} {state_id} {version}", path))
                        source_valid = False
                    elif sorted(item.get("files") or []) != sorted(matching_source.get("files") or []):
                        issues.append(issue("error", "reused_episode_asset_files_mismatch", f"{episode_id} 复用资产文件必须与 {source_episode_id} 来源记录一致：{asset_id} {state_id} {version}", path))
                        source_valid = False
                if source_valid and episode_filter:
                    check_reused_voice_sample(root, matching_source, source_episode_id, source_usage_cache, issues)
                if asset_id and source_valid:
                    remember_asset_version(index, asset_id, version, "approved" if status == "approved" else status)
                if asset_id and state_id and source_valid:
                    remember_state_version(index, asset_id, state_id, version, status)
                key = (source_episode_id, asset_id, state_id, version)
                if key in seen_reused:
                    issues.append(issue("error", "reused_episode_asset_duplicate", f"{episode_id} 复用分集资产重复：{source_episode_id} {asset_id} {state_id} {version}", path))
                seen_reused.add(key)
                for file_value in item.get("files") or []:
                    if not media_location_valid(root, file_value):
                        issues.append(issue("error", "reused_episode_asset_file_missing", f"复用分集资产缺本地文件或有效 HTTP(S) 引用：{file_value}", path))
        if isinstance(episode_assets, list):
            state_keys: set[tuple[str, str, str]] = set()
            for item in episode_assets:
                if not isinstance(item, dict):
                    continue
                asset_id = str(item.get("asset_id") or "")
                state_id = str(item.get("state_id") or "")
                version = str(item.get("version") or "")
                if asset_id:
                    remember_asset_version(index, asset_id, version, item.get("status"))
                if asset_id and state_id:
                    remember_state_version(index, asset_id, state_id, version, item.get("status"))
                key = (asset_id, state_id, version)
                if key in state_keys:
                    issues.append(issue("error", "episode_asset_duplicate", f"{episode_id} 分集资产重复：{asset_id} {state_id} {version}", path))
                state_keys.add(key)
                if item.get("status") is not None and item.get("status") not in ASSET_STATUS_VALUES:
                    issues.append(issue("error", "episode_asset_status_invalid", f"分集资产状态无效：{item.get('status')}", path))
                # episode_assets 的 schema 只有 asset_id/entity_scope/state_id/version/files/status
                # （manifests.md 唯一清单，禁止自造字段）：generation/category 类合同在本面不可达，
                # 图片工具合同只在 asset_registry 面校验，本面不做死门。
                for file_value in item.get("files") or []:
                    if not media_location_valid(root, file_value):
                        issues.append(issue("error", "episode_asset_file_missing", f"分集资产缺本地文件或有效 HTTP(S) 引用：{file_value}", path))
    return index

# ===== 原 lint_checks/prompts.py =====

from rhythm_engine import read_json
from video_confirmations import validate_confirmations, validate_project_confirmations
from h3_contract import check_purity, media_marker_orders


def ordered_inputs(root: Path, items: Any, allowed_roles: set[str], kind: str, path: Path, issues: list[dict[str, Any]]) -> tuple[list[int], set[str]]:
    if items is None:
        return [], set()
    if not isinstance(items, list):
        issues.append(issue("error", f"{kind}_inputs_invalid", f"{kind}_inputs 必须是数组。", path))
        return [], set()
    orders: list[int] = []
    roles: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            issues.append(issue("error", f"{kind}_input_invalid", f"{kind}_inputs 每项必须是对象。", path))
            continue
        order = item.get("order")
        if isinstance(order, int) and not isinstance(order, bool):
            orders.append(order)
        else:
            issues.append(issue("error", f"{kind}_input_order_invalid", f"{kind}_inputs.order 必须是整数。", path))
        role = item.get("role")
        if role in allowed_roles:
            roles.add(role)
        elif allowed_roles:
            issues.append(issue("error", f"{kind}_input_role_invalid", f"{kind}_inputs.role 无效：{role}", path))
        required_fields = ("source_id", "file", "adopt", "exclude") if kind == "reference" else ("resource_id", "file", "adopt", "exclude")
        for field in required_fields:
            if not str(item.get(field) or "").strip():
                issues.append(issue("error", f"{kind}_input_field_missing", f"{kind}_inputs.{field} 必须填写。", path))
        file_value = item.get("file")
        remote = isinstance(file_value, str) and is_url(file_value)
        if file_value and not remote and not file_exists(root, file_value):
            issues.append(issue("error", f"{kind}_input_file_missing", f"输入文件不存在或不是项目相对路径：{file_value}", path))
    if orders and sorted(orders) != list(range(1, len(orders) + 1)):
        issues.append(issue("error", f"{kind}_input_order_not_contiguous", f"{kind}_inputs.order 必须从 1 连续递增。", path))
    return orders, roles


def check_asset_ref(ref: Any, index: dict[str, Any], path: Path, issues: list[dict[str, Any]], owner: str) -> None:
    if not isinstance(ref, str) or not ref.strip():
        issues.append(issue("error", "asset_ref_invalid", f"{owner} 的 asset_refs 必须是非空字符串。", path))
        return
    if ref in index["known_asset_ids"]:
        issues.append(issue("error", "asset_ref_version_missing", f"{owner} 引用资产 {ref} 时必须带版本号。", path))
        return
    if ref not in index["known_version_refs"]:
        issues.append(issue("error", "asset_ref_unknown", f"{owner} 引用了不存在的资产版本：{ref}", path))
        return
    if ref not in index["approved_version_refs"]:
        issues.append(issue("error", "downstream_asset_not_approved", f"{owner} 引用了未 approved 的资产版本：{ref}", path))
        return
    check_stale_asset_version(ref, index, path, issues, owner)


def check_state_ref(ref: Any, index: dict[str, Any], path: Path, issues: list[dict[str, Any]], owner: str) -> None:
    if not isinstance(ref, str) or not ref.strip():
        issues.append(issue("error", "state_ref_invalid", f"{owner} 的 state_refs 必须是非空字符串。", path))
        return
    if ref not in index["known_state_refs"]:
        issues.append(issue("error", "state_ref_unknown", f"{owner} 引用了不存在的状态资产：{ref}", path))
        return
    if ref not in index["approved_state_refs"]:
        issues.append(issue("error", "downstream_state_not_approved", f"{owner} 引用了未 approved 的状态资产：{ref}", path))
        return
    check_stale_asset_version(ref, index, path, issues, owner)


def load_keyframe_ids(root: Path, episode_id: str, issues: list[dict[str, Any]]) -> set[str]:
    path = root / f"episodes/{episode_id}/03_资产/keyframe_manifest_{episode_id}.json"
    data = load_json(path, issues, required=False)
    keyframes = data.get("keyframes") if isinstance(data, dict) else None
    if not isinstance(keyframes, list):
        return set()
    return {item.get("keyframe_id") for item in keyframes if isinstance(item, dict) and item.get("status") == "approved" and isinstance(item.get("keyframe_id"), str)}


def marker_pattern(kind: str, order: int) -> str:
    patterns = {
        "image": rf"<(?:图片\s*{order}(?:\s*-\s*第\s*\d+\s*格)?|IMG\s*{order}(?:\s*-\s*Cell\s*\d+)?)\s*>",
        "video": rf"<(?:视频|VID)\s*{order}\s*>",
        "audio": rf"<(?:音频|AUD)\s*{order}\s*>",
    }
    return patterns[kind]


def check_prompt_markers(
    prompt_path: Path,
    image_orders: list[int],
    video_orders: list[int],
    audio_orders: list[int],
    speech_lines: Any,
    subtitle_enabled: bool,
    issues: list[dict[str, Any]],
    h3_mode: str = "T2VA",
) -> None:
    """校验提交给模型的 Prompt 成稿携带了全部已登记输入与台词。

    成稿格式以 h3-prompt-writing 为准，媒体序号识别与 H3 提交共用同一函数，
    包含合法锚帧首行；每条台词按 speech_key 去标点空格后必须存在于发声块。
    另核素材标记语言不混用及【】字幕源规则。
    五段式是独立导演包的组装规则，不适用于纯 H3 成稿。"""
    if not prompt_path.is_file():
        issues.append(issue("error", "prompt_missing", "Prompt 文件不存在。", prompt_path))
        return
    try:
        text = prompt_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "prompt_unreadable", f"Prompt 无法读取：{exc}", prompt_path))
        return
    expected_by_kind = {"image": sorted(image_orders), "video": sorted(video_orders), "audio": sorted(audio_orders)}
    for kind, expected in expected_by_kind.items():
        label = {"image": "图片", "video": "视频", "audio": "音频"}[kind]
        # 与提交入口共用识别规则，含 FL2VA 合法首行的无尖括号 Picture 标记。
        actual = sorted(media_marker_orders(text, h3_mode, kind))
        if actual != expected:
            issues.append(issue("error", f"prompt_{kind}_markers_mismatch", f"Prompt 中{label}标记 {actual} 必须与实际输入 order {expected} 一致（写法以 h3-prompt-writing 为准）。", prompt_path))
    if ("【" in text or "】" in text) and not subtitle_enabled:
        issues.append(issue("error", "prompt_subtitle_bracket_invalid", "未启用字幕时，最终视频 Prompt 不允许出现【】字幕源标识。", prompt_path))
    if isinstance(speech_lines, list):
        block_keys = [speech_key(block) for block in re.findall(r"<d>(.*?)</d>", text, re.S)]
        for index, line in enumerate(speech_lines, start=1):
            if not isinstance(line, dict):
                issues.append(issue("error", "speech_line_invalid", f"speech_lines 第 {index} 条必须是对象。", prompt_path))
                continue
            spoken = str(line.get("source_text") or "").strip()
            if not spoken:
                issues.append(issue("error", "speech_line_spoken_text_missing", f"speech_lines 第 {index} 条缺少 source_text。", prompt_path))
                continue
            if not any(speech_key(spoken) in key for key in block_keys):
                issues.append(issue("error", "prompt_speech_line_missing", f"Prompt 缺少当前 SEG 台词原文：{spoken}", prompt_path))


def check_h3_prompt(segment: dict[str, Any], root: Path, path: Path, issues: list[dict[str, Any]]) -> None:
    """H3 成稿只核存在、非空与哈希一致；其内部结构由 h3-prompt-writing skill 负责，本脚本不查。"""
    segment_id = segment.get("segment_id") or "视频片段"
    h3_file = segment.get("h3_prompt_file")
    h3_path = relative_file(root, h3_file)
    if h3_file and h3_path is None:
        issues.append(issue("error", "h3_prompt_path_invalid", f"{segment_id} h3_prompt_file 必须是项目相对路径。", path))
        h3_path = None
    if h3_path is not None and not h3_path.is_file():
        issues.append(issue("error", "h3_prompt_missing", f"{segment_id} 登记的 h3_prompt_file 不存在。", h3_path))
        h3_path = None
    if h3_path is not None:
        try:
            if not h3_path.read_text(encoding="utf-8").strip():
                issues.append(issue("error", "h3_prompt_empty", f"{segment_id} 的 H3 成稿为空。", h3_path))
        except (OSError, UnicodeError) as exc:
            issues.append(issue("error", "h3_prompt_unreadable", f"{segment_id} 的 H3 成稿无法读取：{exc}", h3_path))
            h3_path = None
    h3_sha256 = str(segment.get("h3_prompt_sha256") or "").strip()
    if h3_path is not None and h3_sha256:
        try:
            actual = file_sha256(h3_path)
        except OSError as exc:
            issues.append(issue("error", "h3_prompt_sha256_unreadable", f"无法读取 H3 成稿计算 sha256：{exc}", h3_path))
        else:
            if actual != h3_sha256:
                issues.append(issue("error", "h3_prompt_sha256_mismatch", f"{segment_id} h3_prompt_sha256 与实际 H3 成稿不一致。", h3_path))
    generated_segment = bool(str(segment.get("output_file") or "").strip()) or segment.get("status") in {"candidate", "accepted"}
    if generated_segment:
        if h3_path is None and not h3_file:
            issues.append(issue("error", "generated_segment_h3_prompt_missing", f"{segment_id} 已生成或进入候选/验收状态，必须登记真实存在的 h3_prompt_file。", path))
        if not h3_sha256:
            issues.append(issue("error", "generated_segment_h3_prompt_sha256_missing", f"{segment_id} 已生成或进入候选/验收状态，必须登记提交给模型的 H3 成稿 h3_prompt_sha256。", path))


def check_video_state_refs(segment: dict[str, Any], image_roles: set[str], asset_index: dict[str, Any], path: Path, issues: list[dict[str, Any]]) -> None:
    if not (image_roles & STATE_REFERENCE_ROLES):
        return
    state_refs = segment.get("state_refs")
    if not isinstance(state_refs, list) or not state_refs:
        issues.append(issue("error", "video_state_refs_missing", f"{segment.get('segment_id') or 'segment'} 传入角色/道具状态参考图时必须登记 approved state_refs。", path))
        return
    for ref in state_refs:
        check_state_ref(ref, asset_index, path, issues, str(segment.get("segment_id") or "视频片段"))


def _check_h3_prompt_purity(prompt_path, issues, mode="T2VA", duration=6):
    try:
        check_purity(prompt_path.read_text(encoding="utf-8"), mode, duration)
    except (OSError, ValueError) as exc:
        issues.append(issue("error", "h3_prompt_impure", str(exc), prompt_path))


def check_video_generation_confirmations(data, segments, path, issues, root=None, episode=None):
    rows = (validate_project_confirmations(root, episode, data) if root is not None and episode else
            validate_confirmations(data, segments))
    issues.extend(dict(row, path=str(path)) for row in rows)


def check_voice_audio_inputs(
    segment: dict[str, Any],
    audio_roles: set[str],
    path: Path,
    issues: list[dict[str, Any]],
    approved_voice_ids: set[str],
    audio_capable_modes: set[str] | None,
) -> None:
    speech_lines = segment.get("speech_lines")
    if not isinstance(speech_lines, list) or not speech_lines:
        return
    segment_label = str(segment.get("segment_id") or "segment")
    audio_input_supported = segment.get("audio_input_supported") is True
    has_voice_audio_reference = "voice_audio_reference" in audio_roles
    voice_inputs = segment.get("voice_inputs")
    h3_mode = str(segment.get("h3_mode") or segment.get("mode") or "T2VA")
    # 能力档案可用时以 h3.json 物理能力为准；档案加载失败（破损安装另有能力门报错）退回旗标旧逻辑。
    mode_allows_audio = audio_input_supported if audio_capable_modes is None else h3_mode in audio_capable_modes
    spoken_voice_ids = {
        str(line.get("voice_id") or "").strip()
        for line in speech_lines
        if isinstance(line, dict)
    }
    spoken_voice_ids.discard("")
    # 规则 A：台词声部只要在 registry 存在 approved 样音，音频能力开放的模式就必须上传 wav 音色参考。
    mandatory_voices = spoken_voice_ids & approved_voice_ids

    if not mode_allows_audio:
        # 模式物理不支持音频（T2VA/I2VA/FL2VA/L2VA）：voice_anchor 文字锚点是唯一合法声线路径。
        if isinstance(voice_inputs, list) and voice_inputs:
            issues.append(issue("error", "voice_inputs_without_audio_reference", f"{segment_label} 未传 VOICE 音频时不得登记 voice_inputs；文字音色锚点以 project_data_card.json voices[].voice_anchor 单定义为准，按 voice_id 解析，不在台词行复制。", path))
        if has_voice_audio_reference and not audio_input_supported:
            issues.append(issue("error", "voice_audio_support_flag_missing", f"{segment_label} 已传 voice_audio_reference 时 audio_input_supported 必须为 true。", path))
        # 锚点缺失/未知 voice_id 统一由 check_voice_anchor_resolution 按数据卡单定义裁决，此处不重复发射。
        return

    if mandatory_voices and not has_voice_audio_reference:
        issues.append(issue("error", "voice_audio_input_missing", f"{segment_label} 模式 {h3_mode} 支持音频参考，且台词声部 {sorted(mandatory_voices)} 在 registry 存在 approved 样音：必须经 audio_inputs(role=voice_audio_reference) 上传样音作为音色参考，H3 据此以该音色生成该角色全部台词；仅无 approved 样音的声部允许退回 voice_anchor 文字锚点。", path))
    if has_voice_audio_reference and not audio_input_supported:
        issues.append(issue("error", "voice_audio_support_flag_missing", f"{segment_label} 已传 voice_audio_reference 时 audio_input_supported 必须为 true。", path))
    if not has_voice_audio_reference:
        # 音频能力开放但本次无音频参考（全员无 approved 样音的合法文字锚点回退）：voice_inputs 不得登记。
        if isinstance(voice_inputs, list) and voice_inputs:
            issues.append(issue("error", "voice_inputs_without_audio_reference", f"{segment_label} 未传 VOICE 音频时不得登记 voice_inputs；文字音色锚点以 project_data_card.json voices[].voice_anchor 单定义为准，按 voice_id 解析，不在台词行复制。", path))
        return
    if not isinstance(voice_inputs, list) or not voice_inputs:
        issues.append(issue("error", "voice_inputs_missing", f"{segment_label} 有 speech_lines 时必须登记 voice_inputs。", path))
        return
    voice_ids = {
        item.get("voice_id")
        for item in voice_inputs
        if isinstance(item, dict) and isinstance(item.get("voice_id"), str) and item.get("voice_id").strip()
    }
    resource_ids = {
        item.get("resource_id")
        for item in voice_inputs
        if isinstance(item, dict) and isinstance(item.get("resource_id"), str) and item.get("resource_id").strip()
    }
    if not voice_ids or not resource_ids:
        issues.append(issue("error", "voice_inputs_incomplete", f"{segment_label} voice_inputs 必须填写 voice_id 和 resource_id。", path))
    # 每个必传声部的 resource_id 必须落到真实 voice_audio_reference 槽位，防止一个 wav 被多个声部冒名覆盖。
    audio_resource_ids = {
        item.get("resource_id")
        for item in segment.get("audio_inputs") or []
        if isinstance(item, dict) and item.get("role") == "voice_audio_reference"
        and isinstance(item.get("resource_id"), str) and item.get("resource_id").strip()
    }
    voice_to_resource = {
        str(item.get("voice_id") or "").strip(): item.get("resource_id")
        for item in voice_inputs
        if isinstance(item, dict) and isinstance(item.get("voice_id"), str) and item.get("voice_id").strip()
    }
    uncovered = sorted(
        voice_id for voice_id in mandatory_voices
        if voice_id in voice_to_resource and voice_to_resource[voice_id] not in audio_resource_ids
    )
    if uncovered:
        issues.append(issue("error", "voice_audio_input_missing", f"{segment_label} 台词声部 {uncovered} 有 approved 样音，但其 voice_inputs.resource_id 未对应任何 voice_audio_reference 音频槽位。", path))
    for index, line in enumerate(speech_lines, start=1):
        if not isinstance(line, dict):
            continue
        voice_id = line.get("voice_id")
        if isinstance(voice_id, str) and voice_id.strip() and voice_id not in voice_ids:
            issues.append(issue("error", "speech_line_voice_input_missing", f"{segment_label} speech_lines 第 {index} 条 voice_id 未在 voice_inputs 中登记：{voice_id}", path))


def load_voice_anchor_map(root: Path, issues: list[dict[str, Any]]) -> dict[str, str]:
    """voice_id→voice_anchor 单定义解析表；唯一权威是 project_data_card.json 的 voices[]。"""
    card = load_json(root / "00_制作控制/project_data_card.json", issues, required=False)
    anchors: dict[str, str] = {}
    if isinstance(card, dict):
        for item in card.get("voices") or []:
            if not isinstance(item, dict):
                continue
            voice_id = str(item.get("voice_id") or "").strip()
            if voice_id:
                anchors[voice_id] = str(item.get("voice_anchor") or "").strip()
    return anchors


def check_voice_anchor_resolution(segment: dict[str, Any], voice_anchors: dict[str, str], path: Path, issues: list[dict[str, Any]]) -> None:
    """台词行只存 voice_id；声音锚点由数据卡 voices[] 单定义解析，行级副本不再参与校验。"""
    speech_lines = segment.get("speech_lines")
    if not isinstance(speech_lines, list):
        return
    segment_label = str(segment.get("segment_id") or "segment")
    for index, line in enumerate(speech_lines, start=1):
        if not isinstance(line, dict):
            continue
        voice_id = str(line.get("voice_id") or "").strip()
        if not voice_id:
            continue
        if voice_id not in voice_anchors:
            issues.append(issue("error", "speech_line_voice_unknown", f"{segment_label} speech_lines 第 {index} 条 voice_id={voice_id} 在 project_data_card.json voices[] 中不存在。", path))
        elif not voice_anchors[voice_id]:
            issues.append(issue("error", "speech_line_voice_anchor_missing", f"{segment_label} voice_id={voice_id} 已在 voices[] 登记但 voice_anchor 为空，无法约束声线。", path))


# ===== 原 lint_checks/rhythm.py =====

from rhythm_engine import reconcile_storyboard


class RhythmLibrary:
    """H3 能力与可选叙事词汇分别加载；时间核对只依赖 H3 能力，词汇库仅供 beat_type 校验。"""
    def __init__(self):
        self.library = None
        self.h3 = None
        self.error = None

    def ensure(self):
        import rhythm_engine
        try:
            self.h3 = rhythm_engine.load_h3(H3_CAPABILITY_PATH)
        except (OSError, ValueError, KeyError):
            # H3 能力损坏时降级为不核对时间合同；
            # check_rhythm_reconciliation 的 tool_capabilities_invalid 门负责报错。
            pass
        try:
            data = json.loads(BEAT_LIBRARY_JSON_PATH.read_text(encoding="utf-8-sig"))
            beats = data.get("beat_types")
            if not isinstance(beats, dict) or not beats:
                raise ValueError("beat_types.json 缺少非空 beat_types 对象")
            self.library = data
            self.error = None
        except (OSError, ValueError) as exc:
            # 损坏时降级为不校验 beat_type；skill 阶段的 beat_library_unavailable 门负责报错。
            self.library = None
            self.error = str(exc)
        return self.h3 is not None


# 节拍库重建（原 maintenance/build_beat_types.py 内联）：从叙事词汇源表 §2 生成 ID/名称，
# 仅供 desync 对账；运行期仍只消费入库的 beat_types.json，不提供时间参数或生产 fallback。
_BEAT_SECTION_RE = re.compile(r'(?ms)^## §2 beat_type 总表\s*$(.*?)(?=^## §3 )')
_BEAT_HEADING_RE = re.compile(r'(?m)^### ([a-z][a-z_0-9]*)\s+(\S.*?)\s*$')


def build_beat_library(library_md):
    text = Path(library_md).read_text(encoding='utf-8-sig')
    sections = _BEAT_SECTION_RE.findall(text)
    if len(sections) != 1:
        raise ValueError('缺少唯一 beat_type 总表（§2）')
    section = sections[0]
    for line in section.splitlines():
        if line.startswith('### ') and not _BEAT_HEADING_RE.match(line):
            raise ValueError('beat_type 标题必须为「### id 名称」: ' + line)
    beats = {}
    for match in _BEAT_HEADING_RE.finditer(section):
        beat_id, name = match.group(1), match.group(2)
        if beat_id in beats:
            raise ValueError('无效或重复词汇 ID/名称')
        beats[beat_id] = {'name': name}
    if not beats:
        raise ValueError('词汇表不能为空')
    return {'_generated_by': 'build_beat_types.py — 由叙事词汇源表生成，禁止手改', 'beat_types': beats}


def check_beat_library_desync(issues):
    try:
        rebuilt = build_beat_library(str(BEAT_LIBRARY_MD_PATH))
        current = json.loads(BEAT_LIBRARY_JSON_PATH.read_text(encoding="utf-8"))
        if current != rebuilt:
            issues.append(issue("error", "beat_library_desync", "词汇生成物与源库不同，请重生成。", BEAT_LIBRARY_JSON_PATH))
    except (OSError, ValueError, SystemExit) as exc:
        issues.append(issue("error", "beat_library_unavailable", f"可选词汇安装损坏：{exc}", BEAT_LIBRARY_JSON_PATH))


def check_segment_shot_count(
    segment_id: Any,
    shot_count: int,
    shot_mode: Any,
    density_profile: Any,
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    label = str(segment_id or "segment")
    density_profiles = {"high_density_short", "dialogue_emotional", "suspense_build", "micro_film", "custom"}
    if density_profile is not None and density_profile not in density_profiles:
        issues.append(issue("error", "segment_density_profile_invalid", f"{label} density_profile 无效。", path, ))
    if shot_mode not in {"edited", "true_one_take"}:
        issues.append(issue("error", "segment_shot_mode_invalid", f"{label} shot_mode 必须为 edited 或 true_one_take。", path, ))
        return
    if shot_mode == "true_one_take":
        if shot_count != 1:
            issues.append(issue("error", "true_one_take_shot_count_invalid", f"{label} 标记为 true_one_take 时必须且只能包含 1 个镜头。", path, ))
        return


def check_keyframe_request_plan(
    segment: dict[str, Any],
    path: Path,
    issues: list[dict[str, Any]],
) -> int:
    segment_id = str(segment.get("segment_id") or "segment")
    requests = segment.get("keyframe_requests")
    if requests is None:
        return 0
    if not isinstance(requests, list):
        issues.append(issue("error", "keyframe_requests_invalid", f"{segment_id} keyframe_requests 必须是数组；未选中本集高光时可省略或填空数组。", path))
        return 0
    count = len(requests)
    roles = segment.get("required_keyframe_roles")
    if count and isinstance(roles, list) and "highlight" not in roles:
        issues.append(issue("error", "keyframe_role_missing", f"{segment_id} 已规划 keyframe_requests 时，required_keyframe_roles 必须包含 highlight。", path))
    if not count and isinstance(roles, list) and "highlight" in roles:
        issues.append(issue("error", "keyframe_role_without_request", f"{segment_id} 标记了 highlight 但没有 keyframe_requests；未选中本集高光时不要登记关键帧职责。", path))
    return count


def check_episode_keyframe_request_plan(segments, path, issues):
    for segment in segments:
        if isinstance(segment, dict):
            check_keyframe_request_plan(segment, path, issues)


def check_shot_rhythm_fields(
    shots: list[Any],
    path: Path,
    issues: list[dict[str, Any]],
    valid_beat_types: set[str] | None = None,
) -> None:
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        shot_id = str(shot.get("shot_id") or "shot")
        beat_type = shot.get("beat_type")
        if beat_type is not None and valid_beat_types is not None and beat_type not in valid_beat_types:
            issues.append(issue("error", "shot_beat_type_invalid", f"{shot_id} beat_type 无效，必须是 beat_types.json 的 keys 之一：{sorted(valid_beat_types)}。", path))
        cut_motivation = shot.get("cut_motivation")
        if cut_motivation is not None and (not isinstance(cut_motivation, str) or cut_motivation not in CUT_MOTIVATIONS):
            issues.append(issue("error", "cut_motivation_invalid", f"{shot_id} cut_motivation 无效，必须是 {sorted(CUT_MOTIVATIONS)} 之一。", path))


def check_rhythm_reconciliation(episode_id, episode_root, data, path, issues, rhythm):
    root = episode_root.parents[1]
    timing_path = episode_root / f"02_分镜/rhythm_input_{episode_id}.json"
    try:
        if rhythm is None or rhythm.h3 is None:
            issues.append(issue("error", "tool_capabilities_invalid", "真实 H3 能力缺失，不能跳过 pack。", H3_CAPABILITY_PATH))
            return
        inp = read_json(timing_path)
        _, _, found = reconcile_storyboard(root, data, inp, timing_path, rhythm.h3)
        issues.extend(dict(row, path=str(path)) for row in found)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        issues.append(issue("error", "timing_input_invalid", f"当前时间合同不可核对：{exc}", path, ))

# ===== 原 lint_checks/storyboard.py =====

from rhythm_engine import to_ms


def load_storyboard_index(root: Path, episode_id: str, issues: list[dict[str, Any]]) -> dict[str, Any]:
    path = root / f"episodes/{episode_id}/02_分镜/storyboard_{episode_id}.json"
    data = load_json(path, issues, required=False)
    if not isinstance(data, dict):
        return {
            "segments": set(),
            "shots": set(),
            "shot_durations": {},
            "segment_shots": {},
            "segment_durations": {},
            "required_reference_roles": {},
            "required_keyframe_roles": {},
            "keyframe_requests": {},
        }
    shots = data.get("shots") if isinstance(data.get("shots"), list) else []
    segments = data.get("segments") if isinstance(data.get("segments"), list) else []
    return {
        "segments": {item.get("segment_id") for item in segments if isinstance(item, dict) and isinstance(item.get("segment_id"), str)},
        "shots": {item.get("shot_id") for item in shots if isinstance(item, dict) and isinstance(item.get("shot_id"), str)},
        "shot_durations": {
            item.get("shot_id"): item.get("duration_s")
            for item in shots
            if isinstance(item, dict) and isinstance(item.get("shot_id"), str) and isinstance(item.get("duration_s"), (int, float))
        },
        "segment_shots": {
            item.get("segment_id"): item.get("shot_ids")
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("shot_ids"), list)
        },
        "segment_durations": {
            item.get("segment_id"): item.get("duration_s")
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("duration_s"), (int, float))
        },
        "segment_request_durations": {item.get("segment_id"): item.get("request_duration_s") for item in segments if isinstance(item, dict)},
        "required_reference_roles": {
            item.get("segment_id"): {role for role in item.get("required_reference_roles") if isinstance(role, str)}
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("required_reference_roles"), list)
        },
        "required_keyframe_roles": {
            item.get("segment_id"): {role for role in item.get("required_keyframe_roles") if isinstance(role, str)}
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("required_keyframe_roles"), list)
        },
        "keyframe_requests": {
            item.get("segment_id"): item.get("keyframe_requests")
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("keyframe_requests"), list)
        },
    }


def check_storyboards(
    root: Path,
    plan: Any,
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
    asset_index: dict[str, Any] | None = None,
    rhythm: RhythmLibrary | None = None,
) -> None:
    if asset_index is None:
        asset_index = blank_asset_index()
    valid_beat_types: set[str] | None = None
    if rhythm is not None:
        if rhythm.library is not None:
            valid_beat_types = set(rhythm.library["beat_types"])
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"02_分镜/storyboard_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", "storyboard episode_id 与目录不一致。", path))
        expected_director_card = f"episodes/{episode_id}/02_分镜/导演总控卡_{episode_id}.md"
        if data.get("director_control_card") != expected_director_card:
            issues.append(issue("error", "director_control_card_invalid", f"storyboard.director_control_card 必须指向 {expected_director_card}。", path, ))
        elif not file_exists(root, expected_director_card):
            issues.append(issue("error", "director_control_card_missing", "分镜阶段必须存在唯一导演总控卡。", path, ))
        expected_source_markdown = f"episodes/{episode_id}/02_分镜/分镜_完整分镜表_{episode_id}.md"
        source_markdown = relative_file(root, data.get("source_markdown"))
        if data.get("source_markdown") != expected_source_markdown:
            issues.append(issue("error", "storyboard_source_markdown_invalid", f"storyboard.source_markdown 必须指向 {expected_source_markdown}。", path, ))
        elif source_markdown is None or not source_markdown.is_file():
            issues.append(issue("error", "storyboard_source_markdown_missing", "十五列完整分镜表文件不存在。", path, ))
        else:
            try:
                table_text = source_markdown.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                issues.append(issue("error", "storyboard_source_markdown_unreadable", f"十五列完整分镜表无法读取：{exc}", source_markdown))
            else:
                if 15 not in markdown_table_column_counts(table_text):
                    issues.append(issue("error", "storyboard_fifteen_columns_missing", "完整分镜表必须包含一个十五列表格。", source_markdown, ))
        # scale_plan episode durations are allocation estimates; only internal shot/segment sums are exact.
        shots = data.get("shots")
        segments = data.get("segments")
        if not isinstance(shots, list) or not isinstance(segments, list):
            issues.append(issue("error", "storyboard_shape_invalid", "storyboard 必须包含 shots 和 segments 数组。", path, ))
            continue
        shot_ids = check_unique(shots, "shot_id", path, issues, "shots")
        segment_ids = check_unique(segments, "segment_id", path, issues, "segments")
        shot_to_segment = {
            item.get("shot_id"): item.get("segment_id")
            for item in shots
            if isinstance(item, dict) and isinstance(item.get("shot_id"), str)
        }
        scene_ids = {
            item.get("scene_id")
            for item in shots
            if isinstance(item, dict) and isinstance(item.get("scene_id"), str) and item.get("scene_id").strip()
        }
        shot_durations = {
            item.get("shot_id"): item.get("duration_s")
            for item in shots
            if isinstance(item, dict) and isinstance(item.get("shot_id"), str) and isinstance(item.get("duration_s"), (int, float))
        }
        if shot_durations and isinstance(data.get("duration_s"), (int, float)):
            try:
                if to_ms(data["duration_s"]) != sum(to_ms(v) for v in shot_durations.values()):
                    issues.append(issue("error", "shot_duration_total_mismatch", "shots.duration_s 之和必须等于 storyboard.duration_s。", path))
            except ValueError as exc:
                issues.append(issue("error", "timeline_number_invalid", str(exc), path, ))
        covered: list[str] = []
        for index, segment in enumerate(segments, start=1):
            if not isinstance(segment, dict):
                continue
            segment_id = segment.get("segment_id")
            segment_shots = segment.get("shot_ids")
            if not isinstance(segment_shots, list):
                issues.append(issue("error", "segment_shot_ids_invalid", f"{segment_id or index} 缺少 shot_ids 数组。", path))
                continue
            for shot_id in segment_shots:
                if shot_id not in shot_ids:
                    issues.append(issue("error", "segment_unknown_shot", f"{segment_id} 引用了不存在的 shot_id：{shot_id}", path))
                elif shot_to_segment.get(shot_id) not in {None, segment_id}:
                    issues.append(issue("error", "shot_segment_mismatch", f"{shot_id} 的 segment_id 与 segments[].shot_ids 不一致。", path))
            covered.extend(str(item) for item in segment_shots)
            # shot_mode/density 枚举门与一镜到底数量门不得依赖 duration_s 可解析，
            # 否则 SEG 漏填 duration_s 时整组门被绕过。
            check_segment_shot_count(
                segment_id,
                len(segment_shots),
                segment.get("shot_mode"),
                segment.get("density_profile"),
                path,
                issues,
            )
            if isinstance(segment.get("duration_s"), (int, float)):
                try:
                    declared = to_ms(segment["duration_s"])
                    calculated = sum(to_ms(shot_durations[s]) for s in segment_shots if s in shot_durations)
                except ValueError as exc:
                    issues.append(issue("error", "timeline_number_invalid", str(exc), path, ))
                    continue
                if calculated and declared != calculated:
                    issues.append(issue("error", "segment_duration_mismatch", f"{segment_id} duration_s 必须等于其 shot_ids 时长之和。", path))
            tail_mode = segment.get("tail_mode")
            if tail_mode not in {"continuous_motion", "cuttable_completion", "stable_hold", "loop_continuation"}:
                issues.append(issue("error", "segment_tail_mode_invalid", f"{segment_id or index} tail_mode 无效。", path, ))
            if index < len(segments) and tail_mode == "stable_hold" and not has_meaningful_value(segment.get("tail_hold_reason")):
                issues.append(issue("error", "intermediate_stable_hold_reason_missing", f"{segment_id or index} 是中间片段，使用 stable_hold 时必须填写 tail_hold_reason。", path, ))
            check_reference_plan(segment, path, issues)
        check_episode_keyframe_request_plan(segments, path, issues)
        check_asset_usage_reconciliation(data, asset_index, path, issues)
        check_world_facts(data, path, issues)
        check_beat_coverage(data, shot_ids, path, issues)
        check_shot_rhythm_fields(shots, path, issues, valid_beat_types)
        if rhythm is not None:
            check_rhythm_reconciliation(episode_id, episode_root, data, path, issues, rhythm)
        missing = shot_ids - set(covered)
        duplicated = {shot_id for shot_id in covered if covered.count(shot_id) > 1}
        if missing:
            issues.append(issue("error", "shots_not_covered", f"以下镜头未被任何 segment 覆盖：{sorted(missing)}", path))
        if duplicated:
            issues.append(issue("error", "shots_covered_multiple_times", f"以下镜头被多个 segment 重复覆盖：{sorted(duplicated)}", path))
        unknown_segment_refs = {seg for seg in shot_to_segment.values() if isinstance(seg, str) and seg not in segment_ids}
        if unknown_segment_refs:
            issues.append(issue("error", "shot_unknown_segment", f"shots 中引用了不存在的 segment_id：{sorted(unknown_segment_refs)}", path))
        audience_execution = data.get("audience_execution")
        if not isinstance(audience_execution, dict):
            issues.append(issue("error", "audience_execution_missing", "storyboard 必须登记从已确认 audience_plan 派生的 audience_execution。", path, ))
        else:
            source_revision = audience_execution.get("source_plan_revision")
            if not isinstance(source_revision, int) or isinstance(source_revision, bool) or source_revision < 1:
                issues.append(issue("error", "audience_execution_revision_invalid", "audience_execution.source_plan_revision 必须是正整数。", path))
            elif isinstance(plan, dict) and isinstance(plan.get("revision"), int) and source_revision != plan.get("revision"):
                issues.append(issue("error", "audience_execution_revision_mismatch", "audience_execution.source_plan_revision 必须等于当前已确认 drama_plan revision。", path))
            audience_plan = plan.get("audience_plan") if isinstance(plan, dict) and isinstance(plan.get("audience_plan"), dict) else {}
            for field in ("viewing_focus", "emotional_payoff", "platform_viewing_context", "expression_boundaries"):
                execution = audience_execution.get(field)
                if not isinstance(execution, dict) or not str(execution.get("contract") or "").strip():
                    issues.append(issue("error", "audience_execution_field_missing", f"audience_execution.{field} 必须填写 contract。", path))
                    continue
                expected_source = f"audience_plan.{field}"
                if execution.get("source_field") != expected_source:
                    issues.append(issue("error", "audience_execution_source_field_invalid", f"audience_execution.{field}.source_field 必须为 {expected_source}。", path))
                if execution.get("contract") != audience_plan.get(field):
                    issues.append(issue("error", "audience_execution_contract_mismatch", f"audience_execution.{field}.contract 必须逐字继承已确认 audience_plan.{field}。", path))
                refs = execution.get("scene_or_shot_ids")
                if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref.strip() for ref in refs):
                    issues.append(issue("error", "audience_execution_refs_missing", f"audience_execution.{field}.scene_or_shot_ids 必须列出落地场次或镜头。", path))
                    continue
                unknown_refs = sorted(set(refs) - shot_ids - scene_ids)
                if unknown_refs:
                    issues.append(issue("error", "audience_execution_ref_invalid", f"audience_execution.{field} 引用了不存在的场次或镜头：{unknown_refs}", path))
        script_path = episode_root / f"01_剧本/script_contract_{episode_id}.json"
        script_contract = load_json(script_path, issues, required=True)
        highlight_ledger = script_contract.get("highlight_ledger") if isinstance(script_contract, dict) else []
        if isinstance(script_contract, dict) and not isinstance(highlight_ledger, list):
            issues.append(issue("error", "highlight_ledger_invalid", "script_contract.highlight_ledger 必须是数组。", script_path))
            highlight_ledger = []
        primary_highlights = {
            item.get("highlight_id")
            for item in highlight_ledger or []
            if isinstance(item, dict) and item.get("role") == "primary" and isinstance(item.get("highlight_id"), str)
        }
        known_highlights = {
            item.get("highlight_id")
            for item in highlight_ledger or []
            if isinstance(item, dict) and isinstance(item.get("highlight_id"), str)
        }
        highlight_bindings = data.get("highlight_bindings")
        if not isinstance(highlight_bindings, list):
            issues.append(issue("error", "highlight_bindings_missing", "storyboard.highlight_bindings 必须是数组并覆盖剧本主要亮点。", path, ))
            highlight_bindings = []
        binding_ids = check_unique(highlight_bindings, "highlight_id", path, issues, "highlight_bindings")
        shot_positions = {
            shot_id: index
            for index, shot_id in enumerate(
                [
                    item.get("shot_id")
                    for item in shots
                    if isinstance(item, dict) and isinstance(item.get("shot_id"), str)
                ]
            )
        }
        inherited_aftereffects = data.get("inherited_aftereffect_bindings", [])
        if not isinstance(inherited_aftereffects, list):
            issues.append(issue("error", "inherited_aftereffect_bindings_invalid", "inherited_aftereffect_bindings 必须是数组。", path))
            inherited_aftereffects = []
        for inherited in inherited_aftereffects:
            if not isinstance(inherited, dict):
                issues.append(issue("error", "inherited_aftereffect_binding_invalid", "inherited_aftereffect_bindings 每项必须是对象。", path))
                continue
            binding_id = str(inherited.get("binding_id") or "")
            source_episode = str(inherited.get("source_episode_id") or "")
            source_highlight = str(inherited.get("source_highlight_id") or "")
            shot_refs = inherited.get("shot_ids")
            if not binding_id or not re.fullmatch(r"ep_[1-9]\d*", source_episode) or not source_highlight:
                issues.append(issue("error", "inherited_aftereffect_binding_fields_missing", "inherited_aftereffect_bindings 必须填写 binding_id、source_episode_id 和 source_highlight_id。", path))
            if not isinstance(shot_refs, list) or not shot_refs or not all(isinstance(ref, str) and ref.strip() for ref in shot_refs):
                issues.append(issue("error", "inherited_aftereffect_binding_shots_missing", f"{binding_id or '跨集余震承接'} 必须绑定本集真实 shot_ids。", path))
            else:
                unknown_refs = sorted(set(shot_refs) - shot_ids)
                if unknown_refs:
                    issues.append(issue("error", "inherited_aftereffect_binding_shot_invalid", f"{binding_id or '跨集余震承接'} 引用了不存在的本集镜头：{unknown_refs}", path))
            source_storyboard = load_json(root / f"episodes/{source_episode}/02_分镜/storyboard_{source_episode}.json", issues, required=False)
            source_bindings = source_storyboard.get("highlight_bindings") if isinstance(source_storyboard, dict) else []
            matching_sources = [
                item
                for item in source_bindings or []
                if isinstance(item, dict)
                and item.get("highlight_id") == source_highlight
                and isinstance(item.get("deferred_aftereffect_ref"), dict)
                and item["deferred_aftereffect_ref"].get("binding_id") == binding_id
                and item["deferred_aftereffect_ref"].get("episode_id") == episode_id
            ]
            if not matching_sources:
                issues.append(issue("error", "inherited_aftereffect_source_missing", f"{binding_id or '跨集余震承接'} 找不到来源集对应 deferred_aftereffect_ref。", path))
        for binding in highlight_bindings:
            if not isinstance(binding, dict):
                issues.append(issue("error", "highlight_binding_invalid", "highlight_bindings 每项必须是对象。", path))
                continue
            highlight_id = str(binding.get("highlight_id") or "")
            if known_highlights and highlight_id not in known_highlights:
                issues.append(issue("error", "highlight_binding_unknown", f"分镜绑定了剧本中不存在的亮点：{highlight_id}", path))
            segment_id = binding.get("segment_id")
            if segment_id not in segment_ids:
                issues.append(issue("error", "highlight_binding_segment_invalid", f"{highlight_id or '亮点绑定'} 引用了不存在的 segment_id：{segment_id}", path))
            payoff_positions: list[int] = []
            reaction_positions: list[int] = []
            for field in ("payoff_shot_ids", "reaction_shot_ids"):
                refs = binding.get(field)
                if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref.strip() for ref in refs):
                    issues.append(issue("error", "highlight_binding_shots_missing", f"{highlight_id or '亮点绑定'}.{field} 必须至少包含一个镜头。", path))
                    continue
                unknown_refs = sorted(set(refs) - shot_ids)
                if unknown_refs:
                    issues.append(issue("error", "highlight_binding_shot_invalid", f"{highlight_id or '亮点绑定'}.{field} 引用了不存在的镜头：{unknown_refs}", path))
                wrong_segment = sorted(ref for ref in refs if field == "payoff_shot_ids" and shot_to_segment.get(ref) not in {None, segment_id})
                if wrong_segment:
                    issues.append(issue("error", "highlight_binding_segment_mismatch", f"{highlight_id or '亮点绑定'} 的镜头不属于 {segment_id}：{wrong_segment}", path))
                valid_positions = [shot_positions[ref] for ref in refs if ref in shot_positions]
                if field == "payoff_shot_ids":
                    payoff_positions.extend(valid_positions)
                else:
                    reaction_positions.extend(valid_positions)
            if payoff_positions and reaction_positions and min(reaction_positions) < min(payoff_positions):
                issues.append(issue("error", "highlight_binding_reaction_before_payoff", f"{highlight_id or '亮点绑定'} 的反应镜头不得早于兑现镜头。", path))
            aftereffect_refs = binding.get("aftereffect_shot_ids")
            deferred_aftereffect_ref = binding.get("deferred_aftereffect_ref")
            if not isinstance(aftereffect_refs, list) or not all(isinstance(ref, str) and ref.strip() for ref in aftereffect_refs):
                issues.append(issue("error", "highlight_binding_aftereffect_invalid", f"{highlight_id or '亮点绑定'}.aftereffect_shot_ids 必须是数组。", path))
            elif aftereffect_refs:
                unknown_refs = sorted(set(aftereffect_refs) - shot_ids)
                if unknown_refs:
                    issues.append(issue("error", "highlight_binding_shot_invalid", f"{highlight_id or '亮点绑定'}.aftereffect_shot_ids 引用了不存在的本集镜头：{unknown_refs}", path))
                aftereffect_positions = [shot_positions[ref] for ref in aftereffect_refs if ref in shot_positions]
                preceding_positions = payoff_positions + reaction_positions
                if aftereffect_positions and preceding_positions and min(aftereffect_positions) < max(preceding_positions):
                    issues.append(issue("error", "highlight_binding_aftereffect_before_payoff", f"{highlight_id or '亮点绑定'} 的余震镜头不得早于兑现或反应镜头。", path))
                if deferred_aftereffect_ref not in (None, {}):
                    issues.append(issue("error", "highlight_binding_aftereffect_scope_conflict", f"{highlight_id or '亮点绑定'} 已填写本集余震时 deferred_aftereffect_ref 必须为空。", path))
            elif not isinstance(deferred_aftereffect_ref, dict):
                issues.append(issue("error", "highlight_binding_aftereffect_missing", f"{highlight_id or '亮点绑定'} 必须填写本集 aftereffect_shot_ids 或跨集 deferred_aftereffect_ref。", path))
            else:
                target_episode = str(deferred_aftereffect_ref.get("episode_id") or "")
                binding_id = str(deferred_aftereffect_ref.get("binding_id") or "")
                if not re.fullmatch(r"ep_[1-9]\d*", target_episode) or target_episode not in {item[0] for item in episode_dirs(root)}:
                    issues.append(issue("error", "highlight_binding_deferred_episode_invalid", f"{highlight_id or '亮点绑定'} deferred_aftereffect_ref.episode_id 必须是计划内分集。", path))
                elif int(target_episode.split("_", 1)[1]) <= int(episode_id.split("_", 1)[1]):
                    issues.append(issue("error", "highlight_binding_deferred_episode_order_invalid", f"{highlight_id or '亮点绑定'} deferred_aftereffect_ref 必须指向后续分集。", path))
                target_highlight = str(deferred_aftereffect_ref.get("highlight_id") or "")
                if not target_highlight or not binding_id:
                    issues.append(issue("error", "highlight_binding_deferred_ref_invalid", f"{highlight_id or '亮点绑定'} deferred_aftereffect_ref 必须填写 highlight_id 和 binding_id。", path))
                target_script = load_json(root / f"episodes/{target_episode}/01_剧本/script_contract_{target_episode}.json", issues, required=False)
                target_ledger = target_script.get("highlight_ledger") if isinstance(target_script, dict) else []
                target_highlight_ids = {
                    str(item.get("highlight_id"))
                    for item in target_ledger or []
                    if isinstance(item, dict) and str(item.get("highlight_id") or "").strip()
                }
                if target_highlight and target_highlight not in target_highlight_ids:
                    issues.append(issue("error", "highlight_binding_deferred_highlight_missing", f"{highlight_id or '亮点绑定'} deferred_aftereffect_ref.highlight_id 必须存在于目标集 script_contract.highlight_ledger。", path))
            for field in ("visual_execution", "performance_execution", "audio_execution", "compile_notes"):
                if not str(binding.get(field) or "").strip():
                    issues.append(issue("error", "highlight_binding_execution_missing", f"{highlight_id or '亮点绑定'} 缺少 {field}。", path))
        missing_primary = sorted(primary_highlights - binding_ids)
        if missing_primary:
            issues.append(issue("error", "primary_highlight_binding_missing", f"以下主要亮点未绑定到分镜：{missing_primary}", path))


def check_reference_plan(
    segment: dict[str, Any],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    refs = segment.get("reference_input_plan")
    if refs is None:
        issues.append(issue("error", "reference_input_plan_missing", "每个 SEG 必须填写 reference_input_plan。", path, ))
        return
    if not isinstance(refs, list):
        issues.append(issue("error", "reference_input_plan_invalid", "reference_input_plan 必须是数组。", path, ))
        return
    orders: list[int] = []
    for index, ref in enumerate(refs, start=1):
        if not isinstance(ref, dict):
            issues.append(issue("error", "reference_input_plan_invalid", f"第 {index} 条参考计划必须是对象。", path, ))
            continue
        order = ref.get("order")
        role = ref.get("role")
        if isinstance(order, int) and not isinstance(order, bool):
            orders.append(order)
            binding = str(ref.get("opening_binding", "") or "")
            if not re.search(marker_pattern("image", order), binding, flags=re.I):
                issues.append(issue("error", "opening_binding_marker_missing", f"第 {order} 张参考图缺少对应 <图片{order}>/<IMG{order}> 标记。", path, ))
        else:
            issues.append(issue("error", "reference_order_invalid", "参考图 order 必须是整数。", path))
        if role not in REFERENCE_ROLES:
            issues.append(issue("error", "reference_role_invalid", f"参考图职责无效：{role}", path, ))
        for field in ("planned_source", "opening_binding", "adopt", "exclude"):
            if not str(ref.get(field, "") or "").strip():
                issues.append(issue("error", "reference_input_plan_incomplete", f"参考图计划缺少 {field}。", path, ))
    if orders and sorted(orders) != list(range(1, len(orders) + 1)):
        issues.append(issue("error", "reference_order_not_contiguous", "参考图 order 必须从 1 连续递增。", path))


def parse_planned_source_asset(source: Any) -> tuple[str, str] | None:
    """从 planned_source 解析资产 ID 与版本。

    'PROP003_v01（毛驴）' -> ('PROP003', 'v01')；'PROP003（毛驴）' -> ('PROP003', '')；
    'CHR002:STATE01_v01' -> ('CHR002', '')（状态引用只取资产 ID）。
    """
    if not isinstance(source, str):
        return None
    match = ASSET_ID_PATTERN.match(source.strip())
    if not match:
        return None
    version = f"v{match.group(2)}" if match.group(2) else ""
    return match.group(1), version


def check_asset_usage_reconciliation(
    data: dict[str, Any],
    asset_index: dict[str, Any],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    """asset_usage_plan（需求侧台账）与各 SEG reference_input_plan（消费侧）的双向对账。

    方向1：台账登记绑定到某段的资产必须真实出现在该段输入计划中（缺一即 error）。
    方向2：输入计划使用了台账未登记的绑定时同样报 error（临时增补必须回头登记）。
    只检查声明与执行的一致性，不判断资产是否应该出现。
    """
    segments = data.get("segments")
    if not isinstance(segments, list):
        return
    segment_ids_in_order = [
        s.get("segment_id")
        for s in segments
        if isinstance(s, dict) and isinstance(s.get("segment_id"), str)
    ]
    planned_by_segment: dict[str, dict[str, str]] = {}
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_id = segment.get("segment_id")
        refs = segment.get("reference_input_plan")
        if not isinstance(segment_id, str) or not isinstance(refs, list):
            continue
        planned: dict[str, str] = {}
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            parsed = parse_planned_source_asset(ref.get("planned_source"))
            if parsed is None:
                continue
            asset_id, version = parsed
            planned[asset_id] = version
            prefix_match = re.match(r"[A-Z]+", asset_id)
            compatible = ASSET_ROLE_COMPATIBILITY.get(prefix_match.group(0)) if prefix_match else None
            role = ref.get("role")
            if compatible and role not in compatible:
                issues.append(issue("error", "reference_role_asset_mismatch", f"{segment_id} 资产 {asset_id} 的职责 {role} 与资产类型不匹配。", path))
        planned_by_segment[segment_id] = planned

    usage = data.get("asset_usage_plan")
    if not isinstance(usage, list):
        issues.append(issue("error", "asset_usage_plan_missing", "storyboard 必须登记 asset_usage_plan（分镜表附录 B 资产使用摘要的同源数据）。", path))
        return
    known_ids = asset_index.get("known_asset_ids", set())
    seen_pairs: set[tuple[str, str]] = set()
    registered_versions: dict[str, str] = {}
    for entry in usage:
        if not isinstance(entry, dict):
            issues.append(issue("error", "asset_usage_plan_invalid", "asset_usage_plan 每条必须是对象。", path))
            continue
        asset_id = entry.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            issues.append(issue("error", "asset_usage_plan_invalid", "asset_usage_plan 缺少 asset_id。", path))
            continue
        if known_ids and asset_id not in known_ids:
            issues.append(issue("error", "asset_usage_unknown_asset", f"asset_usage_plan 引用了未登记的资产：{asset_id}", path))
        version = entry.get("version")
        if isinstance(version, str) and version.strip():
            registered_versions[asset_id] = version.strip()
        seg_list = entry.get("segments")
        if not isinstance(seg_list, list) or not seg_list:
            issues.append(issue("error", "asset_usage_segments_invalid", f"{asset_id} 的 segments 必须是非空数组（可用 [\"*\"] 表示全部片段）。", path))
            continue
        expanded = segment_ids_in_order if "*" in seg_list else seg_list
        for segment_id in expanded:
            if segment_id not in planned_by_segment:
                issues.append(issue("error", "asset_usage_unknown_segment", f"{asset_id} 绑定了不存在的片段：{segment_id}", path))
                continue
            seen_pairs.add((asset_id, segment_id))
            if asset_id not in planned_by_segment[segment_id]:
                issues.append(issue("error", "asset_required_but_unplanned", f"{asset_id} 在 asset_usage_plan 中绑定 {segment_id}，但该段 reference_input_plan 未计划传入。", path))
            elif (
                asset_id in registered_versions
                and planned_by_segment[segment_id][asset_id]
                and planned_by_segment[segment_id][asset_id] != registered_versions[asset_id]
            ):
                issues.append(issue("error", "asset_version_inconsistent", f"{segment_id} 计划传入 {asset_id} {planned_by_segment[segment_id][asset_id]}，与台账登记版本 {registered_versions[asset_id]} 不一致。", path))
    for segment_id, planned in planned_by_segment.items():
        for asset_id in planned:
            if (asset_id, segment_id) not in seen_pairs:
                issues.append(issue("error", "asset_planned_but_unregistered", f"{segment_id} 计划传入 {asset_id}，但 asset_usage_plan 未登记该绑定；临时增补必须回头登记。", path))

# ===== 原 lint_checks/stages.py =====

from rhythm_engine import source_index_from_contract, speech_key


def check_episode_directories(root: Path, expected_durations: dict[str, int], issues: list[dict[str, Any]]) -> None:
    if not expected_durations:
        return
    expected = set(expected_durations)
    actual = {episode_id for episode_id, _ in episode_dirs(root)}
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    episodes_root = root / "episodes"
    if missing:
        issues.append(issue("error", "episode_directory_missing", f"计划内分集缺少目录：{missing}", episodes_root))
    if extra:
        issues.append(issue("error", "episode_directory_unplanned", f"存在计划外分集目录：{extra}", episodes_root))


def check_episode_manifest_ids(root: Path, stage: str, issues: list[dict[str, Any]], episode_filter: str | None = None) -> None:
    for episode_id, _ in episode_dirs(root, episode_filter):
        path = manifest_path(root, episode_id, stage)
        if path is None or not path.exists():
            continue
        data = load_json(path, issues, required=False)
        if isinstance(data, dict) and data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", f"{stage} episode_id 必须等于目录 ID：{episode_id}", path))


def check_episode_entry_manifests(root: Path, issues: list[dict[str, Any]]) -> None:
    for episode_id, episode_root in episode_dirs(root):
        path = episode_root / f"episode_manifest_{episode_id}.json"
        data = load_json(path, issues, required=True)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", f"episode_manifest episode_id 必须等于目录 ID：{episode_id}", path))
        stage_manifests = data.get("stage_manifests")
        if not isinstance(stage_manifests, dict):
            issues.append(issue("error", "stage_manifests_missing", "episode_manifest 必须使用顶层 stage_manifests 保存阶段文件指针。", path))
            continue
        expected = {
            "script": f"episodes/{episode_id}/01_剧本/script_contract_{episode_id}.json",
            "storyboard": f"episodes/{episode_id}/02_分镜/storyboard_{episode_id}.json",
            "assets": f"episodes/{episode_id}/03_资产/asset_usage_{episode_id}.json",
            "keyframes": f"episodes/{episode_id}/03_资产/keyframe_manifest_{episode_id}.json",
            "video": f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json",
            "delivery": f"episodes/{episode_id}/05_成片/delivery_manifest_{episode_id}.json",
        }
        for stage, expected_path in expected.items():
            if stage_manifests.get(stage) != expected_path:
                issues.append(issue("error", "stage_manifest_path_invalid", f"episode_manifest.stage_manifests.{stage} 必须指向 {expected_path}。", path))


def check_stage_artifacts(
    root: Path,
    stage: str,
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
) -> None:
    required = [root / "00_制作控制/drama_plan.json", root / "00_制作控制/制作状态.json"]
    state = load_json(root / "00_制作控制/制作状态.json", issues, required=False)
    episode_states = state.get("episodes", {}) if isinstance(state, dict) and isinstance(state.get("episodes"), dict) else {}
    if stage == "planning":
        required += [
            root / "00_制作控制/project_manifest.json",
            root / "00_制作控制/source_manifest.json",
            root / "episodes",
        ]
    if stage == "script":
        required += [
            root / "00_制作控制/project_data_card.json",
            root / "01_剧本/project_script_manifest.json",
            root / "01_剧本/项目_事实与假设.md",
            root / "01_剧本/剧本_全局设定与分集总纲.md",
            root / "01_剧本/剧本_全剧完整剧本.md",
        ]
    if stage in {"assets", "storyboard", "keyframes", "video", "final"}:
        required.append(root / "00_制作控制/project_data_card.json")
    for episode_id, episode_root in episode_dirs(root):
        if episode_filter is not None and episode_id != episode_filter:
            continue
        if stage == "planning":
            required.append(episode_root / f"episode_manifest_{episode_id}.json")
        episode_script_status = (
            episode_states.get(episode_id, {}).get("stage_status", {}).get("script")
            if isinstance(episode_states.get(episode_id), dict)
            and isinstance(episode_states.get(episode_id, {}).get("stage_status"), dict)
            else None
        )
        require_episode_script = (
            stage in {"assets", "storyboard", "keyframes", "video", "final"}
            or (
                stage == "script"
                and (
                    episode_filter == episode_id
                    or episode_script_status in {"in_progress", "awaiting_confirmation", "confirmed", "blocked"}
                )
            )
        )
        if require_episode_script:
            required += [
                episode_root / f"01_剧本/script_contract_{episode_id}.json",
                episode_root / f"01_剧本/剧本_完整剧本_{episode_id}.md",
            ]
        if stage in {"assets", "storyboard", "keyframes", "video", "final"}:
            required += [root / "shared/03_资产/asset_registry.json", episode_root / f"03_资产/asset_usage_{episode_id}.json"]
        if stage in {"storyboard", "keyframes", "video", "final"}:
            required += [
                episode_root / f"02_分镜/storyboard_{episode_id}.json",
                episode_root / f"02_分镜/导演总控卡_{episode_id}.md",
                episode_root / f"02_分镜/分镜_完整分镜表_{episode_id}.md",
            ]
        if stage in {"keyframes", "video", "final"}:
            required += [episode_root / f"03_资产/keyframe_manifest_{episode_id}.json"]
        if stage in {"video", "final"}:
            required += [episode_root / f"04_视频片段/video_manifest_{episode_id}.json"]
        if stage == "final":
            required += [episode_root / f"05_成片/delivery_manifest_{episode_id}.json"]
    for path in required:
        if not path.exists():
            issues.append(issue("error", "required_artifact_missing", "缺少当前阶段所需产物。", path))
    if stage == "script":
        combined_path = root / "01_剧本/剧本_全局设定与分集总纲.md"
        if combined_path.is_file():
            try:
                combined_text = combined_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                issues.append(issue("error", "combined_story_outline_unreadable", f"合并剧本文档无法读取：{exc}", combined_path))
            else:
                for heading in ("全局故事圣经", "分集推进总纲"):
                    if re.search(rf"^#{{1,6}}\s+{re.escape(heading)}\s*$", combined_text, flags=re.MULTILINE) is None:
                        issues.append(issue("error", "combined_story_outline_section_missing", f"合并剧本文档缺少“{heading}”章节。", combined_path))
        script_manifest_path = root / "01_剧本/project_script_manifest.json"
        script_manifest = load_json(script_manifest_path, issues, required=False)
        if isinstance(script_manifest, dict):
            expected = "01_剧本/剧本_全局设定与分集总纲.md"
            if script_manifest.get("global_story_and_episode_outline") != expected:
                issues.append(issue("error", "combined_story_outline_reference_invalid", f"project_script_manifest.global_story_and_episode_outline 必须指向 {expected}。", script_manifest_path))
        for episode_id, episode_root in episode_dirs(root, episode_filter):
            episode_script_status = (
                episode_states.get(episode_id, {}).get("stage_status", {}).get("script")
                if isinstance(episode_states.get(episode_id), dict)
                and isinstance(episode_states.get(episode_id, {}).get("stage_status"), dict)
                else None
            )
            if episode_filter is None and episode_script_status not in {"in_progress", "awaiting_confirmation", "confirmed", "blocked"}:
                continue
            contract_path = episode_root / f"01_剧本/script_contract_{episode_id}.json"
            contract = load_json(contract_path, issues, required=False)
            if not isinstance(contract, dict):
                continue
            highlight_ledger = contract.get("highlight_ledger")
            if not isinstance(highlight_ledger, list):
                issues.append(issue("error", "highlight_ledger_invalid", "script_contract.highlight_ledger 必须是数组。", contract_path))
                continue
            source = relative_file(root, contract.get("source_markdown"))
            if source is None or not source.is_file() or file_sha256(source) != contract.get("source_sha256"):
                issues.append(issue("error", "source_revision_mismatch", "源剧本正文 SHA 不符。",
                             contract_path, ))
            else:
                found = []
                source_index_from_contract(contract, source.read_text(encoding="utf-8-sig"), found)
                issues.extend(dict(row, path=str(contract_path)) for row in found)

# ===== 原 lint_checks/planning.py =====



def check_plan_durations(root: Path, plan: Any, issues: list[dict[str, Any]], *, pending_confirmation: bool = False) -> dict[str, int | float]:
    expected: dict[str, int | float] = {}
    if not isinstance(plan, dict):
        return expected
    path = root / "00_制作控制/drama_plan.json"
    if not isinstance(plan.get("revision"), int) or isinstance(plan.get("revision"), bool) or plan.get("revision") < 1:
        issues.append(issue("error", "plan_revision_invalid", "drama_plan.revision 必须是正整数。", path))
    objective = plan.get("objective")
    if not isinstance(objective, dict) or objective.get("target_stage") not in STAGES:
        issues.append(issue("error", "target_stage_invalid", "drama_plan.objective.target_stage 必须是有效阶段。", path))
    if not str(plan.get("selected_direction_id") or "").strip():
        issues.append(issue("error", "selected_direction_missing", "drama_plan 必须锁定 selected_direction_id。", path))
    creative_mechanism = plan.get("creative_mechanism")
    if not isinstance(creative_mechanism, dict):
        issues.append(issue("error", "creative_mechanism_missing", "drama_plan 必须填写 creative_mechanism。", path))
    else:
        selection_mode = creative_mechanism.get("selection_mode")
        if selection_mode not in {"divergent", "user_locked"}:
            issues.append(issue("error", "creative_mechanism_selection_mode_invalid", "creative_mechanism.selection_mode 必须为 divergent 或 user_locked。", path))
        candidates = creative_mechanism.get("candidates")
        candidate_primaries: list[str] = []
        if not isinstance(candidates, list) or not candidates:
            expected_text = "真实采用的"
            issues.append(issue("error", "creative_mechanism_candidates_invalid", f"当前 selection_mode 的 creative_mechanism.candidates 必须包含{expected_text}候选。", path))
        else:
            for index, candidate in enumerate(candidates, start=1):
                supporting = candidate.get("supporting") if isinstance(candidate, dict) else None
                if not isinstance(candidate, dict) or not has_meaningful_value(candidate.get("primary")):
                    issues.append(issue("error", "creative_mechanism_primary_missing", f"创意机制候选 {index} 必须填写主机制。", path))
                else:
                    candidate_primaries.append(str(candidate["primary"]).strip())
                if not isinstance(supporting, list):
                    issues.append(issue("error", "creative_mechanism_supporting_invalid", f"创意机制候选 {index} supporting 必须是实际辅助机制列表，可空。", path))
        selected_primary = str(creative_mechanism.get("primary") or "").strip()
        if not selected_primary:
            issues.append(issue("error", "creative_mechanism_selected_missing", "creative_mechanism.primary 必须锁定唯一主机制。", path))
        elif candidate_primaries and selected_primary not in candidate_primaries:
            issues.append(issue("error", "creative_mechanism_selected_unknown", "creative_mechanism.primary 必须来自当前候选主机制之一。", path))
        selected_supporting = creative_mechanism.get("supporting")
        if not isinstance(selected_supporting, list):
            issues.append(issue("error", "creative_mechanism_selected_supporting_invalid", "creative_mechanism.supporting 必须是实际辅助机制列表，可空。", path))
    rhythm_design = plan.get("rhythm_design", {})
    if not isinstance(rhythm_design, dict):
        issues.append(issue("error", "rhythm_design_invalid", "rhythm_design 是可选定性观看意图。", path))
    elif "duration_allocation" in rhythm_design:
        issues.append(issue("error", "timing_budget_input_forbidden", "规划不得预分配时间。", path, ))
    strategy_contracts = {
        "audience_plan": (
            "target_audience",
            "core_pain_or_desire",
            "platform",
            "evidence_status",
            "viewing_focus",
            "emotional_payoff",
            "platform_viewing_context",
            "expression_boundaries",
        ),
        "type_strategy": ("format", "subject_route", "genre", "story_engine", "audience_promise", "narrative_structure", "main_path"),
        "highlight_strategy": ("primary_story_engine_id", "project_signature", "highlight_pillars", "distribution_policy", "rejected_cliches"),
        "style_contract": ("anchor_type", "anchor", "lighting", "color", "composition", "material", "camera_tendency", "sound_tendency", "excluded_mechanisms"),
    }
    for contract_name, required_fields in strategy_contracts.items():
        contract = plan.get(contract_name)
        if not isinstance(contract, dict):
            issues.append(issue("error", f"{contract_name}_missing", f"drama_plan 缺少 {contract_name}。", path))
            continue
        for field in required_fields:
            if not has_meaningful_value(contract.get(field)):
                issues.append(issue("error", f"{contract_name}_field_missing", f"{contract_name}.{field} 必须填写。", path))
        if contract_name == "audience_plan" and isinstance(contract, dict):
            source_values = contract.get("execution_sources")
            expected_sources = {
                "viewing_focus": "audience_plan.viewing_focus",
                "emotional_payoff": "audience_plan.emotional_payoff",
                "platform_viewing_context": "audience_plan.platform_viewing_context",
                "expression_boundaries": "audience_plan.expression_boundaries",
            }
            if source_values != expected_sources:
                issues.append(issue("error", "audience_plan_execution_sources_invalid", "audience_plan.execution_sources 必须逐项锁定四个 audience_execution 源字段。", path))
    scale = plan.get("scale_plan")
    if not isinstance(scale, dict):
        issues.append(issue("error", "scale_plan_missing", "drama_plan 缺少 scale_plan。", path))
        return expected
    count = scale.get("episode_count")
    durations = scale.get("episode_durations_s")
    displays = scale.get("episode_duration_displays")
    total = scale.get("total_duration_s")
    total_display = scale.get("total_duration_display")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        issues.append(issue("error", "episode_count_invalid", "episode_count 必须是正整数。", path))
        return expected
    if not isinstance(durations, list) or len(durations) != count:
        issues.append(issue("error", "episode_durations_invalid", "episode_durations_s 数量必须等于 episode_count。", path))
        return expected
    if isinstance(displays, list) and len(displays) != count:
        issues.append(issue("error", "episode_duration_displays_invalid", "episode_duration_displays 数量必须等于 episode_count。", path))
    numeric: list[int] = []
    for index, seconds in enumerate(durations, start=1):
        try:
            milliseconds = to_ms(seconds, positive=True)
        except ValueError as exc:
            issues.append(issue("error", "episode_duration_invalid", f"第 {index} 集规划预测无效：{exc}。", path))
            continue
        numeric.append(milliseconds)
        expected[f"ep_{index}"] = seconds
        display = displays[index - 1] if isinstance(displays, list) and index - 1 < len(displays) else None
        check_duration_pair(seconds, display, path, f"ep_{index}", issues)
    try:
        total_ms = to_ms(total, positive=True)
    except ValueError as exc:
        issues.append(issue("error", "total_duration_invalid", f"total_duration_s 规划预测无效：{exc}。", path))
    else:
        if len(numeric) == count and total_ms != sum(numeric):
            issues.append(issue("error", "total_duration_mismatch", "total_duration_s 必须等于各集 episode_durations_s 之和。", path))
        check_duration_pair(total, total_display, path, "total", issues, total_display=True)
    duration_contract = plan.get("duration_contract")
    if not isinstance(duration_contract, dict):
        issues.append(issue("error", "duration_contract_missing", "新制作需显式登记 unbounded/exact/target_band 及真实来源。", path))
    else:
        try:
            duration_contract_bounds(duration_contract)
        except ValueError as exc:
            issues.append(issue("error", "duration_contract_invalid", str(exc), path,
                                ))
        mode = duration_contract.get("mode")
        if mode not in {"unbounded", "exact", "target_band"} or duration_contract.get("scope") not in {"deliverable", "episode", "project"}:
            issues.append(issue("error", "duration_contract_invalid", "时长合同枚举无效。", path,
                                ))
        elif mode == "unbounded":
            if any(duration_contract.get(key) is not None for key in ("target_duration_s", "tolerance_ratio", "bounds")):
                issues.append(issue("error", "duration_contract_unbounded_invalid", "未限定时 target/tolerance/bounds 需 null。", path))
        elif pending_confirmation:
            # 展示前门：exact/target_band 的确认快照只能由本次规划确认产生，回指延至确认后无豁免重跑。
            pass
        else:
            records = load_confirmation_records(root, issues, required=True)
            matching = [row for row in records if row.get("confirmation_id") == duration_contract.get("confirmation_ref")]
            if (len(matching) != 1 or matching[0].get("decision") != "confirmed" or matching[0].get("valid", True) is False
                    or not str(matching[0].get("user_message") or "").strip()
                    or matching[0].get("duration_contract_snapshot") != {key: val for key, val in duration_contract.items() if key != "confirmation_ref"}):
                issues.append(issue("error", "duration_contract_source_invalid", "真实时长约束须回指同 scope/数值/性质的实际确认，不由估时推断。", path))
    delivery = plan.get("delivery_settings")
    if isinstance(delivery, dict):
        subtitle_enabled = delivery.get("subtitle_enabled")
        if not isinstance(subtitle_enabled, bool):
            issues.append(issue("error", "subtitle_enabled_invalid", "delivery_settings.subtitle_enabled 必须是布尔值；默认 false，用户明确要求字幕时为 true。", path))
        if subtitle_enabled is False and delivery.get("subtitle_policy") != "disabled":
            issues.append(issue("error", "subtitle_disabled_policy_missing", "字幕关闭时 subtitle_policy 必须为 disabled。", path))
        expected_deliverables = ["subtitle_master"] if subtitle_enabled is True else ["clean_master"]
        if delivery.get("final_deliverables") != expected_deliverables:
            issues.append(issue("error", "final_deliverables_invalid", f"final_deliverables 必须只包含单一最终视频版本：{expected_deliverables}。", path))
    return expected


def duration_contract_bounds(contract):
    mode = contract.get("mode")
    if mode == "unbounded":
        return None
    if mode not in {"exact", "target_band"}:
        raise ValueError("未知时长合同模式")
    target = to_ms(contract.get("target_duration_s"), positive=True) / 1000
    tolerance = contract.get("tolerance_ratio")
    if mode == "exact":
        if tolerance not in (None, 0) or isinstance(tolerance, bool):
            raise ValueError("exact 不接受非零容差")
        expected = [target, target]
    else:
        if (isinstance(tolerance, bool) or not isinstance(tolerance, (int, float))
                or not math.isfinite(tolerance) or not 0 <= tolerance < 1):
            raise ValueError("target_band 需明确有限 [0,1) 容差，不默认推断")
        expected = [target * (1 - tolerance), target * (1 + tolerance)]
    bounds = contract.get("bounds")
    if (not isinstance(bounds, list) or len(bounds) != 2
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in bounds)
            or any(abs(a - b) > 1e-6 for a, b in zip(bounds, expected))):
        raise ValueError("bounds 需显式 [下限,上限] 且与目标/性质/容差一致")
    if not isinstance(contract.get("source"), str) or not contract["source"].strip():
        raise ValueError("真实时长约束需保留用户来源原文")
    return tuple(bounds)

# ===== 原 lint_checks/keyframes.py =====



def check_keyframes(
    root: Path,
    asset_index: dict[str, Any],
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
) -> None:
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"03_资产/keyframe_manifest_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", "keyframe_manifest episode_id 与目录不一致。", path))
        index = load_storyboard_index(root, episode_id, issues)
        keyframes = data.get("keyframes")
        if not isinstance(keyframes, list):
            issues.append(issue("error", "keyframes_invalid", "keyframes 必须是数组。", path))
            continue
        check_unique(keyframes, "keyframe_id", path, issues, "keyframes")
        planned_keyframes = {
            segment_id: len(requests)
            for segment_id, requests in index.get("keyframe_requests", {}).items()
            if isinstance(segment_id, str) and isinstance(requests, list)
        }
        actual_keyframes: dict[str, int] = {}
        seen_highlight_indexes: set[tuple[str, int]] = set()
        for item in keyframes:
            if not isinstance(item, dict):
                continue
            keyframe_id = item.get("keyframe_id")
            segment_id = item.get("segment_id")
            shot_id = item.get("shot_id")
            if isinstance(segment_id, str) and index["segments"] and segment_id not in index["segments"]:
                issues.append(issue("error", "keyframe_unknown_segment", f"关键帧引用了不存在的 segment_id：{segment_id}", path))
            if isinstance(shot_id, str) and index["shots"] and shot_id not in index["shots"]:
                issues.append(issue("error", "keyframe_unknown_shot", f"关键帧引用了不存在的 shot_id：{shot_id}", path))
            status = str(item.get("status") or "").strip()
            if isinstance(segment_id, str) and status not in {"rejected", "superseded"}:
                actual_keyframes[segment_id] = actual_keyframes.get(segment_id, 0) + 1
            if item.get("role") != "highlight":
                issues.append(issue("error", "keyframe_role_invalid", f"{keyframe_id or '关键帧'} role 必须为 highlight。", path))
            highlight_index = item.get("highlight_index")
            if not isinstance(highlight_index, int) or isinstance(highlight_index, bool) or highlight_index < 1:
                issues.append(issue("error", "keyframe_highlight_index_invalid", f"{keyframe_id or '关键帧'} highlight_index 必须是从 1 开始的正整数。", path))
            elif isinstance(segment_id, str):
                key = (segment_id, highlight_index)
                if key in seen_highlight_indexes:
                    issues.append(issue("error", "keyframe_highlight_index_duplicate", f"{segment_id} 的 highlight_index={highlight_index} 重复。", path))
                seen_highlight_indexes.add(key)
            for used_segment in item.get("used_by_segments") or []:
                if index["segments"] and used_segment not in index["segments"]:
                    issues.append(issue("error", "keyframe_unknown_used_segment", f"used_by_segments 引用了不存在的 segment_id：{used_segment}", path))
            file_value = item.get("file")
            if file_value and not file_exists(root, file_value):
                issues.append(issue("error", "keyframe_file_missing", f"关键帧文件不存在：{file_value}", path))
            if item.get("tool") != "image_edit":
                issues.append(issue("error", "keyframe_tool_not_image_edit", f"{keyframe_id or '关键帧'} 必须使用 image_edit I2I 生成，不得使用 image_gen 或纯文生图。", path))
            asset_refs = item.get("asset_refs")
            if asset_refs is not None:
                if not isinstance(asset_refs, list):
                    issues.append(issue("error", "asset_refs_invalid", f"{keyframe_id or '关键帧'} asset_refs 必须是数组。", path))
                else:
                    for ref in asset_refs:
                        check_asset_ref(ref, asset_index, path, issues, str(keyframe_id or "关键帧"))
            state_refs = item.get("state_refs")
            if state_refs is not None:
                if not isinstance(state_refs, list):
                    issues.append(issue("error", "state_refs_invalid", f"{keyframe_id or '关键帧'} state_refs 必须是数组。", path))
                else:
                    for ref in state_refs:
                        check_state_ref(ref, asset_index, path, issues, str(keyframe_id or "关键帧"))
            style_terms = combined_strings(item, field="style_prompt_terms")
            check_style_anchor_contract(
                root,
                path,
                str(keyframe_id or "关键帧"),
                item.get("tool"),
                item.get("prompt_path"),
                combined_strings(item, field="style_anchor_reference_ids"),
                style_terms,
                combined_strings(item, field="style_adopt"),
                combined_strings(item, field="style_exclude"),
                issues,
            )
            check_generation_prompt_file(root, path, str(keyframe_id or "关键帧"), item.get("tool"), item.get("prompt_path"), issues)
        for segment_id, actual_count in actual_keyframes.items():
            if planned_keyframes.get(segment_id, 0) == 0 and actual_count:
                issues.append(issue("error", "keyframe_unplanned_segment", f"{segment_id} 实际生成了 {actual_count} 张有效关键帧，但 storyboard.keyframe_requests 未规划该段关键帧。", path))
        planned_ids = {request.get("keyframe_id") for requests in index.get("keyframe_requests", {}).values() for request in requests if isinstance(request, dict)}
        actual_ids = {row.get("keyframe_id") for row in keyframes if isinstance(row, dict) and row.get("status") not in {"rejected", "superseded"}}
        if planned_ids != actual_ids:
            issues.append(issue("error", "keyframe_identity_mismatch", "有效 KF 必须逐项对应实际请求 ID，数量相同不能代替。", path))
        # 集级总数门由逐段 keyframe_count_mismatch（含规划为 0 的段）与 keyframe_identity_mismatch 覆盖，不重复上报。
        for segment_id, planned_count in planned_keyframes.items():
            actual_count = actual_keyframes.get(segment_id, 0)
            if actual_count != planned_count:
                issues.append(issue("error", "keyframe_count_mismatch", f"{segment_id} 实际有效关键帧数量 {actual_count} 必须等于 storyboard.keyframe_requests 规划数量 {planned_count}。", path))

# ===== 原 lint_checks/video.py =====



def check_video(
    root: Path,
    asset_index: dict[str, Any],
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
    require_accepted: bool = True,
    audio_capable_modes: set[str] | None = None,
) -> None:
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"04_视频片段/video_manifest_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", "video_manifest episode_id 与目录不一致。", path))
        index = load_storyboard_index(root, episode_id, issues)
        keyframe_ids = load_keyframe_ids(root, episode_id, issues)
        # 声音锚点单定义：每集只解析一次数据卡 voices[]，片段台词按 voice_id 查表。
        voice_anchors = load_voice_anchor_map(root, issues)
        segments = data.get("segments")
        if not isinstance(segments, list):
            issues.append(issue("error", "video_segments_invalid", "video_manifest.segments 必须是数组。", path))
            continue
        check_video_generation_confirmations(data, segments, path, issues, root, episode_id)
        video_segment_ids = check_unique(segments, "segment_id", path, issues, "video segments")
        if index["segments"]:
            missing_segments = sorted(index["segments"] - video_segment_ids)
            extra_segments = sorted(video_segment_ids - index["segments"])
            if missing_segments:
                issues.append(issue("error", "video_segment_missing", f"video_manifest 缺少 storyboard segment：{missing_segments}", path))
            if extra_segments:
                issues.append(issue("error", "video_segment_unplanned", f"video_manifest 含 storyboard 中不存在的 segment：{extra_segments}", path))
        try:
            calculated = sum(to_ms(seg.get("duration_s"), positive=True) for seg in segments if isinstance(seg, dict))
            if to_ms(data.get("duration_s"), positive=True) != calculated:
                issues.append(issue("error", "video_duration_mismatch", "video 总长需等于各整数请求时长之和。", path))
        except ValueError as exc:
            issues.append(issue("error", "video_duration_invalid", str(exc), path))
        for segment in segments:
            if not isinstance(segment, dict):
                issues.append(issue("error", "video_segment_invalid", "segments 每项必须是对象。", path))
                continue
            segment_id = segment.get("segment_id")
            # 未知 segment_id 已由本函数开头的集合差检查统一报 video_segment_unplanned，此处不逐镜重复。
            storyboard_duration = index.get("segment_request_durations", {}).get(segment_id)
            if storyboard_duration is not None and isinstance(segment.get("duration_s"), (int, float)):
                try:
                    if to_ms(segment["duration_s"]) != to_ms(storyboard_duration):
                        issues.append(issue("error", "video_segment_duration_mismatch", f"{segment_id} 请求时长必须与分镜 request_duration_s 一致。", path))
                except ValueError as exc:
                    issues.append(issue("error", "video_duration_invalid", str(exc), path))
            # 声线锚点按 voice_id 解析数据卡单定义，与 tool_mode 无关，先于媒体槽位校验执行。
            check_voice_anchor_resolution(segment, voice_anchors, path, issues)
            tool_mode = segment.get("tool_mode")
            image_orders, image_roles = ordered_inputs(root, segment.get("reference_inputs"), REFERENCE_ROLES, "reference", path, issues)
            video_orders, video_roles = ordered_inputs(root, segment.get("video_inputs"), VIDEO_INPUT_ROLES, "video", path, issues)
            audio_orders, audio_roles = ordered_inputs(root, segment.get("audio_inputs"), AUDIO_INPUT_ROLES, "audio", path, issues)
            required_roles = segment.get("required_reference_roles")
            if tool_mode not in VIDEO_TOOL_MODES:
                issues.append(issue("error", "video_tool_mode_invalid", f"{segment_id or 'segment'} tool_mode 无效：{tool_mode}", path))
            # Mode selection belongs to h3-prompt-writing; check inherited production facts here.
            check_voice_audio_inputs(
                segment, audio_roles, path, issues,
                asset_index["approved_voice_ids"], audio_capable_modes,
            )
            check_video_state_refs(segment, image_roles, asset_index, path, issues)
            planned_roles = index["required_reference_roles"].get(segment_id, set()) if isinstance(segment_id, str) else set()
            declared_roles = set(required_roles) if isinstance(required_roles, list) else set()
            if image_orders or planned_roles:
                if not isinstance(required_roles, list) or not required_roles:
                    issues.append(issue("error", "required_reference_roles_missing", f"{segment_id} 使用图片或分镜声明图片职责时必须填写 required_reference_roles。", path))
                elif any(role not in REFERENCE_ROLES for role in required_roles):
                    issues.append(issue("error", "required_reference_role_invalid", "required_reference_roles 含无效职责。", path))
                elif not declared_roles.issubset(image_roles):
                    missing = sorted(declared_roles - image_roles)
                    issues.append(issue("error", "required_reference_role_not_passed", f"required_reference_roles 未真实传入：{missing}", path))
            elif required_roles not in (None, []):
                issues.append(issue("error", "required_reference_roles_unexpected", "没有图片输入时 required_reference_roles 应为空或省略。", path))
            if not planned_roles.issubset(declared_roles):
                missing = sorted(planned_roles - declared_roles)
                issues.append(issue("error", "storyboard_required_role_not_inherited", f"{segment_id} 未继承 storyboard.required_reference_roles：{missing}", path))
            if not planned_roles.issubset(image_roles):
                missing = sorted(planned_roles - image_roles)
                issues.append(issue("error", "storyboard_required_role_not_passed", f"{segment_id} 的 storyboard.required_reference_roles 未真实传入：{missing}", path))
            if tool_mode == "video_edit":
                if video_roles != {"source_video_for_edit"} or len(video_orders) != 1:
                    issues.append(issue("error", "video_edit_source_invalid", "video_edit 必须且只能登记一个 source_video_for_edit 源视频。", path))
            for input_item in segment.get("reference_inputs") or []:
                if not isinstance(input_item, dict):
                    continue
                source_type = input_item.get("source_type")
                source_id = input_item.get("source_id")
                role = input_item.get("role")
                if role == "previous_tail_as_start_frame" and source_type != "frame":
                    issues.append(issue("error", "previous_tail_source_type_invalid", f"{segment_id} 上一段尾帧必须以 source_type=frame 真实传入。", path))
                if source_type == "asset":
                    if role in STATE_REFERENCE_ROLES:
                        check_state_ref(source_id, asset_index, path, issues, f"{segment_id or '视频片段'} reference_inputs")
                    else:
                        check_asset_ref(source_id, asset_index, path, issues, f"{segment_id or '视频片段'} reference_inputs")
                if source_type == "keyframe" and isinstance(source_id, str) and source_id not in keyframe_ids:
                    issues.append(issue("error", "video_reference_unknown_keyframe", f"{segment_id} 引用了不存在的关键帧：{source_id}", path))
            # 声线参考只能走 audio_inputs（reference_inputs 被 ordered_inputs 限定为图片），
            # 在此对真正可达的槽位执行已批准 VOICE 样音路径策略。
            check_voice_sample_paths(segment, asset_index, path, issues)
            # 提交给模型的是 H3 成稿(h3_prompt_file)；compiled_prompt_file 现指向
            # 五段交付包文件(skill 输入与返修凭证)。标记/哈希/存在性检查一律查成稿。
            prompt_file = segment.get("h3_prompt_file")
            prompt_path = relative_file(root, prompt_file)
            package_file = segment.get("compiled_prompt_file")
            package_path = relative_file(root, package_file)
            if package_path is not None and package_file and not package_path.is_file():
                issues.append(issue("error", "delivery_package_file_missing", f"{segment_id} 登记了 compiled_prompt_file（五段交付包），但文件不存在。", path))
            check_h3_prompt(segment, root, path, issues)
            if prompt_path is not None:
                check_prompt_markers(
                    prompt_path,
                    image_orders,
                    video_orders,
                    audio_orders,
                    segment.get("speech_lines"),
                    segment.get("subtitle_enabled") is True,
                    issues,
                    h3_mode=segment.get("h3_mode", segment.get("mode", "T2VA")),
                )
                _check_h3_prompt_purity(prompt_path, issues, segment.get("h3_mode", segment.get("mode", "T2VA")), segment.get("duration_s", 6))
            # h3_prompt_file 的路径、存在性、非空、sha256 以及已生成片段的补全门，
            # 统一由 prompts.check_h3_prompt 上报（h3_prompt_* / generated_segment_h3_* 码）。
            generated_segment = bool(str(segment.get("output_file") or "").strip()) or segment.get("status") in {"candidate", "accepted"}
            status = segment.get("status")
            if status not in {None, *VIDEO_STATUS_VALUES}:
                issues.append(issue("error", "video_status_invalid", f"视频片段状态无效：{status}", path))
            elif require_accepted and status != "accepted":
                issues.append(issue("error", "video_segment_not_accepted", f"{segment_id or '视频片段'} 必须在进入成片阶段前登记 status=accepted。", path))
            elif not require_accepted and generated_segment and status not in {"candidate", "accepted"}:
                issues.append(issue("error", "video_segment_not_ready_for_confirmation", f"{segment_id or '视频片段'} 在发起拼接确认前必须登记 status=candidate 或 accepted。", path))
            if status == "candidate" and not file_exists(root, segment.get("output_file")):
                issues.append(issue("error", "video_segment_output_missing", f"{segment_id} 已进入候选状态，但 output_file 不存在。", path))
            if status == "accepted":
                if not file_exists(root, segment.get("output_file")):
                    issues.append(issue("error", "accepted_segment_output_missing", f"{segment_id} 已 accepted，但 output_file 不存在。", path))


def check_voice_sample_paths(segment: dict[str, Any], asset_index: dict[str, Any], path: Path, issues: list[dict[str, Any]]) -> None:
    """voice_audio_reference 槽位的可达路径策略：远端 URL 核资源登记，本地文件必须是已批准 VOICE 样音。"""
    segment_id = segment.get("segment_id")
    for audio_item in segment.get("audio_inputs") or []:
        if not isinstance(audio_item, dict) or audio_item.get("role") != "voice_audio_reference":
            continue
        audio_rel = str(audio_item.get("file") or "")
        if audio_rel and is_url(audio_rel):
            check_asset_ref(audio_item.get("resource_id"), asset_index, path, issues, f"{segment_id} 远端 VOICE 样音")
        elif audio_rel and "shared/03_资产/音色/" not in audio_rel.replace("\\", "/"):
            issues.append(issue(
                "error", "ref_audio_not_voice_sample",
                f"{segment_id} 的音频参考必须指向 shared/03_资产/音色/ 下已批准 VOICE 样音（路径：{audio_rel}）；禁止台词级 TTS 临时音频进入 ref_audio 槽位——正片台词由 H3 原生生成，参考只锁声线。",
                path,
            ))

# ===== 原 lint_checks/delivery.py =====



def accepted_video_segment_order(
    root: Path,
    episode_id: str,
    issues: list[dict[str, Any]],
    allow_candidate: bool = False,
) -> list[str]:
    path = root / f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json"
    data = load_json(path, issues, required=False)
    segments = data.get("segments") if isinstance(data, dict) else None
    if not isinstance(segments, list):
        return []
    return [
        item["segment_id"]
        for item in segments
        if isinstance(item, dict)
        and isinstance(item.get("segment_id"), str)
        and item.get("status") in ({"candidate", "accepted"} if allow_candidate else {"accepted"})
    ]


def output_values(data: dict[str, Any]) -> list[str] | None:
    outputs = data.get("outputs")
    if not isinstance(outputs, list):
        return None
    values: list[str] = []
    for item in outputs:
        if isinstance(item, str):
            values.append(item)
        elif isinstance(item, dict) and isinstance(item.get("file"), str):
            values.append(item["file"])
        else:
            return None
    return values


def report_is_blocked(root: Path, entry: Any) -> bool:
    if isinstance(entry, dict):
        return entry.get("status") == "blocked" or entry.get("result") == "blocked"
    target = relative_file(root, entry)
    if target is None or not target.is_file() or target.suffix.lower() != ".json":
        return False
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and (data.get("status") == "blocked" or data.get("result") == "blocked")


def check_delivery(
    root: Path,
    plan: Any,
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
) -> None:
    measured_durations: dict[str, float] = {}
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"05_成片/delivery_manifest_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        # episode_id 一致性由 common 的 check_episode_manifest_ids(stage="final") 集中核对，此处不重复上报。
        assembly_confirmation = data.get("assembly_confirmation")
        if not isinstance(assembly_confirmation, dict):
            issues.append(issue("error", "assembly_confirmation_missing", "delivery_manifest 必须登记进入成片拼接的 interaction.ask 确认。", path))
            assembly_confirmation = {}
        if assembly_confirmation.get("confirmation_purpose") != "final_assembly":
            issues.append(issue("error", "assembly_confirmation_purpose_invalid", "assembly_confirmation.confirmation_purpose 必须为 final_assembly。", path))
        if not str(assembly_confirmation.get("interaction_ask_call_id") or "").strip():
            issues.append(issue("error", "assembly_confirmation_call_id_missing", "assembly_confirmation 必须记录 interaction_ask_call_id。", path))
        if assembly_confirmation.get("interaction_ask_result") != "proceed_assembly":
            issues.append(issue("error", "assembly_confirmation_result_invalid", "assembly_confirmation.interaction_ask_result 必须为 proceed_assembly。", path))
        if not str(assembly_confirmation.get("user_message") or "").strip():
            issues.append(issue("error", "assembly_confirmation_user_message_missing", "assembly_confirmation.user_message 不能为空。", path))
        if parse_iso_time(assembly_confirmation.get("confirmed_at")) is None:
            issues.append(issue("error", "assembly_confirmation_time_invalid", "assembly_confirmation.confirmed_at 必须是带时区 ISO-8601 时间。", path))
        confirmation_records = load_confirmation_records(root, issues, required=True)
        matching_video_confirmations = [
            record
            for record in confirmation_records
            if record.get("stage") == "video"
            and record.get("episode_id") == episode_id
            and record.get("confirmation_purpose") == "video_acceptance_and_final_assembly"
            and record.get("interaction_ask_call_id") == assembly_confirmation.get("interaction_ask_call_id")
            and record.get("interaction_ask_result") == "proceed_assembly"
        ]
        if not matching_video_confirmations:
            issues.append(issue("error", "assembly_confirmation_video_record_missing", "assembly_confirmation 必须与同集 stage=video 用户确认记录使用同一 interaction.ask 调用 ID 和 proceed_assembly 结果。", path))
        subtitle_enabled = data.get("subtitle_enabled")
        if not isinstance(subtitle_enabled, bool):
            issues.append(issue("error", "subtitle_enabled_invalid", "subtitle_enabled 必须是布尔值；默认 false，用户明确要求字幕时为 true。", path))
        if data.get("status") not in {"deliverable", "candidate"}:
            issues.append(issue("error", "delivery_status_not_deliverable", "delivery_manifest.status 必须为 deliverable 或 candidate；blocked 不得交付。", path))
        duration = data.get("duration_s")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool) and math.isfinite(duration) and duration > 0:
            measured_durations[episode_id] = float(duration)
            check_duration_pair(duration, data.get("duration_display"), path, "delivery", issues)
        else:
            issues.append(issue("error", "delivery_duration_invalid", "delivery_manifest.duration_s 必须是数字。", path))
        if not file_inside(root, data.get("clean_master"), episode_root):
            issues.append(issue("error", "clean_master_missing", "clean_master 必须指向当前分集目录下真实媒体文件。", path))
        if subtitle_enabled is True and not file_inside(root, data.get("subtitle_master"), episode_root):
            issues.append(issue("error", "subtitle_master_missing", "字幕开启时 subtitle_master 必须指向当前分集目录下真实媒体文件。", path))
        if subtitle_enabled is False:
            for field in ("subtitle_master", "asr_source", "subtitle_final", "subtitle_source", "subtitle_burn_params", "subtitle_alignment_report"):
                if str(data.get(field) or "").strip():
                    issues.append(issue("error", "subtitle_disabled_field_not_empty", f"字幕关闭时 {field} 必须留空。", path))
        outputs = output_values(data)
        if outputs is None:
            issues.append(issue("error", "outputs_invalid", "outputs 必须是路径数组，或每项包含 file。", path))
        elif subtitle_enabled is False and outputs != [data.get("clean_master")]:
            issues.append(issue("error", "outputs_mismatch", "outputs 必须与用户可见正式交付文件精确一致：字幕关闭时只交付 [clean_master]。", path))
        elif subtitle_enabled is True and outputs != [data.get("subtitle_master")]:
            issues.append(issue("error", "outputs_mismatch", "outputs 必须与用户可见正式交付文件精确一致：字幕开启时只交付 [subtitle_master]。", path))
        if subtitle_enabled is True:
            subtitle_alignment_report = data.get("subtitle_alignment_report")
            if not str(subtitle_alignment_report or "").strip():
                issues.append(issue("error", "subtitle_alignment_report_missing", "字幕开启时必须存在 subtitle_alignment_report（字幕对齐报告）。", path))
            elif not file_inside(root, subtitle_alignment_report, episode_root) or report_is_blocked(root, subtitle_alignment_report):
                issues.append(issue("error", "subtitle_alignment_report_invalid", "subtitle_alignment_report 必须指向当前分集目录下未 blocked 的内部追溯文件。", path))
            subtitle_source = data.get("subtitle_source")
            if not file_inside(root, subtitle_source, episode_root):
                issues.append(issue("error", "subtitle_source_missing", "字幕开启时必须存在当前分集目录下的 subtitle_source。", path))
            subtitle_final = data.get("subtitle_final")
            if not file_inside(root, subtitle_final, episode_root):
                issues.append(issue("error", "subtitle_final_missing", "字幕开启时必须存在当前分集目录下的 subtitle_final。", path))
        accepted_order = accepted_video_segment_order(root, episode_id, issues)
        if assembly_confirmation.get("segment_ids") != accepted_order:
            issues.append(issue("error", "assembly_confirmation_segments_mismatch", "assembly_confirmation.segment_ids 必须按顺序精确等于当前成片采用的 accepted SEG。", path))
    contract = plan.get("duration_contract") if isinstance(plan, dict) else None
    if isinstance(contract, dict):
        mode = contract.get("mode")
        scope = contract.get("scope")
        measured = list(measured_durations.values())
        try:
            bounds = duration_contract_bounds(contract)
        except ValueError:
            # 合同非法已由随各阶段运行的 check_plan_durations 报 duration_contract_invalid；
            # 这里只中止实测时长核对，不重复上报。
            bounds = None
        if bounds is not None and measured:
            if scope == "episode":
                values = [(episode_id, value) for episode_id, value in measured_durations.items()]
            elif episode_filter is None:
                values = [("全项目" if scope == "project" else "交付物", sum(measured))]
            else:
                values = []
            lower, upper = bounds
            for label, value in values:
                if value < lower - 1e-6 or value > upper + 1e-6:
                    issues.append(issue("error", "delivery_duration_out_of_contract", f"{label} 实测 {value:g}s 不在 duration_contract {mode} 范围 [{lower:g}, {upper:g}]s；不得以计划时长代替实测。", root / "00_制作控制/drama_plan.json"))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Focused doubao-creative-drama workflow validator.")
    parser.add_argument("skill_root", nargs="?", default=".")
    parser.add_argument("--project-root")
    parser.add_argument("--stage", choices=("skill", *STAGES, "all"), default="skill")
    parser.add_argument(
        "--pre-confirmation",
        action="store_true",
        help="规划确认展示前门：只豁免 exact/target_band 时长合同对本次规划确认记录的回指，仅限 --stage planning。",
    )
    args = parser.parse_args(argv)
    if args.pre_confirmation and args.stage != "planning":
        parser.error("--pre-confirmation 只允许与 --stage planning 同用")
    return args


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    args = parse_args(argv or sys.argv[1:])
    project_root = Path(args.project_root).resolve() if args.project_root else Path(args.skill_root).resolve()
    issues: list[dict[str, Any]] = []

    if args.stage == "skill":
        check_beat_library_desync(issues)
        issues = dedupe_issues(issues)
        error_count = sum(1 for item in issues if item["level"] == "error")
        payload = {
            "summary": {
                "error_count": error_count,
                "warning_count": sum(1 for item in issues if item["level"] == "warning"),
                "scope": args.stage,
            },
            "release_ready": error_count == 0,
            "issues": issues,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if error_count else 0

    plan = load_json(project_root / "00_制作控制/drama_plan.json", issues, required=False)
    expected_durations = check_plan_durations(project_root, plan, issues, pending_confirmation=args.pre_confirmation)
    check_episode_directories(project_root, expected_durations, issues)
    check_episode_entry_manifests(project_root, issues)
    check_state(project_root, plan, issues)
    check_operation_log_tools(project_root, issues)

    state = load_json(project_root / "00_制作控制/制作状态.json", issues, required=False)
    active_episode = state.get("current_episode") if isinstance(state, dict) else None
    stages_to_check = STAGES if args.stage == "all" else (args.stage,)
    for stage in stages_to_check:
        episode_filter = active_episode if args.stage != "all" and stage in EPISODE_STAGES else None
        check_stage_artifacts(project_root, stage, issues, episode_filter)
        if stage in EPISODE_STAGES:
            check_episode_manifest_ids(project_root, stage, issues, episode_filter)
    episode_filter = active_episode if args.stage != "all" and args.stage in EPISODE_STAGES else None
    selected = set(stages_to_check)
    asset_index = blank_asset_index()
    if selected & {"assets", "storyboard", "keyframes", "video", "final"}:
        asset_index = check_assets(project_root, issues, episode_filter)
    if selected & {"storyboard", "keyframes", "video", "final"}:
        rhythm_lib = RhythmLibrary()
        rhythm_lib.ensure()
        check_storyboards(project_root, plan, issues, episode_filter, asset_index=asset_index, rhythm=rhythm_lib)
    if selected & {"keyframes", "video", "final"}:
        check_keyframes(project_root, asset_index, issues, episode_filter)
    if selected & {"video", "final"}:
        audio_capable_modes: set[str] | None = None
        capabilities = rhythm_lib.h3.get("capabilities") if isinstance(rhythm_lib.h3, dict) else None
        mode_limits = capabilities.get("mode_ref_limits") if isinstance(capabilities, dict) else None
        if isinstance(mode_limits, dict):
            audio_capable_modes = {
                str(mode) for mode, limits in mode_limits.items()
                if isinstance(limits, dict) and isinstance(limits.get("audios_max"), int) and limits["audios_max"] > 0
            }
        check_video(
            project_root,
            asset_index,
            issues,
            episode_filter,
            require_accepted=args.stage in {"final", "all"},
            audio_capable_modes=audio_capable_modes,
        )
    if "final" in selected:
        check_delivery(project_root, plan, issues, episode_filter)

    issues = dedupe_issues(issues)
    error_count = sum(1 for item in issues if item["level"] == "error")
    payload = {
        "summary": {
            "error_count": error_count,
            "warning_count": sum(1 for item in issues if item["level"] == "warning"),
            "scope": args.stage,
        },
        "release_ready": error_count == 0,
        "issues": issues,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
