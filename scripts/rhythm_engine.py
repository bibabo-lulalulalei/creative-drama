"""Content-first CLI：累计已经设计的时间、核对合法分组，只写派生数据。"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import sys
import tempfile

# python -I（隔离模式）不把脚本目录加入 sys.path，入口必须自举同目录兄弟模块。
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from timeline_core import compute_groups, issue, reconcile_timeline
from content_first import (DERIVED_FIELDS, load_source,
                           project_file, read_json, render_reading_times)

DEFAULT_H3 = SCRIPT_DIR.parent / "tools/video/h3.json"


def load_h3(path=None):
    data = read_json(path or DEFAULT_H3)
    cap = data.get("capabilities")
    if not isinstance(cap, dict) or not {"min_duration_s", "max_duration_s", "duration_integer_only"} <= cap.keys():
        raise ValueError("tool_capabilities_invalid: h3.json 缺真实时长能力")
    return data


def atomic_write(path, text):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _write_json(path, data):
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def atomic_write_many(entries):
    """Prepare every output before replacing; roll back completed replacements on I/O failure."""
    staged, backups, replaced = {}, {}, []
    try:
        for value, text in entries:
            path = Path(value)
            if path in staged:
                raise ValueError("重复的事务输出路径")
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
            staged[path] = name
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            backups[path] = None
            if path.exists():
                fd, backup = tempfile.mkstemp(prefix=path.name + ".", suffix=".bak", dir=path.parent)
                backups[path] = backup
                with os.fdopen(fd, "wb") as stream:
                    stream.write(path.read_bytes())
                    stream.flush()
                    os.fsync(stream.fileno())
        for path, name in staged.items():
            os.replace(name, path)
            replaced.append(path)
    except OSError:
        for path in reversed(replaced):
            if backups[path] is None:
                path.unlink()
            else:
                os.replace(backups[path], path)
        raise
    finally:
        for name in list(staged.values()) + list(backups.values()):
            if name and os.path.exists(name):
                os.unlink(name)


def json_text(data):
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def _emit(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False))


def _root(args):
    if not args.project_root:
        raise ValueError("需要显式 --project-root，不依赖 shell 当前路径")
    return Path(args.project_root).resolve()


def _calculate(args, storyboard=None):
    root = _root(args)
    inp = read_json(args.input)
    index, issues = load_source(root, inp, storyboard)
    result = reconcile_timeline(inp, index)
    result["issues"] = issues + result["issues"]
    result["ok"] = not result["issues"]
    return inp, result


def _shot_set(sb, result):
    if [shot.get("shot_id") for shot in sb.get("shots", [])] != [shot["shot_id"] for shot in result["shots"]]:
        return [issue("timeline_shot_set_mismatch", "分镜与时间输入镜头集合/顺序不符；拒绝部分写回", hint='先对齐 rhythm_input、storyboard JSON 与十五列表三处的镜头编号/顺序，再重跑 allocate 与 pack --write；三处必须同源：python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"')]
    return []


def cmd_shot_count(args):
    inp, result = _calculate(args)
    return {"ok": result["ok"], "engine": "shot-count",
            "shot_count": len(result["shots"]), "scenes": [{"scene_id": s["scene_id"], "actual_shots": len(s["shots"])} for s in inp.get("scenes", [])],
            "source_refs": sorted({ref for e in result["events"] for ref in e.get("source_refs", [])}), "issues": result["issues"]}


def cmd_allocate(args):
    if args.total is not None or args.segment_budgets:
        return {"ok": False, "issues": [issue("timing_budget_input_forbidden", "新核算不接受 --total / --segment-budgets 预算", hint='删掉 --total/--segment-budgets/--peaks 等命令行预算参数，以及 rhythm_input 里的预算/配额/计数/merge 字段，只保留事件区间与先后关系；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"')], "written": None}
    if not args.input:
        raise ValueError("allocate 需要 --input")
    sb = read_json(args.storyboard) if args.storyboard else None
    inp, result = _calculate(args, sb)
    if sb is not None:
        result["issues"].extend(_shot_set(sb, result))
    if not result["ok"] or result["issues"]:
        return dict(result, ok=False, written=None)
    if args.write:
        if sb is None:
            raise ValueError("--write 需要 --storyboard")
        updated = copy.deepcopy(sb)
        for shot, computed in zip(updated["shots"], result["shots"]):
            for field in DERIVED_FIELDS:
                shot[field] = computed[field]
        updated.update(duration_s=result["total_s"],
                       timing_input_sha256=result["timing_input_sha256"])
        rendered = None
        md = updated.get("source_markdown")
        if md:
            md_path = project_file(_root(args), md)
            rendered = render_reading_times(md_path.read_text(encoding="utf-8"), result)
        episode = _root(args) / f"episodes/{inp['episode_id']}/episode_manifest_{inp['episode_id']}.json"
        manifest = read_json(episode) if episode.is_file() else None
        if manifest is not None:
            manifest["planned_content_duration_s"] = result["total_s"]
        # 所有语义、文件解析、镜头与阅读稿检查在任何替换前完成。
        entries = [(Path(args.storyboard), json_text(updated))]
        if rendered is not None:
            entries.append((md_path, rendered))
        if manifest is not None:
            entries.append((episode, json_text(manifest)))
        atomic_write_many(entries)
        result["written"] = args.storyboard
    return result


def cmd_pack(args):
    sb = read_json(args.storyboard)
    inp, result = _calculate(args, sb)
    result["issues"].extend(_shot_set(sb, result))
    if not result["ok"] or result["issues"]:
        return dict(result, ok=False, written=None)
    if any(any(shot.get(key) != computed[key] for key in DERIVED_FIELDS) for shot, computed in zip(sb["shots"], result["shots"])):
        return {"ok": False, "issues": [issue("timing_output_drift", "先 allocate 写回当前核算，pack 不更改镜内设计", hint='改 rhythm_input 后必须重跑核算写回派生字度（禁止手填 duration_s/time_range_s）：python scripts/rhythm_engine.py allocate --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write')], "written": None}
    groups = [group for scene in inp["scenes"] for group in scene.get("beat_groups", [])]
    packed = compute_groups(result, groups, load_h3(), sb["shots"])
    if not packed["ok"]:
        return dict(packed, written=None)
    if args.write:
        old = sb.get("segments", [])
        by_identity = {tuple(seg.get("shot_ids", [])): seg for seg in old}
        used_ids = {seg.get("segment_id") for seg in old}
        new = []
        invalidated = []
        for computed in packed["segments"]:
            previous = by_identity.get(tuple(computed["shot_ids"]))
            if previous:
                computed["segment_id"] = previous["segment_id"]
            elif computed["segment_id"] in used_ids:
                next_id = 1
                while f"SEG{next_id:03d}" in used_ids:
                    next_id += 1
                computed["segment_id"] = f"SEG{next_id:03d}"
            used_ids.add(computed["segment_id"])
            if previous and previous.get("design_sha256") == computed["design_sha256"]:
                new.append(dict(previous, **computed))
            else:
                # 内容/组边界变化不继承参考计划、KF、预检或审校。
                new.append(computed)
                invalidated.append(computed["segment_id"])
        old_ids = {seg.get("segment_id") for seg in old}
        removed = sorted(old_ids - {seg["segment_id"] for seg in new})
        sb["segments"] = new
        seg_of = {sid: seg["segment_id"] for seg in new for sid in seg["shot_ids"]}
        for shot in sb["shots"]:
            shot["segment_id"] = seg_of[shot["shot_id"]]
        _write_json(args.storyboard, sb)
        packed.update(segments=new, written=args.storyboard, invalidated_segments=invalidated, retired_segments=removed)
    return packed


def kf_count(storyboard):
    requests = [(seg.get("segment_id"), req) for seg in storyboard.get("segments", []) for req in seg.get("keyframe_requests", [])]
    by_seg = {}
    reused = 0
    for sid, req in requests:
        if not isinstance(req, dict) or not req.get("keyframe_id") or not req.get("purpose"):
            raise ValueError("keyframe_request_invalid: KF 需实际用途和稳定 ID")
        by_seg.setdefault(sid, []).append(req["keyframe_id"])
        reused += bool(req.get("reuse_ref"))
    ids = [req["keyframe_id"] for _, req in requests]
    if len(ids) != len(set(ids)):
        raise ValueError("keyframe_request_invalid: KF ID 重复")
    return {"planned_requests": len(requests), "needs_generation": len(requests) - reused, "reused": reused, "by_segment": by_seg}


def cmd_kf_count(args):
    if args.total is not None or args.peaks is not None:
        return {"ok": False, "issues": [issue("timing_budget_input_forbidden", "kf-count 不接受时长/峰值配额，请用 --storyboard", hint='删掉 --total/--segment-budgets/--peaks 等命令行预算参数，以及 rhythm_input 里的预算/配额/计数/merge 字段，只保留事件区间与先后关系；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"') ]}
    if not args.storyboard:
        raise ValueError("kf-count 需要 --storyboard")
    return dict(ok=True, engine="kf-count", **kf_count(read_json(args.storyboard)))


def main():
    parser = argparse.ArgumentParser(description="累计导演设计时间；不接受规划估时或创意配额")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("shot-count", "allocate", "pack", "kf-count"):
        p = sub.add_parser(name)
        p.add_argument("--project-root")
        if name in {"shot-count", "allocate", "pack"}:
            p.add_argument("--input", required=name in {"shot-count", "pack"})
        if name != "shot-count":
            p.add_argument("--storyboard", required=name == "pack")
        if name in {"allocate", "pack"}:
            p.add_argument("--write", action="store_true")
        if name == "allocate":
            p.add_argument("--total")
            p.add_argument("--segment-budgets", action="store_true")
        if name == "kf-count":
            p.add_argument("--total")
            p.add_argument("--peaks")
    args = parser.parse_args()
    try:
        functions = {"shot-count": cmd_shot_count, "allocate": cmd_allocate, "pack": cmd_pack,
                     "kf-count": cmd_kf_count}
        result = functions[args.cmd](args)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result = {"ok": False, "issues": [issue("timing_input_invalid", str(exc), hint='按随附异常修 rhythm_input 后先 allocate --write，再 pack；作业顺序：python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"')], "written": None}
    _emit(result)
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
