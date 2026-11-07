"""批 2 voice_anchor 单定义重写回归：voices[] 唯一权威，台词行只存 voice_id。

- 锚点解析：未知 voice_id -> speech_line_voice_unknown；登记但锚点为空 -> speech_line_voice_anchor_missing；
- 旧行级 voice_anchor 副本字段容忍不报错（迁移清单手动清理），单定义以数据卡为准；
- 无音频分支不再逐行重复发射锚点码，voice_inputs 违规提示指向 voices[]。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from drama_lint import (  # noqa: E402
    check_voice_anchor_resolution,
    check_voice_audio_inputs,
    load_voice_anchor_map,
)

CARD = "00_制作控制/project_data_card.json"


class VoiceAnchorMapTests(unittest.TestCase):
    def _root(self, card=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        if card is not None:
            target = root / CARD
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
        return root

    def test_missing_card_returns_empty_map_silently(self):
        root = self._root()
        issues: list[dict] = []
        self.assertEqual(load_voice_anchor_map(root, issues), {})
        self.assertEqual(issues, [])

    def test_map_indexes_voices_by_id_and_keeps_blank_anchor(self):
        root = self._root({"voices": [
            {"voice_id": "VOICE001", "voice_anchor": "25岁年轻女性 声音清亮"},
            {"voice_id": "VOICE002", "voice_anchor": "   "},
            {"voice_id": "", "voice_anchor": "ignored"},
            "not-a-dict",
        ]})
        anchors = load_voice_anchor_map(root, [])
        self.assertEqual(anchors, {"VOICE001": "25岁年轻女性 声音清亮", "VOICE002": ""})


class VoiceAnchorResolutionTests(unittest.TestCase):
    def _issues(self, anchors, lines):
        issues: list[dict] = []
        segment = {"segment_id": "SEG001", "speech_lines": lines}
        check_voice_anchor_resolution(segment, anchors, Path("video_manifest.json"), issues)
        return issues

    def test_known_voice_with_anchor_passes(self):
        self.assertEqual(self._issues({"VOICE001": "固定锚点"}, [{"voice_id": "VOICE001"}]), [])

    def test_unknown_voice_id_reports_unknown_code(self):
        codes = [item["code"] for item in self._issues({}, [{"voice_id": "VOICE404"}])]
        self.assertEqual(codes, ["speech_line_voice_unknown"])

    def test_blank_anchor_on_known_voice_reports_missing(self):
        codes = [item["code"] for item in self._issues({"VOICE001": ""}, [{"voice_id": "VOICE001"}])]
        self.assertEqual(codes, ["speech_line_voice_anchor_missing"])

    def test_legacy_line_level_anchor_is_ignored_not_rejected(self):
        # 旧项目台词行残留 voice_anchor：不报错（迁移清单手动清），一切以数据卡解析为准。
        self.assertEqual(
            self._issues({"VOICE001": "数据卡锚点"}, [{"voice_id": "VOICE001", "voice_anchor": "旧行级副本"}]),
            [],
        )
        codes = [item["code"] for item in self._issues({}, [{"voice_id": "VOICE404", "voice_anchor": "行级有值也无效"}])]
        self.assertEqual(codes, ["speech_line_voice_unknown"])

    def test_lines_without_voice_id_skipped_and_garbage_tolerated(self):
        self.assertEqual(self._issues({}, [{}, "garbage", {"voice_id": ""}]), [])

    def test_non_list_speech_lines_safe(self):
        issues: list[dict] = []
        check_voice_anchor_resolution({"segment_id": "SEG001", "speech_lines": None}, {}, Path("x.json"), issues)
        self.assertEqual(issues, [])


class VoiceAudioInputsNoAudioBranchTests(unittest.TestCase):
    def test_voice_inputs_without_audio_reference_points_at_data_card(self):
        segment = {
            "segment_id": "SEG001",
            "speech_lines": [{"voice_id": "VOICE001"}],
            "voice_inputs": [{"voice_id": "VOICE001", "resource_id": "R1"}],
        }
        issues: list[dict] = []
        check_voice_audio_inputs(segment, set(), Path("video_manifest.json"), issues)
        self.assertEqual([item["code"] for item in issues], ["voice_inputs_without_audio_reference"])
        self.assertIn("voices[].voice_anchor", issues[0]["message"])

    def test_no_audio_branch_no_longer_duplicates_anchor_codes(self):
        # 无音频分支不再逐行发射锚点码；锚点裁决全部归属 resolution 检查。
        segment = {"segment_id": "SEG001", "speech_lines": [{"voice_id": "VOICE001"}]}
        issues: list[dict] = []
        check_voice_audio_inputs(segment, set(), Path("video_manifest.json"), issues)
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
