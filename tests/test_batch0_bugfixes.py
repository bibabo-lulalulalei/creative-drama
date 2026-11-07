"""Batch 0 审计修复回归测试。

覆盖四只在真实流水线里难以触发、但会改变门裁决的缺陷：
- B1 偏差接受快照 output_file 字符串逐字比对，路径写法不同即永远不过门；
- B2 content_first 只索引 characters/props 的 states，scenes 与 state_timeline 全部漏索引；
- B5 SEG 漏填 duration_s 时 shot_mode/density/一镜到底数量门被整组绕过；
- B6 VOICE 样音路径策略挂在 reference_inputs 的不可达 audio 分支，真槽位 audio_inputs 无门。
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from content_first import load_source  # noqa: E402
from drama_lint import check_storyboards  # noqa: E402
from drama_lint import (  # noqa: E402
    check_quality_acceptance,
    check_voice_sample_paths,
)

CONFIRMED_AT = "2026-11-03T10:00:00+08:00"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return sha256_bytes(path.read_bytes())


class QualityAcceptanceSnapshotTests(unittest.TestCase):
    """B1：quality_deviation_snapshot.output_file 两侧按规范化项目相对路径比对。"""

    def _project(self, recorded_output: str, manifest_output: str = "episodes/ep_1/04_视频片段/seg_SEG001_v01.mp4"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        output = root / manifest_output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake-video-bytes")
        digest = sha256_bytes(b"fake-video-bytes")
        deviations = [{"deviation_id": "DEV1", "scope": "shadow_density", "detail": "暗部略平，接受"}]
        record = {
            "stage": "video",
            "episode_id": "ep_1",
            "decision": "confirmed",
            "confirmation_mode": "full",
            "revision": 1,
            "confirmation_id": "CONF-DEV-1",
            "user_message": "我接受这个偏差，继续。",
            "confirmed_at": CONFIRMED_AT,
            "quality_deviation_snapshot": {
                "episode_id": "ep_1",
                "segment_id": "SEG001",
                "output_file": recorded_output,
                "output_sha256": digest,
                "deviations": deviations,
            },
        }
        log = root / "00_制作控制/用户确认记录.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
        gate = {"status": "deviation_accepted", "blockers": [], "deviations": deviations, "user_acceptance_ref": "CONF-DEV-1"}
        return root, gate, manifest_output

    def _codes(self, root, gate, manifest_output):
        issues: list[dict] = []
        check_quality_acceptance(root, gate, "ep_1", "SEG001", manifest_output, root / "gate.json", issues)
        return {item["code"] for item in issues}

    def test_dot_prefix_equivalent_to_canonical_relative_path(self):
        root, gate, manifest_output = self._project("./episodes/ep_1/04_视频片段/seg_SEG001_v01.mp4")
        self.assertEqual(self._codes(root, gate, manifest_output), set())

    @unittest.skipUnless(sys.platform == "win32", "反斜杠路径归一化只在 Windows 可解析")
    def test_backslash_record_matches_posix_manifest(self):
        root, gate, manifest_output = self._project(
            "episodes\\ep_1\\04_视频片段\\seg_SEG001_v01.mp4"
        )
        self.assertEqual(self._codes(root, gate, manifest_output), set())

    def test_different_output_file_still_blocks(self):
        root, gate, manifest_output = self._project("episodes/ep_1/04_视频片段/seg_SEG001_other.mp4")
        # 记录里指向另一个文件：canonical 路径不同，必须继续阻断。
        self.assertIn("quality_deviation_acceptance_missing", self._codes(root, gate, manifest_output))


class DataCardStateIndexTests(unittest.TestCase):
    """B2：load_source 必须索引 CHR/SCN/PROP 三类主体 state_timeline 状态。"""

    def test_scene_and_prop_states_indexed_from_state_timeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            md_rel = "episodes/ep_1/01_剧本/剧本_完整剧本_ep_1.md"
            md_path = root / md_rel
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text("# 完整剧本\n", encoding="utf-8")
            contract = {
                "episode_id": "ep_1",
                "revision": 1,
                "source_markdown": md_rel,
                "source_sha256": sha256_bytes(md_path.read_bytes()),
                "scenes": [],
            }
            contract_rel = "episodes/ep_1/01_剧本/script_contract_ep_1.json"
            contract_path = root / contract_rel
            contract_path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
            contract_sha = sha256_bytes(contract_path.read_bytes())
            write_json(
                root / "00_制作控制/project_data_card.json",
                {
                    "characters": [
                        {"character_id": "CHR001", "state_timeline": [{"state_id": "STATE001"}]},
                    ],
                    "scenes": [
                        {"scene_id": "SCN001", "state_timeline": [{"state_id": "SSTATE001"}]},
                    ],
                    "props": [
                        {"prop_id": "PROP001", "state_timeline": [{"state_id": "PSTATE001"}]},
                    ],
                },
            )
            record = {
                "stage": "script",
                "episode_id": "ep_1",
                "decision": "confirmed",
                "confirmation_mode": "full",
                "revision": 1,
                "confirmation_id": "CONF-SCRIPT-1",
                "user_message": "剧本确认。",
                "confirmed_at": CONFIRMED_AT,
                "source_snapshot": {"file": contract_rel, "sha256": contract_sha},
            }
            log = root / "00_制作控制/用户确认记录.jsonl"
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            inp = {
                "episode_id": "ep_1",
                "source_script": {"file": contract_rel, "revision": 1, "sha256": contract_sha},
                "utterances": [],
            }
            index, issues = load_source(root, inp, {"causal_ledger": []})
            self.assertEqual([item["code"] for item in issues], [])
            for key in (
                "asset_state:CHR001:STATE001",
                "asset_state:SCN001:SSTATE001",
                "asset_state:PROP001:PSTATE001",
            ):
                self.assertIn(key, index, key)


class SegmentGatesWithoutDurationTests(unittest.TestCase):
    """B5：SEG 无 duration_s 时，shot_mode/density/一镜到底数量门仍然生效。"""

    def test_enum_and_one_take_gates_fire_without_duration_s(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sb_dir = root / "episodes/ep_1/02_分镜"
            sb_dir.mkdir(parents=True)
            (sb_dir / "导演总控卡_ep_1.md").write_text("# 导演总控卡\n", encoding="utf-8")
            table = "| " + " | ".join(f"c{i}" for i in range(15)) + " |\n"
            table += "| " + " | ".join("---" for _ in range(15)) + " |\n"
            (sb_dir / "分镜_完整分镜表_ep_1.md").write_text(table, encoding="utf-8")
            storyboard = {
                "episode_id": "ep_1",
                "director_control_card": "episodes/ep_1/02_分镜/导演总控卡_ep_1.md",
                "source_markdown": "episodes/ep_1/02_分镜/分镜_完整分镜表_ep_1.md",
                "shots": [
                    {"shot_id": "E01S01-SHOT001", "segment_id": "SEG001", "scene_id": "E01S01"},
                    {"shot_id": "E01S01-SHOT002", "segment_id": "SEG001", "scene_id": "E01S01"},
                ],
                "segments": [
                    {
                        "segment_id": "SEG001",
                        "shot_ids": ["E01S01-SHOT001", "E01S01-SHOT002"],
                        "shot_mode": "true_one_take",
                        "density_profile": "not_a_profile",
                        "tail_mode": "cuttable_completion",
                        "reference_input_plan": [],
                    }
                ],
                "asset_usage_plan": [],
                "inherited_world_facts": [
                    {"fact_id": "WF001", "category": "weather", "statement": "夜雨", "source": "ep_1 剧本 S01"}
                ],
                "beat_coverage": [],
                "highlight_bindings": [],
            }
            (sb_dir / "storyboard_ep_1.json").write_text(
                json.dumps(storyboard, ensure_ascii=False), encoding="utf-8"
            )
            issues: list[dict] = []
            check_storyboards(root, None, issues)
            codes = {item["code"] for item in issues}
            self.assertIn("segment_density_profile_invalid", codes)
            self.assertIn("true_one_take_shot_count_invalid", codes)


class VoiceSamplePathPolicyTests(unittest.TestCase):
    """B6：声线参考槽位（audio_inputs）必须执行 VOICE 样音路径策略。"""

    def _codes(self, audio_inputs):
        issues: list[dict] = []
        segment = {"segment_id": "SEG001", "audio_inputs": audio_inputs}
        check_voice_sample_paths(segment, {}, Path("video_manifest.json"), issues)
        return {item["code"] for item in issues}

    def test_tts_temp_audio_in_voice_slot_blocked(self):
        codes = self._codes(
            [{"role": "voice_audio_reference", "file": "episodes/ep_1/04_视频片段/tts_tmp_LINE001.wav"}]
        )
        self.assertIn("ref_audio_not_voice_sample", codes)

    def test_approved_voice_sample_path_allowed(self):
        codes = self._codes(
            [{"role": "voice_audio_reference", "file": "shared/03_资产/音色/VOICE001/sample_approved_v01.wav"}]
        )
        self.assertNotIn("ref_audio_not_voice_sample", codes)

    def test_non_voice_audio_roles_skipped(self):
        codes = self._codes(
            [{"role": "music_reference", "file": "episodes/ep_1/04_视频片段/tmp_music.wav"}]
        )
        self.assertNotIn("ref_audio_not_voice_sample", codes)


if __name__ == "__main__":
    unittest.main()
