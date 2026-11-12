#!/usr/bin/env python3
"""Save one source-bound scene candidate, then assemble the standard episode inputs."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re
import sys

import rhythm_engine as engine


class DraftError(ValueError):
    pass


def _paths(root, episode):
    if not re.fullmatch(r"ep_[1-9]\d*", episode):
        raise DraftError("episode 必须为 ep_N")
    base = f"episodes/{episode}/02_分镜"
    return {
        "draft_dir": engine.project_file(root, f"{base}/.draft"),
        "storyboard": engine.project_file(root, f"{base}/storyboard_{episode}.json"),
        "rhythm_input": engine.project_file(root, f"{base}/rhythm_input_{episode}.json"),
        "markdown": engine.project_file(root, f"{base}/分镜_完整分镜表_{episode}.md"),
    }


def _scene_path(root, episode, scene):
    if not re.fullmatch(r"E\d+S\d+", scene):
        raise DraftError("scene 必须为 E01S01")
    return engine.project_file(root, f"episodes/{episode}/02_分镜/.draft/{scene}.json")


def _source(root, episode, binding=None):
    relative = f"episodes/{episode}/01_剧本/script_contract_{episode}.json"
    path = engine.project_file(root, relative)
    contract = engine.read_json(path)
    current = {"file": relative, "revision": contract.get("revision"), "sha256": engine.file_sha(path)}
    if contract.get("episode_id", episode) != episode or (binding is not None and binding != current):
        raise DraftError("source_script 必须绑定当前集真实源合同 file/revision/sha256")
    scenes = contract.get("scenes", [])
    ids = [row.get("scene_id") for row in scenes if isinstance(row, dict)]
    if not ids or len(ids) != len(scenes) or len(set(ids)) != len(ids):
        raise DraftError("源合同场次必须非空且身份唯一")
    index, issues = engine.load_source(root, {"episode_id": episode, "source_script": current, "utterances": []}, {})
    if issues:
        raise DraftError(json.dumps(issues, ensure_ascii=False))
    return current, scenes, index


def _standard_progress(paths):
    existing = [{"file": str(path), "exists": path.is_file()} for name, path in paths.items() if name != "draft_dir"]
    scenes = set()
    if paths["storyboard"].is_file() and paths["rhythm_input"].is_file():
        try:
            board = engine.read_json(paths["storyboard"])
            rhythm = engine.read_json(paths["rhythm_input"])
            shots = {row.get("shot_id"): row.get("scene_id") for row in board.get("shots", []) if isinstance(row, dict)}
            for scene in rhythm.get("scenes", []):
                if (isinstance(scene, dict) and scene.get("shots") and
                        all(isinstance(shot, dict) and shots.get(shot.get("shot_id")) == scene.get("scene_id")
                            and shot.get("timeline") for shot in scene["shots"])):
                    scenes.add(scene["scene_id"])
        except (OSError, ValueError, TypeError):
            pass  # Existence is retained below; malformed standard files never authorize overwrite.
    return existing, scenes


def describe_progress(root, episode, source_binding, scene_ids):
    root = Path(root).resolve()
    paths = _paths(root, episode)
    saved, stale = [], []
    for scene in scene_ids:
        path = _scene_path(root, episode, scene)
        if not path.is_file():
            continue
        try:
            draft = engine.read_json(path)
            valid = draft.get("scene_id") == scene and draft.get("episode_id") == episode and draft.get("source_script") == source_binding
        except (OSError, ValueError, TypeError):
            valid = False
        (saved if valid else stale).append(scene)
    standard, standard_scenes = _standard_progress(paths)
    has_standard = any(row["exists"] for row in standard)
    missing = [scene for scene in scene_ids if scene not in standard_scenes]
    next_scene = next((scene for scene in scene_ids if scene not in saved and scene not in standard_scenes), None)
    all_saved = len(saved) == len(scene_ids) and bool(scene_ids)
    action = ("resume_standard" if has_standard else "save_scene" if next_scene else "assemble")
    return {"draft_dir": str(paths["draft_dir"]), "saved_scene_ids": saved, "stale_scene_ids": stale,
            "next_scene_id": next_scene, "all_scenes_saved": all_saved,
            "standard_files": standard, "standard_scene_ids": [scene for scene in scene_ids if scene in standard_scenes],
            "standard_missing_scene_ids": missing, "ready_to_assemble": all_saved and not has_standard,
            "next_action": action, "scope": "scene candidates; no phase confirmation or episode duration publication"}


def _core_ids(draft):
    rhythm = draft["rhythm_input"]
    return {
        "shot": [shot["shot_id"] for scene in rhythm["scenes"] for shot in scene["shots"]],
        "event": [event["event_id"] for scene in rhythm["scenes"] for shot in scene["shots"] for event in shot["timeline"]],
        "utterance": [row["utterance_id"] for row in rhythm["utterances"]],
        "group": [row.get("group_id") if isinstance(row, dict) else None
                  for scene in rhythm["scenes"] for row in scene.get("beat_groups", [])],
    }


def _validate(root, episode, scene_id, payload):
    if not isinstance(payload, dict) or set(payload) - {"source_script", "storyboard", "rhythm_input", "markdown"}:
        raise DraftError("本场输入仅含 source_script/storyboard/rhythm_input/markdown")
    binding, scenes, _ = _source(root, episode, payload.get("source_script"))
    if payload.get("source_script") != binding:
        raise DraftError("本场输入缺 source_script 的当前源绑定")
    current = next((scene for scene in scenes if scene["scene_id"] == scene_id), None)
    if current is None:
        raise DraftError("场次不属于本集源合同")
    board, rhythm = copy.deepcopy(payload.get("storyboard")), copy.deepcopy(payload.get("rhythm_input"))
    text = payload.get("markdown")
    if not isinstance(board, dict) or not isinstance(rhythm, dict) or not isinstance(text, str):
        raise DraftError("storyboard/rhythm_input 必须为对象，markdown 必须为原始十五列表字符串")
    if board.get("episode_id", episode) != episode or rhythm.get("episode_id", episode) != episode or rhythm.get("source_script", binding) != binding:
        raise DraftError("不能跨集写入或替换源绑定")
    for field in ("source_markdown", "director_control_card"):
        if field in board:
            target = engine.project_file(root, board[field])
            if not target.is_relative_to(engine.project_file(root, f"episodes/{episode}/02_分镜")):
                raise DraftError(f"{field} 必须在本集分镜目录")
    if any(field in board for field in ("duration_s", "timing_input_sha256", "content_review")) or board.get("segments"):
        raise DraftError("局部候选不填全集派生时间、审校章或 SEG 执行设计")
    rhythm.update(episode_id=episode, source_script=binding)
    rs = rhythm.get("scenes")
    if not isinstance(rs, list) or len(rs) != 1 or not isinstance(rs[0], dict) or rs[0].get("scene_id") != scene_id:
        raise DraftError("每次只保存当前一个 scene")
    shape_issues = engine.validate_timeline_shape(rhythm)
    if shape_issues:
        raise DraftError(json.dumps(shape_issues, ensure_ascii=False))
    shots = board.get("shots")
    if not isinstance(shots, list) or not shots or any(not isinstance(shot, dict) or shot.get("scene_id") != scene_id for shot in shots):
        raise DraftError("storyboard.shots 必须非空且只属于当前场")
    if [shot.get("shot_id") for shot in shots] != [shot.get("shot_id") for shot in rs[0].get("shots", [])]:
        raise DraftError("分镜与时间输入的镜号集合/顺序必须一致")
    # Source truth is episode-wide: moving beats and continuing sound across scenes
    # are valid creative choices. Completeness is checked only after assembly.
    full_index, source_issues = engine.load_source(root, rhythm, board)
    issues = list(source_issues)
    for utterance in rhythm["utterances"]:
        line = full_index.get("line:" + utterance["line_id"])
        if not isinstance(line, dict) or utterance["speaker_ref"] != line.get("speaker_ref"):
            issues.append(engine.issue("source_line_uncovered", "发声必须引用真实源台词及其说话者"))
        engine.to_ms(utterance.get("estimated_duration_s"), positive=True)
        basis = utterance.get("timing_basis", {})
        if basis.get("method") == "existing_measurement" and "measurement:" + str(basis.get("file")) not in full_index:
            issues.append(engine.issue("speech_timing_basis_invalid", "测量必须引用项目内真实文件及字节 SHA"))
    for shot in rs[0]["shots"]:
        for event in shot["timeline"]:
            engine.to_ms(event.get("start_s"))
            engine.to_ms(event.get("duration_s"), positive=True)
            if event["kind"] == "speech":
                engine.to_ms(event.get("utterance_offset_s"))
            elif any(ref not in full_index for ref in event.get("source_refs", [])):
                issues.append(engine.issue("timeline_ref_unknown", "时间过程不能引用不存在的源事实"))
    coverage = board.get("beat_coverage")
    if not isinstance(coverage, list):
        issues.append(engine.issue("source_event_uncovered", "需要 beat_coverage 数组"))
    else:
        for row in coverage:
            if (not isinstance(row, dict) or "beat:" + str(row.get("beat_id")) not in full_index
                    or row.get("disposition") not in {"kept", "compressed", "moved"}
                    or not isinstance(row.get("target_shots"), list) or not row["target_shots"]
                    or any(not isinstance(target, str) or not target for target in row["target_shots"])):
                issues.append(engine.issue("source_event_uncovered", "事件处置需真实源 beat、合法处置和目标镜号"))
    if issues:
        raise DraftError(json.dumps(issues, ensure_ascii=False))
    rows = engine.reading_rows(text)
    if [row[0] for row in rows] != [shot["shot_id"] for shot in shots] or any(scene_id not in row[1][0] for row in rows):
        raise DraftError("markdown 必须含当前场全部镜头的十五列表，镜号与顺序一致")
    draft = {"episode_id": episode, "scene_id": scene_id, "source_script": binding,
             "storyboard": board, "rhythm_input": rhythm, "markdown": text}
    ids = _core_ids(draft)
    if any(not all(isinstance(value, str) and value for value in values) or len(set(values)) != len(values) for values in ids.values()):
        raise DraftError("镜头/过程/发声/分组 ID 必须非空且在本场唯一")
    return draft, scenes


def save_scene(root, episode, scene_id, payload):
    root = Path(root).resolve()
    path = _scene_path(root, episode, scene_id)
    draft, scenes = _validate(root, episode, scene_id, payload)
    own_ids = _core_ids(draft)
    for scene in scenes:
        other_path = _scene_path(root, episode, scene["scene_id"])
        if other_path == path or not other_path.is_file():
            continue
        other = engine.read_json(other_path)
        if other.get("source_script") != draft["source_script"]:
            continue
        for kind, values in _core_ids(other).items():
            if set(values) & set(own_ids[kind]):
                if kind == "utterance":
                    own = {row["utterance_id"]: row for row in draft["rhythm_input"]["utterances"]}
                    if all(own[value] == row for row in other["rhythm_input"]["utterances"]
                           if (value := row["utterance_id"]) in own):
                        continue  # One utterance may have fragments in multiple scenes.
                raise DraftError(f"{kind} ID 与已保存场次重复，不能跨场覆盖")
    engine.atomic_write_many([(path, engine.json_text(draft))])
    progress = describe_progress(root, episode, draft["source_script"], [scene["scene_id"] for scene in scenes])
    return {"ok": True, "saved": str(path), "scene_id": scene_id,
            "shot_count": len(draft["storyboard"]["shots"]),
            "pending_global_reconciliation": True, "progress": progress}


def _merge(left, right, location="storyboard"):
    if left == right:
        return copy.deepcopy(left)
    if isinstance(left, dict) and isinstance(right, dict):
        result = copy.deepcopy(left)
        for key, value in right.items():
            result[key] = _merge(result[key], value, location + "." + key) if key in result else copy.deepcopy(value)
        return result
    if isinstance(left, list) and isinstance(right, list):
        return copy.deepcopy(left + [row for row in right if row not in left])
    raise DraftError(f"场次创意字段存在冲突：{location}；按真实设计修复后再合并")


def _inherit_sources(root, board, binding):
    """Project exact source values; creative bindings remain author supplied."""
    def inherit(target, key, value, location):
        if key in target and target[key] != value:
            raise DraftError(f"{location}.{key} 与当前真实源冲突，不能静默替换")
        target[key] = copy.deepcopy(value)

    board.setdefault("revision", 1)
    card_path = engine.project_file(root, "00_制作控制/project_data_card.json")
    if card_path.is_file():
        card = engine.read_json(card_path)
        if "revision" in card:
            inherit(board, "project_data_card_revision", card["revision"], "storyboard")
    contract = engine.read_json(engine.project_file(root, binding["file"]))
    source_beats = {event["event_id"]: (scene["scene_id"], event)
                    for scene in contract.get("scenes", []) for event in scene.get("events", [])}
    for beat in board.get("beat_coverage", []):
        source = source_beats.get(beat.get("beat_id"))
        if source:
            beat.setdefault("scene", source[0])
            if "summary" in source[1]:
                beat.setdefault("summary", copy.deepcopy(source[1]["summary"]))
    if isinstance(contract.get("inherited_world_facts"), list):
        inherit(board, "inherited_world_facts", contract["inherited_world_facts"], "storyboard")
    plan_path = engine.project_file(root, "00_制作控制/drama_plan.json")
    if not plan_path.is_file():
        return board
    plan = engine.read_json(plan_path)
    audience = plan.get("audience_plan")
    if not isinstance(audience, dict):
        return board
    execution = board.setdefault("audience_execution", {})
    if not isinstance(execution, dict):
        raise DraftError("audience_execution 必须为对象")
    if "revision" in plan:
        inherit(execution, "source_plan_revision", plan["revision"], "audience_execution")
    for field in ("viewing_focus", "emotional_payoff", "platform_viewing_context", "expression_boundaries"):
        if field not in audience:
            continue
        entry = execution.setdefault(field, {})
        if not isinstance(entry, dict):
            raise DraftError(f"audience_execution.{field} 必须为对象")
        inherit(entry, "source_field", f"audience_plan.{field}", "audience_execution." + field)
        inherit(entry, "contract", audience[field], "audience_execution." + field)
    return board


def assemble(root, episode):
    root = Path(root).resolve()
    paths = _paths(root, episode)
    binding, scenes, _ = _source(root, episode)
    progress = describe_progress(root, episode, binding, [scene["scene_id"] for scene in scenes])
    if not progress["all_scenes_saved"]:
        raise DraftError("本集仍有未保存或源版本过期的场次，不能合并或发布全集时长")
    if any(row["exists"] for row in progress["standard_files"]):
        raise DraftError("标准候选文件已存在；不静默覆盖，请先明确处理现有候选")
    board, rhythm, markdown = {}, {"episode_id": episode, "source_script": binding, "utterances": [], "scenes": []}, []
    for scene in scenes:
        saved = engine.read_json(_scene_path(root, episode, scene["scene_id"]))
        payload = {key: saved[key] for key in ("source_script", "storyboard", "rhythm_input", "markdown")}
        draft, _ = _validate(root, episode, scene["scene_id"], payload)
        board = _merge(board, draft["storyboard"])
        annotations = {key: value for key, value in draft["rhythm_input"].items() if key in engine.ANNOTATIONS}
        rhythm = _merge(rhythm, annotations, "rhythm_input")
        rhythm["utterances"] = _merge(rhythm["utterances"], draft["rhythm_input"]["utterances"], "utterances")
        rhythm["scenes"].extend(draft["rhythm_input"]["scenes"])
        markdown.append(draft["markdown"])
    board = _inherit_sources(root, board, binding)
    index, issues = engine.load_source(root, rhythm, board)
    result = engine.reconcile_timeline(rhythm, index)
    issues += result["issues"]
    if result["ok"]:
        issues += engine.validate_coverage(board, rhythm, index)
    groups = [group for scene in rhythm["scenes"] for group in scene.get("beat_groups", [])]
    group_ids = [group.get("group_id") for group in groups]
    if len(set(group_ids)) != len(group_ids):
        raise DraftError("跨场分组 ID 重复")
    if issues:
        raise DraftError(json.dumps(issues, ensure_ascii=False))
    canonical_markdown = str(paths["markdown"].relative_to(root)).replace("\\", "/")
    if board.get("source_markdown", canonical_markdown) != canonical_markdown:
        raise DraftError("source_markdown 必须指向本集标准分镜表，不能另写或覆盖其他文件")
    board.update(episode_id=episode, source_markdown=canonical_markdown)
    board.setdefault("segments", [])
    director = board.get("director_control_card", f"episodes/{episode}/02_分镜/导演总控卡_{episode}.md")
    if not engine.project_file(root, director).is_file():
        raise DraftError("缺实际导演卡；在本场 storyboard.director_control_card 指向已有文件")
    board["director_control_card"] = director
    entries = [(paths["storyboard"], engine.json_text(board)), (paths["rhythm_input"], engine.json_text(rhythm)),
               (paths["markdown"], "\n\n".join(markdown))]
    reserved = []
    try:
        for path, _ in entries:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8"):
                pass
            reserved.append(path)
        engine.atomic_write_many(entries)
    except (OSError, ValueError):
        for path in reserved:
            if path.is_file() and path.stat().st_size == 0:
                path.unlink()
        raise
    return {"ok": True, "assembled": [str(path) for path, _ in entries], "scene_count": len(scenes),
            "next_action": "allocate_then_pack_then_complete_execution_design_and_content_review",
            "scope": "complete authoring inputs only; no phase confirmation, review stamp or episode duration publication"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("save", "status", "assemble"):
        item = sub.add_parser(name)
        item.add_argument("--project-root", required=True)
        item.add_argument("--episode", required=True)
        if name == "save":
            item.add_argument("--scene", required=True)
            item.add_argument("--input", required=True, help="项目内本场 JSON；支持绝对路径、当前目录或项目相对路径，歧义时须用绝对路径")
    args = parser.parse_args(argv)
    try:
        if args.command == "save":
            # Accept both shell-relative and project-relative paths. Never guess
            # between two existing files or read a file outside the project.
            root = Path(args.project_root).resolve()
            supplied = Path(args.input)
            candidates = {supplied.resolve(), (root / supplied).resolve()}
            candidates = {path for path in candidates if path.is_relative_to(root) and path.is_file()}
            if not candidates:
                raise DraftError("找不到项目内输入文件；请提供本场 JSON 的绝对路径")
            if len(candidates) != 1:
                raise DraftError("输入相对路径有歧义：当前目录与项目目录均有同名文件，请使用绝对路径")
            path = candidates.pop()
            result = save_scene(root, args.episode, args.scene, engine.read_json(path))
        elif args.command == "assemble":
            result = assemble(args.project_root, args.episode)
        else:
            binding, scenes, _ = _source(args.project_root, args.episode)
            result = describe_progress(args.project_root, args.episode, binding, [scene["scene_id"] for scene in scenes])
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
