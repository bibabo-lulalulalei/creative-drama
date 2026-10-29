#!/usr/bin/env python3
"""Focused workflow checks for doubao-creative-drama.

The lint gate only checks deterministic workflow relationships: types, enums,
IDs, durations, declared files, references, stage order, exact prompt media
markers, and structural rhythm/camera distribution over declared shot fields
(shot counts, durations, beat_type, camera_family, cut_motivation,
cut_tolerance_s, including the episode static-camera share hard cap). It does not score natural-language wording, creative quality,
subjective pacing, performance, visual quality, or other subjective content.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote


STAGES = ("planning", "script", "assets", "storyboard", "keyframes", "video", "final")
EPISODE_STAGES = set(STAGES[1:])
STATUS_VALUES = {"pending", "in_progress", "awaiting_confirmation", "confirmed", "merged", "invalidated", "blocked"}
ASSET_STATUS_VALUES = {"draft", "reviewed", "approved", "rejected", "superseded"}
VISUAL_REFERENCE_DECISIONS = {"used", "none_available", "explicit_user_override"}
PROJECT_VISUAL_MODES = {"live_action", "photoreal", "2d_comic", "anime", "ink_animation", "illustration", "stylized_3d", "mixed_with_explicit_scope"}
VIDEO_STATUS_VALUES = {"candidate", "accepted", "rejected", "blocked"}
VIDEO_TOOL_MODES = {"text_to_video", "media_to_video", "image_to_video", "video_edit"}
IMAGE_GENERATION_TOOLS = {"image_gen", "image_edit"}
FORBIDDEN_TOOL_TERMS = ("text_to_image",)
DEFAULT_MEDIA_VIDEO_TOTAL_LIMIT_S = 15
DEFAULT_MEDIA_AUDIO_TOTAL_LIMIT_S = 15
SEEDANCE25_MEDIA_VIDEO_TOTAL_LIMIT_S = 28
SEEDANCE25_MEDIA_AUDIO_TOTAL_LIMIT_S = 30
SKILL_SCRIPTS_DIR = Path(__file__).resolve().parent
BEAT_LIBRARY_JSON_PATH = SKILL_SCRIPTS_DIR / "beat_types.json"
BEAT_LIBRARY_MD_PATH = SKILL_SCRIPTS_DIR.parent / "references" / "节拍类型库.md"
H3_CAPABILITY_PATH = SKILL_SCRIPTS_DIR.parent / "tools" / "video" / "h3.json"

DURATION_BASIS_SUM_TOLERANCE_S = 0.25
DURATION_BASIS_CLONE_MIN_SHOTS = 3
SPEECH_UNDERFILL_MAX_SHARE = 0.4

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
ASSET_PREFIX_BY_CATEGORY = {
    "character": "CHR",
    "scene": "SCN",
    "prop": "PROP",
    "voice": "VOICE",
    "style": "STYLE",
}
MERGEABLE_LIGHTWEIGHT_STAGES = {"script", "assets", "storyboard", "keyframes", "video"}
CURRENT_STAGE_ACTIVE_VALUES = {"in_progress", "awaiting_confirmation", "invalidated", "blocked"}
CONFIRMATION_MODES = {"full", "incremental"}
IMAGE_INPUT_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
ISO_TIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})")


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


class RhythmLibrary:
    """beat_types.json / h3.json / rhythm_engine 的懒加载上下文。

    只在涉及分镜的阶段（storyboard/keyframes/video/final/all）加载；加载失败只影响这些阶段，
    其余阶段（planning/script/assets）完全不受 beat_types.json 状态影响。
    """

    def __init__(self) -> None:
        self._attempted = False
        self.library: dict[str, Any] | None = None
        self.h3: dict[str, Any] | None = None
        self.engine: Any = None
        self.builder: Any = None
        self.error: str | None = None
        self.h3_error: str | None = None

    def ensure(self) -> bool:
        if self._attempted:
            return self.library is not None
        self._attempted = True
        try:
            scripts_dir = str(SKILL_SCRIPTS_DIR)
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            import build_beat_types
            import rhythm_engine

            self.engine = rhythm_engine
            self.builder = build_beat_types
        except Exception as exc:
            self.error = f"rhythm_engine/build_beat_types 导入失败：{exc}"
            return False
        try:
            self.library = self.engine.load_library(BEAT_LIBRARY_JSON_PATH)
        except SystemExit as exc:
            self.error = f"beat_types.json 加载失败：{exc}"
        except Exception as exc:
            self.error = f"beat_types.json 加载失败：{exc}"
        try:
            self.h3 = self.engine.load_h3(H3_CAPABILITY_PATH)
        except Exception as exc:
            self.h3_error = f"h3.json 加载失败：{exc}"
        return self.library is not None

    @property
    def params(self) -> dict[str, Any]:
        return self.library["params"]

    @property
    def placeholder(self) -> bool:
        """库 version==0 为建设期占位：desync/drift 类检查全部降级为 info。"""
        return isinstance(self.library, dict) and self.library.get("version") == 0


def fast_capable_beat_types(beats: dict[str, Any]) -> set[str]:
    """快节奏节拍 = 《节拍类型库》§4 显式标记 fast_pole_capable 的类型（库是唯一权威）。
    不得按「强度 5 锚点 ≤ fast_pole_max_s」推断——锚点只说明该类压得到那么短，
    不代表它要求全片都快（对白/过场的锚点也 ≤3s，但平静戏用长镜天经地义）。"""
    return {
        name
        for name, entry in beats.items()
        if isinstance(entry, dict) and entry.get("fast_pole_capable") is True
    }


def check_beat_library_desync(rhythm: RhythmLibrary, issues: list[dict[str, Any]]) -> None:
    """desync 检查：重跑生成器，输出与磁盘 beat_types.json 逐项比对。
    md 不存在或库 version==0（占位期）→ info；内容不一致 → error。"""
    if rhythm.library is None:
        issues.append(issue("error", "beat_library_unavailable", f"{rhythm.error or 'beat_types.json 不可用'}；涉及分镜阶段的节奏检查无法执行。", BEAT_LIBRARY_JSON_PATH))
        return
    if rhythm.h3 is None and rhythm.h3_error:
        issues.append(issue("info", "h3_capabilities_unavailable", f"{rhythm.h3_error}；模型硬合同类检查（段上限/高密度段）跳过。", H3_CAPABILITY_PATH))
    if not BEAT_LIBRARY_MD_PATH.is_file():
        issues.append(issue("error", "beat_library_desync", "references/节拍类型库.md 缺失：本库已入库为唯一人类权威，缺失即安装破损；恢复该文件后重跑 build_beat_types.py 再执行 lint。", BEAT_LIBRARY_MD_PATH))
        return
    level = "info" if rhythm.placeholder else "error"
    import contextlib
    import io as _io

    capture = _io.StringIO()
    try:
        with contextlib.redirect_stderr(capture):
            rebuilt = rhythm.builder.build(str(BEAT_LIBRARY_MD_PATH))
    except SystemExit:
        detail = capture.getvalue().strip() or "生成器解析失败"
        issues.append(issue(level, "beat_library_desync", f"《节拍类型库.md》无法被 build_beat_types 解析：{detail}", BEAT_LIBRARY_MD_PATH))
        return
    mismatched = [
        key
        for key in ("version", "params", "beat_types", "style_profiles")
        if rhythm.library.get(key) != rebuilt.get(key)
    ]
    if mismatched:
        issues.append(issue(level, "beat_library_desync", f"《节拍类型库.md》重新生成结果与磁盘 beat_types.json 不一致（章节：{mismatched}）；md 是唯一权威，请重跑 build_beat_types.py。", BEAT_LIBRARY_JSON_PATH))


_BASIS_PAREN_PATTERN = re.compile(r"[（(][^（）()]*[）)]")


def duration_basis_sum(text: str) -> float | None:
    """剥离括号注释后，将 duration_basis 各分项数字加总；一个数字都解析不到返回 None。
    兼容引擎发票格式：「台词2.8(8字@4/s)+取整-0.3+配平+0.5」（负号分项直接带符号）。"""
    cleaned = _BASIS_PAREN_PATTERN.sub("", text)
    total = 0.0
    found = False
    for token in re.split(r"[+＋]", cleaned):
        match = re.search(r"-?\d+(?:\.\d+)?", token)
        if match:
            total += float(match.group(0))
            found = True
    return total if found else None


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
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
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


def check_episode_entry_manifests(root: Path, issues: list[dict[str, Any]], lightweight: bool = False) -> None:
    for episode_id, episode_root in episode_dirs(root):
        path = episode_root / f"episode_manifest_{episode_id}.json"
        data = load_json(path, issues, required=True)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", f"episode_manifest episode_id 必须等于目录 ID：{episode_id}", path))
        stage_manifests = data.get("stage_manifests")
        if not isinstance(stage_manifests, dict):
            issues.append(issue("error", "stage_manifests_missing", "episode_manifest 必须使用顶层 stage_manifests，不得使用旧字段 manifests。", path))
            continue
        if lightweight:
            expected = {
                "script": "",
                "storyboard": f"episodes/{episode_id}/02_分镜/分镜_完整分镜表_{episode_id}.md",
                "assets": "",
                "keyframes": "",
                "video": f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json",
                "continuity": "",
                "delivery": f"episodes/{episode_id}/05_成片/delivery_manifest_{episode_id}.json",
            }
        else:
            expected = {
                "script": f"episodes/{episode_id}/01_剧本/script_contract_{episode_id}.json",
                "storyboard": f"episodes/{episode_id}/02_分镜/storyboard_{episode_id}.json",
                "assets": f"episodes/{episode_id}/03_资产/asset_usage_{episode_id}.json",
                "keyframes": f"episodes/{episode_id}/03_资产/keyframe_manifest_{episode_id}.json",
                "video": f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json",
                "continuity": f"episodes/{episode_id}/04_视频片段/continuity_{episode_id}.json",
                "delivery": f"episodes/{episode_id}/05_成片/delivery_manifest_{episode_id}.json",
            }
        for stage, expected_path in expected.items():
            if stage_manifests.get(stage) != expected_path:
                issues.append(issue("error", "stage_manifest_path_invalid", f"episode_manifest.stage_manifests.{stage} 必须指向 {expected_path}。", path))


def plan_revision(plan: Any, state: dict[str, Any]) -> int | None:
    for source in (state, plan if isinstance(plan, dict) else {}):
        value = source.get("revision") if isinstance(source, dict) else None
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def is_lightweight_plan(plan: Any) -> bool:
    return isinstance(plan, dict) and isinstance(plan.get("objective"), dict) and plan["objective"].get("workflow_mode") == "lightweight"


def lightweight_constraints_valid(plan: Any) -> bool:
    if not isinstance(plan, dict):
        return False
    scale = plan.get("scale_plan") if isinstance(plan.get("scale_plan"), dict) else {}
    count = scale.get("episode_count")
    total = scale.get("total_duration_s")
    if count != 1 or not isinstance(total, (int, float)) or isinstance(total, bool):
        return False
    model_plan = plan.get("model_plan") if isinstance(plan.get("model_plan"), dict) else {}
    video_plan = model_plan.get("video") if isinstance(model_plan.get("video"), dict) else {}
    model_text = " ".join(
        str(video_plan.get(key) or "")
        for key in ("model", "name", "user_requested_model", "display_name")
    ).lower()
    limit_s = 30 if "seedance 2.5" in model_text else 15
    return float(total) <= limit_s


def target_stage(plan: Any) -> str | None:
    objective = plan.get("objective") if isinstance(plan, dict) else None
    value = objective.get("target_stage") if isinstance(objective, dict) else None
    return value if value in STAGES else None


def load_confirmation_records(
    root: Path,
    issues: list[dict[str, Any]],
    required: bool,
    require_planning_interaction: bool = False,
    lightweight: bool = False,
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
        expected_purpose = "video_generation" if lightweight else "project_execution"
        expected_result = "generate" if lightweight else "proceed_project"
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
    lightweight = is_lightweight_plan(plan)
    lightweight_valid = lightweight and lightweight_constraints_valid(plan)
    target = target_stage(plan)
    objective = plan.get("objective") if isinstance(plan, dict) else {}
    if not isinstance(objective, dict) or objective.get("target_stage") not in STAGES:
        issues.append(issue("error", "target_stage_invalid", "drama_plan.objective.target_stage 必须是有效阶段。", state_path))
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
            if index < current_index and value not in {"confirmed", "merged"}:
                issues.append(issue("error", "phase_order_invalid", f"{stage} 应先完成后再进入 {current}。", state_path))
            if index > current_index and value not in {"pending", "invalidated"}:
                issues.append(issue("error", "future_phase_status_invalid", f"{stage} 晚于 current_stage={current}，只能是 pending 或 invalidated。", state_path))
            if index == current_index:
                allowed_current = set(CURRENT_STAGE_ACTIVE_VALUES)
                if current == "final" or current == target:
                    allowed_current.add("confirmed")
                if lightweight_valid and stage in MERGEABLE_LIGHTWEIGHT_STAGES:
                    allowed_current.add("merged")
                if value not in allowed_current:
                    issues.append(issue("error", "current_phase_status_invalid", f"{stage} 是 current_stage，状态不能是 {value}。", state_path))
            if value == "merged" and (not lightweight_valid or stage not in MERGEABLE_LIGHTWEIGHT_STAGES):
                issues.append(issue("error", "phase_merged_invalid", f"{stage} 不能标记为 merged。", state_path))
        if current_index > 0:
            needs_confirmations = True
    elif current in EPISODE_STAGES:
        if current_episode not in episode_ids:
            issues.append(issue("error", "current_episode_invalid", "逐集生产阶段必须把 current_episode 指向计划内分集。", state_path))
        if target in STAGES and STAGES.index(current) > STAGES.index(target):
            issues.append(issue("error", "current_stage_beyond_target", f"current_stage={current} 不得晚于 objective.target_stage={target}。", state_path))
        if phases.get("planning") != "confirmed":
            issues.append(issue("error", "project_prerequisite_not_confirmed", "进入逐集生产前 phases.planning 必须为 confirmed。", state_path))
        allowed_script_statuses = {"confirmed", "merged"} if lightweight_valid else {"confirmed"}
        if phases.get("script") not in allowed_script_statuses:
            issues.append(issue("error", "project_prerequisite_not_confirmed", "进入逐集生产前项目级 phases.script 必须为 confirmed；合法轻量模式可为 merged。", state_path))
        for stage in STAGES[2:]:
            value = phases.get(stage)
            if value == "merged" and (not lightweight_valid or stage not in MERGEABLE_LIGHTWEIGHT_STAGES):
                issues.append(issue("error", "phase_merged_invalid", f"{stage} 不能标记为 merged。", state_path))
        needs_confirmations = True
    if lightweight and not lightweight_valid:
        issues.append(issue("error", "lightweight_scope_invalid", "lightweight 只允许单集，且总时长不得超过当前视频模型轻量上限：seedance 2.0 系列 15 秒，seedance 2.5 为 30 秒。", state_path))
    confirmations = load_confirmation_records(
        root,
        issues,
        needs_confirmations,
        require_planning_interaction=target in {"video", "final"},
        lightweight=lightweight_valid,
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
                    if stage in EPISODE_STAGES and value == "merged" and (not lightweight_valid or stage not in MERGEABLE_LIGHTWEIGHT_STAGES):
                        issues.append(issue("error", "episode_phase_merged_invalid", f"{episode_id}.{stage} 不能标记为 merged。", state_path))
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
                                allowed_completed = {"confirmed", "merged"} if lightweight_valid and stage in MERGEABLE_LIGHTWEIGHT_STAGES else {"confirmed"}
                                if statuses.get(stage) not in allowed_completed:
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
                        if current != "script" and statuses.get("script") not in allowed_script_statuses:
                            issues.append(issue("error", "current_episode_script_incomplete", f"{episode_id}.script 必须在后续生产前确认为 confirmed；合法轻量模式可为 merged。", state_path))
                        for stage in EPISODE_STAGES:
                            value = statuses.get(stage)
                            index = STAGES.index(stage)
                            if index < current_episode_index and value not in {"confirmed", "merged"}:
                                issues.append(issue("error", "episode_phase_order_invalid", f"{episode_id}.{stage} 应先完成后再进入 {current}。", state_path))
                            if index > current_episode_index and value not in {"pending", "invalidated"}:
                                issues.append(issue("error", "episode_future_phase_status_invalid", f"{episode_id}.{stage} 晚于当前集 current_stage={current}，只能是 pending 或 invalidated。", state_path))
                            if index == current_episode_index:
                                allowed_current = set(CURRENT_STAGE_ACTIVE_VALUES)
                                current_is_last_episode = episode_position == len(episode_ids) - 1
                                if current_is_last_episode and current in {"final", target}:
                                    allowed_current.add("confirmed")
                                if lightweight_valid and stage in MERGEABLE_LIGHTWEIGHT_STAGES:
                                    allowed_current.add("merged")
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
            if not stage_values or any(value not in {"confirmed", "merged"} for value in stage_values):
                issues.append(issue("error", "aggregate_phase_confirmed_early", f"phases.{stage} 只有在全部分集该阶段完成后才能写 confirmed。", state_path))
        if current in EPISODE_STAGES and current_episode in episodes:
            current_statuses = episodes[current_episode].get("stage_status") if isinstance(episodes[current_episode], dict) else {}
            current_index = STAGES.index(current)
            for stage in STAGES[2:]:
                phase_value = phases.get(stage)
                stage_index = STAGES.index(stage)
                completed_values = {"confirmed", "merged"} if lightweight_valid and stage in MERGEABLE_LIGHTWEIGHT_STAGES else {"confirmed"}
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
                    if phase_value != "confirmed" and not (lightweight_valid and stage in MERGEABLE_LIGHTWEIGHT_STAGES and phase_value == "merged"):
                        issues.append(issue("error", "aggregate_phase_status_mismatch", f"phases.{stage} 必须反映全部分集已完成。", state_path))
                elif stage == current:
                    current_value = current_statuses.get(stage) if isinstance(current_statuses, dict) else None
                    if phase_value != current_value:
                        issues.append(issue("error", "aggregate_current_phase_mismatch", f"phases.{stage} 必须与 {current_episode}.{stage} 当前活动状态一致。", state_path))
                elif stage_index > current_index and phase_value not in ({"pending", "invalidated", "in_progress"} if any_completed else {"pending", "invalidated"}):
                    issues.append(issue("error", "aggregate_future_phase_started", f"phases.{stage} 与已完成分集的聚合状态不一致。", state_path))
                elif stage_index < current_index and phase_value not in {"in_progress", "confirmed", "merged"}:
                    issues.append(issue("error", "aggregate_previous_phase_invalid", f"phases.{stage} 已有分集完成但尚未全量完成，必须保持 in_progress 或合法完成态。", state_path))


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


def check_stage_artifacts(
    root: Path,
    stage: str,
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
    lightweight: bool = False,
) -> None:
    required = [root / "00_制作控制/drama_plan.json", root / "00_制作控制/制作状态.json"]
    state = load_json(root / "00_制作控制/制作状态.json", issues, required=False)
    script_status = state.get("phases", {}).get("script") if isinstance(state, dict) and isinstance(state.get("phases"), dict) else None
    script_should_exist = not lightweight or script_status == "confirmed"
    episode_states = state.get("episodes", {}) if isinstance(state, dict) and isinstance(state.get("episodes"), dict) else {}
    if stage == "planning":
        required += [
            root / "00_制作控制/project_manifest.json",
            root / "00_制作控制/source_manifest.json",
            root / "episodes",
        ]
    if stage == "script" and script_should_exist:
        required += [
            root / "00_制作控制/project_data_card.json",
            root / "01_剧本/project_script_manifest.json",
            root / "01_剧本/项目_事实与假设.md",
            root / "01_剧本/剧本_全局设定与分集总纲.md",
            root / "01_剧本/剧本_全剧完整剧本.md",
        ]
    if stage in {"assets", "storyboard", "keyframes", "video", "final"} and not lightweight:
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
            not lightweight
            and (
                stage in {"assets", "storyboard", "keyframes", "video", "final"}
                or (
                    stage == "script"
                    and (
                        episode_filter == episode_id
                        or episode_script_status in {"in_progress", "awaiting_confirmation", "confirmed", "blocked"}
                    )
                )
            )
        )
        if require_episode_script:
            required += [
                episode_root / f"01_剧本/script_contract_{episode_id}.json",
                episode_root / f"01_剧本/剧本_完整剧本_{episode_id}.md",
            ]
        if stage in {"assets", "storyboard", "keyframes", "video", "final"} and not lightweight:
            required += [root / "shared/03_资产/asset_registry.json", episode_root / f"03_资产/asset_usage_{episode_id}.json"]
        if stage in {"storyboard", "keyframes", "video", "final"} and lightweight:
            required.append(episode_root / f"02_分镜/分镜_完整分镜表_{episode_id}.md")
        elif stage in {"storyboard", "keyframes", "video", "final"}:
            required += [
                episode_root / f"02_分镜/storyboard_{episode_id}.json",
                episode_root / f"02_分镜/分镜_阅读稿_{episode_id}.md",
                episode_root / f"02_分镜/导演总控卡_{episode_id}.md",
                episode_root / f"02_分镜/分镜_完整分镜表_{episode_id}.md",
            ]
        if stage in {"keyframes", "video", "final"} and not lightweight:
            required += [episode_root / f"03_资产/keyframe_manifest_{episode_id}.json"]
        if stage in {"video", "final"}:
            required += [episode_root / f"04_视频片段/video_manifest_{episode_id}.json"]
        if stage == "final":
            required += [episode_root / f"05_成片/delivery_manifest_{episode_id}.json"]
    for path in required:
        if not path.exists():
            issues.append(issue("error", "required_artifact_missing", "缺少当前阶段所需产物。", path))
    if lightweight and stage in {"storyboard", "keyframes", "video", "final"}:
        for episode_id, episode_root in episode_dirs(root, episode_filter):
            storyboard_path = episode_root / f"02_分镜/分镜_完整分镜表_{episode_id}.md"
            if not storyboard_path.is_file():
                continue
            try:
                storyboard_text = storyboard_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                issues.append(issue("error", "storyboard_source_markdown_unreadable", f"十五列完整分镜表无法读取：{exc}", storyboard_path))
            else:
                if 15 not in markdown_table_column_counts(storyboard_text):
                    issues.append(issue("error", "storyboard_fifteen_columns_missing", "完整分镜表必须包含一个十五列表格。", storyboard_path))
    if stage == "script" and script_should_exist:
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
        if not lightweight:
            for episode_id, episode_root in episode_dirs(root, episode_filter):
                episode_script_status = (
                    episode_states.get(episode_id, {}).get("stage_status", {}).get("script")
                    if isinstance(episode_states.get(episode_id), dict)
                    and isinstance(episode_states.get(episode_id, {}).get("stage_status"), dict)
                    else None
                )
                if stage == "script" and episode_filter is None and episode_script_status not in {"in_progress", "awaiting_confirmation", "confirmed", "blocked"}:
                    continue
                contract_path = episode_root / f"01_剧本/script_contract_{episode_id}.json"
                contract = load_json(contract_path, issues, required=False)
                if not isinstance(contract, dict):
                    continue
                highlight_ledger = contract.get("highlight_ledger")
                if not isinstance(highlight_ledger, list):
                    issues.append(issue("error", "highlight_ledger_invalid", "完整模式 script_contract.highlight_ledger 必须是数组。", contract_path))
                    continue
                primary_entries = [
                    item
                    for item in highlight_ledger
                    if isinstance(item, dict) and item.get("role") == "primary" and str(item.get("highlight_id") or "").strip()
                ]
                if not primary_entries:
                    issues.append(issue("error", "primary_highlight_missing", "完整模式每集 script_contract.highlight_ledger 必须至少包含一个有效的 primary 亮点。", contract_path))


def check_plan_durations(root: Path, plan: Any, issues: list[dict[str, Any]]) -> dict[str, int]:
    expected: dict[str, int] = {}
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
        expected_counts = {3} if selection_mode == "divergent" else {1, 2, 3}
        if not isinstance(candidates, list) or len(candidates) not in expected_counts:
            expected_text = "恰好 3 个" if selection_mode == "divergent" else "1-3 个"
            issues.append(issue("error", "creative_mechanism_candidates_invalid", f"当前 selection_mode 的 creative_mechanism.candidates 必须包含{expected_text}候选。", path))
        else:
            for index, candidate in enumerate(candidates, start=1):
                supporting = candidate.get("supporting") if isinstance(candidate, dict) else None
                if not isinstance(candidate, dict) or not has_meaningful_value(candidate.get("primary")):
                    issues.append(issue("error", "creative_mechanism_primary_missing", f"创意机制候选 {index} 必须填写主机制。", path))
                else:
                    candidate_primaries.append(str(candidate["primary"]).strip())
                if not isinstance(supporting, list) or not 1 <= len(supporting) <= 3:
                    issues.append(issue("error", "creative_mechanism_supporting_invalid", f"创意机制候选 {index} 必须包含 1-3 个同源辅助机制。", path))
        selected_primary = str(creative_mechanism.get("primary") or "").strip()
        if not selected_primary:
            issues.append(issue("error", "creative_mechanism_selected_missing", "creative_mechanism.primary 必须锁定唯一主机制。", path))
        elif candidate_primaries and selected_primary not in candidate_primaries:
            issues.append(issue("error", "creative_mechanism_selected_unknown", "creative_mechanism.primary 必须来自当前候选主机制之一。", path))
        selected_supporting = creative_mechanism.get("supporting")
        if not isinstance(selected_supporting, list) or not 1 <= len(selected_supporting) <= 3:
            issues.append(issue("error", "creative_mechanism_selected_supporting_invalid", "creative_mechanism.supporting 必须保留 1-3 个辅助机制。", path))
    rhythm_design = plan.get("rhythm_design")
    rhythm_fields = ("immutable_nodes", "node_loads", "primary_downbeat", "transition_choices", "duration_allocation", "intensity_sequence", "selected_wave")
    if not isinstance(rhythm_design, dict):
        issues.append(issue("error", "rhythm_design_missing", "drama_plan 必须填写六步推导后的 rhythm_design。", path))
    else:
        for field in rhythm_fields:
            if not has_meaningful_value(rhythm_design.get(field)):
                issues.append(issue("error", "rhythm_design_field_missing", f"rhythm_design.{field} 必须填写。", path))
        intensity = rhythm_design.get("intensity_sequence")
        if has_meaningful_value(intensity) and (
            not isinstance(intensity, list)
            or any(not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5 for value in intensity)
        ):
            issues.append(issue("error", "rhythm_intensity_invalid", "rhythm_design.intensity_sequence 只能是 1-5 的整数数组，如 [3,2,4]。", path))
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
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
            issues.append(issue("error", "episode_duration_invalid", f"第 {index} 集时长必须是数字。", path))
            continue
        value = int(round(float(seconds)))
        numeric.append(value)
        expected[f"ep_{index}"] = value
        display = displays[index - 1] if isinstance(displays, list) and index - 1 < len(displays) else None
        check_duration_pair(value, display, path, f"ep_{index}", issues)
    if isinstance(total, (int, float)) and not isinstance(total, bool):
        if numeric and int(round(float(total))) != sum(numeric):
            issues.append(issue("error", "total_duration_mismatch", "total_duration_s 必须等于各集 episode_durations_s 之和。", path))
        check_duration_pair(total, total_display, path, "total", issues, total_display=True)
    else:
        issues.append(issue("error", "total_duration_invalid", "total_duration_s 必须是数字。", path))
    duration_contract = plan.get("duration_contract")
    if not isinstance(duration_contract, dict):
        issues.append(issue("warning", "duration_contract_missing_legacy", "旧版 drama_plan 未登记 duration_contract；新项目必须显式写 target_band/exact/unbounded，存量项目暂按旧计划解释。", path))
    else:
        mode = duration_contract.get("mode")
        scope = duration_contract.get("scope")
        target = duration_contract.get("target_duration_s")
        tolerance = duration_contract.get("tolerance_ratio")
        if mode not in {"target_band", "exact", "unbounded"} or scope not in {"deliverable", "episode", "project"}:
            issues.append(issue("error", "duration_contract_invalid", "duration_contract.mode/scope 必须是有效枚举。", path))
        elif mode == "unbounded":
            if target is not None or tolerance is not None:
                issues.append(issue("error", "duration_contract_unbounded_invalid", "unbounded 模式的 target_duration_s/tolerance_ratio 必须为 null。", path))
        elif not isinstance(target, (int, float)) or isinstance(target, bool) or target <= 0:
            issues.append(issue("error", "duration_contract_target_invalid", "target_band/exact 必须提供正数 target_duration_s。", path))
        elif mode == "exact" and tolerance != 0:
            issues.append(issue("error", "duration_contract_exact_invalid", "exact 模式 tolerance_ratio 必须为 0。", path))
        elif mode == "target_band" and (not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not 0 <= tolerance < 1):
            issues.append(issue("error", "duration_contract_tolerance_invalid", "target_band tolerance_ratio 必须在 [0,1)；默认 0.10。", path))
        elif mode in {"target_band", "exact"} and isinstance(target, (int, float)):
            planning_values = ([ (f"ep_{i}", value) for i, value in enumerate(numeric, 1)] if scope == "episode" else ([ ("全项目" if scope == "project" else "交付物", sum(numeric))] if numeric else []))
            delta = 0 if mode == "exact" else float(tolerance or 0)
            lower, upper = float(target) * (1 - delta), float(target) * (1 + delta)
            for label, planning_total in planning_values:
                if planning_total < lower - 1e-6 or planning_total > upper + 1e-6:
                    issues.append(issue("error", "planned_duration_out_of_contract", f"{label}规划时长 {planning_total:g}s 不在用户 duration_contract 范围 [{lower:g}, {upper:g}]s；不得通过镜头配平修正，应修改内容设计或重新确认目标。", path))
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


def video_model_name(plan: Any, storyboard: dict[str, Any], segment: dict[str, Any]) -> str:
    for value in (
        segment.get("video_model"),
        segment.get("model"),
        storyboard.get("video_model"),
        storyboard.get("model"),
    ):
        if isinstance(value, str) and value.strip():
            return value
    model_plan = plan.get("model_plan") if isinstance(plan, dict) else None
    video_plan = model_plan.get("video") if isinstance(model_plan, dict) else None
    if isinstance(video_plan, dict):
        for field in ("model", "model_name", "selected_model"):
            value = video_plan.get(field)
            if isinstance(value, str) and value.strip():
                return value
    if isinstance(video_plan, str):
        return video_plan
    return ""


def media_to_video_limits(model_name: str) -> tuple[int, int]:
    if "seedance 2.5" in model_name.lower():
        return SEEDANCE25_MEDIA_VIDEO_TOTAL_LIMIT_S, SEEDANCE25_MEDIA_AUDIO_TOTAL_LIMIT_S
    return DEFAULT_MEDIA_VIDEO_TOTAL_LIMIT_S, DEFAULT_MEDIA_AUDIO_TOTAL_LIMIT_S


def check_segment_shot_count(
    segment_id: Any,
    duration_s: int,
    shot_count: int,
    shot_mode: Any,
    density_profile: Any,
    path: Path,
    issues: list[dict[str, Any]],
    high_density_cap_s: float | None = None,
    high_density_min_shots: int | None = None,
) -> None:
    label = str(segment_id or "segment")
    density_profiles = {"high_density_short", "dialogue_emotional", "suspense_build", "micro_film", "custom"}
    if density_profile not in density_profiles:
        issues.append(issue("error", "segment_density_profile_invalid", f"{label} density_profile 无效。", path))
    if shot_mode not in {"edited", "true_one_take"}:
        issues.append(issue("error", "segment_shot_mode_invalid", f"{label} shot_mode 必须为 edited 或 true_one_take。", path))
        return
    if shot_mode == "true_one_take":
        if shot_count != 1:
            issues.append(issue("error", "true_one_take_shot_count_invalid", f"{label} 标记为 true_one_take 时必须且只能包含 1 个镜头。", path))
        return
    # Shot count is evaluated from visible information/action units, never from
    # an exact SEG duration threshold. Density is a semantic review signal.


def check_keyframe_request_plan(
    segment: dict[str, Any],
    path: Path,
    issues: list[dict[str, Any]],
    max_per_segment: int | None = None,
) -> int:
    segment_id = str(segment.get("segment_id") or "segment")
    requests = segment.get("keyframe_requests")
    if requests is None:
        return 0
    if not isinstance(requests, list):
        issues.append(issue("error", "keyframe_requests_invalid", f"{segment_id} keyframe_requests 必须是数组；未选中本集高光时可省略或填空数组。", path))
        return 0
    count = len(requests)
    if max_per_segment is not None and count > max_per_segment:
        issues.append(issue("error", "keyframe_request_count_invalid", f"{segment_id} 单段 keyframe_requests 最多 {max_per_segment} 张（← params.kf.per_seg_max）；关键帧按集总量规划，不得把普通镜头都升级为 KF。", path))
    roles = segment.get("required_keyframe_roles")
    if count and isinstance(roles, list) and "highlight" not in roles:
        issues.append(issue("error", "keyframe_role_missing", f"{segment_id} 已规划 keyframe_requests 时，required_keyframe_roles 必须包含 highlight。", path))
    if not count and isinstance(roles, list) and "highlight" in roles:
        issues.append(issue("error", "keyframe_role_without_request", f"{segment_id} 标记了 highlight 但没有 keyframe_requests；未选中本集高光时不要登记关键帧职责。", path))
    return count


def check_episode_keyframe_request_plan(
    segments: list[Any],
    lightweight: bool,
    path: Path,
    issues: list[dict[str, Any]],
    kf_range: dict[str, Any] | None = None,
) -> None:
    """KF 数量按 kf-count 公式动态判（kf_range 来自 rhythm_engine.kf_count，常数 ← params.kf）。
    kf_range 为 None（库不可用）时只做结构校验，数量区间检查跳过。"""
    valid_segments = [segment for segment in segments if isinstance(segment, dict)]
    kmin = kf_range.get("min") if kf_range else None
    kmax = kf_range.get("max") if kf_range else None
    per_seg_max = kf_range.get("per_seg_max") if kf_range else None
    if kf_range:
        max_per_segment = kmax if len(valid_segments) == 1 else per_seg_max
    else:
        max_per_segment = None
    total = 0
    for segment in valid_segments:
        total += check_keyframe_request_plan(segment, path, issues, max_per_segment)
    range_label = f"{kmin}-{kmax}" if kf_range else "公式区间（库不可用，未校验）"
    if total == 0:
        if not lightweight:
            issues.append(issue("error", "episode_keyframe_requests_missing", f"完整模式每集必须按集规划 {range_label} 张剧情高光关键帧（kf-count 公式）；不是每个 SEG 都需要，但全集不能为 0。", path))
        return
    if kf_range and (total < kmin or total > kmax):
        issues.append(issue("error", "episode_keyframe_request_count_invalid", f"本集 keyframe_requests 总数为 {total}，按 kf-count 公式必须按集规划 {kmin}-{kmax} 张剧情高光关键帧；不是每个 SEG 都需要关键帧。", path))


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
        if cut_motivation is not None:
            if not isinstance(cut_motivation, str) or not cut_motivation.isascii():
                issues.append(issue("info", "cut_motivation_legacy", f"{shot_id} cut_motivation 是存量自由文本格式，应为枚举 {sorted(CUT_MOTIVATIONS)} 之一；新项目应为 0 条。", path))
            elif cut_motivation not in CUT_MOTIVATIONS:
                issues.append(issue("error", "cut_motivation_invalid", f"{shot_id} cut_motivation 无效，必须是 {sorted(CUT_MOTIVATIONS)} 之一。", path))
        tolerance = shot.get("cut_tolerance_s")
        if tolerance is not None and (not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or tolerance <= 0 or tolerance > 5):
            issues.append(issue("error", "cut_tolerance_invalid", f"{shot_id} cut_tolerance_s 必须是 0-5 秒的正数。", path))


def check_rhythm_diversity(
    data: dict[str, Any],
    shots: list[Any],
    segments: list[Any],
    lightweight: bool,
    path: Path,
    issues: list[dict[str, Any]],
    rhythm: RhythmLibrary | None = None,
) -> None:
    lib = rhythm.library if rhythm is not None else None
    params = lib["params"] if isinstance(lib, dict) else None
    health = params["health"] if isinstance(params, dict) else None
    role_floors = params["role_floors"] if isinstance(params, dict) else None
    grid = params["rounding_grid_s"] if isinstance(params, dict) else None
    beats = lib["beat_types"] if isinstance(lib, dict) else None
    shot_by_id = {
        item.get("shot_id"): item
        for item in shots
        if isinstance(item, dict) and isinstance(item.get("shot_id"), str)
    }

    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_shot_ids = segment.get("shot_ids")
        if not isinstance(segment_shot_ids, list) or len(segment_shot_ids) < 2 or segment.get("shot_mode") == "true_one_take":
            continue
        if has_meaningful_value(segment.get("rhythm_uniform_exempt_reason")):
            continue
        durations = [
            float(shot_by_id[s]["duration_s"])
            for s in segment_shot_ids
            if s in shot_by_id and isinstance(shot_by_id[s].get("duration_s"), (int, float))
        ]
        if len(durations) >= 2 and len(set(durations)) == 1:
            issues.append(issue("warning", "rhythm_uniform_segment", f"{segment.get('segment_id')} 段内全部镜头时长相同；复核 beat 与内容是否匹配；均匀若有剧情依据可保留，不为分布而改时长。", path))
        elif health is not None and len(durations) >= 3 and max(durations) - min(durations) < health["segment_min_range_s"]:
            issues.append(issue("warning", "rhythm_uniform_segment_spirit", f"{segment.get('segment_id')} 段内 {len(durations)} 镜时长极差 {max(durations) - min(durations):.1f}s < {health['segment_min_range_s']:g}s，属 ±{grid:g}s 抖动式均匀变体；仅作分布诊断；若 beat、表演和信息职责成立，保留当前镜长。", path))

    valid_segments = [s for s in segments if isinstance(s, dict) and isinstance(s.get("shot_ids"), list)]
    if len(valid_segments) >= 4:
        runs: list[list[str]] = []
        current_run: list[str] = []
        current_count: int | None = None
        for segment in valid_segments:
            if segment.get("density_profile") == "high_density_short":
                if current_run:
                    runs.append(current_run)
                current_run, current_count = [], None
                continue
            count = len(segment["shot_ids"])
            if count == current_count:
                current_run.append(str(segment.get("segment_id")))
            else:
                if current_run:
                    runs.append(current_run)
                current_run, current_count = [str(segment.get("segment_id"))], count
        if current_run:
            runs.append(current_run)
        for run in runs:
            if len(run) >= 3:
                issues.append(issue("warning", "rhythm_shot_count_default", f"连续 {len(run)} 个 SEG 镜数相同（{'、'.join(run)}），视为段落级节拍器；按 beat 数决定镜数，例外在 beat_coverage 说明。", path))

    all_durations = [
        float(item["duration_s"])
        for item in shots
        if isinstance(item, dict) and isinstance(item.get("duration_s"), (int, float))
    ]
    if not lightweight and health is not None and len(all_durations) >= 4 and max(all_durations) - min(all_durations) < health["flatline_window_s"]:
        issues.append(issue("warning", "rhythm_duration_range_narrow", f"全片镜头时长最大值与最小值之差小于 {health['flatline_window_s']:g} 秒（不足一个时长窗，← params.health.flatline_window_s）；复核是否存在信息/动作节拍差异；不为统计极差增删或改时长。", path))

    if not lightweight and health is not None and beats is not None and len(all_durations) >= 8:
        window = health["flatline_window_s"]
        worst_share, worst_lo = rhythm.engine.flatline_share(all_durations, window, grid)
        if worst_share > health["flatline_max_share"]:
            issues.append(issue("warning", "rhythm_distribution_flatline", f"全片 {worst_share * 100:.0f}% 镜头压在 {worst_lo:g}-{worst_lo + window:g}s 时长窗内（>{health['flatline_max_share'] * 100:.0f}%），分布扁平；仅提示复核 beat 语义；不自动或反复调整已分配镜长。", path))
        beat_set = {item.get("beat_type") for item in shots if isinstance(item, dict)}
        fast_beats_in_use = beat_set & fast_capable_beat_types(beats)
        if fast_beats_in_use and min(all_durations) > health["fast_pole_max_s"]:
            issues.append(issue("warning", "rhythm_fast_pole_missing", f"全片含快节奏节拍（{sorted(fast_beats_in_use)}）但最短镜头 {min(all_durations):g}s > {health['fast_pole_max_s']:g}s，快极缺失；核对对应节拍时长来源；不为满足全片极值阈值压缩镜头。", path))
        total_duration = data.get("duration_s")
        if isinstance(total_duration, (int, float)) and total_duration >= health["slow_pole_min_total_s"] and max(all_durations) < health["slow_pole_min_s"]:
            issues.append(issue("warning", "rhythm_slow_pole_missing", f"全片 {total_duration:g}s 但最长镜头 {max(all_durations):g}s < {health['slow_pole_min_s']:g}s，仅作分布提示；不为满足慢极阈值拉长镜头。", path))

    if not lightweight and shot_by_id and role_floors is not None:
        payoff_ids: list[str] = []
        for binding in data.get("highlight_bindings") or []:
            if isinstance(binding, dict) and isinstance(binding.get("payoff_shot_ids"), list):
                payoff_ids.extend(str(s) for s in binding["payoff_shot_ids"])
        payoff_set = set(payoff_ids)
        ordered_shot_items = [item for item in shots if isinstance(item, dict) and isinstance(item.get("shot_id"), str)]
        peak_ids = list(payoff_ids)
        if ordered_shot_items:
            peak_ids.append(str(ordered_shot_items[-1]["shot_id"]))
        for peak_id in dict.fromkeys(peak_ids):
            floor = role_floors["payoff_s"] if peak_id in payoff_set else role_floors["final_s"]
            role_label = "高光兑现镜" if peak_id in payoff_set else "本集最终镜"
            peak_shot = shot_by_id.get(peak_id)
            peak_duration = peak_shot.get("duration_s") if isinstance(peak_shot, dict) else None
            if isinstance(peak_duration, (int, float)) and not isinstance(peak_duration, bool) and peak_duration < floor:
                issues.append(issue("warning", "rhythm_peak_too_short", f"{peak_id} 是{role_label}，时长 {peak_duration:g}s < 角色下限 {floor:g}s（← params.role_floors）；峰值拍按库长区间赋值，确需短促切断时在 tail_selection_reason 或转换差异台账登记例外。", path))

    if beats is not None and health is not None:
        fast_beats = fast_capable_beat_types(beats)
        for item in shots:
            if not isinstance(item, dict):
                continue
            beat_type = item.get("beat_type")
            duration = item.get("duration_s")
            if beat_type not in beats or not isinstance(duration, (int, float)) or item.get("has_speech") is True:
                continue
            low, high = beats[beat_type]["range_s"]
            if not (low <= float(duration) <= high):
                if beat_type in fast_beats:
                    issues.append(issue("warning", "rhythm_beat_duration_mismatch", f"{item.get('shot_id')} beat_type={beat_type} 的时长 {duration}s 超出基准区间 {low}-{high}s（库默认区间）；快节奏节拍必须快，调整时长或改 beat_type。", path))
                else:
                    issues.append(issue("info", "rhythm_beat_duration_mismatch", f"{item.get('shot_id')} beat_type={beat_type} 的时长 {duration}s 不在基准区间 {low}-{high}s（库默认区间）；调整时长或改 beat_type，仅提示不阻断。", path))

    ordered_shots = [item for item in shots if isinstance(item, dict)]
    run_motivation: str | None = None
    run_length = 0
    for item in ordered_shots[:-1]:
        motivation = item.get("cut_motivation")
        if motivation not in CUT_MOTIVATIONS:
            run_motivation, run_length = None, 0
            continue
        if motivation == run_motivation:
            run_length += 1
        else:
            run_motivation, run_length = motivation, 1
        if run_length == 4:
            issues.append(issue("info", "rhythm_cut_type_repeat", f"连续 4 个以上切点 cut_motivation 同为 {motivation}；按优先级换用动作/视线/声音先导切换。", path))


def check_rhythm_reconciliation(
    episode_id: str,
    episode_root: Path,
    data: dict[str, Any],
    shots: list[Any],
    segments: list[Any],
    lightweight: bool,
    path: Path,
    issues: list[dict[str, Any]],
    rhythm: RhythmLibrary,
) -> None:
    """引擎合同对账 + 节奏检查组。

    铁律：storyboard 的算术字段（duration_s/duration_basis/rhythm_extremes 等）只由
    rhythm_engine 写入；lint 拿同一张 rhythm_input 重算对账，对不上即 engine_drift。
    所有公式调 rhythm_engine，所有阈值读 beat_types.json params 节。
    """
    engine = rhythm.engine
    lib = rhythm.library
    params = lib["params"]
    health = params["health"]
    drift_level = "info" if rhythm.placeholder else "error"
    stale_level = "info" if rhythm.placeholder else "warning"

    shot_items = [
        item
        for item in shots
        if isinstance(item, dict) and isinstance(item.get("shot_id"), str)
    ]
    duration_of = {
        item["shot_id"]: float(item["duration_s"])
        for item in shot_items
        if isinstance(item.get("duration_s"), (int, float)) and not isinstance(item.get("duration_s"), bool)
    }

    basis_by_shot: dict[str, str] = {}
    missing_basis: list[str] = []
    for item in shot_items:
        basis = item.get("duration_basis")
        if isinstance(basis, str) and basis.strip():
            basis_by_shot[item["shot_id"]] = basis.strip()
        else:
            missing_basis.append(item["shot_id"])
    if missing_basis and not lightweight:
        issues.append(issue("error", "duration_basis_missing", f"{len(missing_basis)} 个镜头缺 duration_basis（时长发票为引擎必填算术字段）：{missing_basis[:5]}{' 等' if len(missing_basis) > 5 else ''}", path))
    for shot_id, basis in basis_by_shot.items():
        duration = duration_of.get(shot_id)
        if duration is None:
            continue
        summed = duration_basis_sum(basis)
        if summed is None or abs(summed - duration) > DURATION_BASIS_SUM_TOLERANCE_S:
            issues.append(issue("warning", "duration_basis_sum_mismatch", f"{shot_id} duration_basis 各分项加总（{'无法解析' if summed is None else f'{summed:g}s'}）与 duration_s {duration:g}s 偏差超过 {DURATION_BASIS_SUM_TOLERANCE_S:g}s：{basis}", path))
    clone_groups: dict[str, list[str]] = {}
    for shot_id, basis in basis_by_shot.items():
        clone_groups.setdefault(basis, []).append(shot_id)
    for basis, holders in clone_groups.items():
        if len(holders) >= DURATION_BASIS_CLONE_MIN_SHOTS:
            issues.append(issue("warning", "duration_basis_clone", f"{len(holders)} 个镜头 duration_basis 完全雷同（{holders[:5]}{' 等' if len(holders) > 5 else ''}）：{basis}；发票应逐镜构成，不得抄模板。", path))

    rhythm_input_path = episode_root / f"02_分镜/rhythm_input_{episode_id}.json"
    inp = load_json(rhythm_input_path, issues, required=False)
    inp_shots: dict[str, dict[str, Any]] = {}
    inp_scenes: list[dict[str, Any]] = []
    incomplete: list[str] = []
    inp_struct_valid = True
    if isinstance(inp, dict) and not isinstance(inp.get("scenes"), list):
        inp_struct_valid = False
        issues.append(issue("error", "rhythm_input_incomplete", "rhythm_input 缺少 scenes 数组（顶层结构不符）；语义输入表必须按 scenes[].shots[] 嵌套填写（schema 见 manifests.md「rhythm_input_ep_N.json」节），镜头写在顶层会被引擎按空表静默处理。", rhythm_input_path))
    if isinstance(inp, dict):
        for scene in inp.get("scenes") or []:
            if not isinstance(scene, dict):
                continue
            inp_scenes.append(scene)
            for entry in scene.get("shots") or []:
                if not isinstance(entry, dict) or not isinstance(entry.get("shot_id"), str):
                    continue
                inp_shots[entry["shot_id"]] = entry
                if not entry.get("beat_type") or entry.get("intensity") is None:
                    incomplete.append(entry["shot_id"])
        if incomplete:
            issues.append(issue("error", "rhythm_input_incomplete", f"rhythm_input 有 {len(incomplete)} 个镜头缺 beat_type 或 intensity，引擎无法重算：{incomplete[:5]}{' 等' if len(incomplete) > 5 else ''}", rhythm_input_path))

    # 估时 vs 引擎真实时长偏离检查（storyboard.md 冲突协议的机制化）：
    # storyboard.duration_s 是引擎写回的真实总长；rhythm_input.total_duration_s 是
    # 规划估时转录。用户未锁定时长（unbounded）却把内容削进估时时,本检查抓偏离——
    # 偏差超容差且没有处置说明(误差说明字段 duration_drift_note)即报 warning。
    sb_total = data.get("duration_s")
    estimate_s = inp.get("total_duration_s") if isinstance(inp, dict) else None
    if (
        isinstance(sb_total, (int, float))
        and isinstance(estimate_s, (int, float))
        and estimate_s > 0
    ):
        drift = float(sb_total) - float(estimate_s)
        tolerance = max(0.5, float(estimate_s) * 0.10)
        note_present = has_meaningful_value(data.get("duration_drift_note"))
        if abs(drift) > tolerance and not note_present:
            issues.append(issue(
                "warning",
                "storyboard_duration_vs_estimate_drift",
                f"引擎真实总长 {float(sb_total):g}s 与规划估时 {float(estimate_s):g}s 偏差 {drift:+g}s（超容差 {tolerance:g}s）。"
                "估时不是合同（rhythm_input.total_duration_s 是规划预测转录）：duration_contract=unbounded 时以引擎值为准并在 storyboard 登记一句 duration_drift_note 说明（如『估时 60s→实际 75s，内容需要』）；"
                "用户锁定时长（target_band/exact）才走「估时 vs 引擎真实时长冲突协议」的有据压缩或用户裁决。未登记说明的偏离视作把估时当合同硬压的信号。",
                path,
            ))
    elif not lightweight and duration_of:
        issues.append(issue("error", "rhythm_input_missing", f"storyboard 含引擎算术字段（duration_s 等）但缺少 02_分镜/rhythm_input_{episode_id}.json；节奏语义输入表是重算对账的唯一依据，删除输入表不能绕过对账。", path))

    if isinstance(inp, dict) and not incomplete and not lightweight and inp_struct_valid:
        current_hash = engine.engine_output_hash(inp, lib)
        declared_hash = data.get("engine_output_hash")
        by_id: dict[str, Any] | None = None
        balance_note = ""
        try:
            segment_map = {}
            for segment in segments:
                if not isinstance(segment, dict):
                    continue
                for sid in segment.get("shot_ids") or []:
                    segment_map[sid] = (segment.get("segment_id"), segment.get("duration_s"))
            records, _notes = engine.compute_shot_durations(inp, lib, segment_map)
            by_id = {record["shot_id"]: record for record in records}
        except Exception as exc:
            issues.append(issue(drift_level, "engine_drift", f"引擎重算异常，无法完成对账：{exc}", path))
            by_id = None
        if by_id is not None:
            mismatches: list[str] = []
            for shot_id, duration in duration_of.items():
                record = by_id.get(shot_id)
                if record is None:
                    mismatches.append(f"{shot_id}(rhythm_input 缺该镜)")
                else:
                    recomputed = round(record["d"], 2)
                    if abs(recomputed - duration) > 1e-9:
                        mismatches.append(f"{shot_id}(storyboard {duration:g}s≠重算 {recomputed:g}s)")
            for shot_id in sorted(set(by_id) - set(duration_of)):
                mismatches.append(f"{shot_id}(storyboard 缺该镜)")
            if mismatches:
                issues.append(issue(drift_level, "engine_drift", f"{len(mismatches)} 处与引擎重算不符{balance_note}（算术字段只允许引擎写入；改语义后必须重跑 rhythm_engine）：{'; '.join(mismatches[:5])}{' …' if len(mismatches) > 5 else ''}", path))
            elif not (isinstance(declared_hash, str) and declared_hash == current_hash):
                input_library_version = inp.get("beat_library_version")
                if isinstance(input_library_version, int) and input_library_version != lib.get("version"):
                    message = f"rhythm_input 登记 beat_library_version={input_library_version}，当前库 version={lib.get('version')}；逐项重算与 storyboard 一致（仅库版本变化），请重跑 rhythm_engine 刷新 engine_output_hash。"
                else:
                    message = "engine_output_hash 与当前输入表/库不一致，但逐项重算与 storyboard 一致（库或引擎版本已变化）；请重跑 rhythm_engine 刷新 engine_output_hash。"
                issues.append(issue(stale_level, "beat_library_stale", message, path))

    if not lightweight and isinstance(inp, dict) and inp_struct_valid and rhythm.h3 is not None:
        declared_division = [
            [str(sid) for sid in segment.get("shot_ids") or []]
            for segment in segments
            if isinstance(segment, dict) and isinstance(segment.get("shot_ids"), list)
        ]
        pack_shots = [
            {"shot_id": item["shot_id"], "duration_s": duration_of[item["shot_id"]]}
            for item in shot_items
            if item["shot_id"] in duration_of
        ]
        declared_ids = [sid for division in declared_division for sid in division]
        if declared_division and len(pack_shots) == len(shot_items) and set(declared_ids) == {s["shot_id"] for s in pack_shots}:
            pack_candidates: set[str] = set()
            pack_beat_groups: list = []
            for scene in inp_scenes:
                pack_candidates.update(str(c) for c in scene.get("boundary_candidates") or [])
                pack_beat_groups.extend(g for g in scene.get("beat_groups") or [] if isinstance(g, dict))
            h3_caps = rhythm.h3["capabilities"]
            try:
                recomputed_division, _pack_notes, _pack_at_cap = engine.compute_pack(
                    pack_shots, candidates=pack_candidates,
                    cap=h3_caps["max_duration_s"], seg_min=h3_caps["min_duration_s"],
                    beat_groups=pack_beat_groups or None,
                )
            except ValueError as exc:
                issues.append(issue(drift_level, "pack_no_valid_cut", str(exc), path))
                recomputed_division = []
            recomputed_ids = [seg["shot_ids"] for seg in recomputed_division]
            if recomputed_ids != declared_division:
                first_diff = next(
                    (i for i, pair in enumerate(zip(recomputed_ids, declared_division)) if pair[0] != pair[1]),
                    min(len(recomputed_ids), len(declared_division)),
                )
                issues.append(issue(drift_level, "pack_drift", f"SEG 划分与引擎 pack 重算不一致（声明 {len(declared_division)} 段 / 重算 {len(recomputed_ids)} 段，首个差异在第 {first_diff + 1} 段）；段划分只由 pack --write 写入，改镜时长或 beat_groups 后必须重跑 pack。", path))

    if inp_shots:
        speech_params = params["speech"]
        for item in shot_items:
            shot_id = item["shot_id"]
            entry = inp_shots.get(shot_id)
            spoken = str((entry or {}).get("spoken_text") or "").strip()
            if item.get("has_speech") is True and not spoken:
                issues.append(issue("warning", "spoken_text_missing", f"{shot_id} has_speech=true 但 rhythm_input 无 spoken_text；有台词镜必须登记台词文本。", path))
            if not spoken:
                continue
            duration = duration_of.get(shot_id)
            if duration is None:
                continue
            pace = str((entry or {}).get("speech_pace") or "normal")
            _floor, n_chars, rate = engine.speech_floor(spoken, pace, params)
            if not n_chars:
                continue
            reading_s = n_chars / float(rate)
            needed = reading_s + speech_params["min_overhead_s"]
            if needed > duration + 1e-9:
                issues.append(issue("warning", "speech_overrun", f"{shot_id} 台词 {n_chars} 字按 {rate:g} 字/s（{pace}）需 {needed:.2f}s（含 min_overhead {speech_params['min_overhead_s']:g}s）> 镜时长 {duration:g}s；这句台词在本镜读不完。", path))
            elif reading_s <= duration * SPEECH_UNDERFILL_MAX_SHARE:
                issues.append(issue("info", "speech_underfill", f"{shot_id} 台词仅 {n_chars} 字（约 {reading_s:.1f}s），占镜时长 {duration:g}s 不足 {SPEECH_UNDERFILL_MAX_SHARE:.0%}，明显空转；确认画面是否有持续信息注入，否则收紧时长。", path))

    extremes_count = engine.EXTREMES_COUNT
    ordered = sorted(
        (item for item in shot_items if item["shot_id"] in duration_of),
        key=lambda item: duration_of[item["shot_id"]],
    )
    extremes = data.get("rhythm_extremes")
    if extremes is None:
        if not lightweight and duration_of:
            issues.append(issue("warning", "rhythm_extremes_missing", f"storyboard 缺顶层 rhythm_extremes（fastest/slowest 各 {extremes_count} 镜，由引擎写入）。", path))
    elif isinstance(extremes, dict) and len(ordered) >= extremes_count:
        actual_fastest = {item["shot_id"] for item in ordered[:extremes_count]}
        actual_slowest = {item["shot_id"] for item in ordered[-extremes_count:]}
        declared_fastest = {entry.get("shot_id") for entry in extremes.get("fastest") or [] if isinstance(entry, dict)}
        declared_slowest = {entry.get("shot_id") for entry in extremes.get("slowest") or [] if isinstance(entry, dict)}
        if declared_fastest != actual_fastest or declared_slowest != actual_slowest:
            issues.append(issue("warning", "rhythm_extremes_mismatch", f"rhythm_extremes 申报与实际极值不符：实际最快 {[item['shot_id'] for item in ordered[:extremes_count]]}、最慢 {[item['shot_id'] for item in reversed(ordered[-extremes_count:])]}；极值由引擎计算，禁止手填。", path))

    for scene in inp_scenes:
        card = scene.get("rhythm_card")
        if not isinstance(card, dict):
            continue
        scene_durations = [
            (entry["shot_id"], duration_of[entry["shot_id"]])
            for entry in scene.get("shots") or []
            if isinstance(entry, dict) and entry.get("shot_id") in duration_of
        ]
        if len(scene_durations) < extremes_count:
            continue
        ordered_scene = sorted(scene_durations, key=lambda pair: pair[1])
        scene_fastest = {sid for sid, _ in ordered_scene[:extremes_count]}
        scene_slowest = {sid for sid, _ in ordered_scene[-extremes_count:]}
        offending: list[str] = []
        declared_fast = card.get("fastest_beat")
        declared_slow = card.get("slowest_beat")
        if isinstance(declared_fast, str) and declared_fast and declared_fast not in scene_fastest:
            offending.append(f"fastest_beat={declared_fast}")
        if isinstance(declared_slow, str) and declared_slow and declared_slow not in scene_slowest:
            offending.append(f"slowest_beat={declared_slow}")
        if offending:
            issues.append(issue("warning", "rhythm_card_extremes_mismatch", f"{scene.get('scene_id')} rhythm_card 声明的 {'、'.join(offending)} 未落在本场实际最快/最慢 {extremes_count} 镜内（实际最快 {[sid for sid, _ in ordered_scene[:extremes_count]]}、最慢 {[sid for sid, _ in ordered_scene[-extremes_count:]]}）。", path))

    beat_counts: dict[str, int] = {}
    for item in shot_items:
        beat = item.get("beat_type")
        if isinstance(beat, str) and beat:
            beat_counts[beat] = beat_counts.get(beat, 0) + 1
    total_beats = sum(beat_counts.values())
    if total_beats:
        top_beat, top_count = max(beat_counts.items(), key=lambda pair: pair[1])
        if top_count / total_beats > health["beat_monoculture_max_share"]:
            issues.append(issue("warning", "beat_monoculture", f"beat_type={top_beat} 占比 {top_count}/{total_beats}（{top_count / total_beats:.0%}）超过 {health['beat_monoculture_max_share']:.0%}；节拍单一，检查是否标打偷懒或节奏单调。", path))

    if rhythm.h3 is not None:
        cap = rhythm.h3["capabilities"]["max_duration_s"]
        segment_durations = [
            float(segment["duration_s"])
            for segment in segments
            if isinstance(segment, dict) and isinstance(segment.get("duration_s"), (int, float))
        ]
        if len(segment_durations) >= health["cap_uniformity_min_segments"]:
            at_cap = sum(1 for d in segment_durations if abs(d - cap) < 1e-9)
            if at_cap / len(segment_durations) >= health["cap_uniformity_share"]:
                issues.append(issue("info", "segment_cap_uniformity", f"{at_cap}/{len(segment_durations)} 个 SEG 正好顶满模型上限 {cap:g}s（≥{health['cap_uniformity_share']:.0%}）；疑似先切段再填内容，装箱应按真实时长，顶满需可解释。", path))

    overrides = data.get("beat_duration_overrides")
    if isinstance(overrides, dict) and overrides:
        style = data.get("style_profile")
        if not isinstance(style, str) or not style:
            style = inp.get("style_profile") if isinstance(inp, dict) else None
        if not isinstance(style, str) or not style:
            style = None
        effective = engine.effective_ranges(lib, None, style)
        for beat, rng in overrides.items():
            if beat not in effective or not isinstance(rng, (list, tuple)) or len(rng) != 2:
                continue
            eff_low, eff_high = effective[beat]
            if float(rng[1]) - float(rng[0]) > (eff_high - eff_low) + 1e-9:
                issues.append(issue("warning", "beat_override_unconstrained", f"beat_duration_overrides.{beat}=[{rng[0]}, {rng[1]}] 比生效区间（{f'风格 {style}' if style else '库默认'} [{eff_low:g}, {eff_high:g}]）更宽；本集校准应比生效区间更严，更宽等于没校准。", path))


def check_cut_tolerance(segments: list[Any], shots: list[Any], path: Path, issues: list[dict[str, Any]]) -> None:
    shot_by_id = {
        item.get("shot_id"): item
        for item in shots
        if isinstance(item, dict) and isinstance(item.get("shot_id"), str)
    }
    for segment in segments:
        if not isinstance(segment, dict) or not isinstance(segment.get("shot_ids"), list):
            continue
        for shot_id in segment["shot_ids"][:-1]:
            shot = shot_by_id.get(shot_id)
            if not isinstance(shot, dict):
                continue
            tolerance = shot.get("cut_tolerance_s")
            if tolerance is None:
                issues.append(issue("info", "cut_tolerance_missing", f"{shot_id} 缺 cut_tolerance_s（默认 1.0；duration_s < 2.5 秒的镜默认 0.5）；存量项目宽容，新项目应为 0 条。", path))
            else:
                duration = shot.get("duration_s")
                if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration < 2.5 and isinstance(tolerance, (int, float)) and tolerance > 0.5:
                    issues.append(issue("info", "cut_tolerance_short_shot_default", f"{shot_id} duration_s < 2.5 秒，cut_tolerance_s 应收紧为 0.5（短镜两侧切点相向漂移会吞掉镜长）。", path))


STATIC_CAMERA_MAX_SHARE = 0.40


def check_static_camera_share(
    shots: list[Any],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    """Stop storyboard progression when fixed-camera shots exceed 40% per episode."""
    valid_shots = [shot for shot in shots if isinstance(shot, dict)]
    if not valid_shots:
        return
    missing = [str(shot.get("shot_id") or f"shots[{index}]") for index, shot in enumerate(shots) if isinstance(shot, dict) and not has_meaningful_value(shot.get("camera_family"))]
    if missing:
        issues.append(issue(
            "error",
            "camera_family_missing",
            f"每镜必须登记 camera_family 才能执行固定机位熔断；缺失 {len(missing)} 镜：{missing[:12]}{' 等' if len(missing) > 12 else ''}。",
            path,
        ))
        return
    static_ids = [str(shot.get("shot_id") or f"shots[{index}]") for index, shot in enumerate(shots) if isinstance(shot, dict) and str(shot.get("camera_family", "")).strip().lower() in {"static", "locked_off", "locked-off", "fixed", "fixed_camera", "fixed-camera"}]
    total = len(valid_shots)
    if static_ids and len(static_ids) / total > STATIC_CAMERA_MAX_SHARE:
        share = len(static_ids) / total * 100
        issues.append(issue(
            "error",
            "static_camera_share_exceeded",
            f"固定机位为 {len(static_ids)}/{total} 镜（{share:.1f}%），超过单集 40% 熔断线；退回分镜重新设计观看方式后再进入关键帧/视频阶段。超限镜头：{static_ids[:20]}{' 等' if len(static_ids) > 20 else ''}。",
            path,
        ))


def check_storyboards(
    root: Path,
    expected_durations: dict[str, int],
    plan: Any,
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
    asset_index: dict[str, Any] | None = None,
    rhythm: RhythmLibrary | None = None,
) -> None:
    if asset_index is None:
        asset_index = blank_asset_index()
    lightweight = is_lightweight_plan(plan) and lightweight_constraints_valid(plan)
    h3_segment_cap_s: float | None = None
    high_density_min_shots: int | None = None
    valid_beat_types: set[str] | None = None
    if rhythm is not None:
        if rhythm.h3 is not None:
            h3_segment_cap_s = rhythm.h3["capabilities"]["max_duration_s"]
        if rhythm.library is not None:
            high_density_min_shots = rhythm.params["high_density"]["min_shots"]
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
            issues.append(issue("error", "director_control_card_invalid", f"storyboard.director_control_card 必须指向 {expected_director_card}。", path))
        elif not file_exists(root, expected_director_card):
            issues.append(issue("error", "director_control_card_missing", "分镜阶段必须存在唯一导演总控卡。", path))
        expected_source_markdown = f"episodes/{episode_id}/02_分镜/分镜_完整分镜表_{episode_id}.md"
        source_markdown = relative_file(root, data.get("source_markdown"))
        if data.get("source_markdown") != expected_source_markdown:
            issues.append(issue("error", "storyboard_source_markdown_invalid", f"storyboard.source_markdown 必须指向 {expected_source_markdown}。", path))
        elif source_markdown is None or not source_markdown.is_file():
            issues.append(issue("error", "storyboard_source_markdown_missing", "十五列完整分镜表文件不存在。", path))
        else:
            try:
                table_text = source_markdown.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                issues.append(issue("error", "storyboard_source_markdown_unreadable", f"十五列完整分镜表无法读取：{exc}", source_markdown))
            else:
                if 15 not in markdown_table_column_counts(table_text):
                    issues.append(issue("error", "storyboard_fifteen_columns_missing", "完整分镜表必须包含一个十五列表格。", source_markdown))
        # scale_plan episode durations are allocation estimates; only internal shot/segment sums are exact.
        shots = data.get("shots")
        segments = data.get("segments")
        if not isinstance(shots, list) or not isinstance(segments, list):
            issues.append(issue("error", "storyboard_shape_invalid", "storyboard 必须包含 shots 和 segments 数组。", path))
            continue
        check_static_camera_share(shots, path, issues)
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
            if int(round(float(data["duration_s"]))) != int(round(sum(float(v) for v in shot_durations.values()))):
                issues.append(issue("error", "shot_duration_total_mismatch", "shots.duration_s 之和必须等于 storyboard.duration_s。", path))
        covered: list[str] = []
        lightweight = is_lightweight_plan(plan) and lightweight_constraints_valid(plan)
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
            if isinstance(segment.get("duration_s"), (int, float)):
                declared = int(round(float(segment["duration_s"])))
                calculated = int(round(sum(float(shot_durations[s]) for s in segment_shots if s in shot_durations)))
                if calculated and declared != calculated:
                    issues.append(issue("error", "segment_duration_mismatch", f"{segment_id} duration_s 必须等于其 shot_ids 时长之和。", path))
                check_segment_shot_count(
                    segment_id,
                    declared,
                    len(segment_shots),
                    segment.get("shot_mode"),
                    segment.get("density_profile"),
                    path,
                    issues,
                    high_density_cap_s=h3_segment_cap_s,
                    high_density_min_shots=high_density_min_shots,
                )
            tail_mode = segment.get("tail_mode")
            if tail_mode not in {"continuous_motion", "cuttable_completion", "stable_hold", "loop_continuation"}:
                issues.append(issue("error", "segment_tail_mode_invalid", f"{segment_id or index} tail_mode 无效。", path))
            if index < len(segments) and tail_mode == "stable_hold" and not has_meaningful_value(segment.get("tail_hold_reason")):
                issues.append(issue("error", "intermediate_stable_hold_reason_missing", f"{segment_id or index} 是中间片段，使用 stable_hold 时必须填写 tail_hold_reason。", path))
            check_reference_plan(segment, path, issues)
        kf_range = None
        if rhythm is not None and rhythm.library is not None and isinstance(data.get("duration_s"), (int, float)):
            kf_range = rhythm.engine.kf_count(float(data["duration_s"]), None, rhythm.params)
        check_episode_keyframe_request_plan(segments, lightweight, path, issues, kf_range)
        check_asset_usage_reconciliation(data, asset_index, path, issues)
        check_world_facts(data, path, issues)
        check_beat_coverage(data, shot_ids, path, issues)
        check_shot_rhythm_fields(shots, path, issues, valid_beat_types)
        check_rhythm_diversity(data, shots, segments, lightweight, path, issues, rhythm)
        check_cut_tolerance(segments, shots, path, issues)
        if rhythm is not None and rhythm.library is not None:
            check_rhythm_reconciliation(episode_id, episode_root, data, shots, segments, lightweight, path, issues, rhythm)
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
            issues.append(issue("error", "audience_execution_missing", "storyboard 必须登记从已确认 audience_plan 派生的 audience_execution。", path))
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
        script_contract = load_json(script_path, issues, required=not lightweight)
        highlight_ledger = script_contract.get("highlight_ledger") if isinstance(script_contract, dict) else []
        if isinstance(script_contract, dict) and not isinstance(highlight_ledger, list):
            issues.append(issue("error", "highlight_ledger_invalid", "script_contract.highlight_ledger 必须是数组。", script_path))
            highlight_ledger = []
        if not lightweight and isinstance(highlight_ledger, list):
            primary_entries = [
                item
                for item in highlight_ledger
                if isinstance(item, dict) and item.get("role") == "primary" and str(item.get("highlight_id") or "").strip()
            ]
            if not primary_entries:
                issues.append(issue("error", "primary_highlight_missing", "完整模式每集 script_contract.highlight_ledger 必须至少包含一个有效的 primary 亮点。", script_path))
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
            issues.append(issue("error", "highlight_bindings_missing", "storyboard.highlight_bindings 必须是数组并覆盖剧本主要亮点。", path))
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
        check_causal_ledger(
            root,
            data,
            episode_id,
            shots,
            shot_ids,
            shot_positions,
            shot_to_segment,
            [item.get("segment_id") for item in segments if isinstance(item, dict) and isinstance(item.get("segment_id"), str)],
            binding_ids,
            path,
            issues,
        )


def check_reference_plan(
    segment: dict[str, Any],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    refs = segment.get("reference_input_plan")
    if refs is None:
        issues.append(issue("error", "reference_input_plan_missing", "每个 SEG 必须填写 reference_input_plan。", path))
        return
    if not isinstance(refs, list):
        issues.append(issue("error", "reference_input_plan_invalid", "reference_input_plan 必须是数组。", path))
        return
    orders: list[int] = []
    for index, ref in enumerate(refs, start=1):
        if not isinstance(ref, dict):
            issues.append(issue("error", "reference_input_plan_invalid", f"第 {index} 条参考计划必须是对象。", path))
            continue
        order = ref.get("order")
        role = ref.get("role")
        if isinstance(order, int) and not isinstance(order, bool):
            orders.append(order)
            binding = str(ref.get("opening_binding", "") or "")
            if not re.search(marker_pattern("image", order), binding, flags=re.I):
                issues.append(issue("error", "opening_binding_marker_missing", f"第 {order} 张参考图缺少对应 <图片{order}>/<IMG{order}> 标记。", path))
        else:
            issues.append(issue("error", "reference_order_invalid", "参考图 order 必须是整数。", path))
        if role not in REFERENCE_ROLES:
            issues.append(issue("error", "reference_role_invalid", f"参考图职责无效：{role}", path))
        for field in ("planned_source", "opening_binding", "adopt", "exclude"):
            if not str(ref.get(field, "") or "").strip():
                issues.append(issue("error", "reference_input_plan_incomplete", f"参考图计划缺少 {field}。", path))
    if orders and sorted(orders) != list(range(1, len(orders) + 1)):
        issues.append(issue("error", "reference_order_not_contiguous", "参考图 order 必须从 1 连续递增。", path))


ASSET_ID_PATTERN = re.compile(r"^((?:CHR|SCN|PROP|STYLE)\d+)(?:[_:]v?(\d+))?")

ASSET_ROLE_COMPATIBILITY = {
    "CHR": {"identity_reference", "character_state_reference", "previous_character_state_reference"},
    "SCN": {"scene_layout", "previous_scene_anchor_reference"},
    "PROP": {"prop_structure", "prop_state_reference", "previous_prop_state_reference"},
    "STYLE": {"style_reference"},
}


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
    方向2：输入计划使用了台账未登记的绑定时给 warning（临时增补必须回头登记）。
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
        issues.append(issue("error", "asset_usage_plan_missing", "storyboard 必须登记 asset_usage_plan（资产需求清单的结构化同源数据）。", path))
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
                issues.append(issue("warning", "asset_version_inconsistent", f"{segment_id} 计划传入 {asset_id} {planned_by_segment[segment_id][asset_id]}，与台账登记版本 {registered_versions[asset_id]} 不一致。", path))
    for segment_id, planned in planned_by_segment.items():
        for asset_id in planned:
            if (asset_id, segment_id) not in seen_pairs:
                issues.append(issue("warning", "asset_planned_but_unregistered", f"{segment_id} 计划传入 {asset_id}，但 asset_usage_plan 未登记该绑定；临时增补必须回头登记。", path))


WORLD_FACT_CATEGORIES = {"season", "festival", "date", "time_of_day", "weather", "location_fact", "other"}


def check_world_facts(data: dict[str, Any], path: Path, issues: list[dict[str, Any]]) -> None:
    """inherited_world_facts 的结构检查：强制世界事实被显式登记并注明剧本出处。

    语义矛盾（如霜气 vs 中元节）不属于 lint 职责，由剧本-分镜对照审校步骤处理；
    本检查的意义是让审校有对照表可查。
    """
    facts = data.get("inherited_world_facts")
    if not isinstance(facts, list) or not facts:
        issues.append(issue("error", "world_facts_missing", "storyboard 必须登记 inherited_world_facts：从剧本继承的季节/节日/时辰/天气等世界事实。", path))
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


BEAT_DISPOSITIONS = {"kept", "compressed", "moved", "dropped"}


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
    if not isinstance(beats, list) or not beats:
        issues.append(issue("error", "beat_coverage_missing", "storyboard 必须登记 beat_coverage：剧本每条动作/事件的去向台账。", path))
        return
    check_unique(beats, "beat_id", path, issues, "beat_coverage")
    for index, beat in enumerate(beats, start=1):
        if not isinstance(beat, dict):
            issues.append(issue("error", "beat_invalid", f"第 {index} 条 beat 必须是对象。", path))
            continue
        label = beat.get("beat_id") or f"第 {index} 条"
        disposition = beat.get("disposition")
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


CAUSAL_ROLES = {"establish", "evidence", "reaction", "result", "transition"}
CAUSAL_REF_TYPES = {"beat", "shot", "asset_state", "world_fact"}
EVIDENCE_VISIBILITIES = {"in_frame", "partial", "occluded", "audio_only"}
BREAKPOINT_RISKS = {"C1", "C2", "C3", "C4", "C5"}


def storyboard_schema_version(data: dict[str, Any]) -> tuple[int, int]:
    """storyboard schema_version 门控：1.0 为因果字段前的存量版本，跳过 causal 检查。"""
    match = re.match(r"^(\d+)(?:\.(\d+))?", str(data.get("schema_version") or "1.0").strip())
    if not match:
        return (1, 0)
    return (int(match.group(1)), int(match.group(2) or 0))


def collect_data_card_state_ids(root: Path, issues: list[dict[str, Any]]) -> set[str]:
    """asset_state 引用解析表：project_data_card 各主体 state_timeline 的 state_id 集合。"""
    card = load_json(root / "00_制作控制/project_data_card.json", issues, required=False)
    state_ids: set[str] = set()
    if isinstance(card, dict):
        for group in ("characters", "scenes", "props"):
            for item in card.get(group) or []:
                if not isinstance(item, dict):
                    continue
                for state in item.get("state_timeline") or []:
                    if isinstance(state, dict) and str(state.get("state_id") or "").strip():
                        state_ids.add(str(state["state_id"]).strip())
    return state_ids


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


def validate_causal_ref(
    ref: Any,
    owner: str,
    tables: dict[str, set[str]],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    """responds_to/trigger_source 的引用闭合：ref_type 枚举 + ref_id 按各自表查存在性。

    空表守卫：被引表整体缺失时存在性已由对应专项检查报错，此处跳过避免连锁误报。
    """
    if not isinstance(ref, dict):
        issues.append(issue("error", "causal_ref_invalid", f"{owner} 的引用必须是含 ref_type/ref_id 的对象。", path))
        return
    ref_type = ref.get("ref_type")
    if ref_type not in CAUSAL_REF_TYPES:
        issues.append(issue("error", "causal_ref_type_invalid", f"{owner} 的 ref_type 无效：{ref_type}（枚举 {sorted(CAUSAL_REF_TYPES)}）。", path))
        return
    ref_id = str(ref.get("ref_id") or "").strip()
    if not ref_id:
        issues.append(issue("error", "causal_ref_id_missing", f"{owner} 缺少 ref_id。", path))
        return
    table = tables.get(ref_type) or set()
    if table and ref_id not in table:
        issues.append(issue("error", "causal_ref_unknown", f"{owner} 引用了不存在的 {ref_type}：{ref_id}。", path))


def read_text_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def seam_invariant_cell(text: str, seam_id: str) -> str | None:
    """从连续性账本中提取某 SEAM 的 required_invariants 记录。

    优先按 Markdown 表格解析（表头含「必须保持/required_invariants」列，行含 seam_id）；
    否则在 seam_id 所在行起的短窗口内找 required_invariants 字样。返回 None 表示找不到记录。
    """
    lines = text.splitlines()
    header_index: int | None = None
    for line in lines:
        if "|" in line and ("必须保持" in line or "required_invariants" in line):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            for index, cell in enumerate(cells):
                if "必须保持" in cell or "required_invariants" in cell:
                    header_index = index
                    break
            if header_index is not None:
                break
    for line_no, line in enumerate(lines):
        if seam_id not in line:
            continue
        if header_index is not None and "|" in line:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if header_index < len(cells):
                return cells[header_index]
        window = lines[line_no : line_no + 8]
        for follow in window:
            if "required_invariants" in follow or "必须保持" in follow:
                return follow.strip()
        return ""
    return None


def check_causal_ledger(
    root: Path,
    data: dict[str, Any],
    episode_id: str,
    shots: list[Any],
    shot_ids: set[str],
    shot_positions: dict[str, int],
    shot_to_segment: dict[str, Any],
    segment_order: list[str],
    highlight_binding_ids: set[str],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    """causal_ledger 与单镜因果字段的结构检查（schema_version 1.1 起）。

    只查客观项：引用闭合、shots[] 数组序时序、交叉反查必填、枚举合法。
    visibility_contract 措辞质量、遮挡是否真的看不见、反应是否合理等语义判断
    属于剧本-分镜对照审校（SKILL.md 分镜硬门五项编号清单第⑤项），不在此设卡。
    """
    if storyboard_schema_version(data) < (1, 1):
        return
    beat_ids = {
        item.get("beat_id")
        for item in data.get("beat_coverage") or []
        if isinstance(item, dict) and isinstance(item.get("beat_id"), str)
    }
    fact_ids = {
        item.get("fact_id")
        for item in data.get("inherited_world_facts") or []
        if isinstance(item, dict) and isinstance(item.get("fact_id"), str)
    }
    ref_tables = {
        "beat": beat_ids,
        "shot": shot_ids,
        "asset_state": collect_data_card_state_ids(root, issues),
        "world_fact": fact_ids,
    }
    shots_by_id = {
        item.get("shot_id"): item
        for item in shots
        if isinstance(item, dict) and isinstance(item.get("shot_id"), str)
    }
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        shot_id = str(shot.get("shot_id") or "未命名镜头")
        role = shot.get("causal_role")
        if not isinstance(role, str) or not role.strip():
            issues.append(issue("error", "causal_role_missing", f"{shot_id} 缺少 causal_role（每镜必填，枚举 {sorted(CAUSAL_ROLES)}）。", path))
        elif role not in CAUSAL_ROLES:
            issues.append(issue("warning", "causal_role_invalid", f"{shot_id} causal_role={role} 不在枚举 {sorted(CAUSAL_ROLES)} 内。", path))
        responds_to = shot.get("responds_to")
        if role in {"reaction", "result"} and not isinstance(responds_to, dict):
            issues.append(issue("error", "causal_responds_to_missing", f"{shot_id} causal_role={role} 必须填写 responds_to。", path))
        if isinstance(responds_to, dict):
            validate_causal_ref(responds_to, f"{shot_id}.responds_to", ref_tables, path, issues)
            if not str(responds_to.get("trigger_fact") or "").strip():
                issues.append(issue("warning", "causal_trigger_fact_missing", f"{shot_id}.responds_to 缺少 trigger_fact（该镜回应的已建立事实）。", path))
        visibility = shot.get("evidence_visibility")
        if visibility is not None and visibility not in EVIDENCE_VISIBILITIES:
            issues.append(issue("error", "evidence_visibility_invalid", f"{shot_id} evidence_visibility 无效：{visibility}（枚举 {sorted(EVIDENCE_VISIBILITIES)}）。", path))
        if visibility == "occluded" and not str(shot.get("establishes") or "").strip():
            issues.append(issue("warning", "occluded_establishes_missing", f"{shot_id} evidence_visibility=occluded 时必须在 establishes 写明遮挡理由与揭示点。", path))

    ledger = data.get("causal_ledger")
    if not isinstance(ledger, list):
        issues.append(issue("error", "causal_ledger_missing", "storyboard 必须登记 causal_ledger 数组（无反应/证据依赖链的集登记空数组）。", path))
        ledger = []
    chain_ids = check_unique(ledger, "chain_id", path, issues, "causal_ledger")
    members: dict[str, set[str]] = {"evidence": set(), "reaction": set(), "result": set()}
    crossing_chains: list[tuple[str, set[str], set[str]]] = []
    for chain in ledger:
        if not isinstance(chain, dict):
            issues.append(issue("error", "causal_chain_invalid", "causal_ledger 每条必须是对象。", path))
            continue
        chain_id = str(chain.get("chain_id") or "未命名链")
        if not str(chain.get("trigger_fact") or "").strip():
            issues.append(issue("error", "causal_chain_trigger_fact_missing", f"{chain_id} 缺少 trigger_fact。", path))
        if not str(chain.get("visibility_contract") or "").strip():
            issues.append(issue("error", "causal_chain_visibility_contract_missing", f"{chain_id} 缺少 visibility_contract（证据在哪些镜头以什么程度必须可见/可听）。", path))
        trigger_source = chain.get("trigger_source")
        if not isinstance(trigger_source, dict):
            issues.append(issue("error", "causal_chain_trigger_source_missing", f"{chain_id} 缺少 trigger_source（ref_type/ref_id）。", path))
        else:
            validate_causal_ref(trigger_source, f"{chain_id}.trigger_source", ref_tables, path, issues)
        risk = chain.get("breakpoint_risk")
        if risk is not None and risk not in BREAKPOINT_RISKS:
            issues.append(issue("warning", "causal_chain_breakpoint_risk_invalid", f"{chain_id} breakpoint_risk={risk} 不在 C1-C5 内。", path))
        binding_ref = chain.get("highlight_binding_ref")
        if binding_ref not in (None, "") and binding_ref not in highlight_binding_ids:
            issues.append(issue("error", "causal_chain_highlight_binding_ref_unknown", f"{chain_id} 的 highlight_binding_ref 指向不存在的亮点绑定：{binding_ref}。", path))
        positions: dict[str, list[int]] = {}
        shot_fields = (("evidence_shot_ids", "evidence"), ("reaction_shot_ids", "reaction"), ("result_shot_ids", "result"))
        for field, key in shot_fields:
            refs = chain.get(field)
            if refs is None:
                refs = []
            if not isinstance(refs, list) or not all(isinstance(ref, str) and ref.strip() for ref in refs):
                issues.append(issue("error", "causal_chain_shots_invalid", f"{chain_id}.{field} 必须是 shot_id 字符串数组。", path))
                refs = [ref for ref in refs if isinstance(ref, str)] if isinstance(refs, list) else []
            unknown = sorted(set(refs) - shot_ids)
            if unknown:
                issues.append(issue("error", "causal_chain_shot_unknown", f"{chain_id}.{field} 引用了不存在的本集镜头：{unknown}；跨集镜头登记 cross_episode_refs，不进本集数组。", path))
            valid = [ref for ref in refs if ref in shot_positions]
            positions[key] = [shot_positions[ref] for ref in valid]
            members[key].update(valid)
        cross_refs = chain.get("cross_episode_refs")
        if cross_refs is not None:
            if not isinstance(cross_refs, list):
                issues.append(issue("error", "causal_chain_cross_episode_refs_invalid", f"{chain_id}.cross_episode_refs 必须是数组。", path))
                cross_refs = []
            for entry in cross_refs:
                if not isinstance(entry, dict) or not re.fullmatch(r"ep_[1-9]\d*", str(entry.get("episode_id") or "")) or not str(entry.get("note") or "").strip():
                    issues.append(issue("error", "causal_chain_cross_episode_ref_invalid", f"{chain_id}.cross_episode_refs 每项必须含 episode_id（ep_N）与 note。", path))
                    continue
                target_episode = str(entry["episode_id"])
                target_storyboard = load_json(root / f"episodes/{target_episode}/02_分镜/storyboard_{target_episode}.json", issues, required=False)
                if isinstance(target_storyboard, dict) and storyboard_schema_version(target_storyboard) >= (1, 1):
                    target_ledger = target_storyboard.get("causal_ledger")
                    closed = isinstance(target_ledger, list) and any(
                        isinstance(target_chain, dict)
                        and any(
                            isinstance(back, dict) and back.get("episode_id") == episode_id
                            for back in (target_chain.get("cross_episode_refs") or [])
                        )
                        for target_chain in target_ledger
                    )
                    if not closed:
                        issues.append(issue("error", "causal_chain_cross_episode_not_closed", f"{chain_id} 引用 {target_episode}，但目标集 causal_ledger 没有回指 {episode_id} 的链。", path))
        if not any(positions.values()) and not cross_refs:
            issues.append(issue("warning", "causal_chain_empty", f"{chain_id} 未引用任何本集镜头，也没有跨集引用（空链）。", path))
        evidence_pos = positions.get("evidence") or []
        reaction_pos = positions.get("reaction") or []
        result_pos = positions.get("result") or []
        if evidence_pos and reaction_pos and min(reaction_pos) < min(evidence_pos):
            issues.append(issue("error", "causal_chain_reaction_before_evidence", f"{chain_id} 的反应镜头早于证据镜头（按 shots[] 数组序）。", path))
        if reaction_pos and result_pos and min(result_pos) < max(reaction_pos):
            issues.append(issue("error", "causal_chain_result_before_reaction", f"{chain_id} 的结果镜头早于反应镜头（按 shots[] 数组序）。", path))
        evidence_segments = {
            shot_to_segment.get(ref)
            for ref in (chain.get("evidence_shot_ids") or [])
            if isinstance(ref, str) and shot_to_segment.get(ref)
        }
        reaction_segments = {
            shot_to_segment.get(ref)
            for ref in (chain.get("reaction_shot_ids") or [])
            if isinstance(ref, str) and shot_to_segment.get(ref)
        }
        crossing_chains.append((chain_id, evidence_segments, reaction_segments))

    for shot_id in sorted(members["evidence"]):
        shot = shots_by_id.get(shot_id) or {}
        if not str(shot.get("establishes") or "").strip():
            issues.append(issue("error", "causal_evidence_establishes_missing", f"{shot_id} 被因果链列为证据位，必须填写 establishes。", path))
        if shot.get("evidence_visibility") not in EVIDENCE_VISIBILITIES:
            issues.append(issue("error", "causal_evidence_visibility_missing", f"{shot_id} 被因果链列为证据位，必须填写 evidence_visibility（枚举 {sorted(EVIDENCE_VISIBILITIES)}）。", path))
    for shot_id in sorted(members["reaction"] | members["result"]):
        shot = shots_by_id.get(shot_id) or {}
        if not isinstance(shot.get("responds_to"), dict):
            issues.append(issue("error", "causal_reaction_responds_to_missing", f"{shot_id} 被因果链列为反应/结果位，必须填写 responds_to。", path))

    seams = data.get("seams") or []
    seam_by_pair = {
        (seam.get("from_segment"), seam.get("to_segment")): seam.get("seam_id")
        for seam in seams
        if isinstance(seam, dict)
    }
    segment_index = {segment_id: index for index, segment_id in enumerate(segment_order)}
    ledger_text: str | None = None
    ledger_path = root / f"episodes/{episode_id}/02_分镜/分镜_连续性账本_{episode_id}.md"
    for chain_id, evidence_segments, reaction_segments in crossing_chains:
        if not evidence_segments or not reaction_segments:
            continue
        evidence_max = max(segment_index.get(seg, -1) for seg in evidence_segments)
        reaction_min = min(segment_index.get(seg, len(segment_order)) for seg in reaction_segments)
        if evidence_max >= reaction_min:
            continue
        if ledger_text is None:
            ledger_text = read_text_file(ledger_path)
        for cut in range(evidence_max, reaction_min):
            pair = (segment_order[cut], segment_order[cut + 1])
            seam_id = seam_by_pair.get(pair)
            if not seam_id:
                continue
            if ledger_text is None:
                issues.append(issue("warning", "causal_seam_invariant_unknown", f"{chain_id} 的证据跨 {pair[0]}->{pair[1]} 传递给反应位，但找不到连续性账本，无法核对 {seam_id}.required_invariants 派生。", ledger_path))
                break
            cell = seam_invariant_cell(ledger_text, str(seam_id))
            if cell is None or cell.strip() in {"", "无", "—", "-", "/"}:
                issues.append(issue("warning", "causal_seam_invariant_missing", f"{chain_id} 的证据跨 {pair[0]}->{pair[1]} 传递给反应位，{seam_id}.required_invariants 必须派生写入该链 visibility_contract 条款。", path))

    card_text = read_text_file(root / f"episodes/{episode_id}/02_分镜/导演总控卡_{episode_id}.md")
    if card_text:
        for ref_id in sorted(set(re.findall(r"causal_chain_ref[^A-Za-z0-9]{0,6}([A-Za-z]{1,8}\d+)", card_text))):
            if ref_id not in chain_ids:
                issues.append(issue("warning", "causal_chain_ref_unknown", f"导演总控卡台词证据链引用了不存在的链：{ref_id}。", path))


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
                    expected_prefix = ASSET_PREFIX_BY_CATEGORY.get(str(category))
                    if expected_prefix and not asset_id.startswith(expected_prefix):
                        issues.append(issue("error", "asset_id_prefix_mismatch", f"{asset_id} 与 category={category} 的前缀不一致。", registry_path))
                else:
                    issues.append(issue("error", "asset_id_missing", "资产缺少 asset_id。", registry_path))
                status = asset.get("status")
                if status is not None and status not in ASSET_STATUS_VALUES:
                    issues.append(issue("error", "asset_status_invalid", f"资产状态无效：{status}", registry_path))
                state_id = str(asset.get("state_id") or "")
                if isinstance(asset_id, str) and asset_id.strip() and state_id:
                    remember_state_version(index, asset_id, state_id, version, status)
                for file_value in asset.get("files") or []:
                    if not file_exists(root, file_value):
                        issues.append(issue("error", "asset_file_missing", f"资产文件不存在：{file_value}", registry_path))
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
                if category == "style" and asset_id == "STYLE001":
                    style_asset_type = asset.get("style_asset_type") or generation.get("style_asset_type")
                    if status == "approved" and style_asset_type is None:
                        issues.append(issue("error", "style_asset_type_missing", "STYLE001 approved 前必须登记 style_asset_type=global_visual_language_moodboard。", registry_path))
                    if style_asset_type is not None and style_asset_type != "global_visual_language_moodboard":
                        issues.append(issue("error", "style_asset_type_invalid", "STYLE001 必须登记为 global_visual_language_moodboard。", registry_path))
                    scene_links = asset.get("style_scene_atmosphere_links") or generation.get("style_scene_atmosphere_links")
                    if status == "approved" and (not isinstance(scene_links, list) or not any(str(item).strip() for item in scene_links)):
                        issues.append(issue("error", "style_scene_atmosphere_links_missing", "STYLE001 approved 时 style_scene_atmosphere_links 必须是非空数组。", registry_path))
                    visual_language = asset.get("style_visual_language") or generation.get("style_visual_language")
                    if status == "approved":
                        if not isinstance(visual_language, dict):
                            issues.append(issue("error", "style_visual_language_missing", "STYLE001 必须登记色彩、光线、构图、材质或空间氛围等视觉语言。", registry_path))
                        else:
                            filled = [
                                key
                                for key, value in visual_language.items()
                                if isinstance(value, list) and any(str(item).strip() for item in value)
                            ]
                            if len(filled) < 2:
                                issues.append(issue("error", "style_visual_language_too_sparse", "STYLE001 视觉语言至少填写两类：palette/lighting/composition/materials/space_atmosphere/texture_or_grain。", registry_path))
                    if asset.get("contains_story_characters") is not False and generation.get("contains_story_characters") is not False:
                        issues.append(issue("error", "style_moodboard_contains_characters_unknown", "STYLE001 全局风格 moodboard 必须明确 contains_story_characters=false。", registry_path))
                    if asset.get("contains_story_props") is not False and generation.get("contains_story_props") is not False:
                        issues.append(issue("error", "style_moodboard_contains_props_unknown", "STYLE001 全局风格 moodboard 必须明确 contains_story_props=false。", registry_path))
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
                if asset_id and source_valid:
                    remember_asset_version(index, asset_id, version, "approved" if status == "approved" else status)
                if asset_id and state_id and source_valid:
                    remember_state_version(index, asset_id, state_id, version, status)
                key = (source_episode_id, asset_id, state_id, version)
                if key in seen_reused:
                    issues.append(issue("error", "reused_episode_asset_duplicate", f"{episode_id} 复用分集资产重复：{source_episode_id} {asset_id} {state_id} {version}", path))
                seen_reused.add(key)
                for file_value in item.get("files") or []:
                    if not file_exists(root, file_value):
                        issues.append(issue("error", "reused_episode_asset_file_missing", f"复用分集资产文件不存在：{file_value}", path))
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
                generation = item.get("generation") if isinstance(item.get("generation"), dict) else {}
                tool = generation.get("tool")
                refs = [*item.get("reference_asset_ids", [])] if isinstance(item.get("reference_asset_ids"), list) else []
                available_visual_refs = []
                for field_owner in (item, generation):
                    value = field_owner.get("available_visual_reference_ids") if isinstance(field_owner, dict) else None
                    if isinstance(value, list):
                        available_visual_refs.extend(ref for ref in value if isinstance(ref, str) and ref.strip())
                visual_reference_decision = item.get("visual_reference_decision") or generation.get("visual_reference_decision")
                if visual_reference_decision is not None and visual_reference_decision not in VISUAL_REFERENCE_DECISIONS:
                    issues.append(issue("error", "episode_visual_reference_decision_invalid", f"{asset_id or '分集资产'} visual_reference_decision 无效：{visual_reference_decision}", path))
                visual_inputs = []
                for field in ("reference_inputs", "input_files", "input_images"):
                    value = generation.get(field)
                    if isinstance(value, list):
                        visual_inputs.extend(value)
                style_anchor_refs = combined_strings(item, generation, field="style_anchor_reference_ids")
                style_terms = combined_strings(item, generation, field="style_prompt_terms")
                project_visual_mode = item.get("project_visual_mode") or generation.get("project_visual_mode")
                category = item.get("category")
                if category in {"character", "scene", "prop", "style"} and item.get("status") == "approved":
                    if project_visual_mode not in PROJECT_VISUAL_MODES:
                        issues.append(issue("error", "episode_project_visual_mode_missing_or_invalid", f"{asset_id or '分集资产'} approved 图片资产必须登记有效 project_visual_mode。", path))
                if tool == "image_gen" and (refs or visual_inputs or style_anchor_refs):
                    issues.append(issue("error", "episode_image_gen_should_not_have_visual_inputs", f"{asset_id or '分集资产'} 使用 image_gen 时不应登记图片参考输入。", path))
                if tool == "image_gen" and available_visual_refs and visual_reference_decision != "explicit_user_override":
                    issues.append(issue("error", "episode_image_gen_visual_reference_available", f"{asset_id or '分集资产'} 已登记可用视觉参考，必须使用 image_edit；除非用户明确要求不参考并记录 explicit_user_override。", path))
                if tool == "image_gen" and visual_reference_decision == "used":
                    issues.append(issue("error", "episode_image_gen_visual_reference_decision_conflict", f"{asset_id or '分集资产'} visual_reference_decision=used 时不能使用 image_gen。", path))
                if tool == "image_edit" and not (refs or visual_inputs or style_anchor_refs):
                    issues.append(issue("error", "episode_image_edit_reference_missing", f"{asset_id or '分集资产'} 使用 image_edit 时必须登记实际参考来源。", path))
                if tool == "image_edit" and visual_reference_decision == "none_available":
                    issues.append(issue("error", "episode_image_edit_visual_reference_decision_conflict", f"{asset_id or '分集资产'} 使用 image_edit 时 visual_reference_decision 不能写 none_available。", path))
                state_id = str(item.get("state_id") or "")
                if category == "character" and state_id and tool == "image_gen" and visual_reference_decision != "explicit_user_override":
                    issues.append(issue("error", "episode_character_state_asset_requires_image_edit", f"{asset_id or '角色状态资产'} 是人物状态资产时必须基于已批准人物图使用 image_edit；除非用户明确要求重做并记录 explicit_user_override。", path))
                check_generation_prompt_file(root, path, str(asset_id or "分集资产"), tool, generation.get("prompt_path"), issues)
                for file_value in item.get("files") or []:
                    if not file_exists(root, file_value):
                        issues.append(issue("error", "episode_asset_file_missing", f"分集资产文件不存在：{file_value}", path))
    return index


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
        if file_value and not file_exists(root, file_value):
            issues.append(issue("error", f"{kind}_input_file_missing", f"输入文件不存在或不是项目相对路径：{file_value}", path))
        if kind == "reference" and isinstance(file_value, str) and Path(file_value).suffix.lower() not in IMAGE_INPUT_SUFFIXES:
            issues.append(issue("error", "reference_input_file_suffix_invalid", f"reference_inputs.file 必须是图片文件：{file_value}", path))
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
    return {item.get("keyframe_id") for item in keyframes if isinstance(item, dict) and isinstance(item.get("keyframe_id"), str)}


def marker_pattern(kind: str, order: int) -> str:
    patterns = {
        "image": rf"<(?:图片\s*{order}(?:\s*-\s*第\s*\d+\s*格)?|IMG\s*{order}(?:\s*-\s*Cell\s*\d+)?)\s*>",
        "video": rf"<(?:视频|VID)\s*{order}\s*>",
        "audio": rf"<(?:音频|AUD)\s*{order}\s*>",
    }
    return patterns[kind]


def extract_marker_orders(text: str, kind: str) -> list[int]:
    if kind == "image":
        pattern = r"<(?:图片\s*(\d+)(?:\s*-\s*第\s*\d+\s*格)?|IMG\s*(\d+)(?:\s*-\s*Cell\s*\d+)?)\s*>"
        orders: list[int] = []
        for cn_order, en_order in re.findall(pattern, text, flags=re.I):
            orders.append(int(cn_order or en_order))
        return orders
    patterns = {
        "video": r"<(?:视频|VID)\s*(\d+)\s*>",
        "audio": r"<(?:音频|AUD)\s*(\d+)\s*>",
    }
    return [int(match) for match in re.findall(patterns[kind], text, flags=re.I)]


def extract_subject_marker_orders(text: str) -> set[int]:
    orders: set[int] = set()
    pattern = r"<(?:主体\s*(\d+)|SUBJ\s*(\d+))\s*>"
    for cn_order, en_order in re.findall(pattern, text, flags=re.I):
        orders.add(int(cn_order or en_order))
    return orders


def h3_marker_pattern(kind: str, order: int) -> str:
    """h3-prompt-writing 的英文参考标签：<Picture N>/<Video N>/<Audio N>。"""
    patterns = {
        "image": rf"<\s*Picture\s*{order}\s*>",
        "video": rf"<\s*Video\s*{order}\s*>",
        "audio": rf"<\s*Audio\s*{order}\s*>",
    }
    return patterns[kind]


def extract_h3_marker_orders(text: str, kind: str) -> list[int]:
    pattern = {"image": r"<\s*Picture\s*(\d+)\s*>", "video": r"<\s*Video\s*(\d+)\s*>", "audio": r"<\s*Audio\s*(\d+)\s*>"}[kind]
    return [int(match) for match in re.findall(pattern, text, flags=re.I)]


def check_prompt_markers(
    prompt_path: Path,
    image_orders: list[int],
    video_orders: list[int],
    audio_orders: list[int],
    speech_lines: Any,
    subtitle_enabled: bool,
    require_five_sections: bool,  # 保留参数兼容调用方；五段式为组装规则不再检查
    issues: list[dict[str, Any]],
) -> None:
    """校验提交给模型的 Prompt 成稿携带了全部已登记输入与台词。

    格式中立：成稿由 h3-prompt-writing skill 生成并优化，其段数、参考标签写法
    （<Picture 1> 等）与台词块写法以该 skill 为准，本函数不检查格式本身；
    只做存在性核对——每个已登记输入在成稿中有对应序号标记、每条 spoken_text
    逐字存在、素材标记语言不混用、【】字幕源规则。
    五段式是交付包的组装规则（组装已内化为编译步骤），不再检查段数。"""
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
        # 标记格式中立：接受中文 <图片N>/<IMG N> 与 h3 skill 的 <Picture N>/<Video N>/<Audio N>。
        actual = sorted(set(extract_marker_orders(text, kind)) | set(extract_h3_marker_orders(text, kind)))
        if actual != expected:
            issues.append(issue("error", f"prompt_{kind}_markers_mismatch", f"Prompt 中{label}标记 {actual} 必须与实际输入 order {expected} 一致（写法以 h3-prompt-writing 为准）。", prompt_path))
        for order in expected:
            if re.search(marker_pattern(kind, order), text, flags=re.I) is None \
                    and re.search(h3_marker_pattern(kind, order), text, flags=re.I) is None:
                issues.append(issue("error", f"prompt_{kind}_marker_missing", f"Prompt 缺少第 {order} 个{label}标记。", prompt_path))
    cn = re.search(r"<(?:图片\s*\d+(?:\s*-\s*第\s*\d+\s*格)?|视频\s*\d+|音频\s*\d+|主体\s*\d+)\s*>", text)
    en = re.search(r"<(?:IMG\s*\d+(?:\s*-\s*Cell\s*\d+)?|VID\s*\d+|AUD\s*\d+|SUBJ\s*\d+)\s*>", text, flags=re.I)
    if cn and en:
        issues.append(issue("error", "prompt_marker_language_mixed", "同一 Prompt 不要混用中文和英文多媒体标记。", prompt_path))
    for order in sorted(extract_subject_marker_orders(text)):
        cn_labeled = rf"<\s*主体\s*{order}\s*>\s*[（(][^（）()\n]+[）)]"
        en_labeled = rf"<\s*SUBJ\s*{order}\s*>\s*[（(][^（）()\n]+[）)]"
        if not re.search(cn_labeled, text) and not re.search(en_labeled, text, flags=re.I):
            issues.append(issue("error", "prompt_subject_marker_label_missing", f"Prompt 使用 <主体{order}>/<SUBJ{order}> 时，必须至少一次写成 <主体{order}>(名称) 或 <SUBJ{order}>(name) 绑定主体身份。", prompt_path))
    if ("【" in text or "】" in text) and not subtitle_enabled:
        issues.append(issue("error", "prompt_subtitle_bracket_invalid", "未启用字幕时，最终视频 Prompt 不允许出现【】字幕源标识。", prompt_path))
    expected_speech: set[str] = set()
    if isinstance(speech_lines, list):
        for index, line in enumerate(speech_lines, start=1):
            if not isinstance(line, dict):
                issues.append(issue("error", "speech_line_invalid", f"speech_lines 第 {index} 条必须是对象。", prompt_path))
                continue
            spoken = str(line.get("spoken_text") or "").strip()
            if not spoken:
                issues.append(issue("error", "speech_line_spoken_text_missing", f"speech_lines 第 {index} 条缺少 spoken_text。", prompt_path))
                continue
            expected_speech.add(spoken)
            if spoken not in text:
                issues.append(issue("error", "prompt_speech_line_missing", f"Prompt 缺少当前 SEG 台词原文：{spoken}", prompt_path))
    prompt_braces = {match.strip() for match in re.findall(r"\{([^{}\n]+)\}", text) if match.strip()}
    if expected_speech:
        extras = sorted(prompt_braces - expected_speech)
        if extras:
            issues.append(issue("error", "prompt_speech_line_extra", f"Prompt 中 {{}} 只能包裹当前 SEG 的 spoken_text，发现额外内容：{extras[:5]}", prompt_path))


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


def media_duration_s(item: dict[str, Any]) -> float | None:
    for field in ("duration_s", "uploaded_duration_s", "input_duration_s", "trimmed_duration_s", "source_duration_s"):
        value = item.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def check_media_input_durations(segment: dict[str, Any], model_name: str, path: Path, issues: list[dict[str, Any]]) -> None:
    video_limit, audio_limit = media_to_video_limits(model_name)
    audio_inputs = segment.get("audio_inputs") or []
    video_inputs = segment.get("video_inputs") or []
    is_seedance20 = "seedance 2.0" in model_name.lower()
    if is_seedance20:
        if isinstance(video_inputs, list) and len(video_inputs) > 3:
            issues.append(issue("error", "seedance20_video_input_count_over_limit", f"{segment.get('segment_id') or 'segment'} 使用 seedance 2.0 时最多登记 3 个视频参考。", path))
        if isinstance(audio_inputs, list) and len(audio_inputs) > 3:
            issues.append(issue("error", "seedance20_audio_input_count_over_limit", f"{segment.get('segment_id') or 'segment'} 使用 seedance 2.0 时最多登记 3 个音频参考。", path))
    audio_total = 0.0
    audio_seen = False
    for item in audio_inputs:
        if not isinstance(item, dict):
            continue
        duration = media_duration_s(item)
        if duration is not None:
            audio_seen = True
            audio_total += duration
            if is_seedance20 and duration < 2:
                issues.append(issue("error", "seedance20_audio_input_too_short", f"{segment.get('segment_id') or 'segment'} 使用 seedance 2.0 时每个音频参考必须不少于 2 秒。", path))
    if audio_seen and audio_total > audio_limit:
        issues.append(issue("error", "audio_inputs_duration_over_limit", f"{segment.get('segment_id') or 'segment'} 上传音频合计 {audio_total:g} 秒，当前 media_to_video 模型上限为 {audio_limit} 秒。", path))
    video_total = 0.0
    video_seen = False
    for item in video_inputs:
        if not isinstance(item, dict):
            continue
        duration = media_duration_s(item)
        if duration is not None:
            video_seen = True
            video_total += duration
            if is_seedance20 and duration < 2:
                issues.append(issue("error", "seedance20_video_input_too_short", f"{segment.get('segment_id') or 'segment'} 使用 seedance 2.0 时每个视频参考必须不少于 2 秒。", path))
            if video_limit == DEFAULT_MEDIA_VIDEO_TOTAL_LIMIT_S and duration > DEFAULT_MEDIA_VIDEO_TOTAL_LIMIT_S:
                issues.append(issue("error", "video_input_duration_over_limit", f"{segment.get('segment_id') or 'segment'} 上传视频参考 {duration:g} 秒，默认 media_to_video 单条视频参考上限为 {DEFAULT_MEDIA_VIDEO_TOTAL_LIMIT_S} 秒；先裁剪 1-2 秒作为上传副本。", path))
    if video_seen and video_total > video_limit:
        issues.append(issue("error", "video_inputs_duration_over_limit", f"{segment.get('segment_id') or 'segment'} 上传视频参考总时长 {video_total:g} 秒，当前 media_to_video 模型上限为 {video_limit} 秒。", path))


def check_video_state_refs(segment: dict[str, Any], image_roles: set[str], asset_index: dict[str, Any], path: Path, issues: list[dict[str, Any]]) -> None:
    if not (image_roles & STATE_REFERENCE_ROLES):
        return
    state_refs = segment.get("state_refs")
    if not isinstance(state_refs, list) or not state_refs:
        issues.append(issue("error", "video_state_refs_missing", f"{segment.get('segment_id') or 'segment'} 传入角色/道具状态参考图时必须登记 approved state_refs。", path))
        return
    for ref in state_refs:
        check_state_ref(ref, asset_index, path, issues, str(segment.get("segment_id") or "视频片段"))


def generated_segment_indexes(segments: list[Any]) -> list[int]:
    indexes: list[int] = []
    for fallback_index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict):
            continue
        has_output = bool(str(segment.get("output_file") or "").strip())
        status = segment.get("status")
        if not has_output and status not in {"candidate", "accepted"}:
            continue
        index = segment.get("episode_segment_index")
        if isinstance(index, int) and not isinstance(index, bool):
            indexes.append(index)
        else:
            indexes.append(fallback_index)
    return sorted(set(indexes))


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


def _check_h3_prompt_purity(prompt_path: Path, segment_id: str, issues: list[dict[str, Any]]) -> None:
    """成稿纯净性：提交给模型的 H3 成稿只含 H3 正文字段。

    实测事故：交付包与成稿混写一个文件后按分隔符切分，分隔符在头部说明行
    又出现一次，split()[1] 取到说明行之后——五段包整段漏进提交 prompt。
    成稿出现交付包段标/分隔符/说明行即视为混装，阻断。
    """
    try:
        text = prompt_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return
    stripped = text.lstrip()
    if not stripped.startswith(("subject_definitions:", "integrated_multimodal_description:", "summary:", "retention_analysis:", "detailed_description:")):
        issues.append(issue(
            "error", "h3_prompt_impure_start",
            f"{segment_id or '视频片段'} H3 成稿必须以 H3 正文字段起头（subject_definitions:/integrated_multimodal_description: 等）；当前开头不是 H3 字段，疑似交付包/说明内容混入。",
            prompt_path,
        ))
    for marker, label in (
        ("===== H3 FINAL PROMPT =====", "分隔符"),
        ("**①", "五段包段标①"),
        ("**②", "五段包段标②"),
        ("起复制", "切分说明行"),
    ):
        if marker in text:
            issues.append(issue(
                "error", "h3_prompt_impure_content",
                f"{segment_id or '视频片段'} H3 成稿含交付包残留（{label}）：成稿只允许 H3 正文字段，交付包内容留在 交付包_SEGxxx_vNN 文件。",
                prompt_path,
            ))
            break


def check_video_generation_confirmations(
    data: dict[str, Any],
    segments: list[Any],
    path: Path,
    issues: list[dict[str, Any]],
    lightweight: bool = False,
) -> None:
    generated = generated_segment_indexes(segments)
    segments_by_index: dict[int, dict[str, Any]] = {}
    declared_indexes: list[int] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        index_value = segment.get("episode_segment_index")
        if not isinstance(index_value, int) or isinstance(index_value, bool) or index_value < 1:
            issues.append(issue("error", "episode_segment_index_invalid", "每个视频片段必须填写从 1 开始的正整数 episode_segment_index。", path))
            continue
        if index_value in segments_by_index:
            issues.append(issue("error", "episode_segment_index_duplicate", f"episode_segment_index 重复：{index_value}", path))
            continue
        declared_indexes.append(index_value)
        segments_by_index[index_value] = segment
    if sorted(declared_indexes) != list(range(1, len(segments_by_index) + 1)):
        issues.append(issue("error", "episode_segment_index_not_contiguous", "episode_segment_index 必须唯一并按 1..N 连续编号。", path))
    confirmations = data.get("generation_confirmations")
    if not generated and not confirmations:
        return
    if not isinstance(confirmations, list):
        issues.append(issue("error", "video_generation_confirmations_missing", "视频阶段每轮生成都必须记录用户参数确认；每轮最多 2 个视频。", path))
        return
    if lightweight and confirmations and (
        not isinstance(confirmations[0], dict)
        or confirmations[0].get("confirmation_source") != "planning_preview"
    ):
        issues.append(issue("error", "lightweight_planning_confirmation_missing", "轻量模式首次生成确认必须来源于规划参数与五列预览。", path))
    confirmed_ranges: list[tuple[int, int]] = []
    confirmation_items: list[tuple[int, int, dict[str, Any], datetime | None]] = []
    previous_confirmations: list[tuple[int, int, str, datetime | None, int | None]] = []
    confirmation_ids: set[str] = set()
    for item in confirmations:
        if not isinstance(item, dict):
            issues.append(issue("error", "video_generation_confirmation_invalid", "generation_confirmations 每项必须是对象。", path))
            continue
        start = item.get("batch_start_segment_index")
        end = item.get("batch_end_segment_index")
        planned_count = item.get("planned_video_count")
        attempt = item.get("attempt")
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            issues.append(issue("error", "video_generation_confirmation_attempt_invalid", "generation_confirmations.attempt 必须是从 1 开始的正整数。", path))
        confirmation_id = str(item.get("confirmation_id") or "").strip()
        if confirmation_id in confirmation_ids:
            issues.append(issue("error", "video_generation_confirmation_id_duplicate", f"generation_confirmations.confirmation_id 重复：{confirmation_id}", path))
        elif confirmation_id:
            confirmation_ids.add(confirmation_id)
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
            issues.append(issue("error", "video_generation_confirmation_range_invalid", "generation_confirmations 必须填写整数 batch_start_segment_index 和 batch_end_segment_index。", path))
            continue
        covered_count = end - start + 1
        if start < 1 or covered_count < 1 or covered_count > 2:
            issues.append(issue("error", "video_generation_confirmation_too_large", "一次用户确认只能覆盖连续的 1-2 个视频，且索引必须从 1 开始。", path))
            continue
        if start not in segments_by_index or end not in segments_by_index:
            issues.append(issue("error", "video_generation_confirmation_unknown_segment", "视频生成参数确认范围必须对应 video_manifest 中真实存在的连续 SEG。", path))
            continue
        confirmed_ranges.append((start, end))
        confirmed_at = parse_iso_time(item.get("confirmed_at"))
        confirmation_items.append((start, end, item, confirmed_at))
        supersedes = item.get("supersedes_confirmation_ids", [])
        if not isinstance(supersedes, list) or not all(isinstance(value, str) and value.strip() for value in supersedes):
            issues.append(issue("error", "video_generation_supersedes_invalid", "supersedes_confirmation_ids 必须是确认 ID 字符串数组。", path))
            supersedes = []
        overlapping_prior = [
            prior
            for prior in previous_confirmations
            if prior[0] <= end and start <= prior[1]
        ]
        overlapping_ids = {prior[2] for prior in overlapping_prior if prior[2]}
        if overlapping_ids and not overlapping_ids.issubset(set(supersedes)):
            issues.append(issue("error", "video_generation_confirmation_overlap", "重生或返修覆盖既有 SEG 时，必须通过 supersedes_confirmation_ids 显式替代所有重叠的旧确认。", path))
        unknown_supersedes = sorted(set(supersedes) - {prior[2] for prior in previous_confirmations})
        if unknown_supersedes:
            issues.append(issue("error", "video_generation_supersedes_unknown", f"supersedes_confirmation_ids 引用了不存在或尚未发生的确认：{unknown_supersedes}", path))
        unrelated_supersedes = sorted(set(supersedes) - overlapping_ids)
        if unrelated_supersedes:
            issues.append(issue("error", "video_generation_supersedes_unrelated", f"supersedes_confirmation_ids 只能列出与本次范围重叠的旧确认：{unrelated_supersedes}", path))
        for prior in overlapping_prior:
            if prior[2] in supersedes and confirmed_at is not None and prior[3] is not None and confirmed_at <= prior[3]:
                issues.append(issue("error", "video_generation_supersedes_time_invalid", "替代确认的 confirmed_at 必须晚于被替代确认。", path))
        if overlapping_prior and isinstance(attempt, int) and not isinstance(attempt, bool):
            prior_attempts = [prior[4] for prior in overlapping_prior if isinstance(prior[4], int)]
            if prior_attempts and attempt <= max(prior_attempts):
                issues.append(issue("error", "video_generation_confirmation_attempt_not_incremented", "返修或重生确认的 attempt 必须高于其覆盖的旧确认。", path))
        elif not overlapping_prior and attempt != 1:
            issues.append(issue("error", "video_generation_confirmation_initial_attempt_invalid", "首次覆盖一组 SEG 的确认 attempt 必须为 1。", path))
        previous_confirmations.append((start, end, confirmation_id, confirmed_at, attempt if isinstance(attempt, int) else None))
        if not isinstance(planned_count, int) or isinstance(planned_count, bool) or planned_count < 1 or planned_count > 2:
            issues.append(issue("error", "video_generation_count_invalid", "planned_video_count 必须是 1 或 2。", path))
        elif planned_count != covered_count:
            issues.append(issue("error", "video_generation_count_mismatch", "planned_video_count 必须等于本轮确认覆盖的 SEG 数。", path))
        for field in (
            "confirmation_id",
            "model",
            "aspect_ratio",
            "duration_s",
            "planned_video_count",
            "creative_direction",
            "final_parameters_text",
            "interaction_ask_call_id",
            "interaction_ask_result",
            "user_message",
            "confirmed_at",
        ):
            if not str(item.get(field) or "").strip():
                issues.append(issue("error", "video_generation_confirmation_field_missing", f"视频生成参数确认缺少 {field}。", path))
        planning_preview_confirmation = lightweight and item.get("confirmation_source") == "planning_preview"
        if planning_preview_confirmation and (start != 1 or end != 1 or planned_count != 1):
            issues.append(issue("error", "lightweight_generation_scope_invalid", "轻量模式规划确认只能授权唯一一个视频。", path))
        expected_segments = [segments_by_index.get(index) for index in range(start, end + 1)]
        if any(segment is None for segment in expected_segments):
            issues.append(issue("error", "video_generation_confirmation_unknown_segment", "视频生成参数确认范围必须对应 video_manifest 中真实存在的连续 SEG。", path))
            expected_segments = []
        segment_durations = item.get("segment_durations")
        if not isinstance(segment_durations, list) or len(segment_durations) != covered_count:
            issues.append(issue("error", "video_generation_segment_durations_invalid", "segment_durations 必须逐 SEG 记录，项数等于本批次数量。", path))
        elif expected_segments:
            for offset, (duration_item, segment) in enumerate(zip(segment_durations, expected_segments), start=start):
                if not isinstance(duration_item, dict):
                    issues.append(issue("error", "video_generation_segment_duration_invalid", f"本批第 {offset} 个 segment_durations 必须是对象。", path))
                    continue
                expected_id = str(segment.get("segment_id") or "")
                expected_duration = segment.get("duration_s")
                if duration_item.get("segment_id") != expected_id:
                    issues.append(issue("error", "video_generation_segment_duration_id_mismatch", f"本批第 {offset} 个逐段时长必须对应 {expected_id}。", path))
                if duration_item.get("duration_s") != expected_duration:
                    issues.append(issue("error", "video_generation_segment_duration_mismatch", f"{expected_id} 的确认时长必须等于实际片段时长。", path))
            expected_total = sum(
                float(segment.get("duration_s"))
                for segment in expected_segments
                if isinstance(segment.get("duration_s"), (int, float)) and not isinstance(segment.get("duration_s"), bool)
            )
            if item.get("duration_s") != expected_total:
                issues.append(issue("error", "video_generation_total_duration_mismatch", "批次 duration_s 必须等于逐段时长之和。", path))
        displayed_parameters = item.get("displayed_parameter_table")
        required_parameter_fields = (
            "task_type",
            "delivery_format",
            "segment_durations",
            "total_duration",
            "aspect_ratio_and_resolution",
            "model",
            "visual_and_continuity",
            "audio_and_subtitles",
            "reference_materials",
        )
        if planning_preview_confirmation:
            required_lightweight_fields = {
                "task_type",
                "delivery_format",
                "quantity",
                "total_duration",
                "aspect_ratio_and_resolution",
                "model",
                "visual_and_continuity",
                "audio_and_subtitles",
                "reference_materials",
            }
            if not isinstance(displayed_parameters, dict):
                issues.append(issue("error", "lightweight_planning_parameters_missing", "轻量模式生成确认必须登记已展示的规划参数列表。", path))
            else:
                missing_fields = sorted(
                    field
                    for field in required_lightweight_fields
                    if not str(displayed_parameters.get(field) or "").strip()
                )
                if missing_fields:
                    issues.append(issue("error", "lightweight_planning_parameters_incomplete", f"轻量模式规划参数缺少视频生成确认字段：{missing_fields}", path))
                if displayed_parameters.get("quantity") != 1:
                    issues.append(issue("error", "lightweight_planning_quantity_invalid", "轻量模式视频数量必须为 1。", path))
        elif not isinstance(displayed_parameters, dict):
            issues.append(issue("error", "video_generation_parameter_table_missing", "必须登记实际展示的一张本批次合并参数确认表。", path))
        else:
            if displayed_parameters.get("quantity") != planned_count:
                issues.append(issue("error", "video_generation_displayed_quantity_mismatch", "参数确认表“数量”必须等于 planned_video_count。", path))
            for field in required_parameter_fields:
                value = displayed_parameters.get(field)
                if isinstance(value, list):
                    valid = bool(value) and all(str(entry).strip() for entry in value)
                else:
                    valid = bool(str(value or "").strip())
                if not valid:
                    issues.append(issue("error", "video_generation_parameter_table_field_missing", f"合并参数确认表缺少 {field}。", path))
                elif isinstance(value, list):
                    for entry in value:
                        if str(entry).strip() not in str(item.get("final_parameters_text") or ""):
                            issues.append(issue("error", "video_generation_parameter_table_text_mismatch", f"合并参数确认表展示文本缺少 {field} 项：{entry}。", path))
                elif str(value).strip() not in str(item.get("final_parameters_text") or ""):
                    issues.append(issue("error", "video_generation_parameter_table_text_mismatch", f"合并参数确认表展示文本缺少 {field} 的确认值。", path))
            displayed_durations = displayed_parameters.get("segment_durations")
            if isinstance(displayed_durations, list) and len(displayed_durations) != covered_count:
                issues.append(issue("error", "video_generation_displayed_duration_count_mismatch", "参数确认表必须按 SEG 分别展示时长，项数等于“数量”。", path))
            elif isinstance(displayed_durations, list) and expected_segments:
                for displayed_duration, segment in zip(displayed_durations, expected_segments):
                    expected_id = str(segment.get("segment_id") or "")
                    expected_duration = segment.get("duration_s")
                    duration_text = f"{expected_duration:g}" if isinstance(expected_duration, (int, float)) and not isinstance(expected_duration, bool) else str(expected_duration or "")
                    rendered = str(displayed_duration)
                    if expected_id not in rendered or not re.search(rf"{re.escape(duration_text)}\s*(?:秒|s\b|sec(?:ond)?s?\b)", rendered, flags=re.I):
                        issues.append(issue("error", "video_generation_displayed_duration_mismatch", f"参数确认表必须单独显示 {expected_id} 的真实时长。", path))
            displayed_model = str(displayed_parameters.get("model") or "")
            if str(item.get("model") or "") not in displayed_model:
                issues.append(issue("error", "video_generation_displayed_model_mismatch", "参数确认表中的视频模型必须匹配本批次 model。", path))
            displayed_format = str(displayed_parameters.get("aspect_ratio_and_resolution") or "")
            if str(item.get("aspect_ratio") or "") not in displayed_format:
                issues.append(issue("error", "video_generation_displayed_aspect_ratio_mismatch", "参数确认表中的画幅必须匹配本批次 aspect_ratio。", path))
            if expected_segments:
                expected_total = sum(
                    float(segment.get("duration_s"))
                    for segment in expected_segments
                    if isinstance(segment.get("duration_s"), (int, float)) and not isinstance(segment.get("duration_s"), bool)
                )
                total_text = f"{expected_total:g}"
                if not re.search(rf"{re.escape(total_text)}\s*(?:秒|s\b|sec(?:ond)?s?\b)", str(displayed_parameters.get("total_duration") or ""), flags=re.I):
                    issues.append(issue("error", "video_generation_displayed_total_duration_mismatch", "参数确认表中的总时长必须等于本批次逐段时长之和。", path))
        storyboard_rows = item.get("displayed_storyboard_rows")
        if planning_preview_confirmation:
            if not isinstance(storyboard_rows, list) or not 1 <= len(storyboard_rows) <= 8:
                issues.append(issue("error", "lightweight_planning_preview_rows_invalid", "轻量模式规划五列预览必须为 1-8 行。", path))
            elif any(not isinstance(row, dict) or not all(str(row.get(field) or "").strip() for field in ("time_range", "story_and_action", "audio", "camera_transition", "exit_function")) for row in storyboard_rows):
                issues.append(issue("error", "lightweight_planning_preview_field_missing", "轻量模式规划五列预览每行必须填写时间、剧情动作、声音、运镜衔接和段尾功能/承接；不得要求每段另造钩子。", path))
        elif not isinstance(storyboard_rows, list) or len(storyboard_rows) != covered_count:
            issues.append(issue("error", "video_generation_storyboard_rows_invalid", "本批次五列分镜表必须每个 SEG 恰好一行，行数等于“数量”。", path))
        elif expected_segments:
            for offset, (row, segment) in enumerate(zip(storyboard_rows, expected_segments), start=start):
                if not isinstance(row, dict):
                    issues.append(issue("error", "video_generation_storyboard_row_invalid", f"本批第 {offset} 行分镜必须是对象。", path))
                    continue
                expected_id = str(segment.get("segment_id") or "")
                if row.get("segment_id") != expected_id or row.get("duration_s") != segment.get("duration_s"):
                    issues.append(issue("error", "video_generation_storyboard_segment_mismatch", f"本批五列分镜第 {offset} 行的片段与时长必须匹配 {expected_id}。", path))
                for field in ("visual_content", "subject_action", "audio", "camera_and_materials"):
                    if not str(row.get(field) or "").strip():
                        issues.append(issue("error", "video_generation_storyboard_field_missing", f"{expected_id} 五列分镜缺少 {field}。", path))
                    elif str(row.get(field)).strip() not in str(item.get("final_parameters_text") or ""):
                        issues.append(issue("error", "video_generation_storyboard_text_mismatch", f"final_parameters_text 缺少 {expected_id} 五列分镜中的 {field} 内容。", path))
                row_audio = str(row.get("audio") or "")
                for speech_line in segment.get("speech_lines") or []:
                    if not isinstance(speech_line, dict):
                        continue
                    spoken_text = str(speech_line.get("spoken_text") or "").strip()
                    if spoken_text and spoken_text not in row_audio:
                        issues.append(issue("error", "video_generation_storyboard_speech_missing", f"{expected_id} 五列分镜必须完整列出本段台词：{spoken_text}", path))
        final_parameters_text = str(item.get("final_parameters_text") or "")
        expected_table_counts = [5] if planning_preview_confirmation else [2, 5]
        if markdown_table_column_counts(final_parameters_text) != expected_table_counts:
            issues.append(issue("error", "video_generation_confirmation_tables_invalid", "视频生成确认展示结构与当前模式不一致。", path))
        if expected_segments and not planning_preview_confirmation:
            for segment in expected_segments:
                segment_id = str(segment.get("segment_id") or "")
                duration = segment.get("duration_s")
                duration_text = f"{duration:g}" if isinstance(duration, (int, float)) and not isinstance(duration, bool) else str(duration or "")
                if segment_id not in final_parameters_text or not re.search(rf"{re.escape(duration_text)}\s*(?:秒|s\b|sec(?:ond)?s?\b)", final_parameters_text, flags=re.I):
                    issues.append(issue("error", "video_generation_segment_details_not_displayed", f"final_parameters_text 必须分别显示 {segment_id} 及其时长。", path))
        if confirmed_at is None:
            issues.append(issue("error", "video_generation_confirmation_time_invalid", "视频生成参数确认 confirmed_at 必须是带时区 ISO-8601 时间。", path))
        if str(item.get("interaction_ask_result") or "").strip() != "generate":
            issues.append(issue("error", "video_generation_interaction_confirmation_missing", "视频生成参数确认必须登记 interaction.ask 返回 generate；普通文字确认不能替代执行确认。", path))
    for index in generated:
        if not any(start <= index <= end for start, end in confirmed_ranges):
            issues.append(issue("error", "video_generation_confirmation_missing", f"生成 SEG{index:03d} 前必须先取得覆盖该片段的用户确认。", path))
    for fallback_index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict):
            continue
        generated_segment = bool(str(segment.get("output_file") or "").strip()) or segment.get("status") in {"candidate", "accepted"}
        if not generated_segment:
            continue
        index_value = segment.get("episode_segment_index")
        segment_index = index_value if isinstance(index_value, int) and not isinstance(index_value, bool) else fallback_index
        matching = [item for item in confirmation_items if item[0] <= segment_index <= item[1]]
        if not matching:
            continue
        confirmation_id = str(segment.get("generation_confirmation_id") or "").strip()
        if not confirmation_id:
            issues.append(issue("error", "video_generation_confirmation_id_missing", f"SEG{segment_index:03d} 已生成，必须登记 generation_confirmation_id。", path))
        elif all(str(item[2].get("confirmation_id") or "").strip() != confirmation_id for item in matching):
            issues.append(issue("error", "video_generation_confirmation_id_mismatch", f"SEG{segment_index:03d} generation_confirmation_id 必须匹配覆盖该片段的视频生成参数确认。", path))
        else:
            latest = matching[-1]
            if confirmation_id != str(latest[2].get("confirmation_id") or "").strip():
                issues.append(issue("error", "video_generation_confirmation_not_latest", f"SEG{segment_index:03d} 必须引用覆盖该片段的最新有效确认。", path))
        if not str(segment.get("tool_call_id") or "").strip():
            issues.append(issue("error", "video_tool_call_id_missing", f"SEG{segment_index:03d} 已生成，必须登记实际视频工具 tool_call_id。", path))
        called_at = parse_iso_time(segment.get("tool_called_at"))
        if called_at is None:
            issues.append(issue("error", "video_tool_called_at_invalid", f"SEG{segment_index:03d} 已生成，必须登记带时区 ISO-8601 tool_called_at。", path))
            continue
        latest_confirmed_at = matching[-1][3]
        if latest_confirmed_at is None or latest_confirmed_at >= called_at:
            issues.append(issue("error", "video_confirmation_after_tool_call", f"SEG{segment_index:03d} 的视频生成参数确认时间必须早于视频工具调用时间。", path))


def check_voice_audio_inputs(segment: dict[str, Any], audio_roles: set[str], path: Path, issues: list[dict[str, Any]]) -> None:
    speech_lines = segment.get("speech_lines")
    if not isinstance(speech_lines, list) or not speech_lines:
        return
    segment_label = str(segment.get("segment_id") or "segment")
    audio_input_supported = segment.get("audio_input_supported") is True
    has_voice_audio_reference = "voice_audio_reference" in audio_roles
    voice_inputs = segment.get("voice_inputs")

    if not audio_input_supported and not has_voice_audio_reference:
        if isinstance(voice_inputs, list) and voice_inputs:
            issues.append(issue("error", "voice_inputs_without_audio_reference", f"{segment_label} 未传 VOICE 音频时不得登记 voice_inputs；请改用 speech_lines.voice_anchor 作为文字音色锚点。", path))
        for index, line in enumerate(speech_lines, start=1):
            if not isinstance(line, dict):
                continue
            if not str(line.get("voice_anchor") or "").strip():
                issues.append(issue("error", "speech_line_voice_anchor_missing", f"{segment_label} speech_lines 第 {index} 条未传 VOICE 音频时必须填写固定 voice_anchor。", path))
        return

    if audio_input_supported and not has_voice_audio_reference:
        issues.append(issue("error", "voice_audio_input_missing", f"{segment_label} 支持音频输入且有 speech_lines 时必须上传 approved VOICE 音频。", path))
    if has_voice_audio_reference and not audio_input_supported:
        issues.append(issue("error", "voice_audio_support_flag_missing", f"{segment_label} 已传 voice_audio_reference 时 audio_input_supported 必须为 true。", path))
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
    for index, line in enumerate(speech_lines, start=1):
        if not isinstance(line, dict):
            continue
        voice_id = line.get("voice_id")
        if isinstance(voice_id, str) and voice_id.strip() and voice_id not in voice_ids:
            issues.append(issue("error", "speech_line_voice_input_missing", f"{segment_label} speech_lines 第 {index} 条 voice_id 未在 voice_inputs 中登记：{voice_id}", path))


def check_voice_anchor_consistency(segment: dict[str, Any], seen: dict[str, str], path: Path, issues: list[dict[str, Any]]) -> None:
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
        voice_anchor = str(line.get("voice_anchor") or "").strip()
        if not voice_anchor:
            issues.append(issue("error", "speech_line_voice_anchor_missing", f"{segment_label} speech_lines 第 {index} 条有 voice_id 但缺少固定 voice_anchor。", path))
            continue
        previous = seen.get(voice_id)
        if previous is None:
            seen[voice_id] = voice_anchor
        elif previous != voice_anchor:
            issues.append(issue("error", "speech_line_voice_anchor_inconsistent", f"{segment_label} speech_lines 第 {index} 条 voice_id={voice_id} 的 voice_anchor 必须与同一人物前文完全一致。", path))


def check_prompt_preflight(segment: dict[str, Any], expected_shot_ids: list[str], path: Path, issues: list[dict[str, Any]]) -> None:
    label = str(segment.get("segment_id") or "segment")
    preflight = segment.get("prompt_preflight")
    if not isinstance(preflight, dict):
        issues.append(issue("error", "prompt_preflight_missing", f"{label} 必须登记一次集中 Prompt 预检和一次最终客观校验。", path))
        return
    if preflight.get("review_count") != 1:
        issues.append(issue("error", "prompt_preflight_review_count_invalid", f"{label} prompt_preflight.review_count 必须为 1。", path))
    revision_count = preflight.get("revision_count")
    if revision_count not in {0, 1}:
        issues.append(issue("error", "prompt_preflight_revision_count_invalid", f"{label} Prompt 集中修订最多 1 次。", path))
    if preflight.get("final_validation_count") != 1:
        issues.append(issue("error", "prompt_final_validation_count_invalid", f"{label} prompt_preflight.final_validation_count 必须为 1。", path))
    if preflight.get("five_sections_in_order") is not True:
        issues.append(issue("error", "prompt_five_sections_not_verified", f"{label} 必须确认五段式顺序完整。", path))
    compiled_once = preflight.get("shot_ids_compiled_once")
    if not isinstance(compiled_once, list) or compiled_once != expected_shot_ids or len(set(compiled_once)) != len(compiled_once):
        issues.append(issue("error", "prompt_shot_preflight_mismatch", f"{label} shot_ids_compiled_once 必须按分镜顺序恰好列出每个镜头一次。", path))
    if preflight.get("result") != "passed":
        issues.append(issue("error", "prompt_preflight_not_passed", f"{label} 最终客观校验必须通过后才能生成。", path))


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
            if isinstance(file_value, str) and not re.search(r"关键帧_KF\d+_SEG\d+_highlight-\d+_v\d+_ep_[1-9]\d*\.[A-Za-z0-9]+$", file_value):
                issues.append(issue("error", "keyframe_file_name_invalid", f"{keyframe_id or '关键帧'} 文件名必须使用 highlight-N 高光序号。", path))
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
        planned_total = sum(planned_keyframes.values())
        actual_total = sum(actual_keyframes.values())
        if planned_total and actual_total != planned_total:
            issues.append(issue("error", "episode_keyframe_count_mismatch", f"本集实际有效关键帧数量 {actual_total} 必须等于 storyboard.keyframe_requests 规划总数 {planned_total}。", path))
        for segment_id, planned_count in planned_keyframes.items():
            actual_count = actual_keyframes.get(segment_id, 0)
            if actual_count != planned_count:
                issues.append(issue("error", "keyframe_count_mismatch", f"{segment_id} 实际有效关键帧数量 {actual_count} 必须等于 storyboard.keyframe_requests 规划数量 {planned_count}。", path))

def check_video(
    root: Path,
    asset_index: dict[str, Any],
    plan: Any,
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
    require_accepted: bool = True,
) -> None:
    lightweight = is_lightweight_plan(plan) and lightweight_constraints_valid(plan)
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"04_视频片段/video_manifest_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", "video_manifest episode_id 与目录不一致。", path))
        quality_gate_enabled = str(data.get("schema_version", "1.0")) >= "1.1"
        index = load_storyboard_index(root, episode_id, issues)
        keyframe_ids = load_keyframe_ids(root, episode_id, issues)
        segments = data.get("segments")
        if not isinstance(segments, list):
            issues.append(issue("error", "video_segments_invalid", "video_manifest.segments 必须是数组。", path))
            continue
        if lightweight and len(segments) != 1:
            issues.append(issue("error", "lightweight_video_count_invalid", "轻量模式必须只生成一个最终视频；多个独立视频必须拆为独立任务。", path))
        check_video_generation_confirmations(data, segments, path, issues, lightweight)
        if lightweight and isinstance(data.get("generation_confirmations"), list) and data["generation_confirmations"]:
            planning_records = [
                record
                for record in load_confirmation_records(root, issues, required=True)
                if record.get("stage") == "planning"
                and record.get("confirmation_purpose") == "video_generation"
                and record.get("interaction_ask_result") == "generate"
            ]
            latest_planning = max(planning_records, key=lambda record: record.get("revision", 0), default={})
            first_generation = data["generation_confirmations"][0]
            if not isinstance(first_generation, dict) or first_generation.get("interaction_ask_call_id") != latest_planning.get("interaction_ask_call_id"):
                issues.append(issue("error", "lightweight_confirmation_call_mismatch", "轻量模式 planning 与首次视频生成记录必须复用同一个 interaction.ask 调用 ID。", path))
        video_segment_ids = check_unique(segments, "segment_id", path, issues, "video segments")
        if index["segments"]:
            missing_segments = sorted(index["segments"] - video_segment_ids)
            extra_segments = sorted(video_segment_ids - index["segments"])
            if missing_segments:
                issues.append(issue("error", "video_segment_missing", f"video_manifest 缺少 storyboard segment：{missing_segments}", path))
            if extra_segments:
                issues.append(issue("error", "video_segment_unplanned", f"video_manifest 含 storyboard 中不存在的 segment：{extra_segments}", path))
        if isinstance(data.get("duration_s"), (int, float)):
            calculated = int(round(sum(float(s.get("duration_s")) for s in segments if isinstance(s, dict) and isinstance(s.get("duration_s"), (int, float)))))
            if calculated and int(round(float(data["duration_s"]))) != calculated:
                issues.append(issue("error", "video_duration_mismatch", "video_manifest.duration_s 必须等于 segments.duration_s 之和。", path))
        seen_voice_anchors: dict[str, str] = {}
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            segment_duration = segment.get("duration_s")
            if isinstance(segment_duration, (int, float)) and not isinstance(segment_duration, bool) \
                    and abs(float(segment_duration) - round(float(segment_duration))) > 1e-9:
                issues.append(issue(
                    "error", "video_segment_duration_not_integer",
                    f"{segment.get('segment_id') or 'SEG'} 时长 {segment_duration:g}s 非整数秒（视频 API 只接受整数 duration）；"
                    "段时长由分镜 pack 的 beat_groups 校验为整秒，请回查组声明并重跑 pack",
                    path,
                ))
        for segment in segments:
            if not isinstance(segment, dict):
                issues.append(issue("error", "video_segment_invalid", "segments 每项必须是对象。", path))
                continue
            segment_id = segment.get("segment_id")
            if isinstance(segment_id, str) and index["segments"] and segment_id not in index["segments"]:
                issues.append(issue("error", "video_unknown_segment", f"视频引用了分镜中不存在的 segment_id：{segment_id}", path))
            storyboard_duration = index["segment_durations"].get(segment_id)
            if storyboard_duration is not None and isinstance(segment.get("duration_s"), (int, float)):
                if int(round(float(segment["duration_s"]))) != int(round(float(storyboard_duration))):
                    issues.append(issue("error", "video_segment_duration_mismatch", f"{segment_id} 时长必须与分镜片段时长一致。", path))
            tool_mode = segment.get("tool_mode")
            image_orders, image_roles = ordered_inputs(root, segment.get("reference_inputs"), REFERENCE_ROLES, "reference", path, issues)
            video_orders, video_roles = ordered_inputs(root, segment.get("video_inputs"), VIDEO_INPUT_ROLES, "video", path, issues)
            audio_orders, audio_roles = ordered_inputs(root, segment.get("audio_inputs"), AUDIO_INPUT_ROLES, "audio", path, issues)
            required_roles = segment.get("required_reference_roles")
            model_name = video_model_name(plan, data, segment)
            if tool_mode not in VIDEO_TOOL_MODES:
                issues.append(issue("error", "video_tool_mode_invalid", f"{segment_id or 'segment'} tool_mode 无效：{tool_mode}", path))
            else:
                check_voice_anchor_consistency(segment, seen_voice_anchors, path, issues)
            if tool_mode == "text_to_video":
                if image_orders or video_orders or audio_orders or segment.get("voice_inputs"):
                    issues.append(issue("error", "text_to_video_input_invalid", "text_to_video 只能用于没有图片、视频、音频或 voice_inputs 的片段。", path))
            if tool_mode == "media_to_video":
                check_media_input_durations(segment, model_name, path, issues)
                check_voice_audio_inputs(segment, audio_roles, path, issues)
                check_video_state_refs(segment, image_roles, asset_index, path, issues)
                if not video_orders and not audio_orders:
                    issues.append(issue("error", "media_to_video_media_missing", "media_to_video 必须至少登记一个真实视频或音频输入。", path))
                planned_roles = index["required_reference_roles"].get(segment_id, set()) if isinstance(segment_id, str) else set()
                declared_roles = set(required_roles) if isinstance(required_roles, list) else set()
                if image_orders or planned_roles:
                    if not isinstance(required_roles, list) or not required_roles:
                        issues.append(issue("error", "required_reference_roles_missing", "media_to_video 使用图片或分镜声明图片职责时必须填写 required_reference_roles。", path))
                    elif any(role not in REFERENCE_ROLES for role in required_roles):
                        issues.append(issue("error", "required_reference_role_invalid", "required_reference_roles 含无效职责。", path))
                    elif not set(required_roles).issubset(image_roles):
                        missing = sorted(set(required_roles) - image_roles)
                        issues.append(issue("error", "required_reference_role_not_passed", f"required_reference_roles 未真实传入：{missing}", path))
                elif required_roles not in (None, []):
                    issues.append(issue("error", "required_reference_roles_unexpected", "media_to_video 没有图片输入时 required_reference_roles 应为空或省略。", path))
                if planned_roles and not planned_roles.issubset(declared_roles):
                    missing = sorted(planned_roles - declared_roles)
                    issues.append(issue("error", "storyboard_required_role_not_inherited", f"{segment_id} 未继承 storyboard.required_reference_roles：{missing}", path))
                if planned_roles and not planned_roles.issubset(image_roles):
                    missing = sorted(planned_roles - image_roles)
                    issues.append(issue("error", "storyboard_required_role_not_passed", f"{segment_id} 的 storyboard.required_reference_roles 未真实传入：{missing}", path))
            if tool_mode == "image_to_video":
                check_video_state_refs(segment, image_roles, asset_index, path, issues)
                if not image_orders:
                    issues.append(issue("error", "image_to_video_reference_missing", "image_to_video 必须登记实际传入参考图。", path))
                if video_orders or audio_orders or segment.get("voice_inputs"):
                    issues.append(issue("error", "image_to_video_input_invalid", "image_to_video 不支持上传视频、音频或 voice_inputs；本路由只能传参考图。", path))
                if not isinstance(required_roles, list) or not required_roles:
                    issues.append(issue("error", "required_reference_roles_missing", "image_to_video 必须声明 required_reference_roles。", path))
                elif any(role not in REFERENCE_ROLES for role in required_roles):
                    issues.append(issue("error", "required_reference_role_invalid", "required_reference_roles 含无效职责。", path))
                elif not set(required_roles).issubset(image_roles):
                    missing = sorted(set(required_roles) - image_roles)
                    issues.append(issue("error", "required_reference_role_not_passed", f"required_reference_roles 未真实传入：{missing}", path))
                planned_roles = index["required_reference_roles"].get(segment_id, set()) if isinstance(segment_id, str) else set()
                declared_roles = set(required_roles) if isinstance(required_roles, list) else set()
                if planned_roles and not planned_roles.issubset(declared_roles):
                    missing = sorted(planned_roles - declared_roles)
                    issues.append(issue("error", "storyboard_required_role_not_inherited", f"{segment_id} 未继承 storyboard.required_reference_roles：{missing}", path))
                if planned_roles and not planned_roles.issubset(image_roles):
                    missing = sorted(planned_roles - image_roles)
                    issues.append(issue("error", "storyboard_required_role_not_passed", f"{segment_id} 的 storyboard.required_reference_roles 未真实传入：{missing}", path))
            if tool_mode == "video_edit":
                if image_orders or audio_orders or segment.get("voice_inputs"):
                    issues.append(issue("error", "video_edit_input_invalid", "video_edit 只登记源视频，不登记图片、音频或 voice_inputs。", path))
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
                if source_type == "keyframe" and isinstance(source_id, str) and keyframe_ids and source_id not in keyframe_ids:
                    issues.append(issue("error", "video_reference_unknown_keyframe", f"{segment_id} 引用了不存在的关键帧：{source_id}", path))
                if source_type == "audio":
                    audio_rel = str(input_item.get("resource") or input_item.get("path") or "")
                    if audio_rel and "shared/03_资产/音色/" not in audio_rel.replace("\\", "/"):
                        issues.append(issue(
                            "error", "ref_audio_not_voice_sample",
                            f"{segment_id} 的音频参考必须指向 shared/03_资产/音色/ 下已批准 VOICE 样音（路径：{audio_rel}）；禁止台词级 TTS 临时音频进入 ref_audio 槽位——正片台词由 H3 原生生成，参考只锁声线。",
                            path,
                        ))
            # 提交给模型的是 H3 成稿(h3_prompt_file)；compiled_prompt_file 现指向
            # 五段交付包文件(skill 输入与返修凭证)。标记/哈希/存在性检查一律查成稿。
            prompt_file = segment.get("h3_prompt_file") or segment.get("compiled_prompt_file")
            prompt_path = relative_file(root, prompt_file)
            package_file = segment.get("compiled_prompt_file")
            package_path = relative_file(root, package_file)
            if package_path is not None and package_file and not package_path.is_file():
                issues.append(issue("error", "delivery_package_file_missing", f"{segment_id} 登记了 compiled_prompt_file（五段交付包），但文件不存在。", path))
            if lightweight:
                raw_shot_ids = segment.get("shot_ids")
                expected_shot_ids = raw_shot_ids if isinstance(raw_shot_ids, list) else []
            else:
                expected_shot_ids = index["segment_shots"].get(segment_id, []) if isinstance(segment_id, str) else []
            if tool_mode != "video_edit":
                check_prompt_preflight(segment, expected_shot_ids, path, issues)
                check_h3_prompt(segment, root, path, issues)
            if prompt_path is not None:
                check_prompt_markers(
                    prompt_path,
                    image_orders,
                    video_orders,
                    audio_orders,
                    segment.get("speech_lines"),
                    segment.get("subtitle_enabled") is True,
                    tool_mode != "video_edit",
                    issues,
                )
                if tool_mode != "video_edit":
                    _check_h3_prompt_purity(prompt_path, segment_id, issues)
                prompt_sha256 = str(segment.get("prompt_sha256") or "").strip()
                if prompt_sha256:
                    try:
                        actual_sha256 = file_sha256(prompt_path)
                    except OSError as exc:
                        issues.append(issue("error", "prompt_sha256_unreadable", f"无法读取 Prompt 计算 sha256：{exc}", prompt_path))
                    else:
                        if actual_sha256 != prompt_sha256:
                            issues.append(issue("error", "prompt_sha256_mismatch", f"{segment_id} prompt_sha256 与实际 Prompt 文件不一致。", prompt_path))
            elif prompt_file:
                issues.append(issue("error", "prompt_path_invalid", "compiled_prompt_file 必须是项目相对路径。", path))
            generated_segment = bool(str(segment.get("output_file") or "").strip()) or segment.get("status") in {"candidate", "accepted"}
            if generated_segment and (prompt_path is None or not prompt_path.is_file()):
                issues.append(issue("error", "generated_segment_prompt_missing", f"{segment_id} 已生成或进入候选/验收状态，必须登记真实存在的 H3 成稿文件。", path))
            if generated_segment and not str(segment.get("prompt_sha256") or "").strip():
                issues.append(issue("error", "generated_segment_prompt_sha256_missing", f"{segment_id} 已生成或进入候选/验收状态，必须登记实际提交 Prompt 文件的 prompt_sha256。", path))
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
                if prompt_path is None or not prompt_path.is_file():
                    issues.append(issue("error", "accepted_segment_prompt_missing", f"{segment_id} 已 accepted，但 H3 成稿文件不存在。", path))
            if quality_gate_enabled:
                gate = segment.get("quality_gate")
                if not isinstance(gate, dict) or gate.get("status") not in {"pending", "pass", "blocked", "deviation_accepted"}:
                    issues.append(issue("error", "video_quality_gate_invalid", f"{segment_id} 新版清单必须记录 quality_gate 状态。", path))
                else:
                    blockers = gate.get("blockers", [])
                    if not isinstance(blockers, list):
                        issues.append(issue("error", "video_quality_gate_blockers_invalid", f"{segment_id}.quality_gate.blockers 必须是数组。", path))
                        blockers = ["invalid"]
                    if gate.get("status") == "pass" and blockers:
                        issues.append(issue("error", "video_quality_gate_blocked_claim", f"{segment_id} 存在阻断项，不能标记 quality_gate=pass。", path))
                    if status == "accepted" and gate.get("status") not in {"pass", "deviation_accepted"}:
                        issues.append(issue("error", "accepted_without_quality_gate", f"{segment_id} 只有通过质量门或用户接受明确偏差后才能 accepted。", path))
                    if gate.get("status") == "deviation_accepted" and not str(gate.get("user_acceptance_ref") or "").strip():
                        issues.append(issue("error", "quality_deviation_acceptance_missing", f"{segment_id} 带偏差接受必须引用用户确认记录。", path))


def accepted_video_segments(root: Path, episode_id: str, issues: list[dict[str, Any]]) -> set[str]:
    path = root / f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json"
    data = load_json(path, issues, required=False)
    segments = data.get("segments") if isinstance(data, dict) else None
    if not isinstance(segments, list):
        return set()
    return {
        item.get("segment_id")
        for item in segments
        if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and item.get("status") == "accepted"
    }


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


def delivery_segment_refs(data: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    direct_fields = ("source_segments", "segment_ids", "used_segments", "video_segments", "accepted_segments")
    for field in direct_fields:
        value = data.get(field)
        if isinstance(value, list):
            refs.update(item for item in value if isinstance(item, str))
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("segment_id"), str):
                    refs.add(item["segment_id"])
    for field in ("segments", "segment_outputs", "outputs"):
        value = data.get(field)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("segment_id"), str):
                    refs.add(item["segment_id"])
    return refs


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


def check_report_entries(root: Path, entries: Any, expected_count: int, path: Path, issues: list[dict[str, Any]]) -> None:
    if not isinstance(entries, list):
        issues.append(issue("error", "basic_qc_reports_invalid", "basic_qc_reports 必须是数组。", path))
        return
    if len(entries) != expected_count:
        issues.append(issue("error", "basic_qc_reports_count_invalid", f"basic_qc_reports 数量应为 {expected_count}。", path))
    for entry in entries:
        if isinstance(entry, str):
            if not file_exists(root, entry):
                issues.append(issue("error", "basic_qc_report_missing", f"基础质检报告不存在：{entry}", path))
        elif isinstance(entry, dict):
            report_file = entry.get("file")
            if report_file and not file_exists(root, report_file):
                issues.append(issue("error", "basic_qc_report_missing", f"基础质检报告不存在：{report_file}", path))
        else:
            issues.append(issue("error", "basic_qc_report_invalid", "basic_qc_reports 每项必须是路径或对象。", path))
        if report_is_blocked(root, entry):
            issues.append(issue("error", "basic_qc_report_blocked", "基础媒体可用性检查结果为 blocked，不得交付。", path))


def check_continuity_for_delivery(root: Path, episode_id: str, accepted_order: list[str], issues: list[dict[str, Any]]) -> None:
    path = root / f"episodes/{episode_id}/04_视频片段/continuity_{episode_id}.json"
    data = load_json(path, issues, required=bool(accepted_order))
    if not isinstance(data, dict):
        return
    if data.get("episode_id") != episode_id:
        issues.append(issue("error", "episode_id_mismatch", "continuity episode_id 与目录不一致。", path))
    video_manifest = load_json(root / f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json", issues, required=False)
    quality_gate_enabled = isinstance(video_manifest, dict) and str(video_manifest.get("schema_version", "1.0")) >= "1.1"
    frames = data.get("frames")
    if not isinstance(frames, list):
        issues.append(issue("error", "continuity_frames_invalid", "continuity.frames 必须是数组。", path))
        frames = []
    roles_by_segment: dict[str, set[str]] = {}
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        segment_id = frame.get("segment_id")
        role = frame.get("role")
        if isinstance(segment_id, str) and isinstance(role, str):
            roles_by_segment.setdefault(segment_id, set()).add(role)
        file_value = frame.get("file")
        if file_value and not file_exists(root, file_value):
            issues.append(issue("error", "continuity_frame_file_missing", f"连续性抽帧文件不存在：{file_value}", path))
        if isinstance(file_value, str) and Path(file_value).suffix.lower() not in IMAGE_INPUT_SUFFIXES:
            issues.append(issue("error", "continuity_frame_suffix_invalid", f"连续性抽帧必须是图片文件：{file_value}", path))
    for segment_id in accepted_order:
        roles = roles_by_segment.get(segment_id, set())
        missing = sorted({"start", "scene", "tail"} - roles)
        if missing:
            issues.append(issue("error" if quality_gate_enabled else "warning", "continuity_frame_roles_missing", f"{segment_id} 连续性抽帧缺少 start|scene|tail：{missing}。", path))
    seams = data.get("seams")
    if not isinstance(seams, list):
        issues.append(issue("error", "continuity_seams_invalid", "continuity.seams 必须是数组。", path))
        seams = []
    seams_by_pair = {
        (item.get("from_segment"), item.get("to_segment")): item
        for item in seams
        if isinstance(item, dict)
    }
    for left, right in zip(accepted_order, accepted_order[1:]):
        seam = seams_by_pair.get((left, right))
        if not isinstance(seam, dict):
            issues.append(issue("error" if quality_gate_enabled else "warning", "continuity_seam_missing", f"缺少 {left} -> {right} 的 seam 记录。", path))
            continue
        if seam.get("status") != "verified":
            issues.append(issue("error" if quality_gate_enabled else "warning", "continuity_seam_not_verified", f"{left} -> {right} seam 必须通过检查后才能作为合格成片接缝。", path))
        if not isinstance(seam.get("selected_cut"), dict) or not seam.get("selected_cut"):
            issues.append(issue("error" if quality_gate_enabled else "warning", "continuity_seam_cut_missing", f"{left} -> {right} 关键接缝缺少 selected_cut。", path))
        for field in ("outgoing_window_frames", "incoming_window_frames"):
            value = seam.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 12:
                issues.append(issue("error" if quality_gate_enabled else "warning", "continuity_seam_window_invalid", f"{left} -> {right} {field} 必须至少覆盖 12 帧，才能验证并选定安全剪切点。", path))


def check_delivery(
    root: Path,
    expected_durations: dict[str, int],
    plan: Any,
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
    lightweight: bool = False,
) -> None:
    measured_durations: dict[str, float] = {}
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"05_成片/delivery_manifest_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", "delivery_manifest episode_id 与目录不一致。", path))
        assembly_confirmation = data.get("assembly_confirmation")
        if lightweight:
            if assembly_confirmation not in (None, {}):
                issues.append(issue("error", "lightweight_assembly_confirmation_invalid", "轻量模式单条视频不得创建拼接确认。", path))
            assembly_confirmation = {}
        elif not isinstance(assembly_confirmation, dict):
            issues.append(issue("error", "assembly_confirmation_missing", "delivery_manifest 必须登记进入成片拼接的 interaction.ask 确认。", path))
            assembly_confirmation = {}
        if not lightweight and assembly_confirmation.get("confirmation_purpose") != "final_assembly":
            issues.append(issue("error", "assembly_confirmation_purpose_invalid", "assembly_confirmation.confirmation_purpose 必须为 final_assembly。", path))
        if not lightweight and not str(assembly_confirmation.get("interaction_ask_call_id") or "").strip():
            issues.append(issue("error", "assembly_confirmation_call_id_missing", "assembly_confirmation 必须记录 interaction_ask_call_id。", path))
        if not lightweight and assembly_confirmation.get("interaction_ask_result") != "proceed_assembly":
            issues.append(issue("error", "assembly_confirmation_result_invalid", "assembly_confirmation.interaction_ask_result 必须为 proceed_assembly。", path))
        if not lightweight and not str(assembly_confirmation.get("user_message") or "").strip():
            issues.append(issue("error", "assembly_confirmation_user_message_missing", "assembly_confirmation.user_message 不能为空。", path))
        if not lightweight and parse_iso_time(assembly_confirmation.get("confirmed_at")) is None:
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
        if not lightweight and not matching_video_confirmations:
            issues.append(issue("error", "assembly_confirmation_video_record_missing", "assembly_confirmation 必须与同集 stage=video 用户确认记录使用同一 interaction.ask 调用 ID 和 proceed_assembly 结果。", path))
        subtitle_enabled = data.get("subtitle_enabled")
        if not isinstance(subtitle_enabled, bool):
            issues.append(issue("error", "subtitle_enabled_invalid", "subtitle_enabled 必须是布尔值；默认 false，用户明确要求字幕时为 true。", path))
        if data.get("status") not in {"deliverable", "candidate"}:
            issues.append(issue("error", "delivery_status_not_deliverable", "delivery_manifest.status 必须为 deliverable 或 candidate；blocked 不得交付。", path))
        if str(data.get("schema_version", "1.0")) >= "1.1":
            gate = data.get("content_quality_gate")
            if not isinstance(gate, dict) or gate.get("status") not in {"pass", "blocked", "deviation_accepted"}:
                issues.append(issue("error", "delivery_quality_gate_invalid", "新版 delivery_manifest 必须记录 content_quality_gate。", path))
            else:
                blockers = gate.get("blockers", [])
                if not isinstance(blockers, list):
                    issues.append(issue("error", "delivery_quality_gate_blockers_invalid", "content_quality_gate.blockers 必须是数组。", path))
                    blockers = ["invalid"]
                if data.get("status") == "deliverable" and (gate.get("status") not in {"pass", "deviation_accepted"} or blockers):
                    issues.append(issue("error", "delivery_without_quality_pass", "deliverable 必须通过整片内容质量门且无阻断项。", path))
                if gate.get("status") == "deviation_accepted" and not str(gate.get("user_acceptance_ref") or "").strip():
                    issues.append(issue("error", "delivery_deviation_acceptance_missing", "整片带偏差交付必须引用用户明确接受记录。", path))
        duration = data.get("duration_s")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool):
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
        reports = data.get("basic_qc_reports")
        if reports not in (None, []):
            if isinstance(reports, list):
                check_report_entries(root, reports, len(reports), path, issues)
            else:
                issues.append(issue("error", "basic_qc_reports_invalid", "basic_qc_reports 必须是数组。", path))
        if subtitle_enabled is True:
            subtitle_alignment_report = data.get("subtitle_alignment_report")
            if not str(subtitle_alignment_report or "").strip():
                issues.append(issue("error", "subtitle_alignment_report_missing", "字幕开启时必须存在 subtitle_alignment_report（字幕对齐报告）。", path))
            elif not file_inside(root, subtitle_alignment_report, episode_root) or report_is_blocked(root, subtitle_alignment_report):
                issues.append(issue("error", "subtitle_alignment_report_invalid", "subtitle_alignment_report 必须指向当前分集目录下未 blocked 的内部追溯文件。", path))
            subtitle_source = data.get("subtitle_source")
            if not file_inside(root, subtitle_source, episode_root):
                issues.append(issue("error", "subtitle_source_missing", "字幕开启时必须存在当前分集目录下的 subtitle_source。", path))
            elif isinstance(subtitle_source, str) and not re.search(r"字幕_时间轴_v\d+_ep_[1-9]\d*\.srt$", subtitle_source):
                issues.append(issue("error", "subtitle_source_name_invalid", "subtitle_source 应指向 字幕_时间轴_vNN_ep_N.srt。", path))
            subtitle_final = data.get("subtitle_final")
            if not file_inside(root, subtitle_final, episode_root):
                issues.append(issue("error", "subtitle_final_missing", "字幕开启时必须存在当前分集目录下的 subtitle_final。", path))
            elif isinstance(subtitle_final, str) and not re.search(r"字幕_最终版_v\d+_ep_[1-9]\d*\.json$", subtitle_final):
                issues.append(issue("error", "subtitle_final_name_invalid", "subtitle_final 应指向 字幕_最终版_vNN_ep_N.json。", path))
        accepted_order = accepted_video_segment_order(root, episode_id, issues, allow_candidate=lightweight)
        accepted = set(accepted_order)
        if not lightweight and assembly_confirmation.get("segment_ids") != accepted_order:
            issues.append(issue("error", "assembly_confirmation_segments_mismatch", "assembly_confirmation.segment_ids 必须按顺序精确等于当前成片采用的 accepted SEG。", path))
        for segment_id in sorted(delivery_segment_refs(data)):
            if segment_id not in accepted:
                issues.append(issue("error", "delivery_non_accepted_segment", f"delivery 使用了不符合当前模式状态要求的视频片段：{segment_id}", path))
        if not lightweight:
            check_continuity_for_delivery(root, episode_id, accepted_order, issues)
    contract = plan.get("duration_contract") if isinstance(plan, dict) else None
    if isinstance(contract, dict):
        mode = contract.get("mode")
        scope = contract.get("scope")
        target = contract.get("target_duration_s")
        tolerance = contract.get("tolerance_ratio")
        measured = list(measured_durations.values())
        if mode in {"target_band", "exact"} and isinstance(target, (int, float)) and measured:
            if scope == "episode":
                values = [(episode_id, value) for episode_id, value in measured_durations.items()]
            elif episode_filter is None:
                values = [("全项目" if scope == "project" else "交付物", sum(measured))]
            else:
                values = []
            delta = 0 if mode == "exact" else float(tolerance or 0)
            lower, upper = float(target) * (1 - delta), float(target) * (1 + delta)
            for label, value in values:
                if value < lower - 1e-6 or value > upper + 1e-6:
                    issues.append(issue("error", "delivery_duration_out_of_contract", f"{label} 实测 {value:g}s 不在 duration_contract {mode} 范围 [{lower:g}, {upper:g}]s；不得以计划时长代替实测。", root / "00_制作控制/drama_plan.json"))


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


def _flatten_conditional(spec: dict) -> dict[str, list[str]]:
    """conditional 各条件键的 {文件: 锚点} 合并为一份 {文件: 锚点集合}。"""
    merged: dict[str, set] = {}
    for conditional in (spec.get("conditional") or {}).values():
        if not isinstance(conditional, dict):
            continue
        for rel, anchors in conditional.items():
            if anchors:
                merged.setdefault(rel, set()).update(anchors)
    return {rel: sorted(anchors) for rel, anchors in merged.items()}


def anchor_heading_count(text: str, anchor: str) -> int:
    """统计锚点标题在文件中的命中次数（跳过代码围栏），锚点必须恰好命中一次。"""
    count = 0
    fence_char: str | None = None
    fence_length = 0
    for line in text.splitlines():
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
        if re.match(r"^#{1,6}\s", line) and line.strip() == anchor:
            count += 1
    return count


def check_skill_package(root: Path, issues: list[dict[str, Any]]) -> None:
    skill_path = root / "SKILL.md"
    try:
        text = skill_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        issues.append(issue("error", "skill_file_missing", "Skill 根目录缺少 SKILL.md。", skill_path))
        return
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "skill_file_unreadable", f"SKILL.md 无法读取：{exc}", skill_path))
        return

    frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if frontmatter is None:
        issues.append(issue("error", "skill_frontmatter_missing", "SKILL.md 缺少合法的 YAML frontmatter。", skill_path))
        return
    fields: dict[str, str] = {}
    for line in frontmatter.group(1).splitlines():
        match = re.fullmatch(r"([a-z_]+):\s*(.*)", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    name = fields.get("name", "")
    description = fields.get("description", "")
    if not 2 <= len(name) <= 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        issues.append(issue("error", "skill_name_invalid", "Skill name 必须是 2-64 位小写字母、数字或单连字符。", skill_path))
    if name != root.name:
        issues.append(issue("error", "skill_name_path_mismatch", "Skill name 必须与目录名一致。", skill_path))
    if not description or description[:1] in {'"', "'"} or description[-1:] in {'"', "'"}:
        issues.append(issue("error", "skill_description_invalid", "Skill description 必须是非空、未加引号的单行标量。", skill_path))
    if ": " in description or "<" in description or ">" in description or "TODO" in description:
        issues.append(issue("error", "skill_description_forbidden_text", "Skill description 含禁止的格式或占位内容。", skill_path))
    if not text[frontmatter.end():].strip():
        issues.append(issue("error", "skill_body_empty", "SKILL.md 正文不能为空。", skill_path))

    referenced_paths = set(re.findall(r"`((?:references|scripts)/[^`\s]+?\.(?:md|py))`", text))
    for relative in sorted(referenced_paths):
        target = root / relative
        if not target.is_file():
            issues.append(issue("error", "skill_reference_missing", f"SKILL.md 引用的本地文件不存在：{relative}", skill_path))

    reference_map_path = root / "references/reference_map.json"
    try:
        reference_map = json.loads(reference_map_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        issues.append(issue("error", "reference_map_missing", "缺少 references/reference_map.json 阶段包索引。", reference_map_path))
        reference_map = None
    except (OSError, ValueError) as exc:
        issues.append(issue("error", "reference_map_unreadable", f"reference_map.json 无法解析：{exc}", reference_map_path))
        reference_map = None
    if isinstance(reference_map, dict):
        for stage_name, spec in sorted((reference_map.get("stages") or {}).items()):
            if not isinstance(spec, dict):
                continue
            for rel, anchors in sorted({**(spec.get("sections") or {}), **_flatten_conditional(spec)}.items()):
                file_path = root / rel
                if not file_path.is_file():
                    issues.append(issue("error", "reference_map_file_missing", f"阶段 {stage_name} 的 sections 文件不存在：{rel}", reference_map_path))
                    continue
                try:
                    file_text = file_path.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    issues.append(issue("error", "reference_map_file_unreadable", f"reference_map 引用文件无法读取：{rel}：{exc}", reference_map_path))
                    continue
                for anchor in anchors or ():
                    if anchor_heading_count(file_text, anchor) != 1:
                        issues.append(issue("error", "reference_map_anchor_unresolved", f"阶段 {stage_name} 的锚点 {anchor!r} 在 {rel} 中命中次数不等于 1。", reference_map_path))

    markdown_paths = [
        path
        for path in sorted(root.glob("references/**/*.md"))
        if "references/cli" not in path.as_posix()
    ] + [skill_path]
    for markdown_path in markdown_paths:
        try:
            markdown_text = markdown_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(issue("error", "markdown_file_unreadable", f"Markdown 文件无法读取：{exc}", markdown_path))
            continue
        for match in re.finditer(r"(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)", markdown_text):
            raw_target = match.group(1).strip()
            if not raw_target or raw_target.startswith(("#", "http://", "https://", "mailto:", "app://", "codex://")):
                continue
            if " " in raw_target and not (raw_target.startswith("<") and raw_target.endswith(">")):
                raw_target = raw_target.split()[0]
            raw_target = raw_target.strip("<>")
            path_part = raw_target.split("#", 1)[0].split("?", 1)[0]
            if not path_part:
                continue
            target = markdown_path.parent / unquote(path_part)
            if not target.exists():
                issues.append(issue("error", "markdown_link_missing", f"Markdown 相对链接不存在：{raw_target}", markdown_path))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Focused doubao-creative-drama workflow validator.")
    parser.add_argument("skill_root", nargs="?", default=".")
    parser.add_argument("--project-root")
    parser.add_argument("--stage", choices=("skill", *STAGES, "all"), default="skill")
    parser.add_argument("--fix", action="store_true", help="kept for compatibility; no automatic fixes are applied")
    parser.add_argument("--changed-file", action="append", default=[], help="kept for compatibility; runs the same focused checks")
    return parser.parse_args(argv)


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
        check_skill_package(project_root, issues)
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
    expected_durations = check_plan_durations(project_root, plan, issues)
    lightweight = is_lightweight_plan(plan) and lightweight_constraints_valid(plan)
    check_episode_directories(project_root, expected_durations, issues)
    check_episode_entry_manifests(project_root, issues, lightweight)
    check_state(project_root, plan, issues)
    check_operation_log_tools(project_root, issues)

    state = load_json(project_root / "00_制作控制/制作状态.json", issues, required=False)
    active_episode = state.get("current_episode") if isinstance(state, dict) else None
    stages_to_check = STAGES if args.stage == "all" else (args.stage,)
    for stage in stages_to_check:
        episode_filter = active_episode if args.stage != "all" and stage in EPISODE_STAGES else None
        check_stage_artifacts(project_root, stage, issues, episode_filter, lightweight)
        if stage in EPISODE_STAGES:
            check_episode_manifest_ids(project_root, stage, issues, episode_filter)
    episode_filter = active_episode if args.stage != "all" and args.stage in EPISODE_STAGES else None
    asset_index = blank_asset_index()
    if args.stage in {"assets", "storyboard", "keyframes", "video", "final", "all"}:
        asset_index = check_assets(project_root, issues, episode_filter)
    rhythm_lib: RhythmLibrary | None = None
    if args.stage in {"storyboard", "keyframes", "video", "final", "all"}:
        rhythm_lib = RhythmLibrary()
        rhythm_lib.ensure()
        check_beat_library_desync(rhythm_lib, issues)
    if args.stage in {"storyboard", "keyframes", "video", "final", "all"}:
        check_storyboards(project_root, expected_durations, plan, issues, episode_filter, asset_index=asset_index, rhythm=rhythm_lib)
    if args.stage in {"keyframes", "video", "final", "all"}:
        check_keyframes(project_root, asset_index, issues, episode_filter)
    if args.stage in {"video", "final", "all"}:
        check_video(
            project_root,
            asset_index,
            plan,
            issues,
            episode_filter,
            require_accepted=args.stage in {"final", "all"} and not lightweight,
        )
    if args.stage in {"final", "all"}:
        check_delivery(project_root, expected_durations, plan, issues, episode_filter, lightweight)

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
