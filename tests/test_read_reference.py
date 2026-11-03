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
            ("planning", "full", [], "references/planning.md", "## 交付物"),
            ("repair", "repair", [], "references/control-contracts.md", "## 1. 来源与事实锁"),
            ("repair", "repair", [], "references/control-contracts.md", "## 非视频生成的阶段迁移确认"),
            ("storyboard", "full", ["beat_vocabulary"], "references/节拍类型库.md", "## §3 风格节奏档案"),
            ("script", "repair", [], "references/scriptwriter.md", "## 类型变体与差异化生成"),
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

    def test_governance_package_loads_once_at_planning(self):
        stages = read_reference.load_map()["stages"]
        planning = stages["planning"]
        cc_headings = planning["sections"]["references/control-contracts.md"]
        for heading in (
            "## 本 Ref 关键要求",
            "## 1. 来源与事实锁",
            "## 2. 阶段状态与确认",
            "## 3. 版本、引用与失效",
            "## 4. 跨阶段交接",
            "## 5. 运行完整性、证据与基础检查",
            "## 失败、重试与回炉",
            "## 6. 文件操作与恢复",
            "## 7. 自动检查与交付",
            "## 非视频生成的阶段迁移确认",
        ):
            self.assertIn(heading, cc_headings)
        sd_headings = planning["sections"]["references/skill-details.md"]
        for heading in (
            "## 全局执行合同",
            "## 状态、文件与自动校验",
            "## Prompt 文件与可见交付",
        ):
            self.assertIn(heading, sd_headings)
        self.assertEqual(
            planning["sections"]["references/manifests.md"],
            ["## 统一目录", "## 状态、失效与一致性"],
        )
        # governance_reload 条件必须指向同一批治理锚点
        reload_group = stages["planning"]["conditional"]["governance_reload"]
        self.assertIn("## 3. 版本、引用与失效",
                      reload_group["references/control-contracts.md"])
        self.assertIn("## Prompt 文件与可见交付",
                      reload_group["references/skill-details.md"])

    def test_downstream_stages_keep_only_stage_gate_card(self):
        # 治理重灌块从第 2-7 阶段 sections 移除；阶段硬门条保留且带跨会话自检。
        for stage in ("script", "assets", "storyboard", "keyframes", "video", "delivery"):
            with self.subTest(stage=stage):
                route = read_reference.resolve_route(stage)
                keys = [(i["file"], i["section"]) for i in route["sections"]]
                self.assertIn(("references/skill-details.md", f"### {stage}"), keys)
                self.assertFalse(
                    any(f == "references/control-contracts.md" for f, _ in keys),
                    f"{stage} 仍在 sections 重灌 control-contracts",
                )
                self.assertNotIn(
                    ("references/skill-details.md", "## 全局执行合同"), keys
                )
                card = next(
                    read_reference.extract_section(f, s)["content"]
                    for f, s in keys if f == "references/skill-details.md"
                )
                self.assertIn("governance_reload", card)
                self.assertIn("--stage planning", card)

    def test_governance_reload_dedupes_against_sections(self):
        # planning 入口已装治理包；显式 reload 不重复返回相同锚点。
        route = read_reference.resolve_route("planning", "full", ["governance_reload"])
        keys = {(i["file"], i["section"]) for i in route["conditional_sections"]}
        self.assertFalse(
            {"references/control-contracts.md", "references/skill-details.md"}
            & {f for f, _ in keys}
        )

    def test_compression_recovery_routes_recovery_doc(self):
        stages = read_reference.load_map()["stages"]
        for stage in ("planning", "script", "assets", "storyboard",
                      "keyframes", "video", "delivery"):
            with self.subTest(stage=stage):
                group = stages[stage]["conditional"]["compression_recovery"]
                self.assertEqual(
                    group["references/recovery.md"], ["# 压缩恢复协议"]
                )
                route = read_reference.resolve_route(stage, "full", ["compression_recovery"])
                self.assertTrue(any(
                    i["file"] == "references/recovery.md"
                    for i in route["conditional_sections"]
                ))
                text = read_reference.extract_section(
                    "references/recovery.md", "# 压缩恢复协议"
                )["content"]
                self.assertIn("governance_reload", text)
        # repair 入口直接装载恢复协议
        repair = read_reference.resolve_route("repair")
        self.assertIn(
            ("references/recovery.md", "# 压缩恢复协议"),
            {(i["file"], i["section"]) for i in repair["sections"]},
        )

    def test_media_execution_includes_delegation_authority(self):
        for stage in ("assets", "keyframes", "video", "delivery"):
            with self.subTest(stage=stage):
                spec = read_reference.load_map()["stages"][stage]
                self.assertEqual(
                    spec["conditional"]["media_execution"]["references/delegation.md"],
                    ["# 执行委派 Ref"],
                )

    def test_visible_delivery_uses_compact_card_downstream(self):
        for stage in ("script", "assets", "storyboard", "keyframes", "video", "delivery"):
            with self.subTest(stage=stage):
                spec = read_reference.load_map()["stages"][stage]
                sd = spec["conditional"]["visible_delivery"]["references/skill-details.md"]
                self.assertEqual(sd, ["## 阶段可见交付速记卡"])
                route = read_reference.resolve_route(stage, "full", ["visible_delivery"])
                card = "\n".join(
                    read_reference.extract_section(i["file"], i["section"])["content"]
                    for i in route["conditional_sections"]
                    if i["file"] == "references/skill-details.md"
                )
                self.assertIn("不授权生成新视频", card)
                self.assertIn("governance_reload", card)

    def test_delivery_gate_card_keeps_assembly_confirmation_spec(self):
        content = read_reference.extract_section(
            "references/skill-details.md", "### delivery"
        )["content"]
        self.assertIn("final_assembly_confirmation", content)
        self.assertIn("proceed_assembly", content)
        self.assertIn("--stage final", content)

    def test_batch3_routing_downgrades(self):
        # 字幕第二部分：delivery 入口不装，subtitle_requested 条件装，repair 安全网保留
        base = read_reference.resolve_route("delivery")
        base_keys = {(i["file"], i["section"]) for i in base["sections"]}
        subtitle = ("references/delivery.md", "## 第二部分：字幕生成与烧录")
        self.assertNotIn(subtitle, base_keys)
        asked = read_reference.resolve_route("delivery", "full", ["subtitle_requested"])
        self.assertIn(
            subtitle,
            {(i["file"], i["section"]) for i in asked["conditional_sections"]},
        )
        stages = read_reference.load_map()["stages"]
        self.assertIn("subtitle_requested", stages["delivery"]["condition_triggers"])
        repair = read_reference.resolve_route(
            "repair", "repair", ["affected_delivery"]
        )
        self.assertIn(
            subtitle,
            {(i["file"], i["section"]) for i in repair["conditional_sections"]},
        )

        # video 返回值登记样例：入口不装、artifact_write 装、图片输入合同留在入口、repair 保留
        vbase_keys = {
            (i["file"], i["section"]) for i in
            read_reference.resolve_route("video")["sections"]
        }
        example = ("references/video.md", "## h3-prompt-writing 返回值登记示例")
        self.assertNotIn(example, vbase_keys)
        self.assertIn(
            ("references/video.md", "## 图片输入合同"), vbase_keys
        )
        vwrite = read_reference.resolve_route("video", "full", ["artifact_write"])
        self.assertIn(
            example,
            {(i["file"], i["section"]) for i in vwrite["conditional_sections"]},
        )
        vrepair = read_reference.resolve_route("repair", "repair", ["affected_video"])
        self.assertIn(
            example,
            {(i["file"], i["section"]) for i in vrepair["conditional_sections"]},
        )

        # storyboard 外部参考节：入口不装、external_reference 装、repair 保留
        sbase_keys = {
            (i["file"], i["section"]) for i in
            read_reference.resolve_route("storyboard")["sections"]
        }
        ref_section = ("references/storyboard.md", "## 参考资料与参考视频")
        self.assertNotIn(ref_section, sbase_keys)
        external = read_reference.resolve_route(
            "storyboard", "full", ["external_reference"]
        )
        self.assertIn(
            ref_section,
            {(i["file"], i["section"]) for i in external["conditional_sections"]},
        )
        srepair = read_reference.resolve_route(
            "repair", "repair", ["affected_storyboard"]
        )
        self.assertIn(
            ref_section,
            {(i["file"], i["section"]) for i in srepair["conditional_sections"]},
        )

        # assets 专属音色：入口不装、voice_casting 装、repair 保留
        abase_keys = {
            (i["file"], i["section"]) for i in
            read_reference.resolve_route("assets")["sections"]
        }
        voice = ("references/assets.md", "## 专属音色（qwen3tts_autodl）")
        self.assertNotIn(voice, abase_keys)
        cast = read_reference.resolve_route("assets", "full", ["voice_casting"])
        self.assertIn(
            voice,
            {(i["file"], i["section"]) for i in cast["conditional_sections"]},
        )
        arepair = read_reference.resolve_route("repair", "repair", ["affected_assets"])
        self.assertIn(
            voice,
            {(i["file"], i["section"]) for i in arepair["conditional_sections"]},
        )

    def test_batch3_library_water_stays_out_and_routes_remain_valid(self):
        # 删水块不得复活；creative-index 的金句路由改指第三部分传播句策略
        highlight = (read_reference.ROOT / "references/题材亮点与传播库.md").read_text(encoding="utf-8")
        self.assertNotIn("### 九、金句/台词写作公式", highlight)
        self.assertNotIn("#### 不同位置的钩子强度", highlight)
        self.assertNotIn("### 使用合同", highlight[highlight.index("## 第三部分"):])
        audience = (read_reference.ROOT / "references/题材受众库.md").read_text(encoding="utf-8")
        self.assertNotIn("多集整体情绪曲线", audience)
        index = (read_reference.ROOT / "references/creative-index.md").read_text(encoding="utf-8")
        self.assertIn("### 三、传播句策略", index)
        self.assertNotIn("金句/台词写作公式", index)
        # 节拍库 §3 压成对照表但十档气质全部保留
        beat = read_reference.extract_section(
            "references/节拍类型库.md", "## §3 风格节奏档案"
        )["content"]
        for name in (
            "horror_dread", "comedy", "wuxia_action", "noir", "slow_cinema",
            "anime_stylized", "platform_feed", "mystery_detective",
            "romance_art", "documentary",
        ):
            self.assertIn(name, beat)

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
                    if item["file"].startswith("references/manifests")
                )
                self.assertIn("### project_script_manifest.json", schemas)
                self.assertIn("### project_data_card.json", schemas)


if __name__ == "__main__":
    unittest.main()
