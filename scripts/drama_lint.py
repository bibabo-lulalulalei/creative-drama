#!/usr/bin/env python3
"""只读流程检查：结构、算术、依赖、源版本与授权；不证明摄影可达或审美。

源码位于 lint_checks；按码定位：python scripts/build_lint_contract.py --code <code>。
模块小字典见 references/lint-contract/source-index.md；按需读取定位到的完整模块或依赖。
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
import re
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from timeline_core import to_ms
from content_first import reconcile_storyboard, read_json, source_index_from_contract
from video_confirmations import validate_confirmations
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/video"))
from h3_contract import prepare_request, check_purity, ContractError, is_url, media_marker_orders, CAPABILITIES

# Preserve existing imports while checks live in focused modules.
from lint_checks.constants import (
    STAGES, EPISODE_STAGES, STATUS_VALUES, ASSET_STATUS_VALUES, VISUAL_REFERENCE_DECISIONS,
    PROJECT_VISUAL_MODES, VIDEO_STATUS_VALUES, VIDEO_TOOL_MODES, IMAGE_GENERATION_TOOLS,
    FORBIDDEN_TOOL_TERMS, SKILL_SCRIPTS_DIR, BEAT_LIBRARY_JSON_PATH, BEAT_LIBRARY_MD_PATH,
    H3_CAPABILITY_PATH, CUT_MOTIVATIONS, REFERENCE_ROLES, VIDEO_INPUT_ROLES, AUDIO_INPUT_ROLES,
    STATE_REFERENCE_ROLES, ASSET_PREFIX_BY_CATEGORY,
    CURRENT_STAGE_ACTIVE_VALUES, CONFIRMATION_MODES, IMAGE_INPUT_SUFFIXES, ISO_TIME_PATTERN,
    ASSET_ID_PATTERN, ASSET_ROLE_COMPATIBILITY, WORLD_FACT_CATEGORIES, BEAT_DISPOSITIONS,
    CAUSAL_ROLES, CAUSAL_REF_TYPES, EVIDENCE_VISIBILITIES, BREAKPOINT_RISKS,
)
from lint_checks.common import (
    issue, load_json, relative_file, file_exists, media_location_valid, parse_iso_time,
    file_sha256, nonempty_strings, has_meaningful_value, combined_strings,
    check_style_anchor_contract, check_generation_prompt_file, file_inside,
    expected_duration_display, expected_total_duration_display, check_duration_pair, check_unique,
    manifest_path, plan_revision, target_stage,
    episode_dirs, read_text_file, markdown_table_column_counts, dedupe_issues,
)
from lint_checks.state import (
    load_confirmation_records, check_operation_log_tools, has_confirmation, check_state,
)
from lint_checks.stages import (
    check_episode_directories, check_episode_manifest_ids, check_episode_entry_manifests,
    check_stage_artifacts,
)
from lint_checks.planning import check_plan_durations, duration_contract_bounds
from lint_checks.rhythm import (
    RhythmLibrary, check_beat_library_desync, check_segment_shot_count,
    check_keyframe_request_plan, check_episode_keyframe_request_plan, check_shot_rhythm_fields,
    check_rhythm_reconciliation,
)
from lint_checks.storyboard import (
    load_storyboard_index, check_storyboards, check_reference_plan, parse_planned_source_asset,
    check_asset_usage_reconciliation,
)
from lint_checks.causal import (
    check_world_facts, check_beat_coverage, collect_data_card_state_ids,
    validate_collective_profiles, validate_causal_ref, seam_invariant_cell, check_causal_ledger,
)
from lint_checks.assets import (
    asset_version_key, version_rank, split_asset_version_ref, blank_asset_index,
    remember_asset_version, state_ref_keys, remember_state_version, check_stale_asset_version,
    check_voice_sample, check_reused_voice_sample, check_assets,
)
from lint_checks.prompts import (
    ordered_inputs, check_asset_ref, check_state_ref, load_keyframe_ids, marker_pattern,
    extract_subject_marker_orders, check_prompt_markers, check_h3_prompt, check_video_state_refs,
    _check_h3_prompt_purity, check_video_generation_confirmations, check_voice_audio_inputs,
    check_voice_anchor_consistency, check_prompt_preflight,
)
from lint_checks.keyframes import check_keyframes
from lint_checks.video import check_video, check_quality_acceptance
from lint_checks.delivery import (
    accepted_video_segment_order, delivery_segment_refs, output_values, report_is_blocked,
    check_report_entries, check_continuity_for_delivery, check_delivery, check_adopted_delivery,
)
from lint_checks.skill import _reference_targets, anchor_heading_count, check_skill_package


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
    parser.add_argument("--fix", action="store_true", help="has no effect; validation never modifies project files")
    parser.add_argument("--changed-file", action="append", default=[], help="has no effect; the selected stage is checked in full")
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
    expected_durations = check_plan_durations(project_root, plan, issues)
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
