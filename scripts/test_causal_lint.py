# 因果链 lint 单元验证（修4）：在真实项目的临时副本上变异 storyboard，检查 check_causal_ledger 行为。
# 用法：python scripts/test_causal_lint.py "<项目根>"
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
LINT = SKILL_ROOT / "scripts" / "drama_lint.py"
SB_REL = Path("episodes/ep_1/02_分镜/storyboard_ep_1.json")
KEEP_SUFFIXES = {".json", ".md", ".jsonl"}


def copy_project(src: Path, dst: Path) -> None:
    def ignore(directory, names):
        return [n for n in names if (Path(directory) / n).is_file() and Path(n).suffix not in KEEP_SUFFIXES]
    shutil.copytree(src, dst, ignore=ignore)


def run_lint(root: Path) -> list[dict]:
    proc = subprocess.run(
        [sys.executable, str(LINT), "--project-root", str(root), "--stage", "storyboard"],
        capture_output=True, text=True, encoding="utf-8",
    )
    payload = json.loads(proc.stdout)
    return [i for i in payload["issues"] if any(k in i["code"] for k in ("causal", "evidence", "occluded"))]


def fill_all_causal_roles(sb: dict) -> None:
    for shot in sb["shots"]:
        shot.setdefault("causal_role", "transition")


def fill_seg008(sb: dict) -> None:
    shots = {s["shot_id"]: s for s in sb["shots"]}
    shots["E01S04-SHOT001"].update({"causal_role": "establish", "establishes": "次日掌灯酒肆满座，前一夜事件已在场间传开", "evidence_visibility": "in_frame"})
    shots["E01S04-SHOT002"].update({
        "causal_role": "reaction",
        "responds_to": {"ref_type": "beat", "ref_id": "B028", "trigger_fact": "嘴唇肿得老高（SEG007 铜镜显形建立）"},
        "establishes": "肿唇从指缝与嘴角部分可见；若手部全遮则哄笑失去依据，揭示点为 SHOT003 众人围看追问",
        "evidence_visibility": "partial",
    })
    shots["E01S04-SHOT003"].update({
        "causal_role": "reaction",
        "responds_to": {"ref_type": "beat", "ref_id": "B028", "trigger_fact": "嘴唇肿得老高（SEG007 铜镜显形建立）"},
    })
    shots["E01S04-SHOT004"].update({
        "causal_role": "result",
        "responds_to": {"ref_type": "shot", "ref_id": "E01S04-SHOT003", "trigger_fact": "众人哄笑与明知故问"},
    })
    sb["causal_ledger"] = [{
        "chain_id": "CL001",
        "trigger_fact": "嘴唇肿得老高（惩戒显形）",
        "trigger_source": {"ref_type": "beat", "ref_id": "B028"},
        "evidence_shot_ids": ["E01S04-SHOT002"],
        "reaction_shot_ids": ["E01S04-SHOT002", "E01S04-SHOT003"],
        "result_shot_ids": ["E01S04-SHOT004"],
        "cross_episode_refs": [],
        "visibility_contract": "肿唇在 SHOT002/003 必须部分可见（嘴角肿出、捂不住）；手部全遮即断链",
        "breakpoint_risk": "C2",
        "highlight_binding_ref": None,
    }]


