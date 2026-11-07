"""Regression checks for reference navigation and complete Markdown extraction."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts import read_reference

PRODUCTION_STAGES = ("planning", "script", "assets", "storyboard",
                     "keyframes", "video", "delivery")

# 治理包全文标志串：仅当锚点子树真正被渲染时才在行首出现（定位头是 "### L.. "）。
GOVERNANCE_FULLTEXT_MARKERS = (
    "\n## 7. 自动检查与交付",
    "\n## 全局执行合同",
    "\n## 统一目录",
)
# recovery.md 下沉节标志：行首标题用于区分子树正文与 90 秒路径里的指针命令，
# 正文短语只属于对应下沉节（全 references/ 已核过唯一性）。
SUNK_RECOVERY_MARKERS = (
    "\n## 摘要与产物的信任边界（每次恢复都适用）",
    "\n## 压缩最容易丢的硬约束",
    "\n## 用户口头决定的抢救规则",
    "四种时间不可互相覆盖",
    "KF≠FRM",
    "这个决定我会记入确认记录",
)
# 每阶段 affected_<stage> 块里的稳定特征锚点，repair 默认自动激活。
AFFECTED_STAGE_MARKERS = {
    "planning": "## drama_plan.json",
    "script": "## 专业剧本格式规范",
    "assets": "## 资产生成失败处理",
    "storyboard": "## 完整分镜表",
    "keyframes": "## 登记与验收",
    "video": "## 执行顺序",
    "delivery": "## 第二部分：字幕生成与烧录",
}


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
            # 治理锚点只在 planning 入口（sections）与 governance_reload 条件可取，repair 不再默认挂载。
            ("planning", "full", [], "references/control-contracts.md", "## 1. 来源与事实锁"),
            ("planning", "full", [], "references/control-contracts.md", "## 非视频生成的阶段迁移确认"),
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

    def test_compression_recovery_routes_only_90s_section(self):
        stages = read_reference.load_map()["stages"]
        production_stages = ("planning", "script", "assets", "storyboard",
                             "keyframes", "video", "delivery")
        for stage in production_stages:
            with self.subTest(stage=stage):
                group = stages[stage]["conditional"]["compression_recovery"]
                self.assertEqual(
                    group["references/recovery.md"],
                    ["## 90 秒恢复路径（默认路径）"],
                )
                route = read_reference.resolve_route(stage, "full", ["compression_recovery"])
                recovery_sections = [
                    i["section"] for i in route["conditional_sections"]
                    if i["file"] == "references/recovery.md"
                ]
                self.assertEqual(recovery_sections, ["## 90 秒恢复路径（默认路径）"])
                text = read_reference.render_route(stage, "full", ["compression_recovery"])
                rendered = read_reference.format_rendered(text)
                self.assertIn("90 秒恢复路径", rendered)
                for marker in SUNK_RECOVERY_MARKERS:
                    self.assertNotIn(marker, rendered)
        # repair 入口默认只装载 90 秒路径一节，不再整挂恢复协议
        repair = read_reference.resolve_route("repair")
        self.assertEqual(
            repair["sections"],
            [{"file": "references/recovery.md",
              "section": "## 90 秒恢复路径（默认路径）"}],
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

    def test_batch_h_routing_downgrades(self):
        # 批次H：上游阶段写作规则不占下游入口，随对应动作条件取齐，能力不丢失。
        # storyboard：剧本侧三节降 pre_confirm_review（五项剧本-分镜对照审校时才装）；
        # 竖屏写作意图承载分镜创作期唯一竖屏构图规则、storyboard.md 无本地重复，留入口。
        sbase = {
            (i["file"], i["section"])
            for i in read_reference.resolve_route("storyboard")["sections"]
        }
        moved_to_review = [
            ("references/scriptwriter.md", "## 输入门禁"),
            ("references/scriptwriter.md", "## 视觉叙事、母题与声音意图"),
            ("references/scriptwriter.md", "## 交接"),
        ]
        for item in moved_to_review:
            self.assertNotIn(item, sbase)
        self.assertIn(
            ("references/scriptwriter.md", "## 画幅与竖屏写作意图"), sbase
        )
        review = read_reference.resolve_route(
            "storyboard", "full", ["pre_confirm_review"]
        )
        review_keys = {
            (i["file"], i["section"]) for i in review["conditional_sections"]
        }
        for item in moved_to_review:
            self.assertIn(item, review_keys)

        # keyframes：assets 前置关系/人工验收降 asset_work；本阶段「输入条件」已自带
        # approved 前置与返回资产阶段修复路径，入口不再预载上游验收机制。
        kbase = {
            (i["file"], i["section"])
            for i in read_reference.resolve_route("keyframes")["sections"]
        }
        k_moved = [
            ("references/assets.md", "## 关键帧前置关系"),
            ("references/assets.md", "## 资产人工验收"),
        ]
        for item in k_moved:
            self.assertNotIn(item, kbase)
        kwork = read_reference.resolve_route("keyframes", "full", ["asset_work"])
        kwork_keys = {
            (i["file"], i["section"]) for i in kwork["conditional_sections"]
        }
        for item in k_moved:
            self.assertIn(item, kwork_keys)

        # video：前置关系卡讲的是 assets→keyframes 边界、不涉视频执行，降 asset_work；
        # 资产使用职责表（图片传递义务）保留在入口。
        vbase = {
            (i["file"], i["section"])
            for i in read_reference.resolve_route("video")["sections"]
        }
        self.assertNotIn(("references/assets.md", "## 关键帧前置关系"), vbase)
        self.assertIn(
            ("references/assets.md", "## 当前工具链中的资产使用"), vbase
        )
        vwork = read_reference.resolve_route("video", "full", ["asset_work"])
        vwork_keys = {
            (i["file"], i["section"]) for i in vwork["conditional_sections"]
        }
        self.assertIn(("references/assets.md", "## 关键帧前置关系"), vwork_keys)

    def test_batch_l_card_and_performance_contracts_move_to_artifact_write(self):
        # 批次L：字段级合同不占阶段入口，随 artifact_write 动作条件取齐，能力不丢失。
        base_keys = {
            (i["file"], i["section"])
            for i in read_reference.resolve_route("storyboard")["sections"]
        }
        moved = [
            ("references/storyboard.md", "## 导演总控卡字段合同"),
            ("references/storyboard.md", "## 导演总控卡的逐段执行区"),
            ("references/storyboard.md", "## 开场、转场与角色表演控制"),
        ]
        for item in moved:
            self.assertNotIn(item, base_keys)
        write_route = read_reference.resolve_route(
            "storyboard", "full", ["artifact_write"]
        )
        write_keys = {
            (i["file"], i["section"]) for i in write_route["conditional_sections"]
        }
        for item in moved:
            self.assertIn(item, write_keys)
            # 降级不等于删除：子树仍可完整提取
            self.assertTrue(
                read_reference.extract_section(*item)["content"].startswith(item[1])
            )
        # repair 安全网原本就不含这三节，affected_storyboard 不因此变化
        repair = read_reference.resolve_route("storyboard", "repair")
        repair_keys = {(i["file"], i["section"]) for i in repair["conditional_sections"]}
        for item in moved:
            self.assertNotIn(item, repair_keys)

    def test_batch_n_generation_contracts_move_to_asset_work(self):
        # 批次N：生成期 Prompt 合同不占 assets 入口，随 asset_work 动作条件取齐。
        base_keys = {
            (i["file"], i["section"])
            for i in read_reference.resolve_route("assets")["sections"]
        }
        moved = [
            ("references/assets.md", "## 生图工具路由"),
            ("references/assets.md", "## 场景参考与全局风格资产"),
            ("references/assets.md", "## 角色资产"),
            ("references/assets.md", "## 道具资产"),
            ("references/assets.md", "## 图片 Prompt 与参考图引用"),
        ]
        for item in moved:
            self.assertNotIn(item, base_keys)
        work_route = read_reference.resolve_route(
            "assets", "full", ["asset_work"]
        )
        work_keys = {
            (i["file"], i["section"]) for i in work_route["conditional_sections"]
        }
        for item in moved:
            self.assertIn(item, work_keys)
            self.assertTrue(
                read_reference.extract_section(*item)["content"].startswith(item[1])
            )
        # repair 安全网（affected_assets）仍保留生成合同，能力不丢
        repair = read_reference.resolve_route("assets", "repair")
        repair_keys = {(i["file"], i["section"]) for i in repair["conditional_sections"]}
        self.assertIn(("references/assets.md", "## 生图工具路由"), repair_keys)
        self.assertIn(("references/assets.md", "## 角色资产"), repair_keys)

    def test_batch_o_regen_contract_moves_to_video_work(self):
        # 批次O：重生成编辑合同只在编辑动作时需要，不占视频入口；
        # video_work 触发语本就含「生成或编辑视频」。
        regen = ("references/video.md", "## 视频重生成编辑合同")
        base_keys = {
            (i["file"], i["section"])
            for i in read_reference.resolve_route("video")["sections"]
        }
        self.assertNotIn(regen, base_keys)
        work = read_reference.resolve_route("video", "full", ["video_work"])
        work_keys = {
            (i["file"], i["section"]) for i in work["conditional_sections"]
        }
        self.assertIn(regen, work_keys)
        self.assertTrue(
            read_reference.extract_section(*regen)["content"].startswith(regen[1])
        )
        # repair 安全网（affected_video）本就不含该锚点，编辑返修走 video_work 条件
        repair = read_reference.resolve_route("video", "repair")
        repair_keys = {
            (i["file"], i["section"]) for i in repair["conditional_sections"]
        }
        self.assertNotIn(regen, repair_keys)
        # 图片输入合同是 --ref/passed_to_tool 强制门路径，必须留在入口
        self.assertIn(("references/video.md", "## 图片输入合同"), base_keys)

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


class ReferenceRenderTests(unittest.TestCase):
    def test_render_returns_subtree_bodies_for_every_routed_heading(self):
        payload = read_reference.render_route("planning")
        route = read_reference.resolve_route("planning")
        expected = {(i["file"], i["section"]) for i in route["sections"]}
        got = {(i["file"], i["section"]) for i in payload["entries"] if i["section"]}
        self.assertEqual(expected, got)
        for entry in payload["entries"]:
            self.assertTrue(entry["content"].startswith(entry["section"] or entry["file"]))
            self.assertGreaterEqual(entry["end_line"], entry["start_line"])

    def test_render_contains_subtree_text_but_not_unrouted_whole_file_parts(self):
        text = "\n".join(e["content"] for e in read_reference.render_route("planning")["entries"])
        # 路由内锚点（画风候选卡）正文必须在
        self.assertIn("候选卡给出统一画风词、可观察机制和匹配依据", text)
        # 未路由章节（## drama_plan.json schema 节）不得随整文件泄漏
        self.assertNotIn("同时承担创作规划和执行规划", text)
        # full 动作合同默认不随阶段必读渲染
        self.assertNotIn("禁止询问用户视频内容", text)

    def test_render_is_materially_smaller_than_whole_file_reads(self):
        payload = read_reference.render_route("planning")
        rendered = sum(len(e["content"]) for e in payload["entries"])
        whole = 0
        for path in {e["file"] for e in payload["entries"]}:
            whole += len((read_reference.ROOT / path).read_text(encoding="utf-8"))
        self.assertLess(rendered, whole * 0.7, f"render {rendered} vs whole {whole}")

    def test_render_condition_adds_only_extra_subtrees(self):
        base = read_reference.render_route("planning")
        base_files = {e["file"] for e in base["entries"]}
        self.assertNotIn("references/题材亮点与传播库.md", base_files)
        gated = read_reference.render_route("planning", "full", ["genre_research"])
        gated_files = {e["file"] for e in gated["entries"]}
        self.assertIn("references/题材亮点与传播库.md", gated_files)
        # 条件锚点与基础锚点去重，不重复正文
        keys = [(e["file"], e["section"]) for e in gated["entries"]]
        self.assertEqual(len(keys), len(set(keys)))

    def test_render_include_full_loads_action_contracts(self):
        text = "\n".join(
            e["content"] for e in
            read_reference.render_route("planning", include_full=True)["entries"]
        )
        self.assertIn("禁止询问用户视频内容", text)

    def test_cli_render_text_and_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = read_reference.main(["--stage", "planning", "--render"])
        self.assertEqual(code, 0)
        rendered = output.getvalue()
        self.assertIn("# Rendered sections · planning (full)", rendered)
        self.assertIn("## references/planning.md", rendered)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = read_reference.main(["--stage", "storyboard", "--render", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertGreater(payload["entry_count"], 0)
        self.assertTrue(all(e["content"] for e in payload["entries"]))

    def test_bare_file_whole_read_only_for_full_tier_contracts(self):
        # 永久护栏：非 full 文件裸 --file 整读直接拒绝，强制 --section 子树或 --render。
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = read_reference.main(["--file", "references/storyboard.md"])
        self.assertEqual(code, 2)
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["ok"])
        self.assertIn("--section", payload["error"])
        # full 动作合同保留整读能力
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = read_reference.main(["--file", "references/troubleshooting.md"])
        self.assertEqual(code, 0)
        self.assertIn("#", output.getvalue())
        # 配对 --section 的定点读取不受影响
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = read_reference.main([
                "--file", "references/storyboard.md",
                "--section", "## 单镜因果检查",
            ])
        self.assertEqual(code, 0)
        self.assertIn("单镜因果检查", output.getvalue())

    def test_cli_render_rejects_bad_combos(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(read_reference.main(["--stage", "planning", "--include-full"]), 2)
            self.assertEqual(
                read_reference.main(["--file", "references/recovery.md", "--render"]), 2
            )

    def test_render_repair_profile_works(self):
        payload = read_reference.render_route("storyboard", "repair")
        files = {e["file"] for e in payload["entries"]}
        self.assertIn("references/recovery.md", files)

    def test_default_repair_render_omits_governance_fulltext(self):
        # 治理包不再随 repair 共享 profile 全量挂载：七阶段默认 repair 渲染
        # 只保留 90 秒恢复路径，治理全文与 recovery 下沉节均不得出现。
        for stage in PRODUCTION_STAGES:
            with self.subTest(stage=stage):
                text = read_reference.format_rendered(
                    read_reference.render_route(stage, "repair")
                )
                for marker in GOVERNANCE_FULLTEXT_MARKERS:
                    self.assertNotIn(marker, text, f"{stage} repair 泄漏治理全文：{marker}")
                self.assertIn("90 秒恢复路径", text)
                for marker in SUNK_RECOVERY_MARKERS:
                    self.assertNotIn(marker, text, f"{stage} repair 泄漏下沉节：{marker}")

    def test_default_repair_render_keeps_affected_stage_blocks(self):
        # affected_<stage> 自动激活能力不退化：受影响阶段的特征锚点仍在渲染里。
        for stage, marker in AFFECTED_STAGE_MARKERS.items():
            with self.subTest(stage=stage):
                text = read_reference.format_rendered(
                    read_reference.render_route(stage, "repair")
                )
                self.assertIn(marker, text)

    def test_governance_reload_condition_renders_full_package(self):
        # 旧能力没被删：planning 命中 governance_reload 时治理包全文可取齐。
        text = read_reference.format_rendered(
            read_reference.render_route("planning", "full", ["governance_reload"])
        )
        for marker in GOVERNANCE_FULLTEXT_MARKERS:
            self.assertIn(marker, text)

    def test_video_moved_sections_reachable_via_conditions(self):
        # T2 把生成后内容与本地运行时移出 repair 默认挂载；内容必须经条件可取，
        # 防止"摘挂载"变成静默丢失（输入模态复核含阶段末位门，曾漏挂过一次）。
        post_gen = read_reference.format_rendered(
            read_reference.render_route("video", "full", ["post_generation"])
        )
        # 行首标题才能区分子树真实挂载与权威引用节里的 --section 指针命令。
        for marker in ("\n## 输入模态复核", "proceed_assembly",
                       "\n## 第二部分：生成后抽帧与连续性"):
            self.assertIn(marker, post_gen)
        media_exec = read_reference.format_rendered(
            read_reference.render_route("video", "full", ["media_execution"])
        )
        for marker in ("\n# 本地运行时合同（Claude Code 宿主）", "\n# 执行委派 Ref"):
            self.assertIn(marker, media_exec)
        # 默认 full 不预灌这些章节（归条件触发；指针文本不算挂载）。
        default_full = read_reference.format_rendered(
            read_reference.render_route("video", "full")
        )
        self.assertNotIn("\n## 第二部分：生成后抽帧与连续性", default_full)
        self.assertNotIn("\n# 本地运行时合同（Claude Code 宿主）", default_full)

    def test_repair_render_size_stays_near_full(self):
        # 治压缩：默认 repair 不得再比 full 多灌一个治理包。阈值以 format_rendered
        # 字符数计（与 CLI stdout 同一渲染函数）。
        limits = {stage: 12000 for stage in PRODUCTION_STAGES}
        # T2 后 video repair 实测比 full 多约 13.6k 字符（repair 安全网：h3 返回值
        # 完整样例/manifests/recovery 90 秒路径，属有意保留）。批次G 把
        # 资产说明记录从 video 入口降级到 asset_work 条件（full −1.5k 字符、
        # repair 安全网不动），实测差扩到 15.3k；批次H 再把关键帧前置关系降
        # asset_work（full 再 −0.15k），实测差 15.4k；阈值 16700 保持约 1.3k 余量，
        # 并集悄悄回归仍会变红。批次O：重生成编辑合同降 video_work（repair 安全网
        # 本就不含该锚点），实测差回落到约 15.8k，阈值不动。
        limits["video"] = 16700
        # 批次L：导演总控卡字段合同/逐段执行区/开场转场表演三节（约 11k）从
        # storyboard 入口降 artifact_write，repair 安全网本来就不含这三节，
        # 差值被动扩到约 16.7k；17500 留约 0.8k 余量，并集回归仍会变红。
        limits["storyboard"] = 17500
        # 批次N：assets 五个生成合同锚点（约 21k）降 asset_work 条件，
        # affected_assets 安全网仍保留它们，差值被动扩到约 21.7k；
        # 22500 留约 0.8k 余量，并集回归仍会变红。
        limits["assets"] = 22500
        for stage in PRODUCTION_STAGES:
            with self.subTest(stage=stage):
                full = read_reference.format_rendered(
                    read_reference.render_route(stage, "full")
                )
                repair = read_reference.format_rendered(
                    read_reference.render_route(stage, "repair")
                )
                self.assertLessEqual(
                    len(repair), len(full) + limits[stage],
                    f"{stage} repair {len(repair)} 超出 full {len(full)} + {limits[stage]}",
                )

    # 绝对体积天花板（format_rendered 字符数；批 4 设立、批次G/H/K/L/N 随瘦身收紧）：
    # 阶段渲染只许缩小不许悄悄涨；确有必要的新增合同在同一提交里显式上调对应数字。
    # 批次G：script 移除 drama_plan schema 节（−8.6k）、storyboard 两节资产规则
    # 与 video 资产说明记录降级 asset_work 条件，天花板同步钉到新实际值附近。
    # 批次H：storyboard 剧本侧三节降 pre_confirm_review（−1.5k）、keyframes 两个
    # assets 锚点与 video 前置关系降 asset_work，三个天花板同步收紧。
    # 批次K：storyboard 正文脱水（删重复枚举/样板/同义复述，锚点不删），天花板收紧。
    # 批次L：导演总控卡字段合同/逐段执行区/开场转场表演三节降 artifact_write
    # 条件（约 −11k），入口只留方法概览，storyboard 天花板同步收紧到 15800。
    # 批次N：assets 五个生成合同锚点（工具路由/场景风格/角色/道具/图片 Prompt，
    # 约 −21k）降 asset_work 条件，入口只留登记/版本/交接概览，天花板收到 9200。
    # 批次O：video 重生成编辑合同降 video_work + 六处重复表述脱水，天花板收到 22000。
    FULL_RENDER_CEILINGS = {
        "planning": 32122,
        "script": 18393,
        "assets": 9200,
        "storyboard": 15800,
        "keyframes": 10059,
        "video": 22000,
        "delivery": 7123,
    }

    def test_full_render_absolute_size_ceilings(self):
        for stage, ceiling in self.FULL_RENDER_CEILINGS.items():
            with self.subTest(stage=stage):
                rendered = read_reference.format_rendered(
                    read_reference.render_route(stage, "full")
                )
                self.assertLessEqual(
                    len(rendered), ceiling,
                    f"{stage} full 渲染 {len(rendered)} 超出体积天花板 {ceiling}；"
                    "瘦身期只许缩小，确需增长请在同一提交显式更新天花板",
                )


if __name__ == "__main__":
    unittest.main()
