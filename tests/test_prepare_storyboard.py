"""分镜当前场只读选择：保留原文、硬约束、状态来源，明确缺项。"""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_storyboard import PreparationError, load_storyboard_context, main


class PrepareStoryboardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="prepare_storyboard_test_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.base = "episodes/ep_1"
        self.script_file = f"{self.base}/01_剧本/script.md"
        self.contract_file = f"{self.base}/01_剧本/script_contract_ep_1.json"
        self.scene_texts = [
            "## E01S01 船坞 日 外\r\n少年擦拭铜螺号。\r\n\r\n",
            "## E01S02 船坞 夜 外\r\n少年收好铜螺号。\r\n少年：爹，我回来了。\r\n\r\n",
            "## E01S03 海面 夜 外\r\n一艘空船远去。\r\n",
        ]
        self.preamble = "# 剧本\r\n用户锁定：只以人物行动叙事，不加旁白。\r\n\r\n"
        self.script = self.preamble + "".join(self.scene_texts)
        self.write(self.script_file, self.script)
        scenes = [
            {"scene_id": f"E01S0{i + 1}", "location_id": "SCN001", "characters": ["CHR001"],
             "character_states": ["CHR001:STATE001" if i == 0 else "CHR001:STATE002"],
             "prop_states": ["PROP001:STATE001"],
             "events": [{"event_id": f"B00{i + 1}", "source_excerpt": text.splitlines()[1], "summary": "源索引已有摘要"}],
             "speech_lines": ([{"line_id": "LINE001", "speaker": "CHR001", "voice_id": "VOICE001", "source_text": "爹，我回来了。"}] if i == 1 else [])}
            for i, text in enumerate(self.scene_texts)
        ]
        self.contract = {"episode_id": "ep_1", "revision": 2, "source_markdown": self.script_file,
                         "source_sha256": hashlib.sha256(self.script.encode()).hexdigest(), "scenes": scenes,
                         "relationship_tension": [{"characters": ["CHR001", "CHR002"], "initial": "未相认", "change_nodes": [{"scene_id": "E01S03", "after": "告别"}]}],
                         "inherited_world_facts": [{"fact_id": "WF001", "statement": "海在天上"}],
                         "unfamiliar_hard_constraint": {"requirement": "不能丢弃未来新增的全局合同字段"}}
        self.write(self.contract_file, self.contract)
        self.write("00_制作控制/制作状态.json", {"current_episode": "ep_1", "current_stage": "storyboard", "last_successful_operation": "已保存第一场导演设计"})
        self.write("00_制作控制/drama_plan.json", {"source_lock": {"must_avoid": ["旁白"]}, "style_contract": {"lighting": "冷蓝暖金"}, "direction_candidates": ["不需要重选的候选"],
                   "opening_strategy": {"promise": "等归人开口"}, "emotion_design": {"curve": "迟疑后松开"},
                   "highlight_strategy": {"payoff": "手上的动作兑现关系"}, "rhythm_design": {"intentional_wait": "等话落下"}})
        self.write("00_制作控制/project_data_card.json", {
            "revision": 4, "global_settings": {"ratio": "16:9"},
            "characters": [{"character_id": "CHR001", "identity_locked": {"face": "少年", "voice_id": "VOICE001"},
                            "state_timeline": [{"state_id": "CHR001-STATE001", "clothing": "干衣"}, {"state_id": "CHR001-STATE002", "clothing": "湿衣"}]},
                           {"character_id": "CHR999", "identity_locked": "无关人物不得灌入"}],
            "scenes": [{"scene_id": "SCN001", "layout_locked": "旧船在坞内", "state_timeline": [
                {"state_id": "SCN001-STATE001", "effective_from": "ep_1:E01S01", "effective_to": "ep_1:E01S01", "light": "白天"},
                {"state_id": "SCN001-STATE002", "effective_from": "ep_1:E01S02", "effective_to": "", "light": "夜晚"}]}],
            "props": [{"prop_id": "PROP001", "state_timeline": [{"state_id": "PROP001-STATE001", "condition": "铜锈"}]}],
            "voices": [{"voice_id": "VOICE001", "voice_anchor": "清亮少年声"}, {"voice_id": "VOICE999", "voice_anchor": "无关声音"}]})
        self.usage_file = f"{self.base}/03_资产/asset_usage_ep_1.json"
        self.write(self.usage_file, {"revision": 2, "shared_assets": [{"asset_id": "STYLE001", "version": "v01"}, {"asset_id": "SCN001", "version": "v02"}],
                                   "episode_assets": [{"asset_id": "CHR001", "state_id": "STATE002", "version": "v02", "status": "approved"}, {"asset_id": "CHR999", "status": "approved"}]})
        self.write("shared/03_资产/asset_registry.json", {"assets": [{"asset_id": "STYLE001", "status": "approved", "files": ["style.png"]}, {"asset_id": "CHR999", "files": ["unrelated.png"]}]})
        self.write(f"{self.base}/02_分镜/storyboard_ep_1.json", {"revision": 3, "source_markdown": f"{self.base}/02_分镜/shots.md", "director_control_card": f"{self.base}/02_分镜/director.md", "shots": [{"shot_id": "SHOT001", "scene_id": "E01S01"}]})
        self.write(f"{self.base}/02_分镜/director.md", "# 导演卡\n已写的内容只给位置，不反复整篇回显\n")

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
        path.write_bytes(text.encode("utf-8"))

    def read(self, scene=None, **kwargs):
        if scene is None:
            kwargs.setdefault("list_only", True)
        return load_storyboard_context(self.root, "ep_1", scene, **kwargs)

    def test_navigation_is_small_and_does_not_echo_story_or_all_sources(self):
        output = self.read()
        self.assertEqual([row["scene_id"] for row in output["scenes"]], ["E01S01", "E01S02", "E01S03"])
        self.assertEqual(output["scenes"][0]["existing_shot_count"], 1)
        text = json.dumps(output, ensure_ascii=False)
        for absent in ("少年擦拭", "关系", "冷蓝暖金", "无关人物", "已写的内容只给位置"):
            self.assertNotIn(absent, text)
        self.assertNotIn("scene", output)
        self.assertEqual(output["progress"]["current_stage"], "storyboard")
        director = next(row for row in output["artifacts"] if row["file"].endswith("director.md"))
        self.assertTrue(director["exists"])
        self.assertEqual(len(director["sha256"]), 64)

    def test_scene_is_verbatim_with_global_constraints_and_exact_locations(self):
        output = self.read("E01S02", include_global=True)
        self.assertEqual(output["scene"]["text"], self.scene_texts[1])
        self.assertEqual(output["scene"]["contract"]["value"], self.contract["scenes"][1])
        self.assertEqual(output["script_preamble"]["text"], self.preamble)
        self.assertEqual(output["global_contract"]["value"]["relationship_tension"], self.contract["relationship_tension"])
        self.assertIn("unfamiliar_hard_constraint", output["global_contract"]["value"])
        self.assertNotIn("scenes", output["global_contract"]["value"])
        self.assertEqual(output["locked_plan"]["value"]["source_lock"], {"must_avoid": ["旁白"]})
        self.assertNotIn("direction_candidates", output["locked_plan"]["value"])
        for key in ("opening_strategy", "emotion_design", "highlight_strategy", "rhythm_design"):
            plan = json.loads((self.root / "00_制作控制/drama_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(output["locked_plan"]["value"][key], plan[key])
        self.assertNotIn("text", output["neighbors"]["previous"])
        lines = self.script.splitlines(keepends=True)
        row = output["scene"]
        self.assertEqual("".join(lines[row["start_line"] - 1:row["end_line"]]), row["text"])
        self.assertEqual(output["sources"][self.script_file]["sha256"], self.contract["source_sha256"])

    def test_default_resume_returns_actual_next_scene_even_with_full_director_card(self):
        # A finished director card is not a saved machine registration.
        (self.root / f"{self.base}/02_分镜/storyboard_ep_1.json").unlink()
        output = load_storyboard_context(self.root, "ep_1", include_global=True)
        self.assertEqual(output["scene"]["scene_id"], "E01S01")
        self.assertEqual(output["scene"]["text"], self.scene_texts[0])
        self.assertTrue(output["global_context_included"])
        self.assertEqual(output["draft_progress"]["saved_scene_ids"], [])
        self.assertEqual(output["draft_progress"]["next_scene_id"], "E01S01")
        self.assertNotIn("scenes", output)
        self.assertIn("next_action", output)

    def test_list_keeps_navigation_separate_from_default_work_unit(self):
        (self.root / f"{self.base}/02_分镜/storyboard_ep_1.json").unlink()
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["--project-root", str(self.root), "--episode", "ep_1", "--list"])
        self.assertEqual(code, 0)
        output = json.loads(stream.getvalue())
        self.assertIn("scenes", output)
        self.assertNotIn("scene", output)
        with self.assertRaisesRegex(PreparationError, "--list"):
            load_storyboard_context(self.root, "ep_1", list_only=True, include_global=True)

    def test_scene_increment_does_not_reinject_global_baseline_but_keeps_locators(self):
        increment = self.read("E01S02")
        baseline = self.read("E01S02", include_global=True)
        self.assertFalse(increment["global_context_included"])
        self.assertTrue(baseline["global_context_included"])
        for key in ("script_preamble", "global_contract", "locked_plan"):
            self.assertNotIn(key, increment)
            self.assertIn(key, baseline)
            self.assertIn("file", increment["global_sources"][key])
        self.assertIn("/unfamiliar_hard_constraint", increment["global_sources"]["global_contract"]["json_pointers"])
        self.assertIn("unfamiliar_hard_constraint", baseline["global_contract"]["value"])
        self.assertNotIn("不能丢弃未来新增的全局合同字段", json.dumps(increment, ensure_ascii=False))
        self.assertEqual(increment["scene"], baseline["scene"])
        self.assertEqual(increment["source_binding"], baseline["source_binding"])
        self.assertLess(len(json.dumps(increment, ensure_ascii=False)), len(json.dumps(baseline, ensure_ascii=False)))

    def test_neighbors_are_complete_originals_only_when_requested(self):
        output = self.read("E01S02", neighbors=True)
        self.assertEqual(output["neighbors"]["previous"]["text"], self.scene_texts[0])
        self.assertEqual(output["neighbors"]["next"]["text"], self.scene_texts[2])
        self.assertEqual(output["neighbors"]["next"]["contract"]["value"], self.contract["scenes"][2])
        self.assertNotIn("previous", self.read("E01S01", neighbors=True)["neighbors"])
        self.assertNotIn("next", self.read("E01S03", neighbors=True)["neighbors"])

    def test_rhythm_source_identity_is_derived_without_inventing_timing_or_shots(self):
        output = self.read("E01S02")
        self.assertEqual(output["source_binding"], {
            "file": self.contract_file, "revision": 2,
            "sha256": hashlib.sha256((self.root / self.contract_file).read_bytes()).hexdigest()})
        self.assertEqual(output["rhythm_sources"]["source_refs"], ["beat:B002", "line:LINE001"])
        self.assertEqual(output["rhythm_sources"]["utterance_sources"], [
            {"line_id": "LINE001", "speaker_ref": "CHR001", "source_ref": "line:LINE001"}])
        for field in ("estimated_duration_s", "timing_basis", "shots", "timeline"):
            self.assertNotIn(field, output["rhythm_sources"])
        self.assertNotIn("scenes", output)

    def test_current_states_voice_and_assets_are_selected_without_other_entities(self):
        output = self.read("E01S02")
        entities = output["data_card"]["entities"]
        character = entities["characters"][0]["value"]
        self.assertEqual(character["state_timeline"], [{"state_id": "CHR001-STATE002", "clothing": "湿衣"}])
        self.assertEqual(entities["scenes"][0]["value"]["state_timeline"][0]["light"], "夜晚")
        self.assertEqual(entities["voices"][0]["value"]["voice_anchor"], "清亮少年声")
        self.assertEqual(output["asset_usage"]["value"]["episode_assets"][0]["value"]["status"], "approved")
        self.assertEqual(output["registry"]["assets"][0]["value"]["asset_id"], "STYLE001")
        self.assertNotIn("CHR999", json.dumps(output, ensure_ascii=False))
        self.assertNotIn("VOICE999", json.dumps(output, ensure_ascii=False))

    def test_missing_sources_and_stale_sha_are_explicit_without_inventing_facts(self):
        (self.root / self.usage_file).unlink()
        self.contract["source_sha256"] = "stale"
        self.write(self.contract_file, self.contract)
        output = self.read("E01S02")
        codes = {item["code"] for item in output["issues"]}
        self.assertIn("source_sha_mismatch", codes)
        self.assertIn("optional_source_missing", codes)
        self.assertEqual(output["scene"]["text"], self.scene_texts[1])
        self.assertEqual(output["asset_usage"]["value"], {})
        self.assertNotIn("release_ready", output)
        self.assertNotIn("approved", output)

    def test_unresolved_state_is_preserved_as_candidate_instead_of_guessed(self):
        self.contract["scenes"][1]["character_states"] = ["CHR001:STATE777"]
        self.write(self.contract_file, self.contract)
        output = self.read("E01S02")
        character = output["data_card"]["entities"]["characters"][0]["value"]
        self.assertEqual(character["state_timeline"], [])
        self.assertEqual(len(character["unresolved_state_candidates"]), 2)
        self.assertIn("state_scope_unresolved", {issue["code"] for issue in output["issues"]})

    def test_invalid_paths_missing_scenes_and_duplicate_headings_fail_specifically(self):
        with self.assertRaisesRegex(PreparationError, "找不到唯一场次"):
            self.read("E01S99")
        self.write(self.script_file, self.script + "\n## E01S02 重复\n")
        with self.assertRaisesRegex(PreparationError, "唯一场次标题"):
            self.read("E01S02")
        self.contract["source_markdown"] = "../outside.md"
        self.write(self.contract_file, self.contract)
        with self.assertRaisesRegex(ValueError, "项目根内"):
            self.read()

    def test_cli_and_selection_never_modify_project(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["--project-root", str(self.root), "--episode", "ep_1", "--scene", "E01S02", "--neighbors"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stream.getvalue())["scene"]["text"], self.scene_texts[1])
        after = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        with redirect_stdout(io.StringIO()) as failure:
            code = main(["--project-root", str(self.root), "--episode", "ep_1", "--list", "--neighbors"])
        self.assertEqual(code, 2)
        self.assertIn("--list", json.loads(failure.getvalue())["error"])


if __name__ == "__main__":
    unittest.main()
