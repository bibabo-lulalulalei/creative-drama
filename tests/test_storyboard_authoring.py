"""Execute the documented authoring inputs through the real offline rhythm CLI."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
ENGINE = SKILL_ROOT / "scripts/rhythm_engine.py"


def documented_input(heading):
    text = (SKILL_ROOT / "references/manifests.md").read_text(encoding="utf-8")
    section = text.split(heading + "\n", 1)[1].split("\n### ", 1)[0]
    return json.loads(re.search(r"```json\n(.*?)\n```", section, re.S)[1])


class StoryboardAuthoringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="storyboard_authoring_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = "episodes/ep_1"
        self.sb_file = f"{self.base}/02_分镜/storyboard_ep_1.json"
        self.timing_file = f"{self.base}/02_分镜/rhythm_input_ep_1.json"
        self.manifest_file = f"{self.base}/episode_manifest_ep_1.json"
        self.script_file = f"{self.base}/01_剧本/剧本_完整剧本_ep_1.md"
        self.contract_file = f"{self.base}/01_剧本/script_contract_ep_1.json"
        self.storyboard = documented_input("### storyboard_ep_N.json")
        self.timing = documented_input("### rhythm_input_ep_N.json")
        self.write(self.script_file, "## E01S01 门边\n人物抬手示意。\nCHR001：留在这里。\n听者停在门边。\n")
        self.write(self.contract_file, {
            "episode_id": "ep_1", "revision": 1, "source_markdown": self.script_file,
            "source_sha256": self.sha(self.script_file),
            "scenes": [{"scene_id": "E01S01", "events": [
                {"event_id": "B001", "source_excerpt": "人物抬手示意。", "summary": "人物抬手示意"},
                {"event_id": "B002", "source_excerpt": "听者停在门边。", "summary": "听者停在门边"}],
                "speech_lines": [{"line_id": "LINE001", "speaker": "CHR001", "source_text": "留在这里。"}]}],
        })
        self.timing["source_script"]["sha256"] = self.sha(self.contract_file)
        self.write("00_制作控制/用户确认记录.jsonl", json.dumps({
            "stage": "script", "episode_id": "ep_1", "decision": "confirmed", "revision": 1,
            "confirmation_id": "CONF-TEST-SOURCE", "user_message": "测试夹具的源剧本确认",
            "source_snapshot": copy.deepcopy(self.timing["source_script"]),
        }, ensure_ascii=False) + "\n")
        self.write("00_制作控制/drama_plan.json", {"revision": 1, "initial_estimate_s": 120})
        self.write(self.manifest_file, {"episode_id": "ep_1", "planning_estimate_s": 120})
        self.write(self.storyboard["director_control_card"], "# 导演总控卡\n让手势和听者目光在切镜前相接。\n")
        headers = ["场次", "视频片段", "镜号", "镜头职责", "时长", "画面描述", "景别", "机位",
                   "光影", "对白", "音效", "摄影过程", "切入切出", "连续性", "承接"]
        rows = [
            ["E01S01", "待分组", "E01S01-SHOT001", "发出挽留", "待核算", "人物抬手示意", "中景", "眼平",
             "沿用场景光", "LINE001 留在这里。", "衣袖声", "沿视线缓推", "视线切", "手势保持", "听者目光"],
            ["E01S01", "待分组", "E01S01-SHOT002", "接住挽留", "待核算", "听者停在门边", "近景", "眼平",
             "沿用场景光", "无", "环境声", "横移停稳", "目光承接", "方向保持", "注视继续"],
        ]
        self.original_rows = rows
        self.write(self.storyboard["source_markdown"],
                   "| " + " | ".join(headers) + " |\n|" + "---|" * 15 + "\n" +
                   "".join("| " + " | ".join(row) + " |\n" for row in rows))
        self.write(self.sb_file, self.storyboard)
        self.write(self.timing_file, self.timing)

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    def read(self, relative):
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def sha(self, relative):
        return hashlib.sha256((self.root / relative).read_bytes()).hexdigest()

    def command(self, name, *, ok=True):
        completed = subprocess.run([
            sys.executable, str(ENGINE), name, "--project-root", str(self.root),
            "--input", str(self.root / self.timing_file),
            "--storyboard", str(self.root / self.sb_file), "--write",
        ], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0 if ok else 2, completed.stdout + completed.stderr)
        receipt = json.loads(completed.stdout)
        self.assertEqual(receipt["ok"], ok)
        return receipt

    def test_documented_inputs_derive_times_and_preserve_actual_design(self):
        plan_before = (self.root / "00_制作控制/drama_plan.json").read_bytes()
        input_before = (self.root / self.timing_file).read_bytes()
        allocation = self.command("allocate")
        packed = self.command("pack")
        self.assertEqual(allocation["total_s"], 5.5)
        self.assertEqual(allocation["shot_count"], 2)
        self.assertNotIn("shots", allocation)
        self.assertNotIn("segments", packed)
        storyboard = self.read(self.sb_file)
        self.assertEqual(storyboard["duration_s"], 5.5)
        self.assertEqual([row["time_range_s"] for row in storyboard["shots"]], [[0, 3.25], [3.25, 5.5]])
        for original, computed in zip(self.storyboard["shots"], storyboard["shots"]):
            for key, value in original.items():
                self.assertEqual(computed[key], value)
            self.assertTrue(computed["timing_events"])
            self.assertEqual(computed["duration_basis"]["duration_s"], computed["duration_s"])
        segment = storyboard["segments"][0]
        self.assertEqual((segment["duration_s"], segment["request_duration_s"], segment["tail_handle_s"]), (5.5, 6, 0.5))
        self.assertEqual(segment["shot_ids"], [row["shot_id"] for row in storyboard["shots"]])
        self.assertEqual([row["segment_id"] for row in storyboard["shots"]], [segment["segment_id"]] * 2)
        self.assertEqual(len(segment["design_sha256"]), 64)
        self.assertEqual(self.read(self.manifest_file)["planned_content_duration_s"], 5.5)
        self.assertEqual(self.read(self.manifest_file)["planning_estimate_s"], 120)
        self.assertEqual((self.root / "00_制作控制/drama_plan.json").read_bytes(), plan_before)
        self.assertEqual((self.root / self.timing_file).read_bytes(), input_before)
        text = (self.root / self.storyboard["source_markdown"]).read_text(encoding="utf-8")
        rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
                for line in text.splitlines() if "E01S01-SHOT" in line]
        self.assertEqual([row[4] for row in rows], ["00:00–00:03.250（3.25s）", "00:03.250–00:05.500（2.25s）"])
        for original, rendered in zip(self.original_rows, rows):
            self.assertEqual(rendered[1], segment["segment_id"])
            self.assertEqual(original[:1] + original[2:4] + original[5:],
                             rendered[:1] + rendered[2:4] + rendered[5:])
        # Design the real SEG after pack, then verify an unchanged pack preserves it.
        segment.update(shot_mode="edited", tail_mode="cuttable_completion", reference_input_plan=[],
                       density_rationale="两镜交换观看关系，不补反应镜")
        self.write(self.sb_file, storyboard)
        repeat = self.command("pack")
        self.assertEqual(repeat["invalidated_segments"], [])
        self.assertEqual(self.read(self.sb_file), dict(storyboard, asset_usage_plan=[]))

    def test_source_drift_rejects_writes_instead_of_ignoring_confirmation(self):
        self.timing["source_script"]["sha256"] = "0" * 64
        self.write(self.timing_file, self.timing)
        files = [self.sb_file, self.storyboard["source_markdown"], self.manifest_file]
        before = {relative: (self.root / relative).read_bytes() for relative in files}
        failed = self.command("allocate", ok=False)
        self.assertIn("source_revision_mismatch", {row["code"] for row in failed["issues"]})
        self.assertEqual({relative: (self.root / relative).read_bytes() for relative in files}, before)

    def test_over_capacity_group_is_not_automatically_cut_or_shortened(self):
        self.timing["scenes"][0]["shots"][0]["timeline"][0]["duration_s"] = 20
        self.write(self.timing_file, self.timing)
        self.command("allocate")
        before = (self.root / self.sb_file).read_bytes()
        failed = self.command("pack", ok=False)
        self.assertIn("tool_duration_unrepresentable", {row["code"] for row in failed["issues"]})
        self.assertEqual((self.root / self.sb_file).read_bytes(), before)
        self.assertEqual(self.read(self.sb_file)["duration_s"], 22.25)
        self.assertEqual(self.read(self.timing_file)["scenes"][0]["shots"][0]["timeline"][0]["duration_s"], 20)


if __name__ == "__main__":
    unittest.main()
