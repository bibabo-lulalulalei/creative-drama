"""read_reference.py 的管道输出必须是 UTF-8；Windows 默认 GBK 代码页下也不能出乱码。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'read_reference.py'


class StdoutEncodingTests(unittest.TestCase):
    def run_script(self, *args: str) -> bytes:
        # 去掉 PYTHONIOENCODING，确保测试覆盖宿主默认代码页（中文 Windows 为 GBK）。
        env = {key: value for key, value in os.environ.items() if key != 'PYTHONIOENCODING'}
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        return completed.stdout

    def test_stage_route_is_valid_utf8(self):
        raw = self.run_script('--stage', 'planning', '--mode', 'full')
        payload = json.loads(raw.decode('utf-8'))
        self.assertEqual(payload['stage'], 'planning')

    def test_section_extraction_is_valid_utf8(self):
        raw = self.run_script(
            '--file', 'references/planning.md', '--section', '## drama_plan.json',
            '--json',
        )
        payload = json.loads(raw.decode('utf-8'))
        self.assertTrue(payload['content'].strip())
        self.assertLess(payload['start_line'], payload['end_line'])


if __name__ == '__main__':
    unittest.main()
