"""可选叙事词汇库必须真实加载，非法 beat_type 必须被拦。"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from lint_checks.constants import BEAT_LIBRARY_JSON_PATH
from lint_checks.rhythm import RhythmLibrary, check_shot_rhythm_fields


class BeatTypeValidationTests(unittest.TestCase):
    def setUp(self):
        self.rhythm = RhythmLibrary()
        self.assertTrue(self.rhythm.ensure())

    def test_ensure_loads_beat_library(self):
        # 回归：RhythmLibrary.library 曾经只初始化不赋值，beat_type 校验整体失效。
        self.assertIsNotNone(self.rhythm.library)
        self.assertIsNone(self.rhythm.error)
        on_disk = json.loads(BEAT_LIBRARY_JSON_PATH.read_text(encoding='utf-8-sig'))
        self.assertEqual(self.rhythm.library, on_disk)

    def test_invalid_beat_type_is_flagged(self):
        valid = set(self.rhythm.library['beat_types'])
        issues = []
        check_shot_rhythm_fields(
            [{'shot_id': 's1', 'beat_type': 'definitely_not_a_beat'}],
            Path('storyboard_x.json'), issues, valid,
        )
        self.assertTrue(
            any(item['code'] == 'shot_beat_type_invalid' for item in issues), issues
        )

    def test_valid_beat_type_passes(self):
        valid = set(self.rhythm.library['beat_types'])
        beat = next(iter(valid))
        issues = []
        check_shot_rhythm_fields(
            [{'shot_id': 's1', 'beat_type': beat}], Path('storyboard_x.json'), issues, valid
        )
        self.assertFalse(
            any(item['code'] == 'shot_beat_type_invalid' for item in issues), issues
        )

    def test_absent_beat_type_stays_optional(self):
        valid = set(self.rhythm.library['beat_types'])
        issues = []
        check_shot_rhythm_fields(
            [{'shot_id': 's1'}], Path('storyboard_x.json'), issues, valid
        )
        self.assertFalse(
            any(item['code'] == 'shot_beat_type_invalid' for item in issues), issues
        )


if __name__ == '__main__':
    unittest.main()
