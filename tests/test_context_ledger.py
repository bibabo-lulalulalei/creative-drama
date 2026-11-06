from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import context_ledger


def delivered_entries(entries, **kwargs):
    plan = context_ledger.prepare_entries(entries, **kwargs)
    plan.commit()
    return plan.entries, plan.summary()


class ContextLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "references").mkdir()
        self.reference_map = self.root / "references" / "reference_map.json"
        self.reference_map.write_text("{}", encoding="utf-8")
        (self.root / "references" / "guide.md").write_text(
            "## First\nfirst\n## Second\nsecond\n", encoding="utf-8"
        )
        self.ledger = self.root / "context_ledger.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_second_call_skips_same_hash_entry(self):
        entry = {"file": "references/guide.md", "section": "## First", "content": "first"}
        selected, info = delivered_entries(
            [entry], root=self.root, ledger_path=self.ledger, reference_map=self.reference_map
        )
        self.assertEqual(selected, [entry])
        self.assertEqual(info["new_count"], 1)

        selected, info = delivered_entries(
            [entry], root=self.root, ledger_path=self.ledger, reference_map=self.reference_map
        )
        self.assertEqual(selected, [])
        self.assertEqual(info["skipped_count"], 1)
        self.assertEqual(json.loads(self.ledger.read_text(encoding="utf-8"))["schema_version"], context_ledger.SCHEMA_VERSION)

    def test_source_change_returns_entry_again(self):
        entry = {"file": "references/guide.md", "section": "## First", "content": "first"}
        delivered_entries(
            [entry], root=self.root, ledger_path=self.ledger, reference_map=self.reference_map
        )
        (self.root / "references" / "guide.md").write_text(
            "## First\nchanged\n## Second\nsecond\n", encoding="utf-8"
        )
        selected, info = delivered_entries(
            [entry], root=self.root, ledger_path=self.ledger, reference_map=self.reference_map
        )
        self.assertEqual(selected, [entry])
        self.assertEqual(info["changed_count"], 1)

    def test_force_returns_same_entry_again(self):
        entry = {"file": "references/guide.md", "section": "## First", "content": "first"}
        delivered_entries(
            [entry], root=self.root, ledger_path=self.ledger, reference_map=self.reference_map
        )
        selected, info = delivered_entries(
            [entry], root=self.root, ledger_path=self.ledger,
            reference_map=self.reference_map, force=True,
        )
        self.assertEqual(selected, [entry])
        self.assertTrue(info["forced"])

    def test_route_map_change_reloads_entry(self):
        entry = {"file": "references/guide.md", "section": "## First", "content": "first"}
        delivered_entries(
            [entry], root=self.root, ledger_path=self.ledger, reference_map=self.reference_map
        )
        self.reference_map.write_text('{"changed": true}', encoding="utf-8")
        selected, info = delivered_entries(
            [entry], root=self.root, ledger_path=self.ledger, reference_map=self.reference_map
        )
        self.assertEqual(selected, [entry])
        self.assertTrue(info["map_changed"])


if __name__ == "__main__":
    unittest.main()
