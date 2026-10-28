"""rhythm_engine.py — 节奏系统的唯一计算源。

架构铁律：LLM 只做语义判断（beat_type/intensity/spoken_text/动作单元/角色标记），
一切加减乘除由本引擎执行；本文件代码零魔数——所有常数运行时从
beat_types.json 的 params 节读取（唯一例外：模型硬合同读 tools/video/h3.json）。

子命令：
  shot-count   镜数一致性校验（实列镜数 应等于 Σ动作单元+Σ反应单元−Σ合并）
  allocate     时长分配（节拍基准/台词下限/角色下限取最大 → 网格取整；不做总量或 SEG 配平）
  pack         SEG 装箱（段时长=镜时长之和；超上限在自然切点拆分；禁止凑满）
  kf-count     KF 数量公式（min/max/建议张数）
  stats        节奏分布摘要（供用户确认门展示）

既可命令行调用，也可被 drama_lint import（公式只有一份实现）。
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LIBRARY = SCRIPT_DIR / "beat_types.json"
DEFAULT_H3 = SCRIPT_DIR.parent / "tools" / "video" / "h3.json"

ENGINE_VERSION = 2

EXTREMES_COUNT = 3


def _force_utf8_stdio():
    """Windows GBK 控制台/重定向下中文 JSON 输出会花码甚至 UnicodeEncodeError；
    引擎输出契约是 UTF-8 JSON，stdout/stderr 一律强制 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass



def load_library(path=None):
    p = Path(path) if path else DEFAULT_LIBRARY
    if not p.exists():
        raise SystemExit(f"beat_types.json 不存在: {p}（先运行 build_beat_types.py）")
    return json.loads(io.open(str(p), encoding="utf-8-sig").read())


def load_h3(path=None):
    p = Path(path) if path else DEFAULT_H3
    return json.loads(io.open(str(p), encoding="utf-8-sig").read())


def _params(lib):
    return lib["params"]


def _read_json(path):
    return json.loads(io.open(str(path), encoding="utf-8-sig").read())


def _write_json(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _emit(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))



def effective_ranges(lib, overrides=None, style=None):
    """生效区间三层优先级：本集 overrides > 风格档案 > 库默认。返回 {beat: (low, high)}"""
    beats = lib["beat_types"]
    ranges = {b: tuple(v["range_s"]) for b, v in beats.items()}
    if style:
        prof = lib.get("style_profiles", {}).get(style)
        if prof:
            for b, r in prof.get("overrides", {}).items():
                if b in ranges:
                    ranges[b] = tuple(r)
    if overrides:
        for b, r in overrides.items():
            if b in ranges:
                ranges[b] = tuple(r)
    return ranges


def remap_anchors(lib, beat, eff_range):
    """库锚点定义在默认区间内；生效区间变化时按比例重映射进新区间。"""
    entry = lib["beat_types"][beat]
    lo, hi = entry["range_s"]
    nlo, nhi = eff_range
    span = hi - lo
    out = {}
    for k, a in entry["intensity_anchors"].items():
        out[int(k)] = a if span <= 0 else nlo + (a - lo) / span * (nhi - nlo)
    return out


def anchor_at(anchors, intensity):
    """分段线性插值：锚点固定在强度 1/3/5，强度夹取 [1,5]。"""
    x = max(1.0, min(5.0, float(intensity)))
    if x <= 3.0:
        t = (x - 1.0) / 2.0
        return anchors[1] + t * (anchors[3] - anchors[1])
    t = (x - 3.0) / 2.0
    return anchors[3] + t * (anchors[5] - anchors[3])


_CJK = re.compile(r"[一-鿿]")


def speech_floor(text, pace, params):
    """台词下限 s = onset + CJK字数÷语速 + reaction；无台词返回 0。
    语速按 speech_pace 选档：rapid → chars_per_s_rapid，其余 → chars_per_s_normal。"""
    if not text:
        return 0.0, 0, 0
    sp = params["speech"]
    rate = sp["chars_per_s_rapid"] if pace == "rapid" else sp["chars_per_s_normal"]
    n = len(_CJK.findall(text))
    return sp["onset_s"] + n / float(rate) + sp["reaction_s"], n, rate


