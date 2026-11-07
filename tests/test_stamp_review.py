"""stamp_review.py 盖章 CLI 回归测试。

用一个最小但 storyboard 阶段全绿（仅缺 content_review 章）的合成项目验证：
- 无旗标只打印清单、绝不写文件；
- 结构门有任何非 content_review error 时拒绝盖章（exit 2）；
- 已存在 open_issues 非空时拒绝盖章；
- 盖章写三元指纹、open_issues 清空、复检 release_ready；
- 幂等：对当前设计重复盖章结果不变；
- 设计改动后章过期（content_review_stale）。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import stamp_review  # noqa: E402

CONFIRMED_AT = "2026-11-04T10:00:00+08:00"
SHOT = "E01S01-SHOT001"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_project(root: Path) -> tuple[Path, Path]:
    """构造最小全绿项目，返回 (storyboard_path, rhythm_input_path)。"""

    def w(rel: str, payload) -> Path:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    plan = {
        "revision": 1,
        "objective": {"target_stage": "final"},
        "selected_direction_id": "D1",
        "creative_mechanism": {"selection_mode": "divergent",
                               "candidates": [{"primary": "反差机制", "supporting": []}],
                               "primary": "反差机制", "supporting": []},
        "rhythm_design": {},
        "audience_plan": {
            "target_audience": "通勤刷手机的年轻人", "core_pain_or_desire": "想被吓一下",
            "platform": "抖音", "evidence_status": "假设",
            "viewing_focus": "白烛自燃", "emotional_payoff": "后背发凉",
            "platform_viewing_context": "夜间手机独看", "expression_boundaries": "无血腥",
            "execution_sources": {f: f"audience_plan.{f}" for f in (
                "viewing_focus", "emotional_payoff", "platform_viewing_context",
                "expression_boundaries")},
        },
        "type_strategy": {k: "x" for k in (
            "format", "subject_route", "genre", "story_engine", "audience_promise",
            "narrative_structure", "main_path")},
        "highlight_strategy": {k: "x" for k in (
            "primary_story_engine_id", "project_signature", "highlight_pillars",
            "distribution_policy", "rejected_cliches")},
        "style_contract": {k: "x" for k in (
            "anchor_type", "anchor", "lighting", "color", "composition", "material",
            "camera_tendency", "sound_tendency", "excluded_mechanisms")},
        "scale_plan": {"episode_count": 1, "episode_durations_s": [60], "total_duration_s": 60},
        "duration_contract": {"mode": "unbounded", "scope": "project",
                              "target_duration_s": None, "tolerance_ratio": None, "bounds": None},
    }
    w("00_制作控制/drama_plan.json", plan)
    w("00_制作控制/制作状态.json", {
        "current_stage": "storyboard", "current_episode": "ep_1",
        "phases": {"planning": "confirmed", "script": "confirmed", "assets": "confirmed",
                   "storyboard": "in_progress", "keyframes": "pending", "video": "pending",
                   "final": "pending"},
        "episodes": {"ep_1": {"stage_status": {
            "script": "confirmed", "assets": "confirmed", "storyboard": "in_progress",
            "keyframes": "pending", "video": "pending", "final": "pending"}}},
    })
    w("00_制作控制/project_data_card.json",
      {"revision": 1, "characters": [], "scenes": [], "props": []})
    w("shared/03_资产/asset_registry.json", {"assets": []})
    w("episodes/ep_1/03_资产/asset_usage_ep_1.json", {})
    w("episodes/ep_1/episode_manifest_ep_1.json", {"episode_id": "ep_1", "stage_manifests": {
        "script": "episodes/ep_1/01_剧本/script_contract_ep_1.json",
        "storyboard": "episodes/ep_1/02_分镜/storyboard_ep_1.json",
        "assets": "episodes/ep_1/03_资产/asset_usage_ep_1.json",
        "keyframes": "episodes/ep_1/03_资产/keyframe_manifest_ep_1.json",
        "video": "episodes/ep_1/04_视频片段/video_manifest_ep_1.json",
        "continuity": "episodes/ep_1/04_视频片段/continuity_ep_1.json",
        "delivery": "episodes/ep_1/05_成片/delivery_manifest_ep_1.json",
    }})

    script_md = w("episodes/ep_1/01_剧本/剧本_完整剧本_ep_1.md",
                  "# 完整剧本 ep_1\n\n## E01S01 夜 灵堂\n\n白烛自燃。\n")
    contract = {
        "episode_id": "ep_1", "revision": 1,
        "source_markdown": "episodes/ep_1/01_剧本/剧本_完整剧本_ep_1.md",
        "source_sha256": sha256_bytes(script_md.read_bytes()),
        "scenes": [{"scene_id": "E01S01",
                    "events": [{"event_id": "B001", "source_excerpt": "白烛自燃。",
                                "summary": "灵位前白烛无故自燃"}],
                    "speech_lines": []}],
        "highlight_ledger": [],
    }
    contract_path = w("episodes/ep_1/01_剧本/script_contract_ep_1.json", contract)

    records = [
        {"stage": "planning", "decision": "confirmed", "confirmation_mode": "full", "revision": 1,
         "user_message": "方案可以，开工", "confirmed_at": CONFIRMED_AT,
         "confirmation_purpose": "project_execution", "interaction_ask_call_id": "call-plan-1",
         "interaction_ask_result": "proceed_project"},
        {"stage": "script", "decision": "confirmed", "confirmation_mode": "full", "revision": 1,
         "user_message": "全局故事包确认", "confirmed_at": CONFIRMED_AT},
        {"stage": "script", "episode_id": "ep_1", "decision": "confirmed",
         "confirmation_mode": "full", "revision": 1, "user_message": "本集剧本确认",
         "confirmed_at": CONFIRMED_AT, "confirmation_id": "CONF-SCRIPT-EP1-1",
         "source_snapshot": {"file": "episodes/ep_1/01_剧本/script_contract_ep_1.json",
                             "sha256": sha256_bytes(contract_path.read_bytes())}},
        {"stage": "assets", "episode_id": "ep_1", "decision": "confirmed",
         "confirmation_mode": "full", "revision": 1, "user_message": "资产确认",
         "confirmed_at": CONFIRMED_AT},
    ]
    w("00_制作控制/用户确认记录.jsonl",
      "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n")

    timing_path = w("episodes/ep_1/02_分镜/rhythm_input_ep_1.json", {
        "episode_id": "ep_1",
        "source_script": {"file": "episodes/ep_1/01_剧本/script_contract_ep_1.json",
                          "revision": 1, "sha256": sha256_bytes(contract_path.read_bytes())},
        "utterances": [],
        "scenes": [{"scene_id": "E01S01", "shots": [{
            "shot_id": SHOT,
            "timeline": [{"event_id": "V001", "kind": "visual",
                          "process": "灵位前白烛无故自燃的完整可见过程",
                          "source_refs": ["beat:B001"], "start_s": 0, "duration_s": 5,
                          "after": []}]}],
            "beat_groups": [{"group_id": "G001", "shot_ids": [SHOT],
                             "tail_handle": {"mode": "continue_existing_process",
                                             "source_event_id": "V001",
                                             "description": "末镜既有过程继续，不加戏"}}]}],
    })
    w("episodes/ep_1/02_分镜/导演总控卡_ep_1.md", "# 导演总控卡 ep_1\n\n单段测试集。\n")
    w("episodes/ep_1/02_分镜/分镜_阅读稿_ep_1.md", "# 阅读稿 ep_1\n")
    header = "| 集 | 场 | 镜号 | 画面 | 时长 | 声音 | 角色 | 场景 | 道具 | 运镜 | 光线 | 备注1 | 备注2 | 备注3 | 备注4 |"
    sep_line = "|" + "|".join(["---"] * 15) + "|"
    table_row = f"|  |  | {SHOT} | 白烛自燃 | 00:00–00:05（5s） | 环境声 |  | 灵堂 | 白烛 | 固定 | 烛光 |  |  |  |  |"
    w("episodes/ep_1/02_分镜/分镜_完整分镜表_ep_1.md",
      "# 完整分镜表 ep_1\n\n" + header + "\n" + sep_line + "\n" + table_row + "\n")
    storyboard = {
        "episode_id": "ep_1", "revision": 1, "project_data_card_revision": 1,
        "source_markdown": "episodes/ep_1/02_分镜/分镜_完整分镜表_ep_1.md",
        "director_control_card": "episodes/ep_1/02_分镜/导演总控卡_ep_1.md",
        "shots": [{"shot_id": SHOT, "scene_id": "E01S01",
                   "causal_role": "establish", "evidence_visibility": "in_frame"}],
        "segments": [],
        "audience_execution": {
            "source_plan_revision": 1,
            **{f: {"source_field": f"audience_plan.{f}", "contract": plan["audience_plan"][f],
                   "scene_or_shot_ids": [SHOT]}
               for f in ("viewing_focus", "emotional_payoff",
                         "platform_viewing_context", "expression_boundaries")},
        },
        "highlight_bindings": [], "inherited_aftereffect_bindings": [], "causal_ledger": [],
        "asset_usage_plan": [],
        "inherited_world_facts": [{"fact_id": "WF001", "category": "other",
                                   "statement": "故事发生在夜里。",
                                   "source": "剧本_完整剧本_ep_1.md E01S01 场景说明"}],
        "beat_coverage": [{"beat_id": "B001", "disposition": "kept", "scene": "E01S01",
                           "summary": "白烛自燃", "target_shots": [SHOT]}],
        "seams": [],
    }
    sb_path = w("episodes/ep_1/02_分镜/storyboard_ep_1.json", storyboard)

    # 标准作业顺序：allocate --write → pack --write，再补模型 authored 的 SEG 字段。
    def engine(sub: str) -> dict:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/rhythm_engine.py"), sub,
             "--project-root", str(root), "--input", str(timing_path),
             "--storyboard", str(sb_path), "--write"],
            capture_output=True, text=True, encoding="utf-8", check=True)
        return json.loads(result.stdout)

    self_true = engine("allocate")
    assert self_true["ok"], self_true
    packed = engine("pack")
    assert packed["ok"], packed

    data = json.loads(sb_path.read_text(encoding="utf-8"))
    for seg in data["segments"]:
        seg["shot_mode"] = "edited"
        seg["tail_mode"] = "stable_hold"
        seg["tail_selection_reason"] = "唯一/末段，动作完成后稳收。"
        seg["reference_input_plan"] = []
    sb_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return sb_path, timing_path


def lint_error_codes(root: Path) -> set[str]:
    report = stamp_review.evaluate(root, "ep_1")
    return {item["code"] for item in report.get("lint", {}).get("issues", []) if item["level"] == "error"}


class StampReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sb_path, self.timing_path = build_project(self.root)
        # 盖章前只有两个预期的 content_review 码。
        self.assertEqual(lint_error_codes(self.root),
                         {"content_review_stale", "content_review_open_issue"})

    def _args(self, confirmed: bool = False):
        args = ["--project-root", str(self.root), "--episode", "ep_1"]
        if confirmed:
            args.append("--i-did-the-review")
        return args

    def test_checklist_mode_writes_nothing(self):
        before = self.sb_path.read_bytes()
        code = stamp_review.main(self._args())
        self.assertEqual(code, 0)
        self.assertEqual(before, self.sb_path.read_bytes())
        data = json.loads(self.sb_path.read_text(encoding="utf-8"))
        self.assertNotIn("content_review", data)

    def test_stamp_writes_triple_and_releases(self):
        self.assertEqual(stamp_review.main(self._args(confirmed=True)), 0)
        data = json.loads(self.sb_path.read_text(encoding="utf-8"))
        review = data["content_review"]
        self.assertEqual(review["open_issues"], [])
        roles = [item["role"] for item in review["reviewed_inputs"]]
        self.assertEqual(roles, ["script", "storyboard", "timing_input"])
        timing = next(item for item in review["reviewed_inputs"] if item["role"] == "timing_input")
        self.assertEqual(timing["sha256"], sha256_bytes(self.timing_path.read_bytes()))
        self.assertEqual(lint_error_codes(self.root), set())

    def test_stamp_is_idempotent(self):
        self.assertEqual(stamp_review.main(self._args(confirmed=True)), 0)
        first = self.sb_path.read_text(encoding="utf-8")
        self.assertEqual(stamp_review.main(self._args(confirmed=True)), 0)
        self.assertEqual(first, self.sb_path.read_text(encoding="utf-8"))

    def test_structural_dirt_blocks_stamp(self):
        data = json.loads(self.sb_path.read_text(encoding="utf-8"))
        data["segments"][0]["shot_mode"] = "banana"  # 非法枚举
        self.sb_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        before = self.sb_path.read_bytes()
        self.assertEqual(stamp_review.main(self._args(confirmed=True)), 2)
        self.assertEqual(before, self.sb_path.read_bytes())
        self.assertEqual(lint_error_codes(self.root),
                         {"segment_shot_mode_invalid", "content_review_stale",
                          "content_review_open_issue"})

    def test_open_issues_block_stamp(self):
        # 先盖一个合法章，再写入未解决问题；带问题不许重新盖章。
        self.assertEqual(stamp_review.main(self._args(confirmed=True)), 0)
        data = json.loads(self.sb_path.read_text(encoding="utf-8"))
        data["content_review"]["open_issues"] = [{"shot": SHOT, "issue": "道具穿帮待核"}]
        self.sb_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(stamp_review.main(self._args(confirmed=True)), 2)
        report = stamp_review.evaluate(self.root, "ep_1")
        self.assertIn("content_review_open_issue",
                      {item["code"] for item in report["blocking"]})

    def test_design_edit_invalidates_stamp(self):
        self.assertEqual(stamp_review.main(self._args(confirmed=True)), 0)
        self.assertEqual(lint_error_codes(self.root), set())
        data = json.loads(self.sb_path.read_text(encoding="utf-8"))
        data["review_notes"] = "导演临时加的备注"  # 进入设计投影但不引入结构错误
        self.sb_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(lint_error_codes(self.root), {"content_review_stale"})
        # 章过期后清单模式照常可用（结构门仍过），但提示未盖章。
        self.assertEqual(stamp_review.main(self._args()), 0)

    def test_missing_files_exit_2(self):
        other = self.root / "episodes/ep_9"
        other.mkdir()
        code = stamp_review.main(
            ["--project-root", str(self.root), "--episode", "ep_9", "--i-did-the-review"])
        self.assertEqual(code, 2)


class IsolatedModeBootstrapTests(unittest.TestCase):
    """批 5：python -I 隔离模式不把脚本目录加入 sys.path（二大爷项目三次 allocate 裸崩根因），
    带兄弟模块导入的入口必须靠文件内 sys.path 自举存活，且不依赖 shell 当前目录。"""

    def test_rhythm_engine_allocate_runs_under_minus_i(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project_root = Path(tmp.name)
        sb_path, timing_path = build_project(project_root)
        result = subprocess.run(
            [sys.executable, "-I", str(ROOT / "scripts/rhythm_engine.py"), "allocate",
             "--project-root", str(project_root), "--input", str(timing_path),
             "--storyboard", str(sb_path), "--write"],
            capture_output=True, text=True, encoding="utf-8", cwd=tmp.name)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"], payload)

    def test_sibling_import_entry_points_survive_minus_i(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for rel in ("scripts/drama_lint.py", "scripts/drama_rollback.py",
                    "scripts/preflight_video.py",
                    "tools/video/ffmpeg_tool.py"):
            with self.subTest(entry=rel):
                result = subprocess.run(
                    [sys.executable, "-I", str(ROOT / rel), "--help"],
                    capture_output=True, text=True, encoding="utf-8", cwd=tmp.name)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
