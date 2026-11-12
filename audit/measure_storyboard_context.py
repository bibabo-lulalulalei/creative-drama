"""Compare actual rendered rule bodies; bytes are not a token estimate."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from read_reference import render_route


def body_size(root, conditions=None):
    route = render_route("storyboard", root=root, conditions=conditions)
    return sum(len(row["content"].encode("utf-8")) for row in route["entries"])


def main():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    with tempfile.TemporaryDirectory(prefix="storyboard_rules_before_") as directory:
        before = Path(directory)
        names = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", "-z", commit, "references"], cwd=ROOT,
        ).decode("utf-8").strip("\0").split("\0")
        for name in names:
            target = before / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=ROOT))
        old_map = json.loads((before / "references/reference_map.json").read_text(encoding="utf-8"))
        new_map = json.loads((ROOT / "references/reference_map.json").read_text(encoding="utf-8"))
        old_conditions = old_map["stages"]["storyboard"]["conditional"]
        new_conditions = new_map["stages"]["storyboard"]["conditional"]
        rows = [{"route": "baseline", "before_bytes": body_size(before), "after_bytes": body_size(ROOT)}]
        for condition in ("director_design", "artifact_write", "timing_design", "pre_confirm_review"):
            if condition in old_conditions and condition in new_conditions:
                rows.append({"route": condition, "before_bytes": body_size(before, [condition]),
                             "after_bytes": body_size(ROOT, [condition])})
        for row in rows:
            row["reduction_percent"] = round((1 - row["after_bytes"] / row["before_bytes"]) * 100, 1)
        result = {
            "baseline_git_commit": commit,
            "unit": "UTF-8 bytes of rendered source bodies; not tokens or observed compaction frequency",
            "comparable_routes": rows,
            "current_storyboard_routes": {key: body_size(ROOT, [key]) for key in new_conditions},
            "storyboard_entry_file": {"before_bytes": (before / "references/storyboard.md").stat().st_size,
                                      "after_bytes": (ROOT / "references/storyboard.md").stat().st_size},
            "limits": "References remain available for their actual actions. Separate step routes do not represent one mandatory load.",
        }
    target = ROOT / "audit/storyboard-context-budget.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
