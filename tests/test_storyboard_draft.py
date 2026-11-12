"""Exercise scene persistence and complete assembly using real source contracts."""
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
import wave


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import storyboard_draft as draft


class StoryboardDraftTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="storyboard_draft_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.base = "episodes/ep_1/02_分镜"
        self.script = "episodes/ep_1/01_剧本/剧本_完整剧本_ep_1.md"
        self.contract_path = "episodes/ep_1/01_剧本/script_contract_ep_1.json"
        self.contract = {"episode_id": "ep_1", "revision": 1, "source_markdown": self.script,
                         "scenes": []}
        self.write(self.script, "## E01S01 门外\n抬手。\nCHR001：留下。\n"
                                "## E01S02 门内\n转身。\nCHR002：走吧。\n")
        self.contract["source_sha256"] = self.sha(self.script)
        for number, action, line in ((1, "抬手。", "留下。"), (2, "转身。", "走吧。")):
            self.contract["scenes"].append({
                "scene_id": f"E01S0{number}",
                "events": [{"event_id": f"B00{number}", "source_excerpt": action, "summary": action}],
                "speech_lines": [{"line_id": f"LINE00{number}", "speaker": f"CHR00{number}", "source_text": line}],
            })
        self.bind_source()
        self.write(f"{self.base}/导演总控卡_ep_1.md", "# 导演总控卡\n保留人物关系与光位。\n")
        self.write("00_制作控制/制作状态.json", {"current_stage": "storyboard", "status": "working"})
        self.write("episodes/ep_1/episode_manifest_ep_1.json", {"planning_estimate_s": 120})

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    def read(self, relative):
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def sha(self, relative):
        return hashlib.sha256((self.root / relative).read_bytes()).hexdigest()

    def bind_source(self):
        self.write(self.contract_path, self.contract)
        self.binding = {"file": self.contract_path, "revision": self.contract["revision"],
                        "sha256": self.sha(self.contract_path)}
        self.write("00_制作控制/用户确认记录.jsonl", json.dumps({
            "stage": "script", "episode_id": "ep_1", "decision": "confirmed",
            "revision": self.contract["revision"], "confirmation_id": "CONF-TEST-SOURCE",
            "user_message": "测试源剧本确认", "source_snapshot": self.binding,
        }, ensure_ascii=False) + "\n")

    def payload(self, number):
        scene, shot = f"E01S0{number}", f"E01S0{number}-SHOT001"
        headers = ["场次", "视频片段", "镜号", "镜头职责", "时长", "画面描述", "景别", "机位",
                   "光影", "对白", "音效", "摄影过程", "切入切出", "连续性", "承接"]
        cells = [scene, "待分组", shot, "视线交换", "待核算", "人物动作保留全部原文", "中景", "眼平",
                 "窗外柔光", f"LINE00{number}", "现场声", "前推后停", "视线切", "手势延续", "目光接力"]
        return {"source_script": copy.deepcopy(self.binding),
                "storyboard": {"shots": [{"scene_id": scene, "shot_id": shot,
                    "visual_description": "完整构图和摄影设计", "creative_extension": {"keep": ["原文", "不裁剪"]}}],
                    "beat_coverage": [{"beat_id": f"B00{number}", "disposition": "kept", "target_shots": [shot]}]},
                "rhythm_input": {"utterances": [{"utterance_id": f"U00{number}", "line_id": f"LINE00{number}",
                    "speaker_ref": f"CHR00{number}", "estimated_duration_s": 2,
                    "timing_basis": {"method": "director_estimate", "note": "按本场具体表演演读"}}],
                    "scenes": [{"scene_id": scene, "shots": [{"shot_id": shot, "timeline": [
                        {"event_id": f"V00{number}", "kind": "visual", "process": "完整动作过程",
                         "source_refs": [f"beat:B00{number}"], "start_s": 0, "duration_s": 2},
                        {"event_id": f"S00{number}", "kind": "speech", "utterance_id": f"U00{number}",
                         "utterance_offset_s": 0, "start_s": 0, "duration_s": 2}]}], "beat_groups": []}]},
                "markdown": "| " + " | ".join(headers) + " |\n|" + "---|" * 15 + "\n| " + " | ".join(cells) + " |\n"}

    def save(self, number, payload=None):
        return draft.save_scene(self.root, "ep_1", f"E01S0{number}", payload or self.payload(number))

    def standards(self):
        return [self.root / self.base / name for name in
                ("storyboard_ep_1.json", "rhythm_input_ep_1.json", "分镜_完整分镜表_ep_1.md")]

    def test_save_preserves_creative_work_without_publishing_episode(self):
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        payload = self.payload(1)
        receipt = self.save(1, payload)
        saved = self.read(f"{self.base}/.draft/E01S01.json")
        self.assertEqual(saved["storyboard"], payload["storyboard"])
        self.assertEqual(saved["markdown"], payload["markdown"])
        self.assertEqual(saved["rhythm_input"]["scenes"], payload["rhythm_input"]["scenes"])
        self.assertTrue(receipt["pending_global_reconciliation"])
        self.assertNotIn("scene_duration_s", receipt)
        self.assertEqual(receipt["progress"]["next_scene_id"], "E01S02")
        self.assertTrue(all(not path.exists() for path in self.standards()))
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_assembly_preserves_order_fields_annotations_and_original_control(self):
        state_path = self.root / "00_制作控制/制作状态.json"
        manifest_path = self.root / "episodes/ep_1/episode_manifest_ep_1.json"
        card_path = self.root / self.base / "导演总控卡_ep_1.md"
        before = [path.read_bytes() for path in (state_path, manifest_path, card_path)]
        inputs = [self.payload(1), self.payload(2)]
        for number, payload in enumerate(inputs, 1):
            payload["rhythm_input"]["note"] = "全局演读原则"
            self.save(number, payload)
        self.assertTrue(draft.describe_progress(self.root, "ep_1", self.binding, ["E01S01", "E01S02"])["ready_to_assemble"])
        receipt = draft.assemble(self.root, "ep_1")
        self.assertTrue(receipt["ok"])
        board, rhythm = [json.loads(path.read_text(encoding="utf-8")) for path in self.standards()[:2]]
        self.assertEqual(board["shots"], inputs[0]["storyboard"]["shots"] + inputs[1]["storyboard"]["shots"])
        self.assertEqual(rhythm["note"], "全局演读原则")
        self.assertEqual(self.standards()[2].read_text(encoding="utf-8"), "\n\n".join(item["markdown"] for item in inputs))
        self.assertNotIn("duration_s", board)
        self.assertNotIn("content_review", board)
        self.assertEqual(board["segments"], [])
        self.assertEqual([path.read_bytes() for path in (state_path, manifest_path, card_path)], before)

    def test_missing_or_changed_source_never_assembles(self):
        self.save(1)
        with self.assertRaises(draft.DraftError):
            draft.assemble(self.root, "ep_1")
        self.save(2)
        self.contract["revision"] = 2
        self.bind_source()
        progress = draft.describe_progress(self.root, "ep_1", self.binding, ["E01S01", "E01S02"])
        self.assertEqual(progress["stale_scene_ids"], ["E01S01", "E01S02"])
        with self.assertRaises(draft.DraftError):
            draft.assemble(self.root, "ep_1")
        self.assertTrue(all(not path.exists() for path in self.standards()))

    def test_source_confirmation_and_real_reference_are_required_at_save(self):
        payload = self.payload(1)
        payload["rhythm_input"]["scenes"][0]["shots"][0]["timeline"][0]["source_refs"] = ["beat:INVENTED"]
        with self.assertRaises(draft.DraftError):
            self.save(1, payload)
        (self.root / "00_制作控制/用户确认记录.jsonl").unlink()
        with self.assertRaises(draft.DraftError):
            self.save(1)
        self.assertFalse((self.root / self.base / ".draft").exists())

    def test_duplicate_event_ids_across_scenes_are_rejected(self):
        self.save(1)
        payload = self.payload(2)
        payload["rhythm_input"]["scenes"][0]["shots"][0]["timeline"][0]["event_id"] = "V001"
        with self.assertRaisesRegex(draft.DraftError, "event ID"):
            self.save(2, payload)
        self.assertFalse((self.root / self.base / ".draft/E01S02.json").exists())

    def test_moved_beat_and_cross_scene_after_are_preserved_then_reconciled(self):
        first, second = self.payload(1), self.payload(2)
        first["storyboard"]["beat_coverage"][0].update(disposition="moved", target_shots=["E01S02-SHOT001"])
        first["rhythm_input"]["scenes"][0]["shots"][0]["timeline"][0]["source_refs"] = []
        event = second["rhythm_input"]["scenes"][0]["shots"][0]["timeline"][0]
        event["source_refs"].append("beat:B001")
        event["after"] = ["V001"]
        self.save(1, first)
        self.save(2, second)
        draft.assemble(self.root, "ep_1")
        board = json.loads(self.standards()[0].read_text(encoding="utf-8"))
        for key, value in first["storyboard"]["beat_coverage"][0].items():
            self.assertEqual(board["beat_coverage"][0][key], value)
        self.assertEqual(board["beat_coverage"][0]["scene"], "E01S01")

    def test_cross_scene_utterance_fragments_share_one_definition(self):
        first, second = self.payload(1), self.payload(2)
        shared = copy.deepcopy(first["rhythm_input"]["utterances"][0])
        shared["estimated_duration_s"] = 4
        first["rhythm_input"]["utterances"] = [shared]
        second["rhythm_input"]["utterances"].append(copy.deepcopy(shared))
        second["rhythm_input"]["scenes"][0]["shots"][0]["timeline"].append({
            "event_id": "S-CONT", "kind": "speech", "utterance_id": "U001", "utterance_offset_s": 2,
            "start_s": 0, "duration_s": 2})
        self.save(1, first)
        self.save(2, second)
        draft.assemble(self.root, "ep_1")
        rhythm = json.loads(self.standards()[1].read_text(encoding="utf-8"))
        self.assertEqual(sum(row["utterance_id"] == "U001" for row in rhythm["utterances"]), 1)

    def test_incomplete_coverage_and_external_dependency_fail_only_at_assembly(self):
        payload = self.payload(1)
        payload["storyboard"]["beat_coverage"] = []
        payload["rhythm_input"]["scenes"][0]["shots"][0]["timeline"][0]["after"] = ["NEVER-CREATED"]
        self.save(1, payload)
        self.save(2)
        with self.assertRaises(draft.DraftError):
            draft.assemble(self.root, "ep_1")
        self.assertTrue(all(not path.exists() for path in self.standards()))

    def test_existing_standard_files_are_never_overwritten(self):
        self.save(1)
        self.save(2)
        self.write(f"{self.base}/分镜_完整分镜表_ep_1.md", "已有真实候选")
        progress = draft.describe_progress(self.root, "ep_1", self.binding, ["E01S01", "E01S02"])
        self.assertEqual(progress["next_action"], "resume_standard")
        with self.assertRaises(draft.DraftError):
            draft.assemble(self.root, "ep_1")
        self.assertEqual(self.standards()[2].read_text(encoding="utf-8"), "已有真实候选")
        self.assertFalse(self.standards()[0].exists())

    def test_escape_cross_episode_invalid_shape_and_published_fields_reject(self):
        for mutate in (
                lambda value: value["storyboard"].update(source_markdown="../outside.md"),
                lambda value: value["storyboard"].update(director_control_card="episodes/ep_2/02_分镜/card.md"),
                lambda value: value["rhythm_input"].update(episode_id="ep_2"),
                lambda value: value["rhythm_input"]["scenes"].__setitem__(0, []),
                lambda value: value["storyboard"].update(duration_s=30),
                lambda value: value["rhythm_input"]["scenes"][0].update(beat_groups=["invalid"])):
            payload = self.payload(1)
            mutate(payload)
            with self.assertRaises(ValueError):
                self.save(1, payload)
        self.assertFalse((self.root / self.base / ".draft").exists())

    def test_conflicting_global_annotations_refuse_silent_loss(self):
        for number in (1, 2):
            payload = self.payload(number)
            payload["rhythm_input"]["note"] = f"不同的全局原则{number}"
            self.save(number, payload)
        with self.assertRaisesRegex(draft.DraftError, "rhythm_input.note"):
            draft.assemble(self.root, "ep_1")
        self.assertTrue(all(not path.exists() for path in self.standards()))

    def test_cli_receipt_is_small_and_scene_local(self):
        self.write("candidate.json", self.payload(1))
        completed = subprocess.run([sys.executable, "-B", str(SKILL_ROOT / "scripts/storyboard_draft.py"),
            "save", "--project-root", str(self.root), "--episode", "ep_1", "--scene", "E01S01",
            "--input", "candidate.json"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertEqual(json.loads(completed.stdout)["progress"]["next_scene_id"], "E01S02")
        self.assertLess(len(completed.stdout), 3000)
        self.assertNotIn("完整构图和摄影设计", completed.stdout)

    def test_cli_resolves_shell_and_project_relative_inputs_without_double_prefix(self):
        self.write("candidate.json", self.payload(1))
        for input_path, cwd in (("candidate.json", SKILL_ROOT),
                                (str(Path(self.root.name) / "candidate.json"), self.root.parent),
                                (str(self.root / "candidate.json"), SKILL_ROOT)):
            with self.subTest(input_path=input_path):
                completed = subprocess.run([sys.executable, "-B", str(SKILL_ROOT / "scripts/storyboard_draft.py"),
                    "save", "--project-root", str(self.root), "--episode", "ep_1", "--scene", "E01S01",
                    "--input", input_path], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                self.assertEqual(json.loads(completed.stdout)["scene_id"], "E01S01")

    def test_cli_refuses_ambiguous_relative_input_without_writing(self):
        self.write("candidate.json", self.payload(1))
        self.write("nested/candidate.json", self.payload(1))
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        completed = subprocess.run([sys.executable, "-B", str(SKILL_ROOT / "scripts/storyboard_draft.py"),
            "save", "--project-root", str(self.root), "--episode", "ep_1", "--scene", "E01S01",
            "--input", "candidate.json"], cwd=self.root / "nested", capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        self.assertIn("歧义", json.loads(completed.stdout)["error"])
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}, before)

    def measured_payload(self):
        relative = f"{self.base}/演读测量.wav"
        path = self.root / relative
        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\0\0" * 16000)
        payload = self.payload(1)
        payload["rhythm_input"]["utterances"][0]["timing_basis"] = {
            "method": "existing_measurement", "file": relative, "sha256": self.sha(relative),
            "range_s": [0, 2],
            "evidence": {"line_id": "LINE001", "purpose": "utterance_measurement", "duration_s": 2},
        }
        return payload, path

    def test_real_measurement_is_reloaded_and_assembled_without_evidence_loss(self):
        payload, _ = self.measured_payload()
        self.save(1, payload)
        self.save(2)
        draft.assemble(self.root, "ep_1")
        rhythm = json.loads(self.standards()[1].read_text(encoding="utf-8"))
        self.assertEqual(rhythm["utterances"][0], payload["rhythm_input"]["utterances"][0])

    def test_changed_measurement_refuses_assembly_before_any_standard_write(self):
        payload, path = self.measured_payload()
        self.save(1, payload)
        self.save(2)
        path.write_bytes(path.read_bytes() + b"changed")
        with self.assertRaisesRegex(draft.DraftError, "真实文件及字节 SHA"):
            draft.assemble(self.root, "ep_1")
        self.assertTrue(all(not path.exists() for path in self.standards()))

    def test_documented_example_runs_save_assemble_allocate_pack_as_written(self):
        reference = (SKILL_ROOT / "references/storyboard-draft.md").read_text(encoding="utf-8")
        payload = json.loads(re.search(r"```json\n(.*?)\n```", reference, re.S)[1])
        self.write(self.script, "## E01S01 门侧\n人物抬手示意。\n")
        self.contract["source_sha256"] = self.sha(self.script)
        self.contract["scenes"] = [{"scene_id": "E01S01", "events": [
            {"event_id": "B001", "source_excerpt": "人物抬手示意。", "summary": "人物抬手示意"}],
            "speech_lines": []}]
        self.bind_source()
        payload["source_script"] = self.binding
        self.write("documented-example.json", payload)
        commands = [
            [str(SKILL_ROOT / "scripts/storyboard_draft.py"), "save", "--project-root", str(self.root),
             "--episode", "ep_1", "--scene", "E01S01", "--input", "documented-example.json"],
            [str(SKILL_ROOT / "scripts/storyboard_draft.py"), "assemble", "--project-root", str(self.root),
             "--episode", "ep_1"],
        ]
        for name in ("allocate", "pack"):
            commands.append([str(SKILL_ROOT / "scripts/rhythm_engine.py"), name, "--project-root", str(self.root),
                             "--input", str(self.standards()[1]), "--storyboard", str(self.standards()[0]), "--write"])
        for command in commands:
            completed = subprocess.run([sys.executable, "-B"] + command, capture_output=True,
                                       text=True, encoding="utf-8")
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            self.assertTrue(json.loads(completed.stdout)["ok"])
        board = json.loads(self.standards()[0].read_text(encoding="utf-8"))
        self.assertEqual(board["duration_s"], 3)
        self.assertEqual(board["segments"][0]["request_duration_s"], 4)
        self.assertEqual(board["segments"][0]["tail_handle_s"], 1)
        for key, value in payload["storyboard"]["shots"][0].items():
            self.assertEqual(board["shots"][0][key], value)

    def authoring_globals(self):
        self.write("00_制作控制/project_data_card.json", {"revision": 7})
        self.audience = {"viewing_focus": "看人物如何换取信任。", "emotional_payoff": "让克制获得回应。",
                         "platform_viewing_context": "观看空间关系。", "expression_boundaries": "不补旁白解释。"}
        self.write("00_制作控制/drama_plan.json", {"revision": 4, "audience_plan": self.audience})
        self.facts = [{"fact_id": "WF001", "category": "time_of_day", "statement": "夜晚。",
                       "source": "剧本 E01S01 场景说明", "creative_source_extension": {"keep": "原样"}}]
        self.contract["inherited_world_facts"] = copy.deepcopy(self.facts)
        self.bind_source()

    def test_assembly_projects_exact_sources_and_preserves_creative_audience_bindings(self):
        self.authoring_globals()
        first, second = self.payload(1), self.payload(2)
        first["storyboard"]["audience_execution"] = {
            field: {"scene_or_shot_ids": ["E01S01-SHOT001"], "director_note": "保留本镜落点原文"}
            for field in self.audience}
        self.save(1, first)
        self.save(2, second)
        draft.assemble(self.root, "ep_1")
        board = json.loads(self.standards()[0].read_text(encoding="utf-8"))
        self.assertEqual(board["revision"], 1)
        self.assertEqual(board["project_data_card_revision"], 7)
        self.assertEqual(board["inherited_world_facts"], self.facts)
        self.assertEqual(board["audience_execution"]["source_plan_revision"], 4)
        for field, text in self.audience.items():
            entry = board["audience_execution"][field]
            self.assertEqual(entry["source_field"], "audience_plan." + field)
            self.assertEqual(entry["contract"], text)
            self.assertEqual(entry["scene_or_shot_ids"], ["E01S01-SHOT001"])
            self.assertEqual(entry["director_note"], "保留本镜落点原文")

    def test_explicit_source_copy_conflicts_refuse_assembly_without_overwrite(self):
        self.authoring_globals()
        mutations = [
            {"project_data_card_revision": 6},
            {"inherited_world_facts": []},
            {"audience_execution": {"source_plan_revision": 3}},
            {"audience_execution": {"viewing_focus": {"source_field": "wrong"}}},
            {"audience_execution": {"viewing_focus": {"contract": "重写原句"}}},
        ]
        for fields in mutations:
            with self.subTest(fields=fields):
                first = self.payload(1)
                first["storyboard"].update(fields)
                self.save(1, first)
                self.save(2)
                before = (self.root / self.base / ".draft/E01S01.json").read_bytes()
                with self.assertRaisesRegex(draft.DraftError, "当前真实源冲突"):
                    draft.assemble(self.root, "ep_1")
                self.assertTrue(all(not path.exists() for path in self.standards()))
                self.assertEqual((self.root / self.base / ".draft/E01S01.json").read_bytes(), before)

    def test_projection_never_invents_missing_world_facts_or_creative_audience_targets(self):
        self.write("00_制作控制/drama_plan.json", {"revision": 3,
                   "audience_plan": {"viewing_focus": "源要求看人物选择"}})
        self.write(self.script, (self.root / self.script).read_text(encoding="utf-8") + "夜凉，窗边仿佛有霜。\n")
        self.contract["source_sha256"] = self.sha(self.script)
        self.bind_source()
        self.save(1)
        self.save(2)
        draft.assemble(self.root, "ep_1")
        board = json.loads(self.standards()[0].read_text(encoding="utf-8"))
        self.assertNotIn("inherited_world_facts", board)
        self.assertNotIn("project_data_card_revision", board)
        self.assertNotIn("scene_or_shot_ids", board["audience_execution"]["viewing_focus"])
        self.assertNotIn("emotional_payoff", board["audience_execution"])

    def test_beat_source_labels_fill_only_missing_fields_and_preserve_director_mapping(self):
        first = self.payload(1)
        first["storyboard"]["beat_coverage"][0].update(summary="导演保留的具体摘要", scene="E01S01")
        original = copy.deepcopy(first["storyboard"]["beat_coverage"][0])
        self.save(1, first)
        self.save(2)
        draft.assemble(self.root, "ep_1")
        board = json.loads(self.standards()[0].read_text(encoding="utf-8"))
        self.assertEqual(board["beat_coverage"][0], original)
        self.assertEqual(board["beat_coverage"][1]["scene"], "E01S02")
        self.assertEqual(board["beat_coverage"][1]["summary"], "转身。")
        self.assertEqual(board["beat_coverage"][1]["target_shots"], ["E01S02-SHOT001"])


if __name__ == "__main__":
    unittest.main()