def round_to_grid(x, grid):
    """取整到最近的网格倍数（0.5 秒网格）。"""
    import math
    return round(math.floor(x / grid + 0.5) * grid, 6)


def _fmt(x):
    v = round(float(x), 2)
    return str(int(v)) if v == int(v) else str(v)


def flatline_share(durations, window_s, step_s):
    """滑窗最坏占比：任一 window_s 宽时长窗内容纳镜头的最大比例（窗起点按 step_s 步进）。
    对应 storyboard.md「任一 N 秒窗内镜头占比不得超过上限」的语义；返回 (share, window_lo)，
    空列表返回 (0.0, None)。lint 与引擎自检共用本函数（公式单源，禁止另写）。"""
    ds = [float(d) for d in durations]
    if not ds:
        return 0.0, None
    lo = min(ds)
    hi = max(ds)
    best_share, best_lo = 0.0, lo
    while lo <= hi + 1e-9:
        share = sum(1 for d in ds if lo <= d <= lo + window_s) / len(ds)
        if share > best_share:
            best_share, best_lo = share, lo
        lo += step_s
    return best_share, best_lo


def _require_scenes(inp, cmd_name):
    """rhythm_input 顶层结构校验：缺 scenes 数组或全空时给出明确报错，
    防止错误结构（如镜头写在顶层）被引擎静默按 0 镜处理并输出 ok:true。"""
    scenes = inp.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        _emit({"ok": False, "engine": cmd_name, "engine_version": ENGINE_VERSION,
               "error": "rhythm_input 缺少 scenes 数组（或为空）；语义输入表必须按 scenes[].shots[] 嵌套填写，顶层 schema 见 manifests.md「rhythm_input_ep_N.json」节"})
        raise SystemExit(2)
    if not any(isinstance(sc, dict) and sc.get("shots") for sc in scenes):
        _emit({"ok": False, "engine": cmd_name, "engine_version": ENGINE_VERSION,
               "error": "rhythm_input 的 scenes 内没有任何 shots 镜头条目"})
        raise SystemExit(2)



def cmd_shot_count(args):
    lib = load_library(args.library)
    params = _params(lib)
    inp = _read_json(args.input)
    _require_scenes(inp, "shot-count")
    ranges = effective_ranges(lib, inp.get("beat_duration_overrides"), inp.get("style_profile"))

    scenes = []
    problems = []
    for scene in inp.get("scenes", []):
        shots = scene.get("shots", [])
        u = sum(int(s.get("action_units", 0)) for s in shots)
        r = sum(int(s.get("reaction_units", 0)) for s in shots)
        m = sum(1 for s in shots if s.get("merge_with_next"))
        expected = u + r - m
        actual = len(shots)
        floor_sum = round(sum(ranges[s["beat_type"]][0] for s in shots if s.get("beat_type") in ranges), 2)
        ok = expected == actual
        if not ok:
            problems.append(f"{scene.get('scene_id')}: 声明 单元 {u}+反应 {r}−合并 {m} = {expected} 镜，实列 {actual} 镜")
        scenes.append({
            "scene_id": scene.get("scene_id"), "action_units": u, "reaction_units": r,
            "merges": m, "expected_shots": expected, "actual_shots": actual,
            "beat_floor_sum_s": floor_sum, "ok": ok,
        })
        if actual > params["shot_count_risk_threshold"]:
            problems.append(f"{scene.get('scene_id')}: {actual} 镜超过模型合并风险阈值 {params['shot_count_risk_threshold']}（info）")

    _emit({"ok": not any("实列" in p for p in problems), "engine": "shot-count",
           "engine_version": ENGINE_VERSION, "scenes": scenes, "problems": problems})



