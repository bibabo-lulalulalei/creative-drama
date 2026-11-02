"""Regression checks for reference navigation and complete Markdown extraction."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts import read_reference


class ReferenceExtractionTests(unittest.TestCase):
    def extract(self, content: str, heading: str) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "references").mkdir()
            (root / "references" / "example.md").write_text(content, encoding="utf-8")
            return read_reference.extract_section("references/example.md", heading, root)

    def test_delivery_subtitle_contract_includes_final_gates(self):
        result = read_reference.extract_section(
            "references/delivery.md", "## 第二部分：字幕生成与烧录"
        )
        original = (read_reference.ROOT / result["file"]).read_text(encoding="utf-8")
        expected = original[original.index("## 第二部分：字幕生成与烧录"):]
        self.assertEqual(result["content"], expected)
        self.assertIn("#### 3. 时间轴按成片口播对齐", result["content"])
        self.assertIn("### 硬门", result["content"])
        self.assertIn("最终烧录成片保留无字幕母版的音轨", result["content"])
        self.assertIn("用户明确选择无字幕时", result["content"])

    def test_explicit_level_disambiguates_actual_routes(self):
        for path, heading in [
            ("references/storyboard.md", "## 每集导演总控卡"),
            ("references/video.md", "## 权威引用"),
        ]:
            with self.subTest(path=path):
                result = read_reference.extract_section(path, heading)
                self.assertEqual(result["section"], heading)
                with self.assertRaises(read_reference.ReferenceError):
                    read_reference.extract_section(path, heading.lstrip("# "))

    def test_explicit_level_never_falls_back_to_another_level(self):
        with self.assertRaises(read_reference.ReferenceError):
            self.extract("# Document\n### Only nested\ntext\n", "## Only nested")

    def test_backtick_and_tilde_fences_do_not_end_or_create_sections(self):
        content = (
            "# Document\n## Target\nBefore\n"
            "   ````python\n# Fake A\n```\n## Fake B\n"
            "~~~\n# Fake C\n   `````  \n"
            "After backticks\n"
            "  ~~~~text\n# Fake D\n~~~\n## Fake E\n"
            "```\n# Fake F\n ~~~~~\t\n"
            "### Child\nAfter tildes\n## Next\nOutside\n"
        )
        result = self.extract(content, "## Target")
        self.assertEqual(result["content"], content[content.index("## Target"):content.index("## Next")])
        for fake in ("# Fake A", "## Fake B", "# Fake C", "# Fake D", "## Fake E", "# Fake F"):
            with self.subTest(fake=fake), self.assertRaises(read_reference.ReferenceError):
                self.extract(content, fake)

    def test_fence_closer_with_info_text_does_not_close(self):
        content = "## Target\n```text\n```not a closer\n# Fake\n```\nAfter\n## Next\n"
        result = self.extract(content, "## Target")
        self.assertIn("After\n", result["content"])
        with self.assertRaises(read_reference.ReferenceError):
            self.extract(content, "# Fake")

    def test_complete_large_subtree_has_no_reading_limit(self):
        body = "完整的必要教学内容。\n" * 20000
        content = "# Document\n## Target\n" + body + "### Dependency\n末尾原文\n## Next\n"
        result = self.extract(content, "## Target")
        self.assertEqual(result["content"], "## Target\n" + body + "### Dependency\n末尾原文\n")


class ReferenceRouteTests(unittest.TestCase):
    def test_default_route_has_sections_and_condition_navigation(self):
        stages = read_reference.load_map()["stages"]
        for stage, spec in stages.items():
            with self.subTest(stage=stage):
                route = read_reference.resolve_route(stage)
                expected_sections = [
                    {"file": path, "section": heading}
                    for path, headings in spec.get("sections", {}).items()
                    for heading in headings
                ]
                self.assertEqual(route["sections"], expected_sections)
                self.assertEqual(route["section_count"], len(expected_sections))
                self.assertEqual(set(route["available_conditions"]), set(spec.get("conditional", {})))
                for condition, files in spec.get("conditional", {}).items():
                    expected = [
                        {"file": path, "section": heading}
                        for path, headings in files.items()
                        for heading in headings
                    ]
                    self.assertEqual(route["available_conditions"][condition]["sections"], expected)
                    self.assertEqual(
                        route["available_conditions"][condition]["trigger"],
                        spec.get("condition_triggers", {}).get(condition, ""),
                    )
                self.assertEqual(route, read_reference.resolve_route(stage, details=True))

    def test_every_current_route_heading_can_be_extracted(self):
        for stage, spec in read_reference.load_map()["stages"].items():
            groups = [("base", spec.get("sections", {})), *spec.get("conditional", {}).items()]
            for condition, files in groups:
                for path, headings in files.items():
                    for heading in headings:
                        with self.subTest(stage=stage, condition=condition, path=path, heading=heading):
                            result = read_reference.extract_section(path, heading)
                            self.assertTrue(result["content"].startswith(heading))
                            self.assertGreaterEqual(result["end_line"], result["start_line"])

    def test_repair_profile_preserves_navigation(self):
        stages = read_reference.load_map()["stages"]
        for condition in stages["repair"].get("conditional", {}):
            if not condition.startswith("affected_"):
                continue
            stage = condition.removeprefix("affected_")
            if stage not in stages:
                continue
            route = read_reference.resolve_route(stage, "repair")
            self.assertEqual(route["conditions"], [condition])
            self.assertEqual(route["conditional_sections"], route["available_conditions"][condition]["sections"])

    def test_cli_default_outputs_navigation(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = read_reference.main(["--stage", "storyboard"])
        self.assertEqual(code, 0)
        route = json.loads(output.getvalue())
        self.assertTrue(route["sections"])
        self.assertIn("available_conditions", route)

    def test_repair_action_conditions_preserve_affected_stage_and_explicit_override(self):
        route = read_reference.resolve_route("storyboard", "repair", ["visible_delivery"])
        self.assertEqual(route["conditions"], ["affected_storyboard", "visible_delivery"])
        self.assertTrue(any(item["file"] == "references/storyboard.md" for item in route["conditional_sections"]))
        override = read_reference.resolve_route("storyboard", "repair", ["affected_script", "visible_delivery"])
        self.assertEqual(override["conditions"], ["affected_script", "visible_delivery"])

    def test_semantic_review_authority_is_reachable_in_full_and_repair(self):
        for stage, mode in (("storyboard", "full"), ("storyboard", "repair")):
            with self.subTest(stage=stage, mode=mode):
                route = read_reference.resolve_route(stage, mode)
                entries = route["sections"] + route["conditional_sections"]
                contracts = [
                    read_reference.extract_section(item["file"], item["section"])["content"]
                    for item in entries
                    if item["file"] == "references/skill-details.md"
                ]
                content = "\n".join(contracts)
                for gate in ("**beat 覆盖**", "**世界事实**", "**台词逐字**", "**结构顺读**", "**三锚对照**"):
                    self.assertIn(gate, content)

    def test_downstream_writing_rules_are_loaded_when_their_action_runs(self):
        # 这些章节是下游硬门依赖的上游写作规则，必须随对应动作实际进入路由。
        required = [
            ("script", "full", [], "references/scriptwriter.md", "## 视觉叙事、母题与声音意图"),
            ("script", "full", [], "references/scriptwriter.md", "## 画幅与竖屏写作意图"),
            ("script", "full", [], "references/scriptwriter.md", "## 类型变体与差异化生成"),
            ("video", "full", [], "references/video.md", "## 可选叙事过渡"),
            ("video", "full", [], "references/video.md", "## 不同场景类型的交付包侧重点"),
            ("planning", "full", [], "references/planning.md", "## 交付物"),
            ("repair", "repair", [], "references/control-contracts.md", "## 1. 来源与事实锁"),
            ("repair", "repair", [], "references/control-contracts.md", "## 非视频生成的阶段迁移确认"),
            ("storyboard", "full", ["beat_vocabulary"], "references/节拍类型库.md", "## §3 风格节奏档案"),
            ("script", "repair", [], "references/scriptwriter.md", "## 类型变体与差异化生成"),
            ("video", "repair", [], "references/video.md", "## 不同场景类型的交付包侧重点"),
        ]
        for stage, mode, conditions, path, heading in required:
            with self.subTest(stage=stage, mode=mode, heading=heading):
                route = read_reference.resolve_route(stage, mode, conditions)
                entries = route["sections"] + route["conditional_sections"]
                self.assertTrue(any(item["file"] == path and item["section"] == heading for item in entries))
                result = read_reference.extract_section(path, heading)
                self.assertTrue(result["content"].startswith(heading))

    def test_highlight_ledger_execution_comes_with_the_routed_subtree(self):
        result = read_reference.extract_section(
            "references/scriptwriter.md", "## 类型变体与差异化生成"
        )
        self.assertIn("### 逐集亮点执行", result["content"])
        self.assertIn("highlight_ledger", result["content"])

    def test_final_stage_alias_routes_to_delivery(self):
        direct = read_reference.resolve_route("delivery")
        aliased = read_reference.resolve_route("final")
        self.assertEqual(aliased["stage"], "delivery")
        self.assertEqual(aliased["sections"], direct["sections"])
        repair = read_reference.resolve_route("final", "repair")
        self.assertEqual(repair["conditions"], ["affected_delivery"])
        self.assertEqual(repair["conditional_sections"],
                         repair["available_conditions"]["affected_delivery"]["sections"])

    def test_global_story_schemas_remain_available_at_their_creation_stage(self):
        # full 模式下项目级 schema 随 artifact_write 动作加载；返修由 affected_script 带齐。
        cases = [("script", "full", ["artifact_write"]), ("script", "repair", [])]
        for stage, mode, conditions in cases:
            with self.subTest(mode=mode):
                route = read_reference.resolve_route(stage, mode, conditions)
                entries = route["sections"] + route["conditional_sections"]
                schemas = "\n".join(
                    read_reference.extract_section(item["file"], item["section"])["content"]
                    for item in entries
                    if item["file"] == "references/manifests.md"
                )
                self.assertIn("### project_script_manifest.json", schemas)
                self.assertIn("### project_data_card.json", schemas)


if __name__ == "__main__":
    unittest.main()
