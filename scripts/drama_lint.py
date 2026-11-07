#!/usr/bin/env python3
"""只读流程检查：结构、算术、依赖、源版本与授权；不证明摄影可达或审美。

源码位于 lint_checks；按码定位：python scripts/build_lint_contract.py --code <code>。
阶段入口与源码位置用 --stage <stage> 现场查询，维护模块目录用 --modules；按需读取定位到的完整模块或依赖。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from lint_checks.constants import EPISODE_STAGES, STAGES
from lint_checks.common import dedupe_issues, load_json
from lint_checks.state import check_operation_log_tools, check_state
from lint_checks.stages import (
    check_episode_directories, check_episode_entry_manifests, check_episode_manifest_ids,
    check_stage_artifacts,
)
from lint_checks.planning import check_plan_durations
from lint_checks.rhythm import RhythmLibrary, check_beat_library_desync
from lint_checks.storyboard import check_storyboards
from lint_checks.assets import blank_asset_index, check_assets
from lint_checks.keyframes import check_keyframes
from lint_checks.video import check_video
from lint_checks.delivery import check_delivery
from lint_checks.skill import check_skill_package


# Single stage dispatch consumed by execution and generated contracts.
STAGE_CHECKS = {
    "skill": ["check_skill_package", "check_beat_library_desync"],
    "common": ["check_plan_durations", "check_episode_directories", "check_episode_entry_manifests", "check_state", "check_operation_log_tools"],
    "planning": ["check_stage_artifacts"],
    "script": ["check_stage_artifacts", "check_episode_manifest_ids"],
    "assets": ["check_stage_artifacts", "check_episode_manifest_ids", "check_assets"],
    "storyboard": ["check_stage_artifacts", "check_episode_manifest_ids", "check_assets", "check_storyboards"],
    "keyframes": ["check_stage_artifacts", "check_episode_manifest_ids", "check_assets", "check_storyboards", "check_keyframes"],
    "video": ["check_stage_artifacts", "check_episode_manifest_ids", "check_assets", "check_storyboards", "check_keyframes", "check_video"],
    "final": ["check_stage_artifacts", "check_episode_manifest_ids", "check_assets", "check_storyboards", "check_keyframes", "check_video", "check_delivery"]
}


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
        check_skill_package(project_root, issues)
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
    asset_index = blank_asset_index()
    selected_checks = set().union(*(STAGE_CHECKS[stage] for stage in (STAGES if args.stage == "all" else (args.stage,))))
    if "check_assets" in selected_checks:
        asset_index = check_assets(project_root, issues, episode_filter)
    rhythm_lib: RhythmLibrary | None = None
    if "check_storyboards" in selected_checks:
        rhythm_lib = RhythmLibrary()
        rhythm_lib.ensure()
    if "check_storyboards" in selected_checks:
        check_storyboards(project_root, plan, issues, episode_filter, asset_index=asset_index, rhythm=rhythm_lib)
    if "check_keyframes" in selected_checks:
        check_keyframes(project_root, asset_index, issues, episode_filter)
    if "check_video" in selected_checks:
        check_video(
            project_root,
            asset_index,
            issues,
            episode_filter,
            require_accepted=args.stage in {"final", "all"},
        )
    if "check_delivery" in selected_checks:
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