def main() -> None:
    project = Path(sys.argv[1])
    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        def scenario(name, mutate, expect_codes, forbid_codes=()):
            root = tmp / name
            copy_project(project, root)
            sb_path = root / SB_REL
            sb = json.loads(sb_path.read_text(encoding="utf-8"))
            mutate(sb, sb_path)
            sb_path.write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
            issues = run_lint(root)
            codes = {i["code"] for i in issues}
            missing = [c for c in expect_codes if c not in codes]
            unexpected = [c for c in forbid_codes if c in codes]
            status = "PASS" if not missing and not unexpected else "FAIL"
            print(f"[{status}] {name}: codes={sorted(codes)}")
            if missing:
                print(f"       缺少预期: {missing}")
            if unexpected:
                print(f"       出现禁止: {unexpected}")
            return status == "PASS"

        def good(sb, _p=None):
            sb["schema_version"] = "1.1"
            fill_all_causal_roles(sb)
            fill_seg008(sb)
        results.append(scenario("good_full_fill", good, (), forbid_codes=(
            "causal_role_missing", "causal_ledger_missing", "causal_chain_reaction_before_evidence",
            "causal_chain_result_before_reaction", "causal_ref_unknown", "causal_evidence_establishes_missing",
            "causal_reaction_responds_to_missing", "causal_seam_invariant_missing", "causal_chain_ref_unknown",
        )))

        def unfilled(sb, _p=None):
            sb["schema_version"] = "1.1"
            fill_seg008(sb)
        results.append(scenario("partial_fill_enforced", unfilled, ("causal_role_missing",)))

        def no_ledger(sb, _p=None):
            sb["schema_version"] = "1.1"
            fill_all_causal_roles(sb)
        results.append(scenario("ledger_missing", no_ledger, ("causal_ledger_missing",)))

        def no_responds_to(sb, _p=None):
            good(sb)
            for s in sb["shots"]:
                if s["shot_id"] == "E01S04-SHOT003":
                    s.pop("responds_to")
        results.append(scenario("reaction_without_responds_to", no_responds_to, ("causal_reaction_responds_to_missing",)))

        def no_establishes(sb, _p=None):
            good(sb)
            for s in sb["shots"]:
                if s["shot_id"] == "E01S04-SHOT002":
                    s.pop("establishes")
        results.append(scenario("evidence_without_establishes", no_establishes, ("causal_evidence_establishes_missing",)))

        def bad_timing(sb, _p=None):
            good(sb)
            sb["causal_ledger"][0]["evidence_shot_ids"] = ["E01S04-SHOT003"]
            for s in sb["shots"]:
                if s["shot_id"] == "E01S04-SHOT003":
                    s.update({"establishes": "x", "evidence_visibility": "partial"})
        results.append(scenario("reaction_before_evidence", bad_timing, ("causal_chain_reaction_before_evidence",)))

        def bad_ref(sb, _p=None):
            good(sb)
            sb["causal_ledger"][0]["trigger_source"] = {"ref_type": "beat", "ref_id": "B999"}
        results.append(scenario("unknown_beat_ref", bad_ref, ("causal_ref_unknown",)))

        def bad_hl(sb, _p=None):
            good(sb)
            sb["causal_ledger"][0]["highlight_binding_ref"] = "HL999"
        results.append(scenario("unknown_highlight_binding_ref", bad_hl, ("causal_chain_highlight_binding_ref_unknown",)))

        def cross_seam_and_card_refs(sb, sb_path):
            good(sb)
            seg7_shot = next(s["shot_id"] for s in sb["shots"] if s["segment_id"] == "SEG007")
            shots = {s["shot_id"]: s for s in sb["shots"]}
            shots[seg7_shot].update({"establishes": "铜镜显形肿唇", "evidence_visibility": "in_frame"})
            sb["causal_ledger"].append({
                "chain_id": "CL002", "trigger_fact": "铜镜显形",
                "trigger_source": {"ref_type": "shot", "ref_id": seg7_shot},
                "evidence_shot_ids": [seg7_shot],
                "reaction_shot_ids": ["E01S04-SHOT002"],
                "result_shot_ids": ["E01S04-SHOT004"],
                "cross_episode_refs": [], "visibility_contract": "肿唇跨夜保持",
                "breakpoint_risk": "C2", "highlight_binding_ref": None,
            })
            card = sb_path.parent / "导演总控卡_ep_1.md"
            card.write_text(card.read_text(encoding="utf-8") + "\ncausal_chain_ref: CL001\ncausal_chain_ref: CL999\n", encoding="utf-8")
        results.append(scenario("cross_seam_and_card_refs", cross_seam_and_card_refs,
                                ("causal_seam_invariant_missing", "causal_chain_ref_unknown")))

        def gated(sb, _p=None):
            sb["schema_version"] = "1.0"  # 旧版整体跳过
        results.append(scenario("schema_1_0_skipped", gated, (), forbid_codes=(
            "causal_role_missing", "causal_ledger_missing",
        )))

    print("PASS" if all(results) else "FAIL", f"({sum(results)}/{len(results)})")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