def compute_shot_durations(inp, lib, segment_map=None):
    """逐镜计算时长（不配平）。segment_map 仅用于关联 SEG ID，不含预算目标。
    返回 (records, meta)。records 顺序 = 输入顺序。"""
    params = _params(lib)
    grid = params["rounding_grid_s"]
    bounds = params["shot_bounds"]
    floors = params["role_floors"]
    ranges = effective_ranges(lib, inp.get("beat_duration_overrides"), inp.get("style_profile"))

    records = []
    for scene in inp.get("scenes", []):
        for s in scene.get("shots", []):
            beat = s.get("beat_type")
            anchors = remap_anchors(lib, beat, ranges[beat]) if beat in lib["beat_types"] else None
            b = anchor_at(anchors, s.get("intensity", 3)) if anchors else 0.0
            s_floor, n_chars, rate = speech_floor(s.get("spoken_text"), s.get("speech_pace", "normal"), params)
            r_floor = floors["payoff_s"] if s.get("is_payoff") else (floors["final_s"] if s.get("is_final") else 0.0)

            eff_lo, eff_hi = ranges.get(beat, (bounds["min_s"], bounds["max_s"]))
            ceil_i = min(eff_hi, bounds["max_s"])
            floor_i = max(bounds["min_s"], eff_lo if anchors else 0.0, s_floor, r_floor)

            winner = max(b, s_floor, r_floor)
            if winner == s_floor and s_floor > 0:
                base_label = f"台词{_fmt(s_floor)}({n_chars}字@{rate}/s)"
            elif winner == r_floor and r_floor > 0:
                base_label = f"角色{_fmt(r_floor)}({'payoff' if s.get('is_payoff') else 'final'})"
            else:
                base_label = f"节拍{_fmt(b)}({beat})" if beat else f"基础{_fmt(b)}"

            d_raw = max(winner, bounds["min_s"])
            d_grid = round_to_grid(d_raw, grid)
            d_clamped = max(bounds["min_s"], min(d_grid, bounds["max_s"]))
            basis_parts = [base_label]
            if abs(d_grid - d_raw) >= 1e-9:
                basis_parts.append(f"取整{_fmt(d_grid - d_raw) if d_grid < d_raw else '+' + _fmt(d_grid - d_raw)}")
            if abs(d_clamped - d_grid) >= 1e-9:
                basis_parts.append(f"夹取{_fmt(d_clamped - d_grid) if d_clamped < d_grid else '+' + _fmt(d_clamped - d_grid)}")

            rec = {
                "shot_id": s["shot_id"], "scene_id": scene.get("scene_id"),
                "beat_type": beat, "intensity": s.get("intensity"),
                "spoken_text": s.get("spoken_text") or "",
                "speech_pace": s.get("speech_pace", "normal"),
                "is_payoff": bool(s.get("is_payoff")), "is_final": bool(s.get("is_final")),
                "info_injection": bool(s.get("info_injection")),
                "b": round(b, 3), "s": round(s_floor, 3), "r": round(r_floor, 3),
                "floor": round(floor_i, 3), "ceil": round(ceil_i, 3),
                "raw_d": round(d_clamped, 3), "d": round(d_clamped, 3),
                "basis_parts": basis_parts,
                "adjust": 0.0,
            }
            if segment_map and s["shot_id"] in segment_map:
                rec["segment_id"] = segment_map[s["shot_id"]][0]
            records.append(rec)

    notes = []
    for rec in records:
        if rec["d"] > params["shot_bounds"]["info_injection_threshold_s"] and not rec["info_injection"]:
            notes.append(f"{rec['shot_id']}: {_fmt(rec['d'])}s 超过信息注入门槛 "
                         f"{_fmt(params['shot_bounds']['info_injection_threshold_s'])}s 但未声明 info_injection（建议确认持续信息注入）")
    return records, notes


