"""Stage navigation pages render from the authoritative map and print to stdout."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_reference_index


class ReferenceIndexTests(unittest.TestCase):
    def test_current_map_all_stages_and_conditions_are_rendered(self):
        data = json.loads((build_reference_index.ROOT / "references/reference_map.json").read_text(encoding="utf-8"))
        pages = build_reference_index.build()
        self.assertEqual(set(pages), {f"{stage}.md" for stage in data["stages"]})
        for stage, spec in data["stages"].items():
            with self.subTest(stage=stage):
                page = pages[f"{stage}.md"]
                mode = "repair" if stage == "repair" else "full"
                self.assertIn(f"--stage {stage} --mode {mode}", page)
                for path in spec.get("full", []):
                    self.assertIn(f"`{path}`", page)
                for path, headings in spec.get("sections", {}).items():
                    self.assertIn(f"`{path}`", page)
                    for heading in headings:
                        self.assertIn(f"`{heading}`", page)
                for condition, files in spec.get("conditional", {}).items():
                    self.assertIn(f"--condition {condition}", page)
                    trigger = spec.get("condition_triggers", {}).get(condition)
                    if trigger:
                        self.assertIn(trigger, page)
                    for path, headings in files.items():
                        self.assertIn(f"`{path}`", page)
                        for heading in headings:
                            self.assertIn(f"`{heading}`", page)

    def test_repair_page_requires_original_teaching_after_diagnosis(self):
        page = build_reference_index.render_stage("repair", {})
        self.assertIn("最早受影响阶段", page)
        self.assertIn("补齐该阶段原始创作方法和必要依赖", page)
        self.assertIn("修复摘要不能替代原始教学", page)

    def test_stdout_prints_live_page_without_writing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "references").mkdir(parents=True)
            (root / "references/reference_map.json").write_text(
                json.dumps({"stages": {"planning": {"sections": {"references/example.md": ["## Original"]}}}}),
                encoding="utf-8",
            )
            captured = io.StringIO()
            with patch.object(build_reference_index, "ROOT", root), contextlib.redirect_stdout(captured):
                self.assertEqual(build_reference_index.main(["--stdout", "--stage", "planning"]), 0)
            rendered = captured.getvalue()
            self.assertIn("# Reference 路由 · planning", rendered)
            self.assertIn("`references/example.md`", rendered)
            self.assertFalse((root / "references/stage-index").exists())

    def test_stdout_requires_stage_and_rejects_unknown(self):
        with self.assertRaises(SystemExit):
            build_reference_index.main(["--stdout", "--stage", "no_such_stage"])
        with self.assertRaises(SystemExit):
            build_reference_index.main(["--stdout"])
        with self.assertRaises(SystemExit):
            build_reference_index.main([])


if __name__ == "__main__":
    unittest.main()
