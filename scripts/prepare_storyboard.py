#!/usr/bin/env python3
"""只读提取分镜当前场事实；不创作、修改项目、确认阶段或替代整场审校。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from rhythm_engine import file_sha, project_file, source_index_from_contract


class PreparationError(ValueError):
    pass


SCOPE_NOTE = "只读源事实选择，不代表阶段检查通过、资产批准或执行授权；跨场依赖按源定位补读。"
ENTITY_IDS = re.compile(r"\b(?:CHR|SCN|PROP|VOICE|STYLE)\d+\b")
PLAN_KEYS = (
    "source_lock", "language_contract", "explicit_overrides", "style_contract",
    "duration_contract", "scale_plan", "model_plan", "delivery_settings",
    "audience_plan", "creative_proposition", "objective", "selected_direction_id",
    "selection_reason", "creative_mechanism", "opening_strategy", "type_strategy",
    "highlight_strategy", "emotion_design", "rhythm_design", "risk_plan", "handoff",
)
ASSET_FIELDS = {
    "asset_id", "category", "entity_scope", "state_id", "version", "status",
    "file", "files", "duration_s", "project_visual_mode", "representation_scope",
    "reference_asset_ids",
}


def _read(root, relative, sources, issues, *, required=False):
    path = project_file(root, relative)
    if not path.is_file():
        if required:
            raise PreparationError(f"缺必需文件：{relative}")
        issues.append({"code": "optional_source_missing", "file": relative})
        return None
    # Decode and hash the same snapshot; retain original newlines, including CRLF.
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    sources[relative] = {
        "file": relative, "sha256": hashlib.sha256(raw).hexdigest(),
        "line_count": len(text.splitlines()),
    }
    if path.suffix.lower() != ".json":
        return text
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise PreparationError(f"JSON 无法解析：{relative}：{exc}") from exc
    if not isinstance(value, dict):
        raise PreparationError(f"JSON 顶层必须是对象：{relative}")
    if "revision" in value:
        sources[relative]["revision"] = value["revision"]
    return value


def _scene_ranges(contract, text):
    scenes = contract.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise PreparationError("script_contract.scenes 必须是非空数组")
    positions, seen = [], set()
    for scene in scenes:
        sid = scene.get("scene_id") if isinstance(scene, dict) else None
        if not isinstance(sid, str) or not re.fullmatch(r"E\d+S\d+", sid) or sid in seen:
            raise PreparationError("源场次 ID 必须唯一，格式为 E01S01")
        seen.add(sid)
        matches = list(re.finditer(r"(?m)^#{1,6}\s+" + re.escape(sid) + r"(?:\s|[：:|]|$)", text))
        if len(matches) != 1:
            raise PreparationError(f"{sid} 需唯一场次标题以定位源原文")
        positions.append(matches[0].start())
    if positions != sorted(positions):
        raise PreparationError("源剧本场次顺序与 script_contract.scenes 不一致；先修源索引")
    ranges = []
    for index, (scene, start) in enumerate(zip(scenes, positions)):
        end = positions[index + 1] if index + 1 < len(positions) else len(text)
        ranges.append({"scene_id": scene["scene_id"], "start": start, "end": end,
                       "start_line": text.count("\n", 0, start) + 1,
                       "end_line": text.count("\n", 0, end) + (0 if text[:end].endswith("\n") else 1)})
    return ranges


def _locator(relative, row):
    return {"file": relative, "scene_id": row["scene_id"],
            "start_line": row["start_line"], "end_line": row["end_line"]}


def _position(value, episode):
    match = re.fullmatch(r"(?:(ep_[1-9]\d*):)?E\d+S(\d+)", str(value))
    if not match:
        return None
    return int((match[1] or episode)[3:]), int(match[2])


def _states(entity, aid, scene, episode, issues):
    """Resolve explicit state IDs or declared effective ranges; never guess a state."""
    timeline = entity.get("state_timeline")
    if not isinstance(timeline, list):
        return entity
    refs = re.findall(re.escape(aid) + r"(?::|-)(STATE\d+)\b", json.dumps(scene, ensure_ascii=False))
    current = _position(scene["scene_id"], episode)
    selected, unresolved = [], []
    for state in timeline:
        if not isinstance(state, dict):
            unresolved.append(state)
            continue
        state_id = str(state.get("state_id", ""))
        suffix = re.search(r"(?:^|[:-])(STATE\d+)$", state_id)
        if refs:
            if suffix and suffix[1] in refs:
                selected.append(state)
        else:
            start = _position(state.get("effective_from"), episode)
            end = _position(state.get("effective_to"), episode) if state.get("effective_to") else None
            if start is None or (state.get("effective_to") and end is None):
                unresolved.append(state)
            elif start <= current and (end is None or current <= end):
                selected.append(state)
    resolved_refs = {re.search(r"(?:^|[:-])(STATE\d+)$", str(row.get("state_id", "")))[1]
                     for row in selected if re.search(r"(?:^|[:-])(STATE\d+)$", str(row.get("state_id", "")))}
    missing_refs = set(refs) - resolved_refs
    if unresolved or missing_refs or (timeline and not selected):
        # Preserve unresolved candidates verbatim, explicitly separated from resolved state.
        issues.append({"code": "state_scope_unresolved", "asset_id": aid,
                       "message": "状态无法完整定位，保留未决候选；按源核对，不视为当前状态已确认。"})
    result = dict(entity, state_timeline=selected)
    if unresolved or missing_refs or (timeline and not selected):
        result["unresolved_state_candidates"] = unresolved or timeline
    return result


def load_storyboard_context(root, episode, scene_id=None, *, neighbors=False, include_global=False, list_only=False):
    root = Path(root).resolve()
    if not re.fullmatch(r"ep_[1-9]\d*", episode):
        raise PreparationError("episode ID 格式必须为 ep_1")
    if list_only and (scene_id or neighbors or include_global):
        raise PreparationError("--list 不能与 --scene/--neighbors/--include-global 同用")
    sources, issues = {}, []
    base = f"episodes/{episode}"
    contract_file = f"{base}/01_剧本/script_contract_{episode}.json"
    contract = _read(root, contract_file, sources, issues, required=True)
    if contract.get("episode_id", episode) != episode:
        raise PreparationError("script_contract.episode_id 与请求集不一致")
    if type(contract.get("revision")) is not int or contract["revision"] < 1:
        raise PreparationError("script_contract.revision 必须是正整数，不能派生有效 source_binding")
    script_file = contract.get("source_markdown")
    script = _read(root, script_file, sources, issues, required=True)
    if not isinstance(script, str):
        raise PreparationError("source_markdown 必须指向剧本正文")
    ranges = _scene_ranges(contract, script)
    if sources[script_file]["sha256"] != contract.get("source_sha256"):
        issues.append({"code": "source_sha_mismatch", "file": script_file,
                       "message": "正文 SHA 与剧本合同不一致；本输出保留实际原文，须核对源版本。"})
    state = _read(root, "00_制作控制/制作状态.json", sources, issues) or {}
    if state.get("current_episode") and state["current_episode"] != episode:
        issues.append({"code": "different_current_episode", "current_episode": state["current_episode"],
                       "message": "只读查看其他集，不授权推进该集。"})
    storyboard_file = f"{base}/02_分镜/storyboard_{episode}.json"
    storyboard = _read(root, storyboard_file, sources, issues) or {}
    artifacts = []
    candidates = [storyboard_file, f"{base}/02_分镜/rhythm_input_{episode}.json",
                  storyboard.get("director_control_card") or f"{base}/02_分镜/导演总控卡_{episode}.md",
                  storyboard.get("source_markdown") or f"{base}/02_分镜/分镜_完整分镜表_{episode}.md"]
    for relative in dict.fromkeys(candidates):
        path = project_file(root, relative)
        row = {"file": relative, "exists": path.is_file()}
        if path.is_file():
            row["sha256"] = file_sha(path)
        artifacts.append(row)
    result = {
        "scope_note": SCOPE_NOTE, "episode_id": episode,
        "source_binding": {"file": contract_file, "revision": contract.get("revision"),
                           "sha256": sources[contract_file]["sha256"]},
        "progress": {key: state[key] for key in ("current_stage", "current_episode", "last_successful_operation") if key in state},
        "scenes": [dict(_locator(script_file, row), contract_pointer=f"/scenes/{index}",
                        existing_shot_count=sum(shot.get("scene_id") == row["scene_id"] for shot in storyboard.get("shots", []) if isinstance(shot, dict)))
                   for index, row in enumerate(ranges)],
        "artifacts": artifacts, "sources": sources, "issues": issues,
    }
    # Progress follows actual registered scene files, never the apparent completeness
    # of a director card. Keep the default execution-sized; --list is navigation.
    from storyboard_draft import describe_progress
    draft_progress = describe_progress(root, episode, result["source_binding"],
                                       [row["scene_id"] for row in ranges])
    result["draft_progress"] = draft_progress
    result["next_action"] = draft_progress["next_action"]
    result["authoring_contract"] = "references/storyboard-draft.md"
    if draft_progress["ready_to_assemble"]:
        result["next_command"] = ["python", "scripts/storyboard_draft.py", "assemble",
                                  "--project-root", str(root), "--episode", episode]
    if list_only:
        return result
    if not scene_id:
        scene_id = draft_progress.get("next_scene_id")
    if not scene_id:
        return result
    indices = [i for i, row in enumerate(ranges) if row["scene_id"] == scene_id]
    if len(indices) != 1:
        raise PreparationError(f"找不到唯一场次：{scene_id}；用 --list 查看导航")
    index = indices[0]
    # Navigation is a separate mode, not repeated in every current-scene payload.
    result.pop("scenes")
    result["scene_position"] = {"index": index + 1, "total": len(ranges)}
    if draft_progress["next_action"] == "save_scene":
        input_file = f"{base}/02_分镜/本场输入_{scene_id}.json"
        result["author_input_file"] = input_file
        result["next_command"] = ["python", "scripts/storyboard_draft.py", "save",
                                  "--project-root", str(root), "--episode", episode,
                                  "--scene", scene_id, "--input", str(project_file(root, input_file))]

    def original(i):
        row = ranges[i]
        return dict(_locator(script_file, row), text=script[row["start"]:row["end"]],
                    contract={"file": contract_file, "json_pointer": f"/scenes/{i}", "value": contract["scenes"][i]})

    current = contract["scenes"][index]
    result["scene"] = original(index)
    result["neighbors"] = {}
    for name, i in (("previous", index - 1), ("next", index + 1)):
        if 0 <= i < len(ranges):
            result["neighbors"][name] = original(i) if neighbors else _locator(script_file, ranges[i])
    preamble_locator = {"file": script_file, "start_line": 1,
                        "end_line": ranges[0]["start_line"] - 1}
    # Existing parser checks actual source excerpts/lines; selection is not a new lint gate.
    source_index = source_index_from_contract({"scenes": [current]}, result["scene"]["text"], issues)
    result["rhythm_sources"] = {
        "source_refs": list(source_index),
        "utterance_sources": [{"line_id": row.get("line_id"), "speaker_ref": row.get("speaker_ref"),
                               "source_ref": ref} for ref, row in source_index.items() if ref.startswith("line:")],
        "remaining_design": "以上仅为稳定源身份；utterance_id、演读估时/依据、镜头、过程与先后关系仍由导演设计，未填空值或预设秒数。",
    }
    plan_file = "00_制作控制/drama_plan.json"
    plan = _read(root, plan_file, sources, issues) or {}
    global_keys = [key for key in contract if key != "scenes"]
    plan_keys = [key for key in PLAN_KEYS if key in plan]
    result["global_context_included"] = include_global
    result["global_sources"] = {
        "script_preamble": preamble_locator,
        "global_contract": {"file": contract_file, "json_pointers": [f"/{key}" for key in global_keys]},
        "locked_plan": {"file": plan_file, "json_pointers": [f"/{key}" for key in plan_keys]},
        "read_when_missing": "本输出默认只有全局定位；首次进入本集或实际缺少全局原文时加 --include-global 取一次。文件指纹见 sources。",
    }
    if include_global:
        result["script_preamble"] = dict(preamble_locator, text=script[:ranges[0]["start"]])
        result["global_contract"] = {"file": contract_file, "value": {key: contract[key] for key in global_keys}}
        result["locked_plan"] = {"file": plan_file, "value": {key: plan[key] for key in plan_keys}}
    card_file = "00_制作控制/project_data_card.json"
    card = _read(root, card_file, sources, issues) or {}
    ids = set(ENTITY_IDS.findall(json.dumps(current, ensure_ascii=False) + result["scene"]["text"]))
    selected_card = {}
    for collection, id_key in (("characters", "character_id"), ("scenes", "scene_id"), ("props", "prop_id"), ("voices", "voice_id")):
        rows = []
        for i, entity in enumerate(card.get(collection, [])):
            if isinstance(entity, dict) and entity.get(id_key) in ids:
                rows.append({"json_pointer": f"/{collection}/{i}",
                             "value": _states(entity, entity[id_key], current, episode, issues)})
                ids.update(ENTITY_IDS.findall(json.dumps(entity.get("identity_locked", {}), ensure_ascii=False)))
        selected_card[collection] = rows
    result["data_card"] = {"file": card_file, "global_settings": card.get("global_settings", {}), "entities": selected_card}
    usage_file = f"{base}/03_资产/asset_usage_{episode}.json"
    registry_file = "shared/03_资产/asset_registry.json"
    usage = _read(root, usage_file, sources, issues) or {}
    registry = _read(root, registry_file, sources, issues) or {}
    ids.update(row.get("asset_id") for row in usage.get("shared_assets", []) if isinstance(row, dict) and str(row.get("asset_id", "")).startswith("STYLE"))
    selected_usage = {}
    for key, value in usage.items():
        selected_usage[key] = [dict(json_pointer=f"/{key}/{i}", value=row) for i, row in enumerate(value)
                               if isinstance(row, dict) and row.get("asset_id") in ids] if key in {
                                   "shared_assets", "episode_assets", "reused_episode_assets"} and isinstance(value, list) else value
    result["asset_usage"] = {"file": usage_file, "value": selected_usage}
    result["registry"] = {"file": registry_file, "assets": [
        {"json_pointer": f"/assets/{i}", "value": {key: value for key, value in row.items() if key in ASSET_FIELDS}}
        for i, row in enumerate(registry.get("assets", []))
        if isinstance(row, dict) and row.get("asset_id") in ids]}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--episode", required=True)
    parser.add_argument("--scene", help="指定要查看的场；省略时直接提取下一未登记场及下一动作")
    parser.add_argument("--list", dest="list_only", action="store_true", help="仅列进度/场次/产物导航，不提取本场正文")
    parser.add_argument("--neighbors", action="store_true", help="同时输出前后相邻整场原文与合同；默认只给源定位")
    parser.add_argument("--include-global", action="store_true", help="首次进入本集或缺少全局原文时加读一次；默认下一场或指定场均可使用")
    args = parser.parse_args(argv)
    try:
        result = load_storyboard_context(args.project_root, args.episode, args.scene,
                                        neighbors=args.neighbors, include_global=args.include_global,
                                        list_only=args.list_only)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    # Compact JSON avoids spending context on indentation around unchanged source text.
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
