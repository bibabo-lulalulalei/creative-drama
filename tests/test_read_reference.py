"""Reference 路由只输出当前需要的完整教学子树，避免同次调用重复装载。"""
import json
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import read_reference as reader


class ReferenceRenderingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="reference_render_test_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        refs = self.root / "references"
        refs.mkdir()
        self.text = (
            "# 教学\n\n## 入口\n只在首次进入读取。\n\n"
            "## 方法\n必须保留的观看方法。\n\n### 举例\n逐字保留完整案例。\n"
            "```markdown\n## 围栏中的假标题\n这是案例的一部分。\n```\n\n"
            "#### 深层说明\n不要截掉尾部正文。\n\n## 附录\n独立的排障内容。\n"
        )
        (refs / "teaching.md").write_text(self.text, encoding="utf-8")
        (refs / "other.md").write_text("# 另一文件\n\n## 方法\n不同文件的正文。\n", encoding="utf-8")
        self.map = {
            "stages": {
                "storyboard": {
                    "full": ["references/teaching.md"],
                    "sections": {"references/teaching.md": ["## 入口"]},
                    "conditional": {
                        "design": {"references/teaching.md": ["## 方法"]},
                        "overlap": {"references/teaching.md": ["### 举例", "## 方法", "#### 深层说明"]},
                        "separate": {"references/teaching.md": ["## 方法", "## 附录"],
                                     "references/other.md": ["## 方法"]},
                    },
                },
                "repair": {
                    "sections": {"references/teaching.md": ["## 入口"]},
                    "conditional": {"affected_storyboard": {"references/teaching.md": ["## 附录"]}},
                },
            }
        }
        (refs / "reference_map.json").write_text(json.dumps(self.map, ensure_ascii=False), encoding="utf-8")

    def render(self, conditions=None, **kwargs):
        return reader.render_route("storyboard", conditions=conditions, root=self.root, **kwargs)

    def test_baseline_and_condition_are_independent_complete_reads(self):
        baseline = self.render()
        self.assertEqual([row["section"] for row in baseline["entries"]], ["## 入口"])
        selected = self.render(["design"])
        self.assertTrue(selected["condition_only"])
        content = reader.format_rendered(selected)
        self.assertNotIn("只在首次进入读取", content)
        for text in ("必须保留的观看方法", "逐字保留完整案例", "围栏中的假标题", "不要截掉尾部正文"):
            self.assertIn(text, content)
        self.assertNotIn("独立的排障内容", content)

    def test_parent_selected_after_child_covers_it_without_truncating(self):
        payload = self.render(["overlap"])
        self.assertEqual(payload["entry_count"], 1)
        self.assertEqual(payload["entries"][0]["section"], "## 方法")
        content = reader.format_rendered(payload)
        self.assertEqual(content.count("逐字保留完整案例"), 1)
        self.assertEqual(content.count("不要截掉尾部正文"), 1)

    def test_repeated_conditions_and_independent_subtrees_are_preserved_once(self):
        payload = self.render(["design", "overlap", "separate"])
        self.assertEqual(payload["entry_count"], 3)
        content = reader.format_rendered(payload)
        self.assertEqual(content.count("必须保留的观看方法"), 1)
        self.assertEqual(content.count("独立的排障内容"), 1)
        self.assertEqual(content.count("不同文件的正文"), 1)

    def test_full_action_contract_subsumes_selected_sections(self):
        payload = self.render(["overlap"], include_full=True)
        self.assertEqual(payload["entry_count"], 1)
        self.assertIsNone(payload["entries"][0]["section"])
        self.assertEqual(payload["entries"][0]["content"], self.text)

    def test_repair_keeps_recovery_and_only_affected_method(self):
        payload = self.render(mode="repair")
        self.assertEqual([row["section"] for row in payload["entries"]], ["## 入口", "## 附录"])
        self.assertNotIn("必须保留的观看方法", reader.format_rendered(payload))

    def test_cli_multiple_sections_preserve_every_requested_subtree_once(self):
        output = io.StringIO()
        with patch.object(reader, "ROOT", self.root), patch.object(reader, "extract_section",
                         side_effect=lambda path, heading: reader_section(path, heading, self.root)), redirect_stdout(output):
            status = reader.main(["--file", "references/teaching.md", "--section", "### 举例",
                                  "--section", "## 方法", "--section", "## 附录"])
        self.assertEqual(status, 0)
        for text in ("必须保留的观看方法", "逐字保留完整案例", "不要截掉尾部正文", "独立的排障内容"):
            self.assertEqual(output.getvalue().count(text), 1)
        self.assertNotIn("只在首次进入读取", output.getvalue())

    def test_cli_bad_section_cannot_silently_drop_the_requested_method(self):
        output = io.StringIO()
        with patch.object(reader, "extract_section", side_effect=lambda path, heading: reader_section(path, heading, self.root)), redirect_stdout(output):
            status = reader.main(["--file", "references/teaching.md", "--section", "## 方法",
                                  "--section", "不存在的章节"])
        self.assertEqual(status, 2)
        self.assertFalse(json.loads(output.getvalue())["ok"])
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(reader.main(["--stage", "storyboard", "--section", "## 方法"]), 2)


reader_section = reader.extract_section


if __name__ == "__main__":
    unittest.main()
