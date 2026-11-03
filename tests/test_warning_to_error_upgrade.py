"""附录 B 裁决回归：10 个原 warning 码升级为 error。

每只在真实流水线里被无视也不阻断合格交付（release_ready 只数 error），
主审建议与用户拍板（2026-11-03）：全部升 error。本文件逐码证明门真的会以
error 级别响；不得为让测试变绿而降级或删门。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lint_checks.causal import check_causal_ledger  # noqa: E402
from lint_checks.storyboard import check_asset_usage_reconciliation  # noqa: E402


def run_ledger(root: Path, data: dict, shots: list[dict], segment_of: dict[str, str],
               segment_order: list[str]) -> set[tuple[str, str]]:
    issues: list[dict] = []
    shot_ids = {shot["shot_id"] for shot in shots}
    shot_positions = {shot_id: index for index, shot_id in enumerate(sorted(shot_ids))}
    check_causal_ledger(
        root, data, "ep_1", shots, shot_ids, shot_positions, segment_of,
        segment_order, set(), Path("storyboard_ep_1.json"), issues,
    )
    return {(item["code"], item["level"]) for item in issues}


def valid_chain(**overrides) -> dict:
    chain = {
        "chain_id": "CL01",
        "trigger_fact": "戒指在死者手中",
        "visibility_contract": "证据在 SEG001 完整可见",
        "trigger_source": {"ref_type": "world_fact", "ref_id": "WF01"},
        "evidence_shot_ids": [],
        "reaction_shot_ids": [],
        "result_shot_ids": [],
    }
    chain.update(overrides)
    return chain


class CausalWarningUpgradeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _codes(self, data: dict, shots: list[dict] | None = None,
               segment_of: dict[str, str] | None = None,
               segment_order: list[str] | None = None) -> set[tuple[str, str]]:
        shots = shots or []
        return run_ledger(self.root, data, shots, segment_of or {}, segment_order or [])

    def test_causal_role_invalid_is_error(self):
        codes = self._codes({"causal_ledger": []}, [{"shot_id": "S1", "causal_role": "narrator"}])
        self.assertIn(("causal_role_invalid", "error"), codes)

    def test_causal_trigger_fact_missing_is_error(self):
        shots = [{
            "shot_id": "S1", "causal_role": "reaction",
            "responds_to": {"ref_type": "shot", "ref_id": "S1"},
        }]
        codes = self._codes({"causal_ledger": []}, shots)
        self.assertIn(("causal_trigger_fact_missing", "error"), codes)

    def test_occluded_establishes_missing_is_error(self):
        shots = [{"shot_id": "S1", "causal_role": "evidence", "evidence_visibility": "occluded"}]
        codes = self._codes({"causal_ledger": []}, shots)
        self.assertIn(("occluded_establishes_missing", "error"), codes)

    def test_causal_chain_breakpoint_risk_invalid_is_error(self):
        codes = self._codes({"causal_ledger": [valid_chain(breakpoint_risk="C9")]})
        self.assertIn(("causal_chain_breakpoint_risk_invalid", "error"), codes)

    def test_causal_chain_empty_is_error(self):
        codes = self._codes({"causal_ledger": [valid_chain()]})
        self.assertIn(("causal_chain_empty", "error"), codes)

    def _crossing_setup(self) -> tuple[dict, list[dict], dict[str, str], list[str]]:
        shots = [
            {"shot_id": "E1", "causal_role": "evidence", "establishes": "戒指特写",
             "evidence_visibility": "in_frame"},
            {"shot_id": "R1", "causal_role": "reaction",
             "responds_to": {"ref_type": "shot", "ref_id": "E1", "trigger_fact": "戒指出现"}},
        ]
        segment_of = {"E1": "SEG001", "R1": "SEG002"}
        data = {
            "seams": [{"from_segment": "SEG001", "to_segment": "SEG002", "seam_id": "SEAM01"}],
            "causal_ledger": [valid_chain(evidence_shot_ids=["E1"], reaction_shot_ids=["R1"])],
        }
        return data, shots, segment_of, ["SEG001", "SEG002"]

    def test_causal_seam_invariant_unknown_is_error(self):
        data, shots, segment_of, order = self._crossing_setup()
        codes = self._codes(data, shots, segment_of, order)
        self.assertIn(("causal_seam_invariant_unknown", "error"), codes)

    def test_causal_seam_invariant_missing_is_error(self):
        ledger = self.root / "episodes/ep_1/02_分镜/分镜_连续性账本_ep_1.md"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text("| seam_id | 必须保持 |\n|---|---|\n| SEAM01 | 无 |\n", encoding="utf-8")
        data, shots, segment_of, order = self._crossing_setup()
        codes = self._codes(data, shots, segment_of, order)
        self.assertIn(("causal_seam_invariant_missing", "error"), codes)

    def test_causal_seam_invariant_present_passes(self):
        ledger = self.root / "episodes/ep_1/02_分镜/分镜_连续性账本_ep_1.md"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(
            "| seam_id | 必须保持 |\n|---|---|\n| SEAM01 | 戒指在右手、光线方向不变 |\n",
            encoding="utf-8",
        )
        data, shots, segment_of, order = self._crossing_setup()
        codes = self._codes(data, shots, segment_of, order)
        self.assertNotIn("causal_seam_invariant_unknown", {c for c, _ in codes})
        self.assertNotIn("causal_seam_invariant_missing", {c for c, _ in codes})

    def test_causal_chain_ref_unknown_is_error(self):
        card_dir = self.root / "episodes/ep_1/02_分镜"
        card_dir.mkdir(parents=True, exist_ok=True)
        (card_dir / "导演总控卡_ep_1.md").write_text(
            "台词证据链登记 causal_chain_ref: CL99 为核心反转。\n", encoding="utf-8"
        )
        codes = self._codes({"causal_ledger": []})
        self.assertIn(("causal_chain_ref_unknown", "error"), codes)


class AssetUsageWarningUpgradeTests(unittest.TestCase):
    def _codes(self, data: dict) -> set[tuple[str, str]]:
        issues: list[dict] = []
        check_asset_usage_reconciliation(
            data, {"known_asset_ids": set()}, Path("storyboard_ep_1.json"), issues
        )
        return {(item["code"], item["level"]) for item in issues}

    def test_asset_version_inconsistent_is_error(self):
        data = {
            "segments": [{
                "segment_id": "SEG001",
                "reference_input_plan": [
                    {"planned_source": "CHR001_v02", "role": "identity_reference"}
                ],
            }],
            "asset_usage_plan": [
                {"asset_id": "CHR001", "version": "v01", "segments": ["SEG001"]}
            ],
        }
        self.assertIn(("asset_version_inconsistent", "error"), self._codes(data))

    def test_asset_planned_but_unregistered_is_error(self):
        data = {
            "segments": [{
                "segment_id": "SEG001",
                "reference_input_plan": [
                    {"planned_source": "CHR001_v01", "role": "identity_reference"}
                ],
            }],
            "asset_usage_plan": [],
        }
        self.assertIn(("asset_planned_but_unregistered", "error"), self._codes(data))


if __name__ == "__main__":
    unittest.main()
