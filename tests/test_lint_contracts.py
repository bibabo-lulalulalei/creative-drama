"""审计发现的客观合同回归：不借校验规则强迫创作配额。"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import drama_lint as lint


class LintContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write("shared/03_资产/asset_registry.json", {"assets": []})
        self.write("00_制作控制/project_data_card.json", {"characters": []})
        self.write("episodes/ep_1/03_资产/asset_usage_ep_1.json",
                   {"episode_id": "ep_1", "shared_assets": [], "episode_assets": [], "reused_episode_assets": []})

    def write(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_absent_source_world_facts_allow_empty_list(self):
        issues = []
        lint.check_world_facts({"inherited_world_facts": []}, self.root, issues)
        self.assertEqual(issues, [])

    def test_spoken_blocks_preserve_word_count_and_order(self):
        prompt = self.root / "prompt.md"
        for lines, blocks in [
            (["别走。", "别走。"], "<d>别走。</d>"),
            (["谁来了？", "是我。"], "<d>是我。</d><d>谁来了？</d>"),
            (["别走。"], "<d>别走，我爱你。</d>"),
            ([], "<d>新加一句</d>"),
        ]:
            with self.subTest(lines=lines, blocks=blocks):
                prompt.write_text(blocks, encoding="utf-8")
                issues = []
                lint.check_prompt_markers(prompt, [], [], [],
                    [{"source_text": value} for value in lines], False, issues)
                self.assertIn("prompt_speech_text_mismatch", {item["code"] for item in issues})
        prompt.write_text("<d>ここに</d>画面切换<d>いる。</d>", encoding="utf-8")
        issues = []
        lint.check_prompt_markers(prompt, [], [], [], [{"source_text": "ここにいる。"}], False, issues)
        self.assertFalse(issues)

    def test_empty_registry_cannot_authorize_unknown_shared_asset(self):
        self.write("episodes/ep_1/03_资产/asset_usage_ep_1.json",
                   {"shared_assets": [{"asset_id": "CHR999", "version": "v01"}]})
        issues = []
        lint.check_assets(self.root, issues, "ep_1")
        self.assertIn("asset_usage_unknown_shared_asset", {row["code"] for row in issues})

    def test_approved_visual_asset_requires_actual_files(self):
        self.write("shared/03_资产/asset_registry.json", {"assets": [
            {"asset_id": "CHR001", "category": "character", "version": "v01", "status": "approved",
             "project_visual_mode": "live_action"}]})
        issues = []
        lint.check_assets(self.root, issues, "ep_1")
        self.assertIn("asset_file_missing", {row["code"] for row in issues})

    def test_state_version_does_not_obsolete_base_identity_version(self):
        (self.root / "base.png").write_bytes(b"base image")
        (self.root / "state.png").write_bytes(b"state image")
        self.write("shared/03_资产/asset_registry.json", {"assets": [
            {"asset_id": "CHR001", "category": "character", "version": "v01", "status": "approved",
             "files": ["base.png"], "project_visual_mode": "live_action"}]})
        self.write("episodes/ep_1/03_资产/asset_usage_ep_1.json", {"shared_assets": [], "episode_assets": [
            {"asset_id": "CHR001", "state_id": "STATE001", "version": "v02", "status": "approved", "files": ["state.png"]}]})
        issues = []
        index = lint.check_assets(self.root, issues, "ep_1")
        references = []
        lint.check_asset_ref("CHR001_v01", index, self.root, references, "base")
        lint.check_state_ref("CHR001:STATE001_v02", index, self.root, references, "state")
        self.assertEqual(references, [])

    def test_episode_voice_uses_schema_fields_and_remains_mandatory_on_reuse(self):
        sample = self.root / "voice.wav"
        with wave.open(str(sample), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(8000)
            stream.writeframes(b"\0\0" * 8000)
        voice = {"asset_id": "VOICE001", "version": "v01", "status": "approved", "files": ["voice.wav"]}
        self.write("episodes/ep_1/03_资产/asset_usage_ep_1.json", {"shared_assets": [], "episode_assets": [voice]})
        self.write("episodes/ep_2/03_资产/asset_usage_ep_2.json", {"shared_assets": [], "episode_assets": [],
                   "reused_episode_assets": [dict(voice, source_episode_id="ep_1")]})
        issues = []
        index = lint.check_assets(self.root, issues, "ep_2")
        self.assertEqual(issues, [])
        self.assertIn("VOICE001", index["approved_voice_ids"])

    def test_storyboard_cannot_drop_locked_source_event(self):
        issues = []
        lint.check_beat_coverage({"beat_coverage": [{"beat_id": "BEAT001", "scene": "SC001", "summary": "离开",
                                                     "disposition": "dropped", "reason": "省时", "target_shots": []}]},
                                 {"SHOT001"}, self.root, issues)
        self.assertIn("beat_disposition_invalid", {row["code"] for row in issues})

    def test_highlight_does_not_require_added_reaction_or_aftereffect_shots(self):
        self.write("episodes/ep_1/01_剧本/script_contract_ep_1.json", {"highlight_ledger": [{"highlight_id": "H1", "role": "primary"}]})
        storyboard = {"episode_id": "ep_1", "duration_s": 4, "shots": [{"shot_id": "SHOT001", "segment_id": "SEG001", "duration_s": 4}],
                      "segments": [{"segment_id": "SEG001", "duration_s": 4, "shot_ids": ["SHOT001"],
                                    "shot_mode": "true_one_take", "tail_mode": "cuttable_completion", "reference_input_plan": []}],
                      "asset_usage_plan": [], "inherited_world_facts": [], "beat_coverage": [],
                      "highlight_bindings": [{"highlight_id": "H1", "segment_id": "SEG001", "payoff_shot_ids": ["SHOT001"],
                                              "reaction_shot_ids": [], "aftereffect_shot_ids": [],
                                              "visual_execution": "门在同镜中打开", "performance_execution": "停在门前",
                                              "audio_execution": "门响", "compile_notes": "同镜保留"}]}
        self.write("episodes/ep_1/02_分镜/storyboard_ep_1.json", storyboard)
        issues = []
        lint.check_storyboards(self.root, {}, issues, "ep_1")
        self.assertFalse([row for row in issues if "highlight" in row["code"]], issues)
        storyboard["highlight_bindings"][0]["reaction_shot_ids"] = ["UNKNOWN"]
        self.write("episodes/ep_1/02_分镜/storyboard_ep_1.json", storyboard)
        issues = []
        lint.check_storyboards(self.root, {}, issues, "ep_1")
        self.assertIn("highlight_binding_shot_invalid", {row["code"] for row in issues})


if __name__ == "__main__":
    unittest.main()
