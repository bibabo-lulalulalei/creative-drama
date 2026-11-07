"""Regression checks for diagnostic navigation, using actual lint diagnostics."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import build_lint_contract as contract
from drama_lint import check_unique
from drama_lint import check_plan_durations
from drama_lint import check_prompt_markers, ordered_inputs
from timeline_core import validate_timeline_shape


class LintContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = contract.scan(ROOT)
        # Each lookup uses the same parsed source, so these tests exercise routing
        # without reparsing the entire package for every emitted diagnostic.
        mocked_scan = patch.object(contract, 'scan', return_value=cls.index)
        mocked_scan.start()
        cls.addClassCleanup(mocked_scan.stop)

    def assert_diagnostics_locatable(self, issues):
        for item in issues:
            with self.subTest(code=item['code']):
                found = contract.lookup(ROOT, 'code', item['code'])
                self.assertTrue(found['ok'], item)
                self.assertEqual(found['total'], len(found['results']))
                for location in found['results']:
                    self.assertEqual(item['code'], location['code'])
                    self.assertTrue(location['message'])
                    self.assertGreaterEqual(location['issue_line'], location['line'])
                    self.assertLessEqual(location['issue_line'], location['end_line'])

    def test_eight_dynamic_planning_codes_are_locatable(self):
        names = ('audience_plan', 'type_strategy', 'highlight_strategy', 'style_contract')
        issues = []
        check_plan_durations(ROOT, {'revision': 1}, issues)
        check_plan_durations(ROOT, {'revision': 1, **{name: {} for name in names}}, issues)
        expected = {f'{name}_{suffix}' for name in names for suffix in ('missing', 'field_missing')}
        actual = [item for item in issues if item['code'] in expected]
        self.assertEqual(expected, {item['code'] for item in actual})
        self.assert_diagnostics_locatable(actual)
        located = contract.lookup(ROOT, 'code', 'audience_plan_missing')['results']
        self.assertTrue(any(item['message'] == 'drama_plan 缺少 audience_plan。' for item in located))

    def test_dynamic_input_and_marker_diagnostics_are_locatable(self):
        issues = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for kind in ('reference', 'video', 'audio'):
                ordered_inputs(root, {}, {'identity_reference'}, kind, root, issues)
                ordered_inputs(root, [None, {}, {'order': 2, 'file': 'missing.png'}],
                               {'identity_reference'}, kind, root, issues)
            prompt = root / 'prompt.txt'
            prompt.write_text('No media markers here.', encoding='utf-8')
            check_prompt_markers(prompt, [1], [1], [1], [], False, issues)
        expected = {f'{kind}_{suffix}' for kind in ('reference', 'video', 'audio')
                    for suffix in ('inputs_invalid', 'input_invalid', 'input_order_invalid',
                                   'input_role_invalid', 'input_field_missing',
                                   'input_file_missing', 'input_order_not_contiguous')}
        expected.update(f'prompt_{kind}_markers_mismatch' for kind in ('image', 'video', 'audio'))
        actual = [item for item in issues if item['code'] in expected]
        self.assertEqual(expected, {item['code'] for item in actual})
        self.assert_diagnostics_locatable(actual)

    def test_dynamic_unique_fields_and_conditional_codes_are_locatable(self):
        issues = []
        for field in ('fact_id', 'beat_id', 'chain_id', 'keyframe_id', 'shot_id', 'segment_id', 'highlight_id'):
            check_unique([{}, {field: 'same'}, {field: 'same'}], field, ROOT, issues, 'objects')
        issues.extend(validate_timeline_shape({'unexpected': True, 'total_duration_s': 6}))
        self.assert_diagnostics_locatable(issues)
        self.assertEqual({'timeline_field_unknown', 'timing_budget_input_forbidden'},
                         {item['code'] for item in issues if item['code'].startswith(('timeline_field_', 'timing_budget_'))})

    def test_templates_do_not_match_unknown_values_or_substrings(self):
        for code in ('unrecognized_missing', 'unrecognized_input_invalid',
                     'prefix_audio_input_invalid', 'audio_input_invalid_suffix',
                     'audience_plan_missing_extra', 'prompt_reference_markers_mismatch'):
            with self.subTest(code=code):
                found = contract.lookup(ROOT, 'code', code)
                self.assertFalse(found['ok'])
                self.assertEqual([], found['results'])

    def test_new_unresolved_templates_fail_instead_of_silently_disappearing(self):
        function = ast.parse('def check(kind):\n    issue("error", f"{kind}_unknown", "details")\n').body[0]
        with self.assertRaisesRegex(ValueError, 'Unresolved diagnostic template'):
            list(contract.rule_entries(function))
        expression = ast.parse('__import__("os").system("must never run")', mode='eval').body
        self.assertEqual(set(), contract.string_values(expression, {}))

    def test_code_lookup_preserves_complete_messages_and_all_matches(self):
        found = contract.lookup(ROOT, 'code', 'h3_request_invalid')
        self.assertGreater(found['total'], 10)
        self.assertEqual(found['total'], len(found['results']))
        page = contract.lookup(ROOT, 'code', 'h3_request_invalid', offset=2, limit=3)
        self.assertEqual(found['results'][2:5], page['results'])
        self.assertEqual(5, page['next_offset'])
        oversized_page = contract.lookup(ROOT, 'code', 'h3_request_invalid', limit=100000)
        self.assertEqual(found['results'], oversized_page['results'])
        message = contract.lookup(ROOT, 'code', 'ref_audio_not_voice_sample')['results'][0]['message']
        self.assertIn('禁止台词级 TTS 临时音频进入 ref_audio 槽位', message)
        self.assertTrue(message.endswith('正片台词由 H3 原生生成，参考只锁声线。'))

    def test_modules_catalog_lists_every_lint_module(self):
        # 原 source-index.md 的模块目录独家价值由 render_modules（--modules）现场承接；
        # lint_checks 包已并入 drama_lint 单文件，目录里不得再出现包路径。
        payload = json.loads(contract.render_modules(self.index))
        names = {row['module'] for row in payload['modules']}
        self.assertIn('drama_lint', names)
        self.assertFalse(any(name.startswith('lint_checks') for name in names))
        for row in payload['modules']:
            self.assertTrue(row['path'].endswith('.py'))
            self.assertTrue(row['summary'])


if __name__ == '__main__':
    unittest.main()