def _health_checks(recs_by_seg, all_recs, lib, total_s, seg_density=None):
    """自检：不过则输出调整建议而非静默通过。阈值全部 ← params.health / role_floors / shot_bounds。"""
    params = _params(lib)
    h = params["health"]
    floors = params["role_floors"]
    bounds = params["shot_bounds"]
    issues = []
    sp = _params(lib)["speech"]
    for seg_id, recs in recs_by_seg.items():
        seg_dur = sum(r["d"] for r in recs)
        if seg_dur <= 0:
            continue
        voice = 0.0
        for r in recs:
            if r.get("spoken_text"):
                rate = sp["chars_per_s_rapid"] if r.get("speech_pace") == "rapid" else sp["chars_per_s_normal"]
                voice += sp["onset_s"] + len(_CJK.findall(r["spoken_text"])) / float(rate)
        dense = (seg_density or {}).get(seg_id) == "high_density_short"
        cap = h["speech_voice_max_share_dense"] if dense else h["speech_voice_max_share_normal"]
        share = voice / seg_dur
        if share > cap:
            issues.append(f"{seg_id}: 人声时长占比 {round(share * 100)}% > {'高密度' if dense else '常态'}上限 "
                          f"{round(cap * 100)}%（台词灌满挤压画面叙事，建议拆白到反应镜或收紧台词）")
    for seg_id, recs in recs_by_seg.items():
        if len(recs) >= 3:
            rng = max(r["d"] for r in recs) - min(r["d"] for r in recs)
            if rng < h["segment_min_range_s"]:
                issues.append(f"{seg_id}: 段内极差 {_fmt(rng)}s < {_fmt(h['segment_min_range_s'])}s（镜头时长过于均匀）")
    ds = [r["d"] for r in all_recs]
    if ds:
        w = h["flatline_window_s"]
        top, top_lo = flatline_share(ds, w, params["rounding_grid_s"])
        if top > h["flatline_max_share"]:
            issues.append(f"全片: {round(top * 100)}% 镜头压在 {_fmt(top_lo)}-{_fmt(top_lo + w)}s 时长窗内（上限 {round(h['flatline_max_share'] * 100)}%）")
        fast_capable = any(
            r["beat_type"] in lib["beat_types"] and
            bool(lib["beat_types"][r["beat_type"]].get("fast_pole_capable"))
            for r in all_recs
        )
        if fast_capable and min(ds) > h["fast_pole_max_s"]:
            issues.append(f"全片: 存在快节奏节拍但最短镜 {_fmt(min(ds))}s > {_fmt(h['fast_pole_max_s'])}s（缺快极值锚点）")
        if total_s >= h["slow_pole_min_total_s"] and max(ds) < h["slow_pole_min_s"]:
            issues.append(f"全片: 总时长 {_fmt(total_s)}s ≥ {_fmt(h['slow_pole_min_total_s'])}s 但最长镜 {_fmt(max(ds))}s < {_fmt(h['slow_pole_min_s'])}s（缺慢极值锚点）")
    for r in all_recs:
        if r["is_payoff"] and r["d"] < floors["payoff_s"]:
            issues.append(f"{r['shot_id']}: 高光兑现镜 {_fmt(r['d'])}s < 角色下限 {_fmt(floors['payoff_s'])}s")
        if r["is_final"] and r["d"] < floors["final_s"]:
            issues.append(f"{r['shot_id']}: 集尾镜 {_fmt(r['d'])}s < 角色下限 {_fmt(floors['final_s'])}s")
        if r["d"] < bounds["min_s"] or r["d"] > bounds["max_s"]:
            issues.append(f"{r['shot_id']}: {_fmt(r['d'])}s 越出单镜硬边界 [{_fmt(bounds['min_s'])}, {_fmt(bounds['max_s'])}]")
    return issues


