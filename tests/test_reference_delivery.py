"""Regression checks for delivery, budget failures and cross-call recovery."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import context_ledger, read_reference


class ReferenceDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.ledger = self.project / "ledger.json"
        self.events = self.project / "events.jsonl"

    def run_reader(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = read_reference.main(list(args))
        return code, output.getvalue()

    def test_overflow_does_not_mark_undelivered_sections_as_read(self):
        args = ("--stage", "planning", "--condition", "governance_reload",
                "--render", "--ledger", str(self.ledger), "--events", str(self.events))
        for _ in range(2):
            code, output = self.run_reader(*args)
            self.assertEqual(code, 2)
            self.assertNotIn("content", json.loads(output)["entries"][0])
            self.assertFalse(self.ledger.exists())
            if self.events.exists():
                records = [json.loads(line) for line in self.events.read_text(encoding="utf-8").splitlines()]
                self.assertFalse(any(record.get("status") == "returned" for record in records))

    def test_file_section_and_stage_share_the_project_ledger(self):
        payload = read_reference.render_route("planning")
        entry = payload["entries"][0]
        code, output = self.run_reader(
            "--file", entry["file"], "--section", entry["section"],
            "--project-root", str(self.project), "--json",
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["content"], entry["content"])
        code, output = self.run_reader(
            "--stage", "planning", "--render", "--project-root", str(self.project), "--json",
            "--max-chars", "20000",
        )
        self.assertEqual(code, 0)
        result = json.loads(output)
        self.assertEqual(result["ledger"]["skipped_count"], 1)
        self.assertNotIn(entry["section"], [item["section"] for item in result["entries"]])

    def test_next_batches_deliver_every_section_once_within_budget(self):
        expected = read_reference.render_route("storyboard", conditions=["artifact_write"])
        actual = []
        for _ in range(12):
            code, output = self.run_reader(
                "--stage", "storyboard", "--condition", "artifact_write", "--render",
                "--project-root", str(self.project), "--next", "--json",
            )
            self.assertEqual(code, 0, output)
            self.assertLessEqual(len(output), read_reference.DEFAULT_MAX_CHARS)
            result = json.loads(output)
            actual.extend(result["entries"])
            if not result["remaining_count"]:
                break
        else:
            self.fail("bounded reads did not finish")
        self.assertEqual(actual, expected["entries"])
        ledger_path, events_path = context_ledger.project_paths(self.project)
        records = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sum(record.get("status") == "returned" for record in records), len(actual))
        self.assertEqual(len(context_ledger.load_ledger(ledger_path)["loaded"]), len(actual))

    def test_legacy_ledger_cannot_hide_previously_undelivered_content(self):
        entry = read_reference.render_route("planning")["entries"][0]
        self.ledger.write_text(json.dumps({
            "schema_version": 1,
            "reference_map_sha256": context_ledger.sha256_file(read_reference.REFERENCE_MAP),
            "loaded": [{"file": entry["file"], "section": entry["section"],
                        "sha256": context_ledger.sha256_file(read_reference.ROOT / entry["file"])}],
        }), encoding="utf-8")
        code, output = self.run_reader(
            "--file", entry["file"], "--section", entry["section"],
            "--ledger", str(self.ledger), "--json",
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["content"], entry["content"])

    def test_failed_stdout_does_not_commit_the_read(self):
        with patch.object(read_reference, "_write_output", side_effect=BrokenPipeError("closed")):
            with contextlib.redirect_stderr(io.StringIO()):
                code, _ = self.run_reader("--stage", "planning", "--render", "--ledger", str(self.ledger))
        self.assertEqual(code, 2)
        self.assertFalse(self.ledger.exists())

    def test_file_overflow_does_not_commit_the_read(self):
        entry = max(read_reference.render_route("planning")["entries"], key=lambda item: len(item["content"]))
        code, output = self.run_reader(
            "--file", entry["file"], "--section", entry["section"],
            "--ledger", str(self.ledger), "--max-chars", "512",
        )
        self.assertEqual(code, 2)
        self.assertNotIn("content", json.loads(output))
        self.assertFalse(self.ledger.exists())

    def test_failed_forced_reload_preserves_previous_ledger(self):
        args = ("--stage", "planning", "--render", "--ledger", str(self.ledger))
        code, _ = self.run_reader(*args)
        self.assertEqual(code, 0)
        original = self.ledger.read_bytes()
        code, _ = self.run_reader(*args, "--force", "--max-chars", "512")
        self.assertEqual(code, 2)
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_next_cannot_repeatedly_force_or_reset_the_same_batch(self):
        for flag in ("--force", "--reset-ledger"):
            code, _ = self.run_reader("--stage", "planning", "--render", "--next",
                                      "--project-root", str(self.project), flag)
            self.assertEqual(code, 2)
        self.assertFalse(context_ledger.project_paths(self.project)[0].exists())


if __name__ == "__main__":
    unittest.main()
