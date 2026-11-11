"""源台词、跨镜发声和覆盖必须遵守真实内容，不由旧格式或一般确认放行。"""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from rhythm_engine import reconcile_timeline, source_index_from_contract, validate_coverage


class SourceContractTests(unittest.TestCase):
    def test_multilingual_locked_lines_reject_a_changed_word(self):
        for original, changed in [
            ("ここにいる。", "どこにいる。"),
            ("문이 열렸다.", "문이 닫혔다."),
            ("Écoute-moi.", "Ecoute-moi."),
            ("افتح الباب", "اغلق الباب"),
        ]:
            with self.subTest(original=original):
                contract = {"scenes": [{"scene_id": "E01S01", "events": [],
                    "speech_lines": [{"line_id": "L1", "speaker": "CHR001", "source_text": original}]}]}
                issues = []
                index = source_index_from_contract(contract, "## E01S01 房间\n" + original, issues)
                self.assertFalse(issues)
                self.assertEqual(index["line:L1"]["speaker_ref"], "CHR001")
                issues = []
                source_index_from_contract(contract, "## E01S01 房间\n" + changed, issues)
                self.assertIn("source_revision_mismatch", [item["code"] for item in issues])

    def test_equivalent_composed_letters_preserve_source_matching(self):
        contract = {"scenes": [{"scene_id": "E01S01", "events": [], "speech_lines": [
            {"line_id": "L1", "speaker": "CHR001", "source_text": "Écoute-moi !"}]}]}
        issues = []
        source_index_from_contract(contract, "## E01S01 房间\nE\u0301coute moi", issues)
        self.assertFalse(issues)

    def test_cross_shot_speech_is_continuous_and_never_silently_retimed(self):
        inp = {"episode_id": "ep_1", "utterances": [{"utterance_id": "U1", "line_id": "L1",
            "speaker_ref": "CHR001", "estimated_duration_s": 4,
            "timing_basis": {"method": "director_estimate", "note": "本句连贯演读"}}],
            "scenes": [{"scene_id": "E01S01", "shots": [
                {"shot_id": "S1", "timeline": [{"event_id": "A1", "kind": "speech", "utterance_id": "U1",
                    "utterance_offset_s": 0, "start_s": 0, "duration_s": 2, "after": []}]},
                {"shot_id": "S2", "timeline": [{"event_id": "A2", "kind": "speech", "utterance_id": "U1",
                    "utterance_offset_s": 2, "start_s": 0, "duration_s": 2, "after": ["A1"]}]}]}]}
        index = {"line:L1": {"speaker_ref": "CHR001", "source_text": "ここにいる。"}}
        result = reconcile_timeline(inp, index)
        self.assertTrue(result["ok"], result["issues"])
        self.assertEqual(result["total_s"], 4)
        broken = copy.deepcopy(inp)
        broken["scenes"][0]["shots"][1]["timeline"][0]["start_s"] = 0.5
        before = copy.deepcopy(broken)
        result = reconcile_timeline(broken, index)
        self.assertIn("speech_span_discontinuous", [item["code"] for item in result["issues"]])
        self.assertEqual(broken, before)

    def test_source_event_cannot_be_deleted_via_a_coverage_flag(self):
        inp = {"scenes": [{"shots": [{"shot_id": "S1", "timeline": []}]}], "utterances": []}
        storyboard = {"beat_coverage": [{"beat_id": "B1", "disposition": "dropped",
            "confirmation_ref": "general_script_approval", "target_shots": []}]}
        issues = validate_coverage(storyboard, inp, {"beat:B1": {}})
        self.assertIn("source_event_uncovered", [item["code"] for item in issues])


if __name__ == "__main__":
    unittest.main()
