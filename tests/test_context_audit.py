from __future__ import annotations

import json
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts import context_audit


class ContextAuditTests(unittest.TestCase):
    def test_summarize_events_counts_duplicates_and_limits(self):
        events = [
            {"kind": "reference", "status": "returned", "file": "references/a.md", "section": "## A", "sha256": "same", "chars": 120},
            {"kind": "reference", "status": "returned", "file": "references/a.md", "section": "## A", "sha256": "same", "chars": 120},
            {"kind": "reference", "status": "skipped", "file": "references/a.md", "section": "## A", "sha256": "same", "chars": 0},
            {"kind": "lint_source", "file": "scripts/lint_checks/a.py", "chars": 5000},
            {"kind": "project_read", "file": "plan.json", "full": True, "chars": 20000},
            {"kind": "tool_result", "chars": 12001},
        ]

        result = context_audit.summarize_events(events)

        self.assertEqual(result["reference"]["returned_chars"], 240)
        self.assertEqual(result["reference"]["skipped_count"], 1)
        self.assertEqual(len(result["reference"]["duplicate_groups"]), 1)
        self.assertEqual(result["lint_source_read_count"], 1)
        self.assertEqual(result["project"]["full_read_count"], 1)
        self.assertEqual(result["tool_results"]["over_limit_count"], 1)

    def test_cli_reports_route_sizes_and_missing_events_as_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "events.jsonl"
            result = context_audit.main(["--events", str(events), "--stage", "storyboard"])

        self.assertEqual(result, 0)

    def test_observation_distinguishes_missing_empty_and_recorded_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "events.jsonl"
            for expected, contents in (("missing", None), ("empty", ""),
                                       ("recorded", '{"kind":"tool_result","chars":12}\n')):
                if contents is not None:
                    events.write_text(contents, encoding="utf-8")
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(context_audit.main(["--events", str(events)]), 0)
                result = json.loads(output.getvalue())
                self.assertEqual(result["observation"]["status"], expected)
                self.assertIn("project_read", result["events"]["unobserved_kinds"])
                if expected == "recorded":
                    self.assertEqual(result["events"]["observed_kinds"], {"tool_result": 1})


if __name__ == "__main__":
    unittest.main()
