from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import context_ledger, project_snapshot


class ProjectSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "episodes").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, value):
        path = self.root / "episodes" / "storyboard.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def test_successful_projection_records_project_evidence_and_exact_stdout_size(self):
        self.write_json({"revision": 3, "irrelevant": "x" * 20000})
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = project_snapshot.main([
                "--project-root", str(self.root), "--file", "episodes/storyboard.json",
                "--pointer", "/revision",
            ])
        self.assertEqual(code, 0)
        records = [json.loads(line) for line in context_ledger.project_paths(self.root)[1].read_text(encoding="utf-8").splitlines()]
        self.assertEqual(records[0]["kind"], "project_read")
        self.assertFalse(records[0]["full"])
        self.assertEqual(records[0]["selection"], "json_pointer")
        self.assertEqual(records[1]["chars"], len(output.getvalue()))
        self.assertNotIn("irrelevant", output.getvalue())

    def test_metadata_only_reports_hash_without_reading_document_body(self):
        self.write_json({"private": "do not return this"})

        result = project_snapshot.create_snapshot(self.root, "episodes/storyboard.json")

        self.assertEqual(result["selection"], "metadata_only")
        self.assertNotIn("private", result)
        self.assertEqual(len(result["sha256"]), 64)

    def test_json_pointer_supports_arrays_and_escaped_keys(self):
        self.write_json({"shots": [{"image/process": "close-up", "~note": "revealed"}]})

        result = project_snapshot.create_snapshot(
            self.root,
            "episodes/storyboard.json",
            pointers=["/shots/0/image~1process", "/shots/0/~0note"],
        )

        self.assertEqual(
            [item["value"] for item in result["values"]], ["close-up", "revealed"]
        )

    def test_id_projection_returns_only_requested_fields(self):
        self.write_json({
            "shots": [
                {"shot_id": "SHOT036", "visual": "oil lamp", "sound": "quiet", "internal": {"large": True}},
                {"shot_id": "SHOT037", "visual": "lamp lit", "sound": "click"},
            ]
        })

        result = project_snapshot.create_snapshot(
            self.root,
            "episodes/storyboard.json",
            ids=["SHOT036"],
            fields=["shot_id", "visual", "sound"],
        )

        match = result["records"][0]["matches"][0]
        self.assertEqual(match["value"], {"shot_id": "SHOT036", "visual": "oil lamp", "sound": "quiet"})
        self.assertNotIn("internal", match["value"])

    def test_text_match_returns_bounded_context(self):
        path = self.root / "episodes" / "delivery.md"
        path.write_text("before\nSHOT036 row\nafter\nunrelated\n", encoding="utf-8")

        result = project_snapshot.create_snapshot(
            self.root, "episodes/delivery.md", match="SHOT036", context_lines=1
        )

        self.assertEqual(result["match_count"], 1)
        self.assertIn("1: before\n2: SHOT036 row\n3: after", result["matches"][0]["text"])
        self.assertNotIn("unrelated", result["matches"][0]["text"])

    def test_path_traversal_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "relative to --project-root"):
            project_snapshot.create_snapshot(self.root, "../outside.json")

    def test_output_cap_rejects_overwide_projection(self):
        self.write_json({"payload": "x" * 1000})
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            code = project_snapshot.main([
                "--project-root", str(self.root),
                "--file", "episodes/storyboard.json",
                "--pointer", "/payload",
                "--max-chars", "100",
            ])

        self.assertEqual(code, 2)
        self.assertIn("narrow the pointer/fields/match", stderr.getvalue())

    def test_cli_output_is_utf8_under_windows_default_encoding(self):
        path = self.root / "episodes" / "分镜.json"
        path.write_text(
            json.dumps({"shots": [{"shot_id": "SHOT01", "画面": "窗边的旧灯"}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        env = {key: value for key, value in os.environ.items() if key != "PYTHONIOENCODING"}

        completed = subprocess.run(
            [
                sys.executable,
                str(Path(project_snapshot.__file__).resolve()),
                "--project-root", str(self.root),
                "--file", "episodes/分镜.json",
                "--id", "SHOT01",
                "--field", "画面",
            ],
            cwd=Path(project_snapshot.__file__).resolve().parents[1],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        result = json.loads(completed.stdout.decode("utf-8"))
        self.assertEqual(result["records"][0]["matches"][0]["value"]["画面"], "窗边的旧灯")

    def test_batch_metadata_returns_hashes_for_each_file(self):
        self.write_json({"one": 1})
        (self.root / "episodes" / "delivery.json").write_text("{}", encoding="utf-8")

        result = project_snapshot.create_batch_snapshot(
            self.root, ["episodes/storyboard.json", "episodes/delivery.json"]
        )

        self.assertEqual(result["selection"], "batch_metadata")
        self.assertEqual(result["count"], 2)
        self.assertEqual({item["file"] for item in result["files"]}, {
            "episodes/storyboard.json", "episodes/delivery.json"
        })
        self.assertTrue(all(len(item["sha256"]) == 64 for item in result["files"]))

    def test_cli_rejects_selectors_in_batch_mode(self):
        self.write_json({"one": 1})
        (self.root / "episodes" / "delivery.json").write_text("{}", encoding="utf-8")
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            code = project_snapshot.main([
                "--project-root", str(self.root),
                "--file", "episodes/storyboard.json",
                "--file", "episodes/delivery.json",
                "--pointer", "/one",
            ])

        self.assertEqual(code, 2)
        self.assertIn("selectors may be used with one --file only", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
