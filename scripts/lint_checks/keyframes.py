"""Keyframe manifests, source shots and asset-reference checks."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from .common import (
    check_generation_prompt_file, check_style_anchor_contract, check_unique, combined_strings,
    episode_dirs, file_exists, issue, load_json,
)
from .prompts import check_asset_ref, check_state_ref
from .storyboard import load_storyboard_index


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
        planned_ids = {request.get("keyframe_id") for requests in index.get("keyframe_requests", {}).values() for request in requests if isinstance(request, dict)}
        actual_ids = {row.get("keyframe_id") for row in keyframes if isinstance(row, dict) and row.get("status") not in {"rejected", "superseded"}}
        if planned_ids != actual_ids:
            issues.append(issue("error", "keyframe_identity_mismatch", "有效 KF 必须逐项对应实际请求 ID，数量相同不能代替。", path))
        # 集级总数门由逐段 keyframe_count_mismatch（含规划为 0 的段）与 keyframe_identity_mismatch 覆盖，不重复上报。
        for segment_id, planned_count in planned_keyframes.items():
            actual_count = actual_keyframes.get(segment_id, 0)
            if actual_count != planned_count:
                issues.append(issue("error", "keyframe_count_mismatch", f"{segment_id} 实际有效关键帧数量 {actual_count} 必须等于 storyboard.keyframe_requests 规划数量 {planned_count}。", path))
