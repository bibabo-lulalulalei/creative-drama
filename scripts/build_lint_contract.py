# -*- coding: utf-8 -*-
"""build_lint_contract.py — 从 drama_lint.py 源码机读抽取检查合同（字典卡片）。

为什么存在：实测生产会话中模型把 drama_lint.py 源码当字典查（34 次读取、
9.9 万 token）——模型需要知道"lint 查什么"，但唯一答案是源码。本脚本把
548 个检查码按 --stage 调度映射抽取为 per-stage 卡片（每张 1-4.5K 字符），
模型读卡片不读源码。

红线（来自评审实测）：合同必须机读生成——手写第二份必然漂移，漂移的合同
比源码更危险。本脚本以 AST 解析源码，零手写；输出含源码指纹（issue() 调用
数 + 检查码集合 hash），--check 模式与源码对不上即报错退出（防漂移闸）。

用法：
  生成/更新合同: python scripts/build_lint_contract.py            # 写 references/lint-contract/
  防漂移校验:    python scripts/build_lint_contract.py --check    # 对不上 exit 1
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINT_PY = ROOT / "scripts" / "drama_lint.py"
OUT_DIR = ROOT / "references" / "lint-contract"

# main() 调度映射（源码 main() 的忠实转录；改 main() 时同步这张表——
# --check 会用 STAGE_GATES 与源码 main() 的 stage 分发比对吗？不会：
# 本表只决定"每个 check 函数的输出归属哪个阶段卡片"，抽取的检查码
# 集合与源码逐字一致（AST），表错了顶多卡片归属错、不产生内容漂移）。
# 字段: {stage: [ (check 函数名, 触发条件说明) ]}
STAGE_GATES: dict[str, list[tuple[str, str]]] = {
    "common": [
        ("check_episode_directories", "每集目录与时长文件存在"),
        ("check_episode_entry_manifests", "episode_manifest 指针与路径规则"),
        ("check_state", "制作状态.json 状态机推进合法性"),
        ("check_operation_log_tools", "操作日志登记的工具名合法"),
        ("check_plan_durations", "drama_plan 时长合同与逐集时长对账"),
    ],
    "planning": [
        ("check_stage_artifacts", "planning 阶段产物存在性（stage=planning）"),
        ("check_episode_manifest_ids", "episode_manifest 与 stage 绑定"),
    ],
    "script": [
        ("check_stage_artifacts", "script 阶段产物存在性"),
        ("check_episode_manifest_ids", "episode_manifest 与 stage 绑定"),
    ],
    "assets": [
        ("check_stage_artifacts", "assets 阶段产物存在性"),
        ("check_episode_manifest_ids", "episode_manifest 与 stage 绑定"),
        ("check_assets", "asset_registry/asset_usage/数据卡身份与状态"),
        ("validate_collective_profiles", "群像画像字段与 entity_scope 一致"),
    ],
    "storyboard": [
        ("check_stage_artifacts", "storyboard 阶段产物存在性"),
        ("check_episode_manifest_ids", "episode_manifest 与 stage 绑定"),
        ("check_assets", "资产索引（storyboard 阶段也全量复核）"),
        ("validate_collective_profiles", "群像画像一致性"),
        ("check_beat_library_desync", "节拍库 md 与 beat_types.json 漂移"),
        ("check_rhythm_reconciliation", "engine_drift/pack_drift 引擎对账（beat_groups 传递）"),
        ("check_rhythm_diversity", "节奏健康度（static 占比/极差/扁平度）"),
        ("check_storyboards", "十五列/rhythm_input/总控卡/causal_ledger/highlight_bindings 全链"),
    ],
    "keyframes": [
        ("check_stage_artifacts", "keyframes 阶段产物存在性"),
        ("check_episode_manifest_ids", "episode_manifest 与 stage 绑定"),
        ("check_assets", "资产索引"),
        ("validate_collective_profiles", "群像画像一致性"),
        ("check_beat_library_desync", "节拍库漂移"),
        ("check_rhythm_reconciliation", "引擎对账"),
        ("check_rhythm_diversity", "节奏健康度"),
        ("check_storyboards", "分镜全链（keyframes 阶段也复核）"),
        ("check_keyframes", "keyframe_manifest 张数与 storyboard.keyframe_requests 对账"),
    ],
    "video": [
        ("check_stage_artifacts", "video 阶段产物存在性"),
        ("check_episode_manifest_ids", "episode_manifest 与 stage 绑定"),
        ("check_assets", "资产索引"),
        ("validate_collective_profiles", "群像画像一致性"),
        ("check_beat_library_desync", "节拍库漂移"),
        ("check_rhythm_reconciliation", "引擎对账"),
        ("check_rhythm_diversity", "节奏健康度"),
        ("check_storyboards", "分镜全链（video 阶段也复核）"),
        ("check_keyframes", "KF 清单对账（video 阶段也复核）"),
        ("check_video", "video_manifest/gen.json/成稿/speech_lines/确认链"),
        ("check_prompt_markers", "成稿标记与台词逐字（check_video 内部调用）"),
        ("check_prompt_preflight", "成稿五段结构预检（check_video 内部调用）"),
        ("check_h3_prompt", "成稿存在/非空/哈希"),
        ("check_video_generation_confirmations", "生成确认记录与批次参数"),
        ("check_asset_usage_reconciliation", "asset_usage_plan 与 reference_inputs 双向对账"),
    ],
    "final": [
        ("check_stage_artifacts", "final 阶段产物存在性"),
        ("check_episode_manifest_ids", "episode_manifest 与 stage 绑定"),
        ("check_assets", "资产索引"),
        ("validate_collective_profiles", "群像画像一致性"),
        ("check_beat_library_desync", "节拍库漂移"),
        ("check_rhythm_reconciliation", "引擎对账"),
        ("check_rhythm_diversity", "节奏健康度"),
        ("check_storyboards", "分镜全链（final 阶段也复核）"),
        ("check_keyframes", "KF 清单对账"),
        ("check_video", "video_manifest 复核（require_accepted=true）"),
        ("check_prompt_markers", "成稿标记与台词逐字"),
        ("check_prompt_preflight", "成稿预检"),
        ("check_h3_prompt", "成稿存在/哈希"),
        ("check_video_generation_confirmations", "生成确认记录"),
        ("check_asset_usage_reconciliation", "资产双向对账"),
        ("check_delivery", "delivery_manifest/字幕链/outputs 唯一性"),
        ("check_continuity_for_delivery", "接缝与抽帧记录复核"),
    ],
    "skill": [
        ("check_skill_package", "SKILL frontmatter/引用/锚点存在性（--stage skill 专用）"),
    ],
}

LEVEL_LABEL = {"error": "❌错误(阻断)", "warning": "⚠警告(复核)", "info": "ℹ提示"}


def parse_issue_calls(tree: ast.Module) -> dict[str, list[dict]]:
    """AST 解析：每个函数内的 issue(调用) → {code, level, message}。

    只取字面量字符串参数（检查码/消息中含 f-string 或变量的归为
    动态码，单列防漏）；同一个函数内的调用按源码顺序保留。
    """
    calls_by_fn: dict[str, list[dict]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        entries: list[dict] = []
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            callee = sub.func
            name = callee.id if isinstance(callee, ast.Name) else (
                callee.attr if isinstance(callee, ast.Attribute) else "")
            if name != "issue":
                continue
            if not sub.args:
                continue
            entry = {"code": None, "level": None, "message": None}
            for arg in sub.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if entry["level"] is None and arg.value in LEVEL_LABEL:
                        entry["level"] = arg.value
                    elif entry["code"] is None and re.fullmatch(
                            r"[a-z0-9]+(?:_[a-z0-9]+)+", arg.value):
                        entry["code"] = arg.value
                    elif entry["message"] is None:
                        entry["message"] = arg.value
                else:
                    entry["message"] = entry["message"] or "<动态生成，见源码>"
            entry["level"] = entry["level"] or "error"
            if entry["code"] is None:
                entry["code"] = "<动态码，见源码>"
            entry["message"] = entry["message"] or "<动态消息，见源码>"
            entries.append(entry)
        if entries:
            calls_by_fn[node.name] = entries
    return calls_by_fn


def fingerprint(calls_by_fn: dict[str, list[dict]]) -> str:
    """源码指纹：全部字面检查码有序集合的 sha256 前 16 位。"""
    codes = sorted({e["code"] for entries in calls_by_fn.values() for e in entries})
    blob = "\n".join(codes).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def build_card(stage: str, gates: list[tuple[str, str]], calls_by_fn: dict[str, list[dict]]) -> str:
    lines = [f"# lint 检查合同 · {stage} 阶段", ""]
    lines.append("> 本卡片由 `scripts/build_lint_contract.py` 从 `drama_lint.py` 机读生成，禁止手改。")
    lines.append("> 用途：开工前读这张卡知道本阶段 lint 会查什么；报错后按码查修复方向。")
    lines.append("> 与源码不一致时以源码为准，并重跑 `python scripts/build_lint_contract.py --check`。")
    lines.append("")
    # 阶段复用上游 check 函数时只引用不重列，避免同一批条目在多张卡重复出现。
    upstream_owner: dict[str, str] = {}
    for earlier in STAGE_GATES:
        if earlier == stage:
            break
        for fn, _ in STAGE_GATES[earlier]:
            upstream_owner.setdefault(fn, earlier)
    own_gates = [(fn, why) for fn, why in gates if fn not in upstream_owner]
    ref_gates = [(fn, why) for fn, why in gates if fn in upstream_owner]
    total = sum(len(calls_by_fn.get(fn, [])) for fn, _ in own_gates)
    lines.append(f"本阶段新增检查项：{total}。运行命令：`python scripts/drama_lint.py --stage {stage}`（skill 阶段在 skill 根目录运行）。")
    if ref_gates:
        lines.append("")
        lines.append("本阶段同时全量复核以下上游检查（报错时先读对应上游卡）：")
        for fn, why in ref_gates:
            lines.append(f"- {upstream_owner[fn]} 阶段卡 · `{fn}` —— {why}")
    lines.append("")
    lines.append("| 检查码 | 级别 | 查什么（源码原文消息） |")
    lines.append("|---|---|---|")
    seen: set[str] = set()
    for fn, _ in own_gates:
        for e in calls_by_fn.get(fn, []):
            key = (e["code"], e["message"])
            if key in seen:
                continue
            seen.add(key)
            msg = e["message"].replace("|", "\\|").replace("\n", " ")
            if len(msg) > 120:
                msg = msg[:117] + "..."
            lines.append(f"| `{e['code']}` | {e['level']} | {msg} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="lint 检查合同机读生成/校验")
    ap.add_argument("--check", action="store_true", help="只校验现有合同与源码一致，不写出")
    args = ap.parse_args()

    src = LINT_PY.read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls_by_fn = parse_issue_calls(tree)
    fp = fingerprint(calls_by_fn)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cards: dict[str, str] = {}
    for stage, gates in STAGE_GATES.items():
        cards[stage] = build_card(stage, gates, calls_by_fn)

    manifest = {
        "source": "scripts/drama_lint.py",
        "source_sha256": hashlib.sha256(src.encode("utf-8")).hexdigest()[:16],
        "issue_calls_total": sum(len(v) for v in calls_by_fn.values()),
        "unique_literal_codes": len({e["code"] for v in calls_by_fn.values() for e in v}),
        "code_fingerprint": fp,
        "stages": sorted(cards),
    }

    if args.check:
        current = OUT_DIR / "manifest.json"
        if not current.is_file():
            print("lint 合同缺失：先运行 python scripts/build_lint_contract.py 生成")
            return 1
        import json
        old = json.loads(current.read_text(encoding="utf-8"))
        if old.get("code_fingerprint") != fp or old.get("source_sha256") != manifest["source_sha256"]:
            print("lint 合同与源码漂移：drama_lint.py 已修改，请重跑 python scripts/build_lint_contract.py 更新合同")
            return 1
        print("lint 合同与源码一致")
        return 0

    import json
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for stage, text in cards.items():
        (OUT_DIR / f"{stage}.md").write_text(text, encoding="utf-8")
    total_chars = sum(len(t) for t in cards.values())
    print(json.dumps({
        "ok": True,
        "stages": sorted(cards),
        "issue_calls": manifest["issue_calls_total"],
        "unique_literal_codes": manifest["unique_literal_codes"],
        "cards_chars": {s: len(t) for s, t in sorted(cards.items())},
        "total_chars": total_chars,
        "fingerprint": fp,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