def engine_output_hash(inp, lib):
    """快速检测「输入表或库在引擎跑完后被改动」。逐项重算用于定位差异——两道闸分工。"""
    canon = json.dumps({"input": inp, "library_version": lib["version"],
                        "engine_version": ENGINE_VERSION}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def cmd_allocate(args):
    lib = load_library(args.library)
    params = _params(lib)
    grid = params["rounding_grid_s"]
    inp = _read_json(args.input)
    _require_scenes(inp, "allocate")

    if args.segment_budgets or args.total is not None:
        _emit({"ok": False, "engine": "allocate", "engine_version": ENGINE_VERSION,
               "error": "已移除总量/SEG 预算配平；allocate 只计算语义镜长。请运行 allocate --write 后再运行 pack。"})
        raise SystemExit(2)

    segment_map = None
    if args.storyboard:
        sb = _read_json(args.storyboard)
        segment_map = {}
        for seg in sb.get("segments", []):
            for sid in seg.get("shot_ids", []):
                segment_map[sid] = (seg["segment_id"], seg.get("duration_s"))

    records, notes = compute_shot_durations(inp, lib, segment_map)
    by_id = {r["shot_id"]: r for r in records}

    recs_by_seg = {}
    for r in records:
        recs_by_seg.setdefault(r.get("segment_id") or r.get("scene_id") or "ALL", []).append(r)

    total_s = round(sum(r["d"] for r in records), 6)

    thresh = params["shot_bounds"]["info_injection_threshold_s"]
    notes = [f"{r['shot_id']}: {_fmt(r['d'])}s 超过信息注入门槛 {_fmt(thresh)}s 但未声明 info_injection（建议确认持续信息注入）"
             for r in records if r["d"] > thresh and not r["info_injection"]]

    seg_density = {}
    if args.storyboard:
        for seg in sb.get("segments", []):
            seg_density[seg["segment_id"]] = seg.get("density_profile")
    issues = _health_checks(recs_by_seg, records, lib, total_s, seg_density)

    for r in records:
        parts = list(r["basis_parts"])
        r["duration_basis"] = "+".join(parts)
        r["duration_s"] = round(r["d"], 2)

    out = {
        "ok": True,
        "engine": "allocate", "engine_version": ENGINE_VERSION,
        "library_version": lib["version"],
        "total_s": total_s,
        "engine_output_hash": engine_output_hash(inp, lib),
        "shots": [{
            "shot_id": r["shot_id"], "segment_id": r.get("segment_id"),
            "duration_s": r["duration_s"], "duration_basis": r["duration_basis"],
            "beat_type": r["beat_type"], "intensity": r["intensity"],
        } for r in records],
        "health_issues": issues,
        "notes": notes,
    }

    extremes = sorted(records, key=lambda r: r["d"])
    out["rhythm_extremes"] = {
        "fastest": [{"shot_id": r["shot_id"], "duration_s": r["duration_s"],
                     "beat": lib["beat_types"].get(r["beat_type"], {}).get("name", r["beat_type"])}
                    for r in extremes[:EXTREMES_COUNT]],
        "slowest": [{"shot_id": r["shot_id"], "duration_s": r["duration_s"],
                     "beat": lib["beat_types"].get(r["beat_type"], {}).get("name", r["beat_type"])}
                    for r in reversed(extremes[-EXTREMES_COUNT:])],
    }

    if args.write and args.storyboard:
        seg_time = {}
        cursor = 0.0
        for shot in sb.get("shots", []):
            r = by_id.get(shot["shot_id"])
            if not r:
                continue
            shot["duration_s"] = r["duration_s"]
            shot["duration_basis"] = r["duration_basis"]
            shot["beat_type"] = r["beat_type"]
            shot["intensity"] = r["intensity"]
            if r["spoken_text"]:
                shot["spoken_text"] = r["spoken_text"]
                shot["speech_pace"] = r["speech_pace"]
            else:
                shot.pop("spoken_text", None)
                shot.pop("speech_pace", None)
            shot["time_range_s"] = [round(cursor, 2), round(cursor + r["duration_s"], 2)]
            cursor = round(cursor + r["duration_s"], 2)
        for seg in sb.get("segments", []):
            ds = [by_id[sid]["duration_s"] for sid in seg.get("shot_ids", []) if sid in by_id]
            if ds:
                seg["duration_s"] = round(sum(ds), 2)
        t = 0.0
        for seg in sb.get("segments", []):
            seg["time_range_s"] = [round(t, 2), round(t + seg.get("duration_s", 0), 2)]
            t = round(t + seg.get("duration_s", 0), 2)
        sb["duration_s"] = round(cursor, 2)
        sb["rhythm_extremes"] = out["rhythm_extremes"]
        sb["engine_output_hash"] = out["engine_output_hash"]
        if inp.get("beat_duration_overrides"):
            sb["beat_duration_overrides"] = inp["beat_duration_overrides"]
        _write_json(args.storyboard, sb)
        out["written"] = args.storyboard

    _emit(out)



def compute_pack(shots, candidates, cap, seg_min, beat_groups=None):
    """SEG 划分核心（引擎与 lint 对账共用，公式单源）。

    beat-first：导演在 rhythm_input 各场声明 beat_groups（镜头组），每组 = 一次
    [seg_min, cap] 秒的整数秒生成任务；本函数只做校验——组覆盖完整、顺序连续、
    组时长在界内且为整数秒；镜时长本身保持 0.5s 网格不变。组时长非整秒时报错，
    要求导演在组边界上调整（±0.5s 的镜长取舍是创作决定）。
    未声明 beat_groups 时直接报错（机械装箱回退路径已废弃）：段划分是导演的剧情
    决定，回到 rhythm_input 各场补 beat_groups 声明。
    shots 元素须含 shot_id 与 duration_s。返回 (out_segs, notes, at_cap_count)。"""
    if not beat_groups:
        raise ValueError(
            "beat_groups_missing: rhythm_input 各场未声明镜头组（beat_groups）。"
            "先按剧情节拍划组（组边界=真实剪辑点，组时长 [4, 15] 整数秒）写入各场 beat_groups，"
            "再运行 pack；机械装箱回退路径已废弃。")
    return _pack_beat_groups(shots, beat_groups, cap, seg_min)


def _pack_beat_groups(shots, beat_groups, cap, seg_min):
    """beat-first：校验导演声明的镜头组并转为 SEG。"""
    dur_of = {s["shot_id"]: s["duration_s"] for s in shots}
    order = [s["shot_id"] for s in shots]
    flat = []
    for gi, group in enumerate(beat_groups, 1):
        gids = group.get("shot_ids") or []
        label = group.get("group_id") or f"第{gi}组"
        if not gids:
            raise ValueError(f"beat_group {label}: shot_ids 为空。")
        unknown = [sid for sid in gids if sid not in dur_of]
        if unknown:
            raise ValueError(f"beat_group {label}: 引用不存在的镜头 {unknown[:3]}。")
        gsum = round(sum(dur_of[sid] for sid in gids), 2)
        if gsum < seg_min - 1e-9 or gsum > cap + 1e-9:
            raise ValueError(
                f"beat_group {label}: 组时长 {_fmt(gsum)}s 超出 [{_fmt(seg_min)}, {_fmt(cap)}]s；"
                f"拆组、并组或回到组内镜长设计调整。")
        if abs(gsum - round(gsum)) > 1e-9:
            raise ValueError(
                f"beat_group {label}: 组时长 {_fmt(gsum)}s 非整数秒（视频 API 只接受整数 duration）；"
                f"在组边界上调整镜长取舍使组总长为整秒（组内 0.5s 网格镜长不变，±0.5s 取舍是创作决定）。")
        flat.extend(gids)
    if flat != order:
        missing = [sid for sid in order if sid not in flat]
        extra = [sid for sid in flat if sid not in order]
        raise ValueError(
            f"beat_groups 覆盖不完整：镜头组必须按顺序恰好覆盖全部镜头"
            f"{'；缺镜头 ' + str(missing[:3]) if missing else ''}"
            f"{'；多出/错序 ' + str(extra[:3]) if extra else ''}。")
    segments = [[next(s for s in shots if s["shot_id"] == sid) for sid in group.get("shot_ids") or []]
                for group in beat_groups]
    return _emit_segments(segments, set(), cap)


def _emit_segments(segments, candidates, cap):
    """统一输出 SEG 结构（time_range 累计）。"""
    out_segs = []
    t = 0.0
    for i, seg in enumerate(segments, 1):
        dur = round(sum(s["duration_s"] for s in seg), 2)
        out_segs.append({
            "segment_id": f"SEG{i:03d}",
            "shot_ids": [s["shot_id"] for s in seg],
            "duration_s": dur,
            "time_range_s": [round(t, 2), round(t + dur, 2)],
            "boundary_at_candidate": bool(segments[i - 2] and segments[i - 2][-1]["shot_id"] in candidates) if i > 1 else None,
        })
        t = round(t + dur, 2)

    at_cap = sum(1 for s in out_segs if abs(s["duration_s"] - cap) < 1e-9)
    return out_segs, [], at_cap


def cmd_pack(args):
    lib = load_library(args.library)
    h3 = load_h3(args.h3)
    cap = h3["capabilities"]["max_duration_s"]
    seg_min = h3["capabilities"]["min_duration_s"]

    sb = _read_json(args.storyboard)
    inp = _read_json(args.input) if args.input else {}
    candidates = set()
    beat_groups = []
    for scene in inp.get("scenes", []):
        candidates.update(scene.get("boundary_candidates", []))
        for group in scene.get("beat_groups", []) or []:
            if isinstance(group, dict):
                beat_groups.append(group)

    shots = sb.get("shots", [])
    missing_dur = [s.get("shot_id") for s in shots if isinstance(s, dict) and not isinstance(s.get("duration_s"), (int, float))]
    if missing_dur:
        _emit({"ok": False, "engine": "pack", "engine_version": ENGINE_VERSION,
               "error": f"{len(missing_dur)} 个镜头缺 duration_s（组校验依据是引擎算定的镜时长）："
                        f"{missing_dur[:5]}{' 等' if len(missing_dur) > 5 else ''}；先运行 allocate --write 再运行 pack"})
        raise SystemExit(2)

    try:
        out_segs, notes, at_cap = compute_pack(shots, candidates, cap, seg_min, beat_groups=beat_groups or None)
    except ValueError as exc:
        _emit({"ok": False, "engine": "pack", "engine_version": ENGINE_VERSION,
               "cap_s": cap, "error": str(exc), "written": None})
        raise SystemExit(2)

    out = {
        "ok": True, "engine": "pack", "engine_version": ENGINE_VERSION,
        "cap_s": cap, "segment_min_s": seg_min,
        "segments": out_segs,
        "stats": {
            "count": len(out_segs),
            "at_cap": at_cap,
            "at_cap_share": round(at_cap / len(out_segs), 3) if out_segs else 0,
        },
        "notes": notes + ([f"{at_cap} 组正好顶满 {_fmt(cap)}s（组划分只按真实时长，顶满需可解释）"] if at_cap else []),
    }

    if args.write:
        existing = {seg.get("segment_id"): seg for seg in sb.get("segments", []) if isinstance(seg, dict)}
        new_segments = []
        fresh = []
        for seg_out in out_segs:
            prev = existing.get(seg_out["segment_id"])
            if prev is None:
                fresh.append(seg_out["segment_id"])
                new_segments.append(dict(seg_out))
            else:
                prev["shot_ids"] = seg_out["shot_ids"]
                prev["duration_s"] = seg_out["duration_s"]
                prev["time_range_s"] = seg_out["time_range_s"]
                prev["boundary_at_candidate"] = seg_out["boundary_at_candidate"]
                new_segments.append(prev)
        dropped = sorted(set(existing) - {s["segment_id"] for s in out_segs})
        sb["segments"] = new_segments
        seg_of = {sid: seg_out["segment_id"] for seg_out in out_segs for sid in seg_out["shot_ids"]}
        for shot in sb.get("shots", []):
            if isinstance(shot, dict) and shot.get("shot_id") in seg_of:
                shot["segment_id"] = seg_of[shot["shot_id"]]
        _write_json(args.storyboard, sb)
        out["written"] = args.storyboard
        if fresh:
            out["notes"].append(f"新段 {fresh} 只有组校验字段，density_profile/tail_mode 等段级元数据需补齐")
        if dropped:
            out["notes"].append(f"旧段 {dropped} 不在本次组校验结果中，已随划分更新移除（其人工元数据一并失效）")

    _emit(out)



def kf_count(total_s, peaks, params):
    """KF_min = min；KF_max = min(base_max + floor(max(0,T−threshold)÷step), cap)；
    建议 = clamp(真实峰值数, KF_min, KF_max)。常数 ← params.kf"""
    import math
    kf = params["kf"]
    kmax = min(kf["base_max"] + int(math.floor(max(0.0, total_s - kf["long_episode_threshold_s"]) / kf["step_s"])), kf["cap"])
    kmin = kf["min"]
    suggested = None
    note = None
    if peaks is not None:
        if peaks < kmin:
            note = f"真实峰值数 {peaks} < 下限 {kmin}：回剧本补强峰值，不得凑数"
            suggested = kmin
        else:
            suggested = min(peaks, kmax)
    return {"min": kmin, "max": kmax, "suggested": suggested, "note": note,
            "per_seg_max": kf["per_seg_max"]}


def cmd_kf_count(args):
    lib = load_library(args.library)
    _emit({"ok": True, "engine": "kf-count", "engine_version": ENGINE_VERSION,
           **kf_count(float(args.total), args.peaks, _params(lib))})



def stats_of_storyboard(sb, lib, h3):
    params = _params(lib)
    h = params["health"]
    cap = h3["capabilities"]["max_duration_s"]
    shots = sb.get("shots", [])
    segs = sb.get("segments", [])
    ds = [s["duration_s"] for s in shots]
    names = {b: v["name"] for b, v in lib["beat_types"].items()}

    w = h["flatline_window_s"]
    bins = {}
    for d in ds:
        bins[int(d // w)] = bins.get(int(d // w), 0) + 1
    histogram = {f"{int(k * w)}-{int(k * w + w)}s": v for k, v in sorted(bins.items())}

    ordered = sorted(shots, key=lambda s: s["duration_s"])
    seg_of = {sid: g.get("segment_id") for g in segs if isinstance(g, dict) for sid in g.get("shot_ids", [])}

    def brief(s):
        return {"shot_id": s["shot_id"], "duration_s": s["duration_s"],
                "beat": names.get(s.get("beat_type"), s.get("beat_type")),
                "segment_id": s.get("segment_id") or seg_of.get(s["shot_id"])}

    at_cap = sum(1 for g in segs if abs(g.get("duration_s", 0) - cap) < 1e-9)
    return {
        "total_s": round(sum(ds), 2),
        "shot_count": len(ds),
        "duration_range_s": [min(ds), max(ds)] if ds else None,
        "histogram": histogram,
        "modal_window_share": round(max(bins.values()) / len(ds), 3) if ds else 0,
        "fastest3": [brief(s) for s in ordered[:EXTREMES_COUNT]],
        "slowest3": [brief(s) for s in reversed(ordered[-EXTREMES_COUNT:])],
        "segments": [{"segment_id": g["segment_id"], "shots": len(g.get("shot_ids", [])),
                      "duration_s": g.get("duration_s")} for g in segs],
        "segment_count": len(segs),
        "segments_at_cap": at_cap,
        "segments_at_cap_share": round(at_cap / len(segs), 3) if segs else 0,
    }


def cmd_stats(args):
    lib = load_library(args.library)
    h3 = load_h3(args.h3)
    sb = _read_json(args.storyboard)
    _emit({"ok": True, "engine": "stats", "engine_version": ENGINE_VERSION,
           **stats_of_storyboard(sb, lib, h3)})



def main():
    ap = argparse.ArgumentParser(description="rhythm_engine —— 节奏系统唯一计算源")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def base(p):
        p.add_argument("--library", default=None)

    p = sub.add_parser("shot-count")
    base(p); p.add_argument("--input", required=True)
    p.set_defaults(fn=cmd_shot_count)

    p = sub.add_parser("allocate")
    base(p); p.add_argument("--input", required=True)
    p.add_argument("--storyboard", default=None, help="提供时按段分组并（--write 时）写回")
    p.add_argument("--total", type=float, default=None)
    p.add_argument("--segment-budgets", action="store_true", help="以 storyboard 各段 duration_s 为段预算（优先于 --total）")
    p.add_argument("--write", action="store_true")
    p.set_defaults(fn=cmd_allocate)

    p = sub.add_parser("pack")
    base(p); p.add_argument("--storyboard", required=True)
    p.add_argument("--input", default=None)
    p.add_argument("--h3", default=None)
    p.add_argument("--write", action="store_true", help="把 SEG 划分与镜上 segment_id 写回 storyboard（段划分唯一写入路径）")
    p.set_defaults(fn=cmd_pack)

    p = sub.add_parser("kf-count")
    base(p); p.add_argument("--total", required=True)
    p.add_argument("--peaks", type=int, default=None)
    p.set_defaults(fn=cmd_kf_count)

    p = sub.add_parser("stats")
    base(p); p.add_argument("--storyboard", required=True)
    p.add_argument("--h3", default=None)
    p.set_defaults(fn=cmd_stats)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    _force_utf8_stdio()
    main()
