"""离线比较同一渲染器下起点与当前阶段的规则正文载入量，不估算运行耗时。"""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from read_reference import render_route

BASE = "bcfa34ab576eebee4840dc72dd06c55d2257aaf9"


def size(root, stage, conditions=None):
    data = render_route(stage, conditions=conditions, root=root)
    return sum(len(entry["content"].encode("utf-8")) for entry in data["entries"])


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="skill_reference_baseline_") as directory:
        baseline = Path(directory)
        files = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", "-z", BASE, "references"], cwd=ROOT
        ).decode("utf-8").strip("\0").split("\0")
        for name in files:
            target = baseline / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT))
        for stage in ("planning", "script", "assets", "storyboard", "keyframes", "video", "delivery", "repair"):
            before, after = size(baseline, stage), size(ROOT, stage)
            rows.append({"route": stage, "before_bytes": before, "after_bytes": after,
                         "reduction_percent": round((before - after) / before * 100, 1)})
        for stage in ("planning", "script"):
            before, after = size(baseline, stage, ["genre_research"]), size(ROOT, stage, ["genre_research"])
            rows.append({"route": stage + "/genre_research", "before_bytes": before,
                         "after_bytes": after, "reduction_percent": round((before - after) / before * 100, 1)})
        for condition in ("affected_script", "affected_assets", "affected_video", "affected_delivery"):
            before, after = size(baseline, "repair", [condition]), size(ROOT, "repair", [condition])
            rows.append({"route": "repair/" + condition, "before_bytes": before,
                         "after_bytes": after, "reduction_percent": round((before - after) / before * 100, 1)})
    result = {"base_commit": BASE, "unit": "UTF-8 bytes of rendered source bodies; excludes navigation wrappers",
              "routes": rows, "new_writing_baseline_bytes": size(ROOT, "writing"),
              "limits": "Static reference load only. Selected topic methods are extra; no generated-media runtime or compression-frequency claim."}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
