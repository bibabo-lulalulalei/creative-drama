"""creative-index anchors must stay resolvable when teaching headings are renamed."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from drama_lint import (  # noqa: E402
    _creative_index_targets,
    anchor_heading_count,
    check_skill_package,
)


class CreativeIndexLintTests(unittest.TestCase):
    def test_every_backticked_heading_in_the_shipped_index_resolves_once(self):
        text = (ROOT / "references/creative-index.md").read_text(encoding="utf-8")
        targets = _creative_index_targets(text)
        self.assertTrue(targets)
        cache: dict[str, str] = {}
        for rel, headings in targets:
            self.assertIsNotNone(rel, f"标题缺少所属文件：{headings}")
            if rel not in cache:
                cache[rel] = (ROOT / rel).read_text(encoding="utf-8")
            for heading in headings:
                with self.subTest(rel=rel, heading=heading):
                    self.assertEqual(anchor_heading_count(cache[rel], heading), 1)

    def test_repeated_file_rows_follow_the_last_declared_file(self):
        text = (
            "| 动作 | 原始文件 | 必须读取的标题 |\n"
            "|---|---|---|\n"
            "| 写人物 | `references/a.md` | `### 人物引擎` |\n"
            "| 写关系 | 同上 | `### 关系矩阵` |\n"
            "| 换库 | `references/b.md` | `### 传播句` |\n"
        )
        self.assertEqual(
            _creative_index_targets(text),
            [
                ("references/a.md", ["### 人物引擎"]),
                ("references/a.md", ["### 关系矩阵"]),
                ("references/b.md", ["### 传播句"]),
            ],
        )

    def test_lint_flags_stale_and_undeclared_index_anchors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "references").mkdir(parents=True)
            (root / "SKILL.md").write_text(
                "---\nname: temp-skill\ndescription: 临时校验夹具。\n---\n\n正文。\n",
                encoding="utf-8",
            )
            (root / "references/reference_map.json").write_text(
                json.dumps({"stages": {}}), encoding="utf-8"
            )
            library = root / "references/library.md"
            library.write_text("# 库\n### 存在的标题\n正文\n", encoding="utf-8")
            (root / "references/creative-index.md").write_text(
                "| 动作 | 原始文件 | 必须读取的标题 |\n"
                "|---|---|---|\n"
                "| 旧动作 | `references/library.md` | `### 已改名的标题` |\n"
                "| 无文件 | 同上 | `### 存在的标题` |\n",
                encoding="utf-8",
            )
            issues: list[dict] = []
            check_skill_package(root, issues)
            codes = {item["code"] for item in issues}
            self.assertIn("creative_index_anchor_unresolved", codes)

            # 无文件声明的行：删除文件声明后必须报错而不是静默跳过。
            (root / "references/creative-index.md").write_text(
                "| 动作 | 原始文件 | 必须读取的标题 |\n"
                "|---|---|---|\n"
                "| 孤儿 | 未声明 | `### 存在的标题` |\n",
                encoding="utf-8",
            )
            issues = []
            check_skill_package(root, issues)
            self.assertIn("creative_index_file_undeclared", {item["code"] for item in issues})


if __name__ == "__main__":
    unittest.main()
