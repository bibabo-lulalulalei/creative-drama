"""展示前结构门：--pre-confirmation 只豁免时长合同对本次规划确认的回指。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import drama_lint  # noqa: E402
from drama_lint import check_plan_durations  # noqa: E402


def base_plan(*, pending_source: bool) -> dict:
    duration_contract = (
        {
            "mode": "unbounded",
            "scope": "project",
            "target_duration_s": None,
            "tolerance_ratio": None,
            "bounds": None,
            "source": "新制作，用户未限定时长。",
            "confirmation_ref": None,
        }
        if not pending_source
        else {
            "mode": "exact",
            "scope": "project",
            "target_duration_s": 75,
            "tolerance_ratio": None,
            "bounds": [75, 75],
            "source": "用户种子原文：做一个 75 秒的短片。",
            "confirmation_ref": None,
        }
    )
    return {
        "revision": 1,
        "selected_direction_id": "DIR001",
        "objective": {"target_stage": "video"},
        "creative_mechanism": {
            "selection_mode": "divergent",
            "candidates": [{"primary": "主机制：误会驱动的身份反转。", "supporting": []}],
            "primary": "主机制：误会驱动的身份反转。",
            "supporting": [],
        },
        "rhythm_design": {},
        "audience_plan": {
            "target_audience": "x",
            "core_pain_or_desire": "x",
            "platform": "x",
            "evidence_status": "assumed",
            "viewing_focus": "x",
            "emotional_payoff": "x",
            "platform_viewing_context": "x",
            "expression_boundaries": "x",
            "execution_sources": {
                "viewing_focus": "audience_plan.viewing_focus",
                "emotional_payoff": "audience_plan.emotional_payoff",
                "platform_viewing_context": "audience_plan.platform_viewing_context",
                "expression_boundaries": "audience_plan.expression_boundaries",
            },
        },
        "type_strategy": {
            "format": "x",
            "subject_route": "x",
            "genre": "x",
            "story_engine": "x",
            "audience_promise": "x",
            "narrative_structure": "x",
            "main_path": "x",
        },
        "highlight_strategy": {
            "primary_story_engine_id": "x",
            "project_signature": "x",
            "highlight_pillars": ["x"],
            "distribution_policy": "x",
            "rejected_cliches": ["x"],
        },
        "style_contract": {
            "anchor_type": "x",
            "anchor": "x",
            "lighting": "x",
            "color": "x",
            "composition": "x",
            "material": "x",
            "camera_tendency": "x",
            "sound_tendency": "x",
            "excluded_mechanisms": ["x"],
        },
        "duration_contract": duration_contract,
        "scale_plan": {
            "episode_count": 1,
            "episode_durations_s": [75],
            "episode_duration_displays": ["1分15秒"],
            "total_duration_s": 75,
            "total_duration_display": "75秒/1分15秒",
        },
        "delivery_settings": {
            "subtitle_enabled": False,
            "subtitle_policy": "disabled",
            "final_deliverables": ["clean_master"],
        },
    }


def codes(issues: list[dict]) -> set[str]:
    return {item["code"] for item in issues if item["level"] == "error"}


class PendingConfirmationUnitTests(unittest.TestCase):
    def test_exact_contract_pending_skips_only_confirmation_ref(self) -> None:
        issues: list[dict] = []
        with tempfile.TemporaryDirectory() as tmp:
            check_plan_durations(Path(tmp), base_plan(pending_source=True), issues, pending_confirmation=True)
        self.assertEqual(codes(issues), set())

    def test_exact_contract_without_pending_requires_record(self) -> None:
        issues: list[dict] = []
        with tempfile.TemporaryDirectory() as tmp:
            check_plan_durations(Path(tmp), base_plan(pending_source=True), issues)
        self.assertIn("duration_contract_source_invalid", codes(issues))
        self.assertIn("confirmation_log_missing", codes(issues))

    def test_pending_still_validates_bounds_and_enum(self) -> None:
        plan = base_plan(pending_source=True)
        plan["duration_contract"]["bounds"] = [70, 80]
        issues: list[dict] = []
        with tempfile.TemporaryDirectory() as tmp:
            check_plan_durations(Path(tmp), plan, issues, pending_confirmation=True)
        self.assertIn("duration_contract_invalid", codes(issues))

    def test_pending_does_not_waive_unbounded_rules(self) -> None:
        plan = base_plan(pending_source=False)
        plan["duration_contract"]["bounds"] = [1, 2]
        issues: list[dict] = []
        with tempfile.TemporaryDirectory() as tmp:
            check_plan_durations(Path(tmp), plan, issues, pending_confirmation=True)
        self.assertIn("duration_contract_unbounded_invalid", codes(issues))


def build_awaiting_project(root: Path) -> None:
    control = root / "00_制作控制"
    episodes = root / "episodes" / "ep_1"
    (control).mkdir(parents=True)
    (episodes).mkdir(parents=True)
    (control / "drama_plan.json").write_text(
        json.dumps(base_plan(pending_source=True), ensure_ascii=False), encoding="utf-8"
    )
    (control / "project_manifest.json").write_text("{}", encoding="utf-8")
    (control / "source_manifest.json").write_text(
        json.dumps({"sources": []}, ensure_ascii=False), encoding="utf-8"
    )
    state = {
        "revision": 1,
        "current_stage": "planning",
        "current_episode": "",
        "phases": {
            "planning": "awaiting_confirmation",
            "script": "pending",
            "assets": "pending",
            "storyboard": "pending",
            "keyframes": "pending",
            "video": "pending",
            "final": "pending",
        },
        "episodes": {
            "ep_1": {
                "stage_status": {
                    "script": "pending",
                    "assets": "pending",
                    "storyboard": "pending",
                    "keyframes": "pending",
                    "video": "pending",
                    "final": "pending",
                }
            }
        },
    }
    (control / "制作状态.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    (episodes / "episode_manifest_ep_1.json").write_text(
        json.dumps(
            {
                "episode_id": "ep_1",
                "stage_manifests": {
                    "script": "episodes/ep_1/01_剧本/script_contract_ep_1.json",
                    "storyboard": "episodes/ep_1/02_分镜/storyboard_ep_1.json",
                    "assets": "episodes/ep_1/03_资产/asset_usage_ep_1.json",
                    "keyframes": "episodes/ep_1/03_资产/keyframe_manifest_ep_1.json",
                    "video": "episodes/ep_1/04_视频片段/video_manifest_ep_1.json",
                    "continuity": "episodes/ep_1/04_视频片段/continuity_ep_1.json",
                    "delivery": "episodes/ep_1/05_成片/delivery_manifest_ep_1.json",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


class PreConfirmationCliTests(unittest.TestCase):
    def test_awaiting_project_passes_only_with_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_awaiting_project(root)
            self.assertEqual(
                drama_lint.main(["--project-root", str(root), "--stage", "planning", "--pre-confirmation"]),
                0,
            )
            self.assertEqual(
                drama_lint.main(["--project-root", str(root), "--stage", "planning"]),
                1,
            )

    def test_flag_rejected_for_other_stages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                drama_lint.main(
                    ["--project-root", tmp, "--stage", "script", "--pre-confirmation"]
                )


if __name__ == "__main__":
    unittest.main()
