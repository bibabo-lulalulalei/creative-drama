from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import context_checkpoint


class ContextCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "00_制作控制").mkdir()
        (self.root / "episodes" / "ep_1" / "03_资产").mkdir(parents=True)
        (self.root / "episodes" / "ep_1" / "02_分镜").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, relative: str, value: object):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def write_jsonl(self, relative: str, values: list[dict]):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(value, ensure_ascii=False) for value in values) + "\n", encoding="utf-8")

    def write_project(self, stage: str, phase: str, *, lint_report: str | None = None):
        self.write_json("00_制作控制/制作状态.json", {
            "project_id": "P001",
            "revision": 4,
            "current_stage": stage,
            "current_episode": None if stage == "planning" else "ep_1",
            "phases": {stage: phase},
            "episodes": {
                "ep_1": {
                    "manifest": "episodes/ep_1/episode_manifest_ep_1.json",
                    "stage_status": {stage: phase},
                }
            },
            "last_successful_operation": "op-004",
        })
        self.write_json("00_制作控制/drama_plan.json", {
            "project_id": "P001",
            "revision": 3,
            "objective": {"target_stage": "video"},
        })
        self.write_json("episodes/ep_1/episode_manifest_ep_1.json", {
            "project_id": "P001",
            "episode_id": "ep_1",
            "revision": 2,
            "stage_manifests": {
                "script": "episodes/ep_1/01_剧本/script_contract_ep_1.json",
                "assets": "episodes/ep_1/03_资产/asset_usage_ep_1.json",
                "storyboard": "episodes/ep_1/02_分镜/storyboard_ep_1.json",
            },
        })
        self.write_json("episodes/ep_1/01_剧本/script_contract_ep_1.json", {"revision": 6})
        self.write_json("episodes/ep_1/03_资产/asset_usage_ep_1.json", {
            "episode_id": "ep_1", "revision": 7, "shared_assets": []
        })
        self.write_json("episodes/ep_1/02_分镜/storyboard_ep_1.json", {
            "episode_id": "ep_1", "revision": 8, "shots": []
        })
        records = [
            {"stage": "planning", "episode_id": "", "revision": 1,
             "decision": "confirmed", "confirmation_id": "PLAN-1",
             "user_message": "用户真实确认规划", "valid": True},
        ]
        previous_scopes = {
            "script": ("script", ""),
            "assets": ("script", "ep_1"),
            "storyboard": ("assets", "ep_1"),
            "keyframes": ("storyboard", "ep_1"),
            "video": ("keyframes", "ep_1"),
            "final": ("video", "ep_1"),
        }
        if stage in previous_scopes:
            previous_stage, previous_episode = previous_scopes[stage]
            records.append({
                "stage": previous_stage, "episode_id": previous_episode,
                "revision": 6, "decision": "confirmed",
                "confirmation_id": f"{previous_stage.upper()}-UPSTREAM",
                "user_message": "用户真实确认上一阶段", "valid": True,
            })
        records.extend([
            {"stage": stage, "episode_id": "ep_1", "revision": 7,
             "decision": "pending", "confirmation_id": "OLD-NOT-AUTH",
             "user_message": "这段不应成为授权"},
            {"stage": stage, "episode_id": "ep_1", "revision": 8,
             "decision": "confirmed", "confirmation_id": f"{stage.upper()}-1",
             "user_message": "用户真实确认当前阶段", "valid": True},
        ])
        self.write_jsonl("00_制作控制/用户确认记录.jsonl", records)
        self.write_jsonl("00_制作控制/操作日志.jsonl", [
            {"operation_id": "op-004", "stage": stage, "status": "succeeded",
             "timestamp": "2026-11-06T10:00:00+08:00",
             "recovery_action": "继续当前阶段"},
        ])
        if lint_report:
            self.write_json(lint_report, {
                "lint": {"issues": [{"level": "error", "code": "asset_missing"}], "release_ready": False}
            })

    def test_planning_checkpoint_is_compact_and_keeps_only_authorization_ids(self):
        self.write_project("planning", "in_progress")
        checkpoint = context_checkpoint.build_checkpoint(self.root)

        self.assertEqual(checkpoint["current_stage"], "planning")
        self.assertIsNone(checkpoint["current_episode"])
        self.assertEqual(checkpoint["target_stage"], "video")
        self.assertEqual(checkpoint["context"], {
            "ledger": "00_制作控制/上下文账本.json", "events": "00_制作控制/上下文事件.jsonl",
        })
        self.assertEqual([item["id"] for item in checkpoint["authorization_ids"]], ["PLAN-1"])
        self.assertNotIn("用户真实确认规划", context_checkpoint.format_checkpoint(checkpoint))
        self.assertLess(len(context_checkpoint.format_checkpoint(checkpoint)), 4000)

    def test_assets_checkpoint_reports_error_code_and_current_manifest(self):
        self.write_project("assets", "in_progress", lint_report="00_制作控制/lint_assets.json")
        checkpoint = context_checkpoint.build_checkpoint(self.root, lint_report="00_制作控制/lint_assets.json")

        self.assertEqual(checkpoint["current_episode"], "ep_1")
        self.assertEqual(checkpoint["lint"]["error_codes"], ["asset_missing"])
        self.assertIn("asset_missing", checkpoint["next_action"])
        self.assertTrue(any(item["path"].endswith("asset_usage_ep_1.json") for item in checkpoint["artifacts"]))
        self.assertEqual([item["id"] for item in checkpoint["authorization_ids"]], ["ASSETS-1", "PLAN-1"])
        self.assertEqual(checkpoint["handoff"]["confirmation_id"], "SCRIPT-UPSTREAM")
        self.assertEqual(checkpoint["handoff"]["from_stage"], "script")
        self.assertIn("script_contract_ep_1.json", checkpoint["handoff"]["artifact"]["path"])

    def test_handoff_uses_previous_confirmed_stage_not_current_or_invalidated_record(self):
        self.write_project("storyboard", "in_progress")
        records = [
            {"stage": "assets", "episode_id": "ep_1", "decision": "confirmed",
             "confirmation_id": "OLD-ASSET", "valid": False, "revision": 2},
            {"stage": "assets", "episode_id": "ep_1", "decision": "confirmed",
             "confirmation_id": "ASSET-OK", "valid": True, "revision": 3},
            {"stage": "storyboard", "episode_id": "ep_1", "decision": "confirmed",
             "confirmation_id": "CURRENT", "valid": True, "revision": 4},
        ]

        handoff = context_checkpoint._handoff_confirmation(records, "storyboard", "ep_1")

        self.assertEqual(handoff["confirmation_id"], "ASSET-OK")
        self.assertEqual(handoff["from_stage"], "assets")
        self.assertEqual(handoff["to_stage"], "storyboard")

    def test_project_story_package_handoff_points_to_project_script_manifest(self):
        self.write_project("script", "in_progress")
        state_path = self.root / "00_制作控制/制作状态.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["current_episode"] = None
        state_path.write_text(json.dumps(state), encoding="utf-8")
        (self.root / "01_剧本").mkdir()
        self.write_json("01_剧本/project_script_manifest.json", {"revision": 5})

        checkpoint = context_checkpoint.build_checkpoint(self.root)

        self.assertEqual(checkpoint["handoff"]["confirmation_id"], "PLAN-1")
        self.assertEqual(checkpoint["handoff"]["artifact"]["path"], "00_制作控制/drama_plan.json")
        self.assertTrue(any(item["path"] == "01_剧本/project_script_manifest.json" for item in checkpoint["artifacts"]))

    def test_episode_script_handoff_points_to_confirmed_project_story_package(self):
        self.write_project("script", "in_progress")
        (self.root / "01_剧本").mkdir()
        self.write_json("01_剧本/project_script_manifest.json", {"revision": 5})

        checkpoint = context_checkpoint.build_checkpoint(self.root)

        self.assertEqual(checkpoint["handoff"]["confirmation_id"], "SCRIPT-UPSTREAM")
        self.assertEqual(checkpoint["handoff"]["from_stage"], "script")
        self.assertIsNone(checkpoint["handoff"]["from_episode_id"])
        self.assertEqual(checkpoint["handoff"]["artifact"]["path"], "01_剧本/project_script_manifest.json")

    def test_storyboard_waiting_confirmation_and_hash_change_hint(self):
        self.write_project("storyboard", "awaiting_confirmation")
        first = context_checkpoint.build_checkpoint(self.root)
        storyboard = self.root / "episodes/ep_1/02_分镜/storyboard_ep_1.json"
        storyboard.write_text('{"episode_id":"ep_1","revision":9,"shots":[{"shot_id":"SHOT001"}]}', encoding="utf-8")

        second = context_checkpoint.build_checkpoint(self.root, previous=first)

        self.assertIn("等待用户确认", second["next_action"])
        self.assertIn("需要用户确认", second["required_user_action"])
        self.assertTrue(any(item["path"].endswith("storyboard_ep_1.json") for item in second["changes"]))
        self.assertNotIn("OLD-NOT-AUTH", context_checkpoint.format_checkpoint(second))

    def test_missing_optional_files_are_warnings_and_do_not_abort_checkpoint(self):
        self.write_project("planning", "in_progress")
        (self.root / "00_制作控制/操作日志.jsonl").unlink()

        checkpoint = context_checkpoint.build_checkpoint(self.root)

        self.assertTrue(any(item.startswith("missing:00_制作控制/操作日志.jsonl") for item in checkpoint["read_warnings"]))
        self.assertIsNone(checkpoint["last_operation"])


if __name__ == "__main__":
    unittest.main()
