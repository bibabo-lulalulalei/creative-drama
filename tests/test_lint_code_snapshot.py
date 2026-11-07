"""瘦身/重构期间检查覆盖零变化：各阶段可达检查码集合必须与黄金快照一致。

快照由 build_lint_contract.scan() 的真实 STAGE_CHECKS 可达图生成；
新增/删除检查码是有意决策，需人工确认后重跑唯一维护入口更新
tests/fixtures/lint_code_snapshot.json，不能静默漂移或手编 fixture：
  校验 python scripts/maintenance/regen_lint_code_snapshot.py --check
  重写 python scripts/maintenance/regen_lint_code_snapshot.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import build_lint_contract as contract

SNAPSHOT = ROOT / 'tests' / 'fixtures' / 'lint_code_snapshot.json'


def stage_code_sets():
    index = contract.scan(ROOT)
    sets = {}
    for stage, reachable in index['reachable'].items():
        codes = set()
        for qualified in reachable:
            for code, _level, _message, _issue_line in index['rules'][qualified]:
                codes.add(code)
        sets[stage] = codes
    return sets


class LintCodeSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads(SNAPSHOT.read_text(encoding='utf-8'))

    def test_per_stage_sets_match_snapshot(self):
        actual = stage_code_sets()
        self.assertEqual(set(actual), set(self.snapshot['stages']))
        for stage, codes in actual.items():
            expected = set(self.snapshot['stages'][stage])
            self.assertFalse(codes - expected, f'{stage} 新增未审计检查码：{sorted(codes - expected)}')
            self.assertFalse(expected - codes, f'{stage} 检查码丢失：{sorted(expected - codes)}')

    def test_union_count(self):
        actual = stage_code_sets()
        union = set().union(*actual.values())
        self.assertEqual(len(union), self.snapshot['union_count'])
        # Batch 1（瘦身 4.2）经逐条源码核实删除 10 个不可触发/重复码：547 → 537。
        self.assertEqual(self.snapshot['union_count'], 537)

    def test_fixture_is_byte_reproducible_via_maintenance_script(self):
        # 守卫：fixture 只能由维护脚本重生成，手编或跨平台行尾漂移都会在此失败。
        from maintenance.regen_lint_code_snapshot import build_payload, render
        self.assertEqual(SNAPSHOT.read_bytes(), render(build_payload()))


if __name__ == '__main__':
    unittest.main()
