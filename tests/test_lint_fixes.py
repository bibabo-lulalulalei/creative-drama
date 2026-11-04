"""lint 修法卡（scripts/lint_checks/fixes.py）回归。

守护四件事：
1. 覆盖快照：P0 关键路径码集合固定，删码/改名会被本测试拦下（扩卡是有意改动，连此快照一起改）。
2. 每张卡结构完整且对应的检查码真实存在于扫描图，--code 输出 fix.available=true。
3. 未覆盖码诚实回退 fix.available=false（「修法待补」），不许造假修法。
4. 调用点一致性：每个被覆盖码的 issue() 调用都带 hint=，且字面值与卡片 hint 完全相同；
   反过来，带 hint= 的调用其码必须在 FIXES 内——防止两处各说各话。
"""
from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_lint_contract  # noqa: E402
from lint_checks.fixes import FIXES  # noqa: E402

# P0 覆盖快照：分镜关键路径 48 码（漂移/时间输入/源覆盖/盖章/SEG 字段/因果/台账）。
EXPECTED_COVERED = {
    "timing_output_drift", "timeline_shot_set_mismatch", "pack_drift",
    "tool_duration_unrepresentable", "technical_handle_unresolved",
    "timing_budget_input_forbidden",
    "timeline_shape_invalid", "timeline_field_unknown", "timeline_id_duplicate",
    "timeline_number_invalid", "timeline_ref_unknown",
    "timeline_dependency_conflict", "timeline_dependency_cycle",
    "timing_input_invalid", "speech_span_incomplete", "speech_span_discontinuous",
    "source_revision_mismatch", "source_event_uncovered", "source_line_uncovered",
    "content_review_stale", "content_review_open_issue",
    "storyboard_shape_invalid", "storyboard_fifteen_columns_missing",
    "storyboard_source_markdown_missing", "storyboard_source_markdown_invalid",
    "director_control_card_missing", "director_control_card_invalid",
    "segment_shot_mode_invalid", "segment_tail_mode_invalid",
    "intermediate_stable_hold_reason_missing", "segment_density_profile_invalid",
    "true_one_take_shot_count_invalid",
    "reference_input_plan_missing", "reference_input_plan_invalid",
    "reference_input_plan_incomplete", "reference_role_invalid",
    "opening_binding_marker_missing",
    "causal_role_missing", "causal_role_invalid", "evidence_visibility_invalid",
    "occluded_establishes_missing", "causal_ledger_missing",
    "causal_seam_invariant_unknown", "causal_seam_invariant_missing",
    "beat_coverage_missing", "world_facts_missing",
    "audience_execution_missing", "highlight_bindings_missing",
}

# 两种 issue() 签名：lint_checks 内带 level（码在 args[1]）；时间链模块码在 args[0]。
CALL_SITE_FILES = [
    ("scripts/content_first.py", False),
    ("scripts/timeline_core.py", False),
    ("scripts/rhythm_engine.py", False),
    ("scripts/lint_checks/storyboard.py", True),
    ("scripts/lint_checks/rhythm.py", True),
    ("scripts/lint_checks/causal.py", True),
    ("scripts/lint_checks/planning.py", True),
]

CARD_KEYS = {"what", "fields", "command", "doc", "hint"}


class FixCardTests(unittest.TestCase):
    def test_covered_set_snapshot(self):
        self.assertEqual(set(FIXES), EXPECTED_COVERED)
        self.assertGreaterEqual(len(FIXES), 40)

    def test_cards_well_formed(self):
        for code, card in FIXES.items():
            with self.subTest(code=code):
                self.assertEqual(set(card), CARD_KEYS)
                self.assertTrue(card["what"].strip())
                self.assertTrue(card["doc"].strip())
                self.assertTrue(card["hint"].strip())
                self.assertIsInstance(card["fields"], list)
                self.assertTrue(card["fields"])
                self.assertTrue(all(isinstance(f, str) and f.strip() for f in card["fields"]))
                self.assertTrue(card["command"] is None or card["command"].strip())
                # doc 必须是定点读取命令（短路径），不能把模型推回整文件/源码。
                self.assertIn("--file", card["doc"])
                self.assertIn("--section", card["doc"])

    def test_code_lookup_carries_available_fix(self):
        index = build_lint_contract.scan(ROOT)
        for code, card in FIXES.items():
            with self.subTest(code=code):
                payload = build_lint_contract.lookup(ROOT, "code", code)
                self.assertGreaterEqual(payload["total"], 1, f"{code} 不是真实检查码")
                for result in payload["results"]:
                    fix = result["fix"]
                    self.assertTrue(fix["available"])
                    self.assertEqual(fix["hint"], card["hint"])
                    self.assertEqual(fix["what"], card["what"])
        # 扫描图本身仍被构建（index 健全性）
        self.assertIn("storyboard", index["dispatch"])

    def test_uncovered_code_is_honest_todo(self):
        payload = build_lint_contract.lookup(ROOT, "code", "asset_id_missing")
        self.assertTrue(payload["ok"])
        fix = payload["results"][0]["fix"]
        self.assertFalse(fix["available"])
        self.assertIn("修法待补", fix["note"])

    def test_call_site_hints_match_cards(self):
        problems = []
        for relative, has_level in CALL_SITE_FILES:
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name)
                        or node.func.id != "issue"):
                    continue
                code_arg = node.args[1] if has_level else node.args[0]
                if not isinstance(code_arg, ast.Constant) or not isinstance(code_arg.value, str):
                    continue
                code = code_arg.value
                hint_kw = next((kw for kw in node.keywords if kw.arg == "hint"), None)
                if code in FIXES:
                    if hint_kw is None:
                        problems.append(f"{relative}:{node.lineno} {code} 缺 hint=")
                    elif not isinstance(hint_kw.value, ast.Constant):
                        problems.append(f"{relative}:{node.lineno} {code} hint 必须是字符串字面量")
                    elif hint_kw.value.value != FIXES[code]["hint"]:
                        problems.append(f"{relative}:{node.lineno} {code} hint 与 FIXES 卡不一致")
                elif hint_kw is not None:
                    problems.append(f"{relative}:{node.lineno} {code} 带 hint 但不在 FIXES（先建卡）")
        self.assertEqual(problems, [])

    def test_pre_stamp_lint_payload_includes_hints(self):
        # 端到端：盖章前 lint 报的 content_review error 自带最短动作，模型无需读源码。
        from test_stamp_review import build_project
        import stamp_review

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_project(root)
            report = stamp_review.evaluate(root, "ep_1")
            review_errors = [i for i in report["lint"]["issues"]
                             if i["code"] in {"content_review_stale", "content_review_open_issue"}]
            self.assertEqual(len(review_errors), 2)
            for item in review_errors:
                self.assertTrue(item.get("hint"), item["code"])


if __name__ == "__main__":
    unittest.main()
