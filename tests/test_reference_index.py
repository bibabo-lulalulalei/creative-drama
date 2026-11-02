"""Ensure generated reference pages retain navigation and reveal source drift."""

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

    def test_check_detects_missing_changed_and_obsolete_pages_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "references/stage-index"
            output.mkdir(parents=True)
            pages = {"planning.md": "expected\n", "video.md": "video\n"}
            (output / "planning.md").write_text("changed\n", encoding="utf-8")
            (output / "obsolete.md").write_text("keep this file\n", encoding="utf-8")
            drift = build_reference_index.check(root, pages)
            self.assertEqual(set(drift), {
                "changed: references/stage-index/planning.md",
                "missing: references/stage-index/video.md",
                "obsolete: references/stage-index/obsolete.md",
            })
            self.assertFalse((output / "video.md").exists())
            self.assertEqual((output / "obsolete.md").read_text(encoding="utf-8"), "keep this file\n")
            (output / "planning.md").write_text(pages["planning.md"], encoding="utf-8")
            (output / "video.md").write_text(pages["video.md"], encoding="utf-8")
            (output / "obsolete.md").unlink()
            self.assertEqual(build_reference_index.check(root, pages), [])

    def test_repair_page_requires_original_teaching_after_diagnosis(self):
        page = build_reference_index.render_stage("repair", {})
        self.assertIn("最早受影响阶段", page)
        self.assertIn("补齐该阶段原始创作方法和必要依赖", page)
        self.assertIn("修复摘要不能替代原始教学", page)

    def test_cli_generation_and_check_follow_map_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            references = root / "references"
            references.mkdir()
            source = references / "reference_map.json"
            data = {"stages": {"planning": {"sections": {"references/example.md": ["## Original"]}}}}
            source.write_text(json.dumps(data), encoding="utf-8")
            with patch.object(build_reference_index, "ROOT", root), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(build_reference_index.main([]), 0)
                self.assertEqual(build_reference_index.main(["--check"]), 0)
                target = references / "stage-index/planning.md"
                original = target.read_text(encoding="utf-8")
                data["stages"]["planning"]["sections"]["references/example.md"] = ["## Changed"]
                source.write_text(json.dumps(data), encoding="utf-8")
                self.assertEqual(build_reference_index.main(["--check"]), 1)
                self.assertEqual(target.read_text(encoding="utf-8"), original)
                self.assertEqual(build_reference_index.main([]), 0)
                self.assertIn("## Changed", target.read_text(encoding="utf-8"))
                self.assertEqual(build_reference_index.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
