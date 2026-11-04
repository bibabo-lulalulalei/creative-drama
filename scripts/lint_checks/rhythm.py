"""Rhythm-library loading and objective storyboard timing checks."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from content_first import reconcile_storyboard, read_json
from .common import issue
from .constants import (
    BEAT_LIBRARY_JSON_PATH, BEAT_LIBRARY_MD_PATH, CUT_MOTIVATIONS, H3_CAPABILITY_PATH,
)


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


def check_beat_library_desync(issues):
    try:
        import build_beat_types
        rebuilt = build_beat_types.build(str(BEAT_LIBRARY_MD_PATH))
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
        issues.append(issue("error", "segment_density_profile_invalid", f"{label} density_profile 无效。", path, hint='该字段是可选定性标注；填写时取合法枚举，custom 在 density_rationale 说明，不确定就整字段删除。'))
    if shot_mode not in {"edited", "true_one_take"}:
        issues.append(issue("error", "segment_shot_mode_invalid", f"{label} shot_mode 必须为 edited 或 true_one_take。", path, hint='按片段职责填 shot_mode=edited（默认）或 true_one_take（且只能含 1 个镜头）；schema：python scripts/read_reference.py --file references/manifests/storyboard.md --section "### storyboard_ep_N.json"'))
        return
    if shot_mode == "true_one_take":
        if shot_count != 1:
            issues.append(issue("error", "true_one_take_shot_count_invalid", f"{label} 标记为 true_one_take 时必须且只能包含 1 个镜头。", path, hint='不是严格一镜到底就改回 edited；确属一镜到底则收敛为单镜头并补 one_take_route 与总控卡证明。python scripts/read_reference.py --file references/storyboard.md --section "### 真正一镜到底的场面调度算法"'))
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
        issues.append(issue("error", "timing_input_invalid", f"当前时间合同不可核对：{exc}", path, hint='按随附异常修 rhythm_input 后先 allocate --write，再 pack；作业顺序：python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
