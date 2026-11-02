"""Episode directories, manifest identity and required stage artifacts."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from content_first import source_index_from_contract
from .common import (
    episode_dirs, file_sha256, issue, load_json, manifest_path,
    relative_file,
)


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
            "continuity": f"episodes/{episode_id}/04_视频片段/continuity_{episode_id}.json",
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
                episode_root / f"02_分镜/分镜_阅读稿_{episode_id}.md",
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
                issues.append(issue("error", "source_revision_mismatch", "源剧本正文 SHA 不符。", contract_path))
            else:
                found = []
                source_index_from_contract(contract, source.read_text(encoding="utf-8-sig"), found)
                issues.extend(dict(row, path=str(contract_path)) for row in found)
