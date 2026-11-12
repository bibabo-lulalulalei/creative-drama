"""Run real pack writes to verify deterministic registration and preservation."""
from __future__ import annotations

import copy
import json
import unittest

import test_storyboard_authoring as authoring


class StoryboardRenderingTests(unittest.TestCase):
    setUp = authoring.StoryboardAuthoringTests.setUp
    write = authoring.StoryboardAuthoringTests.write
    read = authoring.StoryboardAuthoringTests.read
    sha = authoring.StoryboardAuthoringTests.sha
    command = authoring.StoryboardAuthoringTests.command

    def table_rows(self):
        text = (self.root / self.storyboard["source_markdown"]).read_text(encoding="utf-8")
        return [[cell.strip() for cell in line.strip().strip("|").split("|")]
                for line in text.splitlines() if line.lstrip().startswith("|") and len(line.strip().strip("|").split("|")) == 15
                and "E01S01-SHOT" in line]

    def authored_references(self, source="CHR001_v01（人物）"):
        return [{"order": 1, "role": "identity_reference", "planned_source": source,
                 "opening_binding": "<图片1> 锁定身份", "adopt": "实际面部", "exclude": "不继承背景"}]

    def prepare(self, *, split=False):
        board = self.read(self.sb_file)
        board["beat_coverage"] = [
            {"beat_id": "B001", "scene": "E01S01", "summary": "人物抬手示意", "disposition": "kept",
             "target_shots": ["E01S01-SHOT001"], "reason": "保持视线|连接\n延续手势"},
            {"beat_id": "B002", "scene": "E01S01", "summary": "听者停在门边", "disposition": "compressed",
             "target_shots": ["E01S01-SHOT002"]},
        ]
        self.write(self.sb_file, board)
        if split:
            timing = self.read(self.timing_file)
            timing["scenes"][0]["beat_groups"] = [
                {"group_id": f"G00{number}", "shot_ids": [f"E01S01-SHOT00{number}"],
                 "tail_handle": {"mode": "continue_existing_process", "source_event_id": f"V00{number}",
                                 "description": "既有观看继续"}}
                for number in (1, 2)]
            self.write(self.timing_file, timing)
        self.command("allocate")
        self.command("pack")
        return self.read(self.sb_file)

    def test_first_pack_updates_only_segment_cell_and_renders_real_beat_appendix(self):
        path = self.root / self.storyboard["source_markdown"]
        self.write(self.storyboard["source_markdown"], "# 人物如何看见挽留\n\n" + path.read_text(encoding="utf-8") +
                   "\n## 场后导演说明\n保留这段创意原文与符号。\n")
        self.command("allocate")
        before_rows = self.table_rows()
        board = self.prepare()
        after_rows = self.table_rows()
        for before, after in zip(before_rows, after_rows):
            self.assertEqual(before[:1] + before[2:], after[:1] + after[2:])
            self.assertEqual(after[1], board["shots"][after_rows.index(after)]["segment_id"])
        text = path.read_text(encoding="utf-8")
        self.assertIn("# 人物如何看见挽留\n\n", text)
        self.assertIn("## 场后导演说明\n保留这段创意原文与符号。\n", text)
        self.assertIn("## 附录 A：剧本节拍去向", text)
        self.assertIn("B001 | E01S01 | 人物抬手示意 | 保留 | E01S01-SHOT001", text)
        self.assertIn("B002 | E01S01 | 听者停在门边 | 压缩 | E01S01-SHOT002", text)
        self.assertIn("&#124;", text)
        self.assertNotIn("asset_usage_plan", board)
        self.assertNotIn("## 附录 B", text)
        self.assertTrue(all("reference_input_plan" not in seg for seg in board["segments"]))

    def test_explicit_reference_plans_project_usage_preserve_notes_and_are_idempotent(self):
        board = self.prepare()
        segment = board["segments"][0]
        segment["reference_input_plan"] = self.authored_references()
        segment.update(shot_mode="edited", tail_mode="cuttable_completion", density_rationale="不补动作")
        original_segment = copy.deepcopy(segment)
        note = {"asset_id": "CHR001", "version": "v01", "segments": [segment["segment_id"]],
                "category": "人物", "note": "脖颈疤痕与观看关系必须保留", "extension": {"keep": ["原文"]}}
        board["asset_usage_plan"] = [copy.deepcopy(note)]
        self.write(self.sb_file, board)
        self.command("pack")
        saved = self.read(self.sb_file)
        self.assertEqual(saved["asset_usage_plan"], [note])
        self.assertEqual(saved["segments"][0], original_segment)
        path = self.root / self.storyboard["source_markdown"]
        text = path.read_text(encoding="utf-8")
        self.assertIn("## 附录 B：资产使用摘要", text)
        self.assertIn("CHR001 |  | 人物 | v01 | " + segment["segment_id"], text)
        self.assertIn("脖颈疤痕与观看关系必须保留", text)
        before = {relative: (self.root / relative).read_bytes() for relative in
                  (self.sb_file, self.storyboard["source_markdown"], self.timing_file, self.manifest_file)}
        self.command("pack")
        self.assertEqual({relative: (self.root / relative).read_bytes() for relative in before}, before)

    def test_usage_comes_from_inputs_not_source_characters_and_missing_versions_stay_missing(self):
        board = self.prepare()
        board["segments"][0]["reference_input_plan"] = self.authored_references("PROP002:STATE001_v01")
        self.write(self.sb_file, board)
        self.command("pack")
        usage = self.read(self.sb_file)["asset_usage_plan"]
        self.assertEqual(usage, [{"asset_id": "PROP002", "segments": [board["segments"][0]["segment_id"]]}])
        self.assertNotIn("CHR001", json.dumps(usage))

    def test_partial_reference_plans_do_not_claim_usage_is_complete(self):
        board = self.prepare(split=True)
        board["segments"][0]["reference_input_plan"] = self.authored_references()
        self.write(self.sb_file, board)
        self.command("pack")
        saved = self.read(self.sb_file)
        self.assertNotIn("asset_usage_plan", saved)
        self.assertNotIn("reference_input_plan", saved["segments"][1])

    def test_asset_version_conflict_and_declared_binding_conflicts_never_partially_write(self):
        board = self.prepare(split=True)
        for index, segment in enumerate(board["segments"], 1):
            segment["reference_input_plan"] = self.authored_references(f"CHR001_v0{index}")
        self.write(self.sb_file, board)
        files = (self.sb_file, self.storyboard["source_markdown"], self.timing_file, self.manifest_file)
        before = {relative: (self.root / relative).read_bytes() for relative in files}
        failed = self.command("pack", ok=False)
        self.assertIn("版本冲突", failed["issues"][0]["message"])
        self.assertEqual({relative: (self.root / relative).read_bytes() for relative in files}, before)
        board["segments"][1]["reference_input_plan"] = []
        board["asset_usage_plan"] = [{"asset_id": "CHR001", "version": "v01", "segments": ["*"]}]
        self.write(self.sb_file, board)
        before = {relative: (self.root / relative).read_bytes() for relative in files}
        failed = self.command("pack", ok=False)
        self.assertIn("已登记片段", failed["issues"][0]["message"])
        self.assertEqual({relative: (self.root / relative).read_bytes() for relative in files}, before)

    def test_existing_appendix_prose_and_later_sections_survive_source_table_replacement(self):
        board = self.prepare()
        path = self.root / self.storyboard["source_markdown"]
        text = path.read_text(encoding="utf-8").replace(
            "## 附录 A：剧本节拍去向\n", "## 附录 A：剧本节拍去向\n这段导演备注保留。\n")
        text += "\n## 其他创意说明\n手势含义保持开放。\n"
        self.write(self.storyboard["source_markdown"], text)
        board["beat_coverage"][0]["summary"] = "人物抬手进入听者视线"
        self.write(self.sb_file, board)
        self.command("pack")
        rendered = path.read_text(encoding="utf-8")
        self.assertIn("这段导演备注保留。\n", rendered)
        self.assertIn("## 其他创意说明\n手势含义保持开放。\n", rendered)
        self.assertIn("人物抬手进入听者视线", rendered)
        self.assertEqual(rendered.count("## 附录 A：剧本节拍去向"), 1)
        self.assertNotIn("| 人物抬手示意 |", rendered.split("## 附录 A：剧本节拍去向", 1)[1])

    def test_markdown_failure_keeps_both_registration_files_unchanged(self):
        board = self.prepare()
        path = self.root / self.storyboard["source_markdown"]
        self.write(self.storyboard["source_markdown"], path.read_text(encoding="utf-8").replace(
            "| E01S01 | SEG001 | E01S01-SHOT002", "| E01S01 | SEG001 | MISSING-SHOT"))
        board["segments"][0]["reference_input_plan"] = self.authored_references()
        self.write(self.sb_file, board)
        before = {relative: (self.root / relative).read_bytes() for relative in
                  (self.sb_file, self.storyboard["source_markdown"])}
        self.command("pack", ok=False)
        self.assertEqual({relative: (self.root / relative).read_bytes() for relative in before}, before)

    def test_appendices_show_human_notes_without_exposing_machine_metadata(self):
        board = self.prepare()
        segment = board["segments"][0]
        segment["reference_input_plan"] = self.authored_references()
        hidden = {"sha256": "f" * 64, "internal_file": "private/source_contract.json",
                  "arbitrary_metadata_key": {"do_not_show": "internal value"}}
        board["beat_coverage"][0].update(hidden, note="让听者能读懂这个手势")
        board["asset_usage_plan"] = [{"asset_id": "CHR001", "version": "v01",
            "name": "门边人物", "category": "人物", "segments": [segment["segment_id"]],
            "note": "保留脖颈疤痕", "rationale": "身份识别需要", **hidden}]
        self.write(self.sb_file, board)
        self.command("pack")
        saved = self.read(self.sb_file)
        for key, value in hidden.items():
            self.assertEqual(saved["beat_coverage"][0][key], value)
            self.assertEqual(saved["asset_usage_plan"][0][key], value)
        text = (self.root / self.storyboard["source_markdown"]).read_text(encoding="utf-8")
        appendices = text.split("## 附录 A：剧本节拍去向", 1)[1]
        self.assertIn("让听者能读懂这个手势", appendices)
        self.assertIn("CHR001 | 门边人物 | 人物 | v01", appendices)
        self.assertIn("保留脖颈疤痕；身份识别需要", appendices)
        for value in ("sha256", "f" * 64, "private/source_contract.json", "arbitrary_metadata_key", "internal value"):
            self.assertNotIn(value, appendices)

    def test_state_plan_preserves_existing_explicit_version_without_guessing(self):
        board = self.prepare(split=True)
        for segment in board["segments"]:
            segment["reference_input_plan"] = self.authored_references("CHR001:STATE001_v01")
        board["asset_usage_plan"] = [{"asset_id": "CHR001", "version": "v01",
            "segments": [segment["segment_id"] for segment in board["segments"]],
            "note": "原先明确登记的版本"}]
        self.write(self.sb_file, board)
        self.command("pack")
        self.assertEqual(self.read(self.sb_file)["asset_usage_plan"], board["asset_usage_plan"])
        # The gate's parser omits STATE versions. A separately explicit base
        # version remains authoritative; it is not an incompatible blank version.
        board["segments"][1]["reference_input_plan"] = self.authored_references("CHR001_v01")
        self.write(self.sb_file, board)
        self.command("pack")
        self.assertEqual(self.read(self.sb_file)["asset_usage_plan"], board["asset_usage_plan"])


if __name__ == "__main__":
    unittest.main()
