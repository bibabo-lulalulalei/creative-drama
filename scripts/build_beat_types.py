"""build_beat_types.py — 由《节拍类型库.md》生成 beat_types.json 的唯一生成器。

《节拍类型库.md》是唯一人类权威；本脚本解析其中三张机器表：
  §4 机读映射表:  | id | name | range_low_s | range_high_s | anchor_1_s | anchor_3_s | anchor_5_s | fast_pole_capable |
  §3 风格机器表:  | style_id | beat_id | override_low_s | override_high_s | note |
  §5 节奏参数表:  | path | value |
以及文件头的 `library_version: N` 行。

产物 scripts/beat_types.json 是纯生成物，禁止手改。
lint 的 desync 检查 = 以 --check 重跑本脚本并与磁盘 json 逐项比对。

用法:
  python build_beat_types.py --library-md <节拍类型库.md路径> [--output <json路径>]
  python build_beat_types.py --library-md <路径> --check   # 只比对，不写盘；一致 exit 0，不一致 exit 1
"""
import argparse
import io
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = SCRIPT_DIR / "beat_types.json"

BEAT_TABLE_HEADER = ["id", "name", "range_low_s", "range_high_s", "anchor_1_s", "anchor_3_s", "anchor_5_s", "fast_pole_capable"]
STYLE_TABLE_HEADER = ["style_id", "beat_id", "override_low_s", "override_high_s", "note"]
PARAMS_TABLE_HEADER = ["path", "value"]

REQUIRED_PARAM_PATHS = [
    "speech.chars_per_s_normal", "speech.chars_per_s_rapid", "speech.onset_s",
    "speech.reaction_s", "speech.min_overhead_s",
    "rounding_grid_s",
    "role_floors.payoff_s", "role_floors.final_s",
    "shot_bounds.min_s", "shot_bounds.max_s", "shot_bounds.info_injection_threshold_s",
    "kf.min", "kf.base_max", "kf.long_episode_threshold_s", "kf.step_s", "kf.cap", "kf.per_seg_max",
    "high_density.min_shots", "high_density.golden_window_s", "high_density.first_shot_max_s",
    "asl_targets.dialogue_emotional", "asl_targets.suspense_build", "asl_targets.micro_film",
    "health.segment_min_range_s", "health.flatline_window_s", "health.flatline_max_share",
    "health.fast_pole_max_s", "health.slow_pole_min_s", "health.slow_pole_min_total_s",
    "health.beat_monoculture_max_share", "health.cap_uniformity_min_segments",
    "health.cap_uniformity_share", "health.speech_voice_max_share_normal",
    "health.speech_voice_max_share_dense",
    "shot_count_risk_threshold",
]


def _fail(msg):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False), file=sys.stderr)
    sys.exit(2)


def _parse_md_tables(text):
    """解析全部 markdown 表格，返回 [(header_cells, [row_cells,...]), ...]（跳过分隔行）。"""
    tables = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and line.endswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            rows = []
            for bl in block:
                cells = [c.strip() for c in bl.strip("|").split("|")]
                if all(re.fullmatch(r":?-{2,}:?", c or "---") for c in cells):
                    continue
                rows.append(cells)
            if rows:
                tables.append((rows[0], rows[1:]))
        else:
            i += 1
    return tables


def _find_table(tables, expected_header, label, required=True):
    matches = [(h, r) for h, r in tables if h[: len(expected_header)] == expected_header]
    if not matches:
        if required:
            _fail(f"未找到{label}（表头应为 {'|'.join(expected_header)}）")
        return None
    if len(matches) > 1:
        _fail(f"找到 {len(matches)} 张{label}，机器表必须唯一")
    return matches[0]


def _to_number(cell, ctx):
    try:
        v = float(cell)
    except ValueError:
        _fail(f"{ctx}: 无法解析数值 '{cell}'")
    return int(v) if v == int(v) and "." not in cell else v


def _parse_param_value(cell):
    cell = cell.strip()
    if cell.startswith("["):
        try:
            v = json.loads(cell)
        except json.JSONDecodeError:
            _fail(f"§5 参数值 JSON 解析失败: '{cell}'")
        if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)):
            _fail(f"§5 数组参数必须为 [low, high] 两个数值: '{cell}'")
        return v
    return _to_number(cell, "§5 参数")


def _set_path(tree, dotted, value):
    parts = dotted.split(".")
    node = tree
    for p in parts[:-1]:
        node = node.setdefault(p, {})
        if not isinstance(node, dict):
            _fail(f"§5 参数路径冲突: '{dotted}'")
    node[parts[-1]] = value


