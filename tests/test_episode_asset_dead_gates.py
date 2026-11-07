"""批次S：asset_usage episode_assets 死门删除的回归钉。

manifests.md 规定 episode_assets 项的唯一字段清单为
asset_id/entity_scope/state_id/version/files/status（禁止自造字段），
generation/category/visual_reference_decision 等合同字段只存在于 asset_registry。
因此原 8 个 episode_ 孪生图片工具码在该台账面结构不可达，已整组删除；
registry 面的 8 个基础码一条不丢。本测试钉住：
1. registry 面八码仍按原条件触发；
2. episode_assets 携带 schema 外字段时不触发任何图片工具/样音门，
   schema 内检查（重复、状态枚举）照常生效；
3. 八个死码字面量不得回流 drama_lint.py。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from drama_lint import check_assets  # noqa: E402

DEAD_CODES = [
    "episode_image_gen_should_not_have_visual_inputs",
    "episode_image_gen_visual_reference_available",
    "episode_image_gen_visual_reference_decision_conflict",
    "episode_image_edit_reference_missing",
    "episode_image_edit_visual_reference_decision_conflict",
    "episode_character_state_asset_requires_image_edit",
    "episode_project_visual_mode_missing_or_invalid",
    "episode_visual_reference_decision_invalid",
]

REGISTRY_EXPECTED = {
    "project_visual_mode_missing_or_invalid",
    "image_gen_should_not_have_visual_inputs",
    "image_edit_reference_missing",
    "image_gen_visual_reference_available",
    "image_gen_visual_reference_decision_conflict",
    "image_edit_visual_reference_decision_conflict",
    "character_state_asset_requires_image_edit",
    "visual_reference_decision_invalid",
}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class ImageToolContractSurfaceTests(unittest.TestCase):
    def _project(self, registry_assets: list[dict], episode_assets: list[dict]) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        write_json(
            root / "shared/03_资产/asset_registry.json",
            {"project_id": "P1", "revision": 1, "assets": registry_assets},
        )
        write_json(
            root / "episodes/ep_1/03_资产/asset_usage_ep_1.json",
            {"episode_id": "ep_1", "revision": 1, "episode_assets": episode_assets},
        )
        return root

    def test_registry_surface_still_enforces_all_eight_rules(self):
        def gen(tool: str, **extra) -> dict:
            return {"tool": tool, "prompt_path": "shared/03_资产/prompts/p.md", **extra}

        registry_assets = [
            {
                "asset_id": "CHR001", "category": "character", "version": "v01", "status": "approved",
                "reference_asset_ids": ["CHR000"],
                "generation": gen("image_gen"),
            },
            {
                "asset_id": "SCN001", "category": "scene", "version": "v01", "status": "draft",
                "generation": gen("image_edit"),
            },
            {
                "asset_id": "PROP001", "category": "prop", "version": "v01", "status": "draft",
                "available_visual_reference_ids": ["PROP000"],
                "generation": gen("image_gen"),
            },
            {
                "asset_id": "PROP002", "category": "prop", "version": "v01", "status": "draft",
                "visual_reference_decision": "used",
                "generation": gen("image_gen"),
            },
            {
                "asset_id": "SCN002", "category": "scene", "version": "v01", "status": "draft",
                "reference_asset_ids": ["SCN000"],
                "visual_reference_decision": "none_available",
                "generation": gen("image_edit"),
            },
            {
                "asset_id": "CHR002", "category": "character", "version": "v01", "status": "draft",
                "state_id": "STATE001",
                "generation": gen("image_gen"),
            },
            {
                "asset_id": "CHR003", "category": "character", "version": "v01", "status": "draft",
                "visual_reference_decision": "bogus",
            },
        ]
        root = self._project(registry_assets, [])
        (root / "shared/03_资产/prompts").mkdir(parents=True, exist_ok=True)
        (root / "shared/03_资产/prompts/p.md").write_text("# prompt\n", encoding="utf-8")
        issues: list[dict] = []
        check_assets(root, issues)
        self.assertEqual({item["code"] for item in issues}, REGISTRY_EXPECTED)

    def test_episode_surface_ignores_schema_foreign_generation_fields(self):
        episode_assets = [
            {
                # schema 外字段全家桶：按 manifests.md 唯一清单这些字段不得存在，
                # 即使手写进来也不触发图片工具门（合同只在 registry 面校验）。
                "asset_id": "CHR101", "state_id": "STATE101", "version": "v01", "status": "approved",
                "category": "character", "project_visual_mode": "bogus",
                "visual_reference_decision": "bogus",
                "reference_asset_ids": ["CHR000"],
                "generation": {"tool": "image_gen", "reference_inputs": ["x.png"]},
            },
            {
                # category=voice 同样是 schema 外字段：分集面不再有声样技术核验门。
                "asset_id": "VOICE101", "state_id": "", "version": "v01", "status": "approved",
                "category": "voice", "files": ["episodes/ep_1/03_资产/missing.wav"],
            },
            {
                # schema 内真实违规：重复三元组 + 非法状态，必须照常报。
                "asset_id": "CHR102", "state_id": "STATE102", "version": "v01", "status": "approved",
            },
            {
                "asset_id": "CHR102", "state_id": "STATE102", "version": "v01", "status": "bogus_status",
            },
        ]
        root = self._project([], episode_assets)
        issues: list[dict] = []
        check_assets(root, issues)
        codes = {item["code"] for item in issues}
        # 只剩 schema 内检查：重复三元组、状态枚举、files 存在性。
        self.assertEqual(
            codes,
            {"episode_asset_duplicate", "episode_asset_status_invalid", "episode_asset_file_missing"},
        )
        for dead in DEAD_CODES:
            self.assertNotIn(dead, codes)
        self.assertNotIn("voice_sample_invalid", codes)

    def test_dead_codes_absent_from_lint_source(self):
        source = (ROOT / "scripts/drama_lint.py").read_text(encoding="utf-8")
        for dead in DEAD_CODES:
            self.assertNotIn(dead, source)
        base_codes = [code for code in REGISTRY_EXPECTED]
        for code in base_codes:
            self.assertIn(code, source)


if __name__ == "__main__":
    unittest.main()
