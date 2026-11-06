from __future__ import annotations

import contextlib
import io
from argparse import Namespace
import json
import tempfile
import unittest
from pathlib import Path

from scripts import context_ledger, drama_lint, rhythm_engine


class OutputBudgetTests(unittest.TestCase):
    def test_project_lint_output_is_recorded_in_the_shared_event_log(self):
        payload = {"summary": {"error_count": 0, "warning_count": 0, "scope": "storyboard"},
                   "release_ready": True, "issues": []}
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = drama_lint._emit_payload(payload, Namespace(
                    report=None, summary=True, max_chars=10000, project_root=directory,
                ))
            self.assertEqual(code, 0)
            records = [json.loads(line) for line in context_ledger.project_paths(Path(directory))[1].read_text(encoding="utf-8").splitlines()]
            self.assertEqual(records[0]["tool"], "drama_lint")
            self.assertEqual(records[0]["chars"], len(output.getvalue()))

    def test_lint_report_is_saved_while_stdout_contains_only_summary(self):
        payload = {
            "summary": {"error_count": 1, "warning_count": 1, "scope": "storyboard"},
            "release_ready": False,
            "issues": [
                {"level": "error", "code": "shot_missing", "message": "full error details"},
                {"level": "warning", "code": "style_hint", "message": "full warning details"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "reports" / "storyboard.json"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = drama_lint._emit_payload(
                    payload, Namespace(report=report, summary=False, max_chars=10_000)
                )

            self.assertEqual(code, 1)
            self.assertTrue(report.is_file())
            self.assertIn("full error details", report.read_text(encoding="utf-8"))
            stdout = json.loads(output.getvalue())
            self.assertEqual(stdout["summary"]["error_codes"], ["shot_missing"])
            self.assertNotIn("full error details", output.getvalue())

    def test_lint_output_budget_refuses_silent_truncation(self):
        payload = {
            "summary": {"error_count": 0, "warning_count": 0, "scope": "skill"},
            "release_ready": True,
            "issues": [{"level": "info", "code": "x", "message": "x" * 5000}],
        }
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = drama_lint._emit_payload(
                payload, Namespace(report=None, summary=False, max_chars=512)
            )

        self.assertEqual(code, 2)
        result = json.loads(output.getvalue())
        self.assertIn("--summary --report", result["hint"])

    def test_rhythm_summary_drops_large_timing_arrays(self):
        result = rhythm_engine._summary({
            "ok": True,
            "engine": "allocate",
            "total_s": 12.5,
            "shots": [{"shot_id": "SHOT001"}],
            "segments": [{"segment_id": "SEG001"}],
            "issues": [],
        })

        self.assertEqual(result["shot_count"], 1)
        self.assertEqual(result["segment_count"], 1)
        self.assertNotIn("shots", result)
        self.assertNotIn("segments", result)

    def test_rhythm_full_output_is_saved_when_over_budget(self):
        payload = {
            "ok": True,
            "engine": "allocate",
            "shots": [{"shot_id": f"SHOT{index:03d}", "details": "x" * 100} for index in range(80)],
            "segments": [],
            "issues": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "allocate.json"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                emitted = rhythm_engine._emit(payload, max_chars=512, output_file=report)

            self.assertTrue(emitted)
            self.assertTrue(report.is_file())
            self.assertGreater(len(json.loads(report.read_text(encoding="utf-8"))["shots"]), 50)
            summary = json.loads(output.getvalue())
            self.assertEqual(summary["shot_count"], 80)
            self.assertNotIn("details", output.getvalue())
            self.assertLessEqual(len(output.getvalue()), 512)

    def test_rhythm_oversized_default_returns_bounded_non_truncated_summary(self):
        payload = {
            "ok": True,
            "engine": "allocate",
            "shots": [{"shot_id": f"SHOT{index:03d}", "details": "x" * 100} for index in range(80)],
            "issues": [],
        }
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            emitted = rhythm_engine._emit(payload, max_chars=512)

        self.assertFalse(emitted)
        result = json.loads(output.getvalue())
        self.assertTrue(result["output_omitted"])
        self.assertEqual(result["shot_count"], 80)
        self.assertLessEqual(len(output.getvalue()), 512)


if __name__ == "__main__":
    unittest.main()