def build(md_path):
    text = io.open(str(md_path), encoding="utf-8-sig").read()

    m = re.search(r"(?m)^library_version:\s*(\d+)\s*$", text)
    if not m:
        _fail("未找到文件头 `library_version: N` 行")
    version = int(m.group(1))

    tables = _parse_md_tables(text)

    _, beat_rows = _find_table(tables, BEAT_TABLE_HEADER, "§4 机读映射表")
    beat_types = {}
    for row in beat_rows:
        if len(row) < 8:
            _fail(f"§4 行列数不足: {row}")
        bid = row[0]
        if not re.fullmatch(r"[a-z][a-z0-9_]*", bid):
            _fail(f"§4 id 必须为 snake_case: '{bid}'")
        if bid in beat_types:
            _fail(f"§4 id 重复: '{bid}'")
        lo = _to_number(row[2], f"§4 {bid}.range_low_s")
        hi = _to_number(row[3], f"§4 {bid}.range_high_s")
        a1 = _to_number(row[4], f"§4 {bid}.anchor_1_s")
        a3 = _to_number(row[5], f"§4 {bid}.anchor_3_s")
        a5 = _to_number(row[6], f"§4 {bid}.anchor_5_s")
        if not lo < hi:
            _fail(f"§4 {bid}: range_low_s 必须小于 range_high_s（{lo} vs {hi}）")
        for label, a in (("anchor_1_s", a1), ("anchor_3_s", a3), ("anchor_5_s", a5)):
            if not (lo <= a <= hi):
                _fail(f"§4 {bid}: {label}={a} 不在区间 [{lo}, {hi}] 内")
        fpc = row[7].strip().lower()
        if fpc not in ("yes", "no"):
            _fail(f"§4 {bid}: fast_pole_capable 只能是 yes/no（'{row[7]}'）")
        beat_types[bid] = {
            "name": row[1],
            "range_s": [lo, hi],
            "intensity_anchors": {"1": a1, "3": a3, "5": a5},
            "fast_pole_capable": fpc == "yes",
        }
    if not beat_types:
        _fail("§4 机读映射表无任何数据行")

    style_profiles = {}
    found = _find_table(tables, STYLE_TABLE_HEADER, "§3 风格机器表", required=False)
    if found:
        for row in found[1]:
            if len(row) < 5:
                _fail(f"§3 风格机器表列数不足: {row}")
            sid, bid = row[0], row[1]
            if bid not in beat_types:
                _fail(f"§3 风格 '{sid}' 引用了不存在的 beat_id '{bid}'")
            lo = _to_number(row[2], f"§3 {sid}/{bid}.override_low_s")
            hi = _to_number(row[3], f"§3 {sid}/{bid}.override_high_s")
            if not lo < hi:
                _fail(f"§3 {sid}/{bid}: override_low_s 必须小于 override_high_s")
            prof = style_profiles.setdefault(sid, {"overrides": {}, "note": ""})
            if bid in prof["overrides"]:
                _fail(f"§3 风格 '{sid}' 对 '{bid}' 重复校准")
            prof["overrides"][bid] = [lo, hi]
            note = row[4].strip()
            if note and note != "-":
                prof["note"] = (prof["note"] + "；" + note).strip("；")

    _, param_rows = _find_table(tables, PARAMS_TABLE_HEADER, "§5 节奏参数表")
    params = {}
    for row in param_rows:
        if len(row) < 2:
            _fail(f"§5 行列数不足: {row}")
        _set_path(params, row[0], _parse_param_value(row[1]))
    for path in REQUIRED_PARAM_PATHS:
        node = params
        for p in path.split("."):
            if not isinstance(node, dict) or p not in node:
                _fail(f"§5 缺少必需参数: '{path}'")
            node = node[p]

    return {
        "_generated_by": "build_beat_types.py —— 由《节拍类型库.md》生成，禁止手改",
        "version": version,
        "params": params,
        "beat_types": beat_types,
        "style_profiles": style_profiles,
    }


def main():
    ap = argparse.ArgumentParser(description="由《节拍类型库.md》生成 beat_types.json")
    ap.add_argument("--library-md", required=True)
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    ap.add_argument("--check", action="store_true", help="只与现有 json 比对，不写盘")
    args = ap.parse_args()

    data = build(args.library_md)
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        out = Path(args.output)
        if not out.exists():
            print(json.dumps({"ok": False, "error": f"json 不存在: {out}"}, ensure_ascii=False))
            sys.exit(1)
        existing = json.loads(io.open(str(out), encoding="utf-8-sig").read())
        if existing == data:
            print(json.dumps({"ok": True, "version": data["version"], "beats": len(data["beat_types"])}, ensure_ascii=False))
            sys.exit(0)
        diffs = []
        for key in ("version", "params", "beat_types", "style_profiles"):
            if existing.get(key) != data.get(key):
                diffs.append(key)
        print(json.dumps({"ok": False, "mismatch_sections": diffs}, ensure_ascii=False))
        sys.exit(1)

    Path(args.output).write_text(rendered, encoding="utf-8")
    print(json.dumps({
        "ok": True, "output": args.output, "version": data["version"],
        "beats": len(data["beat_types"]), "styles": len(data["style_profiles"]),
    }, ensure_ascii=False))


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _rc = getattr(_stream, "reconfigure", None)
        if _rc:
            try:
                _rc(encoding="utf-8", errors="replace")
            except Exception:
                pass
    main()
