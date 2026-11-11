#!/usr/bin/env python3
"""从已确认上游派生单段执行登记与两表确认材料；不创作叙事、不调用模型。"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re
import sys

import drama_lint as lint
from h3_contract import CAPABILITIES, load_capabilities, prepare_request
from rhythm_engine import atomic_write_many, canonical_sha, file_sha, json_text, project_file, read_json, to_ms
from video_confirmations import authorization_binding, request_segment_snapshot


class PreparationError(ValueError):
    pass


def _json(root, rel, required=True):
    path = project_file(root, rel)
    if not path.is_file():
        if required:
            raise PreparationError(f"缺上游文件：{rel}")
        return {}
    return read_json(path)


def _relative(root, value):
    path = Path(value)
    if path.is_absolute():
        path = path.resolve().relative_to(root)
    return project_file(root, path.as_posix()).relative_to(root).as_posix()


def _rows(text, ids):
    """只投影已有表格，保留表头；不重新写画面、动作或摄影描述。"""
    selected, header = [], []
    patterns = [re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(value) + r"(?![A-Za-z0-9_-])") for value in ids]
    previous = ""
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            if re.match(r"^\s*\|\s*:?-{3,}", line):
                header = [previous, line]
            elif any(pattern.search(line) for pattern in patterns):
                if header and not selected:
                    selected.extend(header)
                selected.append(line)
        previous = line
    return selected


def _excerpt(text, ids):
    rows = _rows(text, ids)
    if rows:
        return "\n".join(rows)
    # Heading-delimited segment notes are also supported, copied verbatim.
    lines, result = text.splitlines(), []
    active_level = None
    for line in lines:
        heading = re.match(r"^(#{1,6})\s+(.+)", line)
        if heading:
            if active_level is not None and len(heading[1]) <= active_level:
                active_level = None
            if any(re.search(r"(?<![\w-])" + re.escape(value) + r"(?![\w-])", heading[2]) for value in ids):
                active_level = len(heading[1])
        if active_level is not None:
            result.append(line)
    return "\n".join(result)


def _director_globals(text):
    """保留全部全局导演原文；逐段执行区由当前段摘录提供。"""
    result, excluded_level, global_section = [], None, False
    for line in text.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+)", line)
        if heading:
            level, title = len(heading[1]), heading[2]
            if excluded_level is not None and level <= excluded_level:
                excluded_level = None
            if "逐段" in title or re.search(r"\bSEG\d+\b", title):
                excluded_level = level if excluded_level is None else min(level, excluded_level)
            elif excluded_level is None:
                global_section = level >= 2
        if excluded_level is None and (global_section or not re.search(r"\bSEG\d+\b", line)):
            result.append(line)
    return "\n".join(result).strip()


def _source_token(value):
    match = re.match(r"[A-Za-z]+\d+(?:(?::|_)[A-Za-z0-9_-]+)*", str(value).strip())
    return match[0] if match else str(value).strip()


def _assets(root, usage):
    index, records = lint.blank_asset_index(), {}
    registry = _json(root, "shared/03_资产/asset_registry.json")
    available = registry.get("assets", []) + usage.get("episode_assets", []) + usage.get("reused_episode_assets", [])
    for asset in available:
        aid, version = asset.get("asset_id"), str(asset.get("version") or "")
        if not aid:
            continue
        lint.remember_asset_version(index, aid, version, asset.get("status"))
        refs = {lint.asset_version_key(aid, version), lint.asset_version_key(aid, version, ":")}
        if asset.get("state_id"):
            lint.remember_state_version(index, aid, asset["state_id"], version, asset.get("status"))
            refs = lint.state_ref_keys(aid, asset["state_id"], version)
        if asset.get("category") == "voice" and asset.get("status") == "approved":
            index["approved_voice_ids"].add(aid)
        for ref in refs:
            records[ref] = asset
    return index, records


def load_segment_context(root, episode, segment_id):
    root = Path(root).resolve()
    if not re.fullmatch(r"ep_[1-9]\d*", episode) or not re.fullmatch(r"SEG\d+", segment_id):
        raise PreparationError("episode/segment ID 格式无效")
    base = f"episodes/{episode}"
    files = {
        "storyboard": f"{base}/02_分镜/storyboard_{episode}.json",
        "script": f"{base}/01_剧本/script_contract_{episode}.json",
        "asset_usage": f"{base}/03_资产/asset_usage_{episode}.json",
        "keyframes": f"{base}/03_资产/keyframe_manifest_{episode}.json",
        "data_card": "00_制作控制/project_data_card.json",
        "plan": "00_制作控制/drama_plan.json",
    }
    data = {key: _json(root, rel) for key, rel in files.items()}
    state = _json(root, "00_制作控制/制作状态.json")
    if state.get("current_episode") and state["current_episode"] != episode:
        raise PreparationError(f"当前制作集为 {state['current_episode']}，不能准备 {episode}")
    stages = (state.get("episodes", {}).get(episode) or {}).get("stage_status", {})
    for stage in ("script", "assets", "storyboard", "keyframes"):
        if stages.get(stage, state.get("phases", {}).get(stage)) != "confirmed":
            raise PreparationError(f"{episode} 上游 {stage} 尚未 confirmed")
    storyboard = data["storyboard"]
    matches = [(i, seg) for i, seg in enumerate(storyboard.get("segments", []), 1) if seg.get("segment_id") == segment_id]
    if len(matches) != 1:
        raise PreparationError(f"分镜中找不到唯一 {segment_id}")
    position, segment = matches[0]
    shots = {shot["shot_id"]: shot for shot in storyboard.get("shots", [])}
    selected_shots = [shots[sid] for sid in segment["shot_ids"]]
    markdown = storyboard.get("source_markdown")
    director = storyboard.get("director_control_card")
    if not markdown or not director:
        raise PreparationError("分镜缺 source_markdown/director_control_card")
    rows = _rows(project_file(root, markdown).read_text(encoding="utf-8-sig"), segment["shot_ids"])
    if len(rows) - 2 != len(selected_shots):
        raise PreparationError("当前段十五列分镜行缺失或重复")
    director_source = project_file(root, director).read_text(encoding="utf-8-sig")
    director_text = _excerpt(director_source, [segment_id])
    if not director_text:
        raise PreparationError(f"导演卡缺 {segment_id} 执行区")
    all_lines = {line["line_id"]: line for scene in data["script"].get("scenes", []) for line in scene.get("speech_lines", [])}
    line_ids = re.findall(r"\bLINE\d+\b", "\n".join(rows))
    speech_events = [event for shot in selected_shots for event in shot.get("timing_events", []) if event.get("kind") == "speech"]
    timing_rel = f"{base}/02_分镜/rhythm_input_{episode}.json"
    if speech_events:
        timing = _json(root, timing_rel)
        utterances = {row["utterance_id"]: row for row in timing.get("utterances", [])}
        for event in speech_events:
            lid = event.get("line_id") or utterances.get(event.get("utterance_id"), {}).get("line_id")
            if not lid or lid not in all_lines:
                raise PreparationError(f"无法从已确认剧本解析台词：{event.get('event_id')}")
            line_ids.append(lid)
    line_ids = list(dict.fromkeys(line_ids))
    if any(lid not in all_lines for lid in line_ids):
        raise PreparationError("分镜引用了剧本中不存在的 LINE")
    relevant_voices = {all_lines[lid].get("voice_id") for lid in line_ids}
    keys = {"source_lock", "language_contract", "style_contract", "explicit_overrides", "model_plan", "scale_plan", "delivery_settings"}
    locked = {key: data["plan"][key] for key in keys if key in data["plan"]}
    if "source_lock" in locked:
        locked["source_lock"] = {key: value for key, value in locked["source_lock"].items() if key in {"user_requirements", "must_include", "must_avoid"}}
    if "scale_plan" in locked:
        locked["scale_plan"] = {key: value for key, value in locked["scale_plan"].items() if key in {"aspect_ratio", "resolution", "resolution_plan"}}
    if "model_plan" in locked:
        locked["model_plan"] = {"video": locked["model_plan"].get("video", {})}
    source_files = [{"file": rel, "revision": data[key].get("revision")} for key, rel in files.items()]
    source_files.extend({"file": rel, "sha256": file_sha(project_file(root, rel))} for rel in (markdown, director))
    context = {
        "episode_id": episode, "segment_id": segment_id, "episode_segment_index": position,
        "source_files": source_files, "segment": segment, "shots": selected_shots,
        "storyboard_rows": rows, "director_segment": director_text,
        "director_global_contracts": _director_globals(director_source),
        "director_control_card": director, "source_markdown": markdown,
        "speech_lines": [all_lines[lid] for lid in line_ids],
        "voices": [voice for voice in data["data_card"].get("voices", []) if voice.get("voice_id") in relevant_voices],
        "locked_settings": locked, "global_settings": data["data_card"].get("global_settings", {}),
        "project_data_card_revision": data["data_card"].get("revision"),
        "incoming_seam": next((seam for seam in storyboard.get("seams", []) if seam.get("to_segment") == segment_id), None),
        "asset_usage_plan": [row for row in storyboard.get("asset_usage_plan", []) if "*" in row.get("segments", []) or segment_id in row.get("segments", [])],
        "keyframes": [row for row in data["keyframes"].get("keyframes", []) if row.get("segment_id") == segment_id and row.get("status") == "approved"],
    }
    _, assets = _assets(root, data["asset_usage"])
    planned_ids = {row.get("asset_id") for row in context["asset_usage_plan"]}
    planned_ids.update(_source_token(row.get("planned_source", "")).split(":")[0].split("_")[0] for row in segment.get("reference_input_plan", []))
    media_fields = {"asset_id", "category", "state_id", "version", "status", "file", "files", "duration_s"}
    context["available_media"] = [dict({key: value for key, value in asset.items() if key in media_fields}, source_refs=sorted(ref for ref, value in assets.items() if value is asset)) for asset in {id(value): value for value in assets.values() if value.get("asset_id") in planned_ids | relevant_voices}.values()]
    manifest = _json(root, f"{base}/04_视频片段/video_manifest_{episode}.json", False)
    result_fields = ("segment_id", "output_file", "status", "generation_confirmation_id")
    positions = {row["segment_id"]: index for index, row in enumerate(storyboard["segments"], 1)}
    results = [{key: row[key] for key in result_fields if key in row} for row in manifest.get("segments", [])
               if row.get("segment_id") in positions and row.get("output_file")]
    context["earlier_results"] = [row for row in results if positions[row["segment_id"]] < position]
    context["current_result"] = next((row for row in results if row["segment_id"] == segment_id), None)
    context["video_source_results"] = []
    for row in manifest.get("segments", []):
        if row.get("segment_id") not in positions or positions[row["segment_id"]] > position:
            continue
        for version in [row, *row.get("previous_results", [])]:
            if version.get("output_file"):
                context["video_source_results"].append(dict(
                    {key: version[key] for key in result_fields if key in version}, segment_id=row["segment_id"]))
    if position > 1:
        previous_id = storyboard["segments"][position - 2]["segment_id"]
        context["previous_result"] = next((row for row in context["earlier_results"] if row.get("segment_id") == previous_id), None)
    return context


def _fail_issues(issues):
    errors = [row for row in issues if row.get("level", "error") == "error"]
    if errors:
        raise PreparationError("; ".join(f"{row.get('code')}: {row.get('message')}" for row in errors))


def _lock_request(context, request):
    segment, locked = context["segment"], context["locked_settings"]
    fixed = {"duration_s": segment["request_duration_s"], "content_duration_s": segment["duration_s"], "tail_handle_s": segment.get("tail_handle_s", 0)}
    aspect = locked.get("scale_plan", {}).get("aspect_ratio") or context["global_settings"].get("ratio")
    if aspect:
        fixed["aspect"] = aspect
    profile = read_json(CAPABILITIES)
    planned_model = locked.get("model_plan", {}).get("video", {}).get("model")
    if planned_model and planned_model.strip().lower() not in {profile["model"].lower(), "minimax h3"}:
        raise PreparationError("已锁定模型与本 H3 工具不一致")
    fixed["model"] = profile["model"]
    scale = locked.get("scale_plan", {})
    resolution = scale.get("resolution") or scale.get("resolution_plan")
    resolutions = [value for value in profile["capabilities"]["resolutions"] if value in str(resolution or "")]
    if len(resolutions) == 1:
        fixed["resolution"] = resolutions[0]
    for key, expected in fixed.items():
        actual = request.get(key, expected)
        if key == "model" and str(actual).lower() == "minimax h3":
            actual = profile["model"]
        if actual != expected:
            raise PreparationError(f"请求 {key}={actual!r} 与已确认上游 {expected!r} 不一致")
        request[key] = expected
    return request


def _input_records(root, context, request, manifest_file):
    usage = _json(root, f"episodes/{context['episode_id']}/03_资产/asset_usage_{context['episode_id']}.json")
    asset_index, assets = _assets(root, usage)
    plans = context["segment"].get("reference_input_plan", [])
    keyframes = {row["keyframe_id"]: row for row in context["keyframes"]}
    records = {"image": [], "video": [], "audio": []}
    state_refs, issues, passed, basis = [], [], set(), []
    for item in request.get("inputs", []):
        ref, role, kind, location = (item.get(key) for key in ("source_ref", "role", "kind", "path"))
        if not ref or not role or kind not in records:
            raise PreparationError("每个真实输入必须给 kind/path/source_ref/role")
        plan = next((p for p in plans if p.get("role") == role and _source_token(p.get("planned_source")) == ref), None)
        asset, keyframe = assets.get(ref), keyframes.get(ref)
        if asset:
            checker = lint.check_state_ref if ref in asset_index["known_state_refs"] else lint.check_asset_ref
            checker(ref, asset_index, manifest_file, issues, context["segment_id"])
            files = asset.get("files") or [asset.get("file")]
            if location not in files:
                raise PreparationError(f"{ref} 的输入路径不是该 approved 资产登记文件")
        elif keyframe:
            if location != keyframe.get("file"):
                raise PreparationError(f"{ref} 的输入路径不是 approved KF")
        elif kind == "video" and role in {"previous_segment_video_reference", "source_video_for_edit"}:
            candidates = context["video_source_results"]
            source = next((row for row in candidates if row["segment_id"] == ref and row["output_file"] == location
                           and (role == "source_video_for_edit" or ref != context["segment_id"])), None)
            allowed_statuses = {"accepted"} if role == "previous_segment_video_reference" else {"candidate", "accepted", "rejected"}
            if not source or source.get("status") not in allowed_statuses:
                raise PreparationError(f"{ref} 缺可用的同集既有视频；前段参考需 accepted，编辑源需真实候选/验收/返修结果")
            if not project_file(root, location).is_file():
                raise PreparationError(f"{ref} 的输入路径不是已登记真实视频")
        elif kind == "image" and role in {"previous_tail_as_start_frame", "previous_scene_anchor_reference", "previous_character_state_reference", "previous_prop_state_reference"}:
            if not str(ref).startswith("FRM") or not context.get("earlier_results"):
                raise PreparationError("承接帧缺真实既有片段及 FRM source_ref")
            if role == "previous_tail_as_start_frame" and not context.get("previous_result"):
                raise PreparationError("承接尾帧缺上一段真实结果")
            if plan is None:
                plan = next((p for p in plans if p.get("role") == role), None)
        else:
            raise PreparationError(f"输入 source_ref 未解析到已批准资产/KF/既有视频/真实承接帧：{ref}")
        record = {"order": len(records[kind]) + 1, "role": role, "file": location,
                  "adopt": plan.get("adopt") if plan else role,
                  "exclude": plan.get("exclude") if plan else "仅采用已登记职责；不复制参考素材中的非采用内容"}
        if kind == "image":
            record.update(source_id=ref, source_type="asset" if asset else "keyframe" if keyframe else "frame")
            basis.append({"keyframe_id" if keyframe else "asset_id": ref, "role": role, "passed_to_tool": True})
            if ref in asset_index["known_state_refs"]:
                state_refs.append(ref)
        else:
            record["resource_id"] = ref
            if "duration_s" in item:
                record["duration_s"] = item["duration_s"]
        records[kind].append(record)
        passed.add((ref, role))
    for plan in plans:
        if plan.get("required", True) is False or plan.get("optional") is True:
            continue
        ref, role = _source_token(plan.get("planned_source")), plan.get("role")
        if role == "previous_tail_as_start_frame":
            if not any(row[1] == role for row in passed):
                raise PreparationError("缺必需输入：previous_tail_as_start_frame")
        elif (ref, role) not in passed:
            raise PreparationError(f"缺必需输入：{ref} ({role})")
    for planned in context["asset_usage_plan"]:
        aid = planned.get("asset_id")
        if aid and not any(_source_token(ref).split(":")[0].split("_")[0] == aid for ref, _ in passed):
            raise PreparationError(f"缺当前段资产计划中的真实输入：{aid}")
    for keyframe_id in keyframes:
        if not any(ref == keyframe_id for ref, _ in passed):
            raise PreparationError(f"缺当前段已规划高光 KF：{keyframe_id}")
    if any(row["role"] == "source_video_for_edit" for row in records["video"]) and len(records["video"]) != 1:
        raise PreparationError("视频编辑必须且只能传入一个 source_video_for_edit 源视频")
    required = set(context["segment"].get("required_reference_roles", []))
    required.update(row["role"] for row in records["image"])
    for kind, allowed in (("image", lint.REFERENCE_ROLES), ("video", lint.VIDEO_INPUT_ROLES), ("audio", lint.AUDIO_INPUT_ROLES)):
        lint.ordered_inputs(root, records[kind], allowed, "reference" if kind == "image" else kind, manifest_file, issues)
    _fail_issues(issues)
    return records, sorted(required), state_refs, basis, asset_index


def _cell(value):
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _render_evidence(table, rows, durations):
    labels = {"task_type": "任务类型", "delivery_format": "交付形态", "quantity": "数量", "total_duration": "总时长", "aspect_ratio_and_resolution": "画幅与分辨率", "model": "模型", "visual_and_continuity": "画面与连续性", "audio_and_subtitles": "声音与字幕", "reference_materials": "参考素材"}
    text = "| 参数 | 本批次确认值 |\n|---|---|\n" + "\n".join(f"| {labels[key]} | {value} |" for key, value in table.items())
    text += "\n| 分段时长 | " + "；".join(f"{sid}：{duration}秒" for sid, duration in durations) + " |\n\n"
    text += "| SEG 与时长 | 画面内容 | 画面过程 | 声音与台词 | 摄影过程与素材 |\n|---|---|---|---|---|\n"
    text += "\n".join("| " + " | ".join(str(value) for value in (
        f"{row['segment_id']} {row['duration_s']}秒", row["visual_content"], row["subject_action"],
        row["audio"], row["camera_and_materials"])) + " |" for row in rows)
    return {"displayed_parameter_table": table, "displayed_storyboard_rows": rows, "final_parameters_text": text}


def build_evidence(context, segment):
    rows = [line for line in context["storyboard_rows"] if line.startswith("|")][2:]
    columns = [[cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))] for line in rows]
    if any(len(row) < 15 for row in columns):
        raise PreparationError("十五列分镜格式不完整，无法投影确认表")
    preview = {
        "segment_id": segment["segment_id"], "duration_s": segment["duration_s"],
        "visual_content": "；".join(row[5] for row in columns),
        "subject_action": "；".join(event.get("process", "") for shot in context["shots"] for event in shot.get("timing_events", []) if event.get("kind") == "visual") or "；".join(row[5] for row in columns),
        "audio": "；".join(row[9] + "／" + row[10] for row in columns),
        "camera_and_materials": "；".join(row[11] + "／" + row[12] + "／" + row[13] for row in columns),
    }
    dialogue = "；".join(f"{line['type']} {line['source_text']}" for line in segment["speech_lines"])
    if dialogue:
        preview["audio"] += "；" + dialogue
    media = "；".join(f"{row['role']}: {row['file']}" for key in ("reference_inputs", "video_inputs", "audio_inputs") for row in segment[key]) or "无外部媒体输入"
    preview["camera_and_materials"] += "；" + media
    snapshot = segment["request_snapshot"]
    table = {
        "task_type": "视频生成", "delivery_format": "视频片段", "quantity": 1,
        "total_duration": f"{segment['duration_s']}秒",
        "aspect_ratio_and_resolution": f"{snapshot.get('aspect')} / {snapshot.get('resolution')}",
        "model": snapshot["model"], "visual_and_continuity": context["director_segment"],
        "audio_and_subtitles": (dialogue or "无计划人声") + f"；字幕：{segment['subtitle_enabled']}",
        "reference_materials": media,
    }
    # The evidence is rendered from the same values, including Markdown-safe escaping.
    table = {key: _cell(value) if isinstance(value, str) else value for key, value in table.items()}
    preview = {key: _cell(value) if isinstance(value, str) else value for key, value in preview.items()}
    return _render_evidence(table, [preview], [(segment["segment_id"], segment["duration_s"])])


def combine_evidence(root, episode, segment_ids, check_only=False):
    """合并已准备且互不依赖的连续片段，避免模型抄写两表与授权指纹。"""
    root = Path(root).resolve()
    if not 1 <= len(segment_ids) <= 2 or len(set(segment_ids)) != len(segment_ids):
        raise PreparationError("合批仅接受 1–2 个不同且连续的 SEG")
    base = f"episodes/{episode}/04_视频片段"
    manifest = _json(root, f"{base}/video_manifest_{episode}.json")
    segments, evidences = [], []
    for sid in segment_ids:
        load_segment_context(root, episode, sid)
        matches = [row for row in manifest["segments"] if row.get("segment_id") == sid]
        if len(matches) != 1:
            raise PreparationError(f"合批缺唯一已准备段：{sid}")
        segment = matches[0]
        evidence = _json(root, f"{base}/生成确认_{sid}.json")
        if (evidence.get("request_snapshot_sha256") != canonical_sha({"segments": [request_segment_snapshot(segment)]})
                or evidence.get("authorization_bindings") != [authorization_binding(root, segment)]):
            raise PreparationError(f"{sid} 准备后请求、Prompt 或素材已变，请重新准备")
        prepared = prepare_request(snapshot=segment["request_snapshot"], root=root, prompt_file=segment["h3_prompt_file"])
        if prepared.snapshot != segment["request_snapshot"]:
            raise PreparationError(f"{sid} 缺实际冻结请求，请重新准备")
        seam = segment.get("incoming_seam") or {}
        if seam.get("seam_mode") == "continuous" and seam.get("from_segment") in segment_ids:
            raise PreparationError("continuous 后段须等待前段本次真实结果，不能合批授权")
        segments.append(segment)
        evidences.append(evidence)
    indexes = [row["episode_segment_index"] for row in segments]
    if indexes != list(range(indexes[0], indexes[0] + len(indexes))):
        raise PreparationError("合批 SEG 必须按本集顺序连续")
    table = {}
    for key in evidences[0]["displayed_parameter_table"]:
        values = [row["displayed_parameter_table"][key] for row in evidences]
        table[key] = values[0] if all(value == values[0] for value in values) else "；".join(
            f"{sid}：{value}" for sid, value in zip(segment_ids, values))
    table["quantity"] = len(segments)
    table["total_duration"] = f"{sum(to_ms(row['duration_s'], positive=True) for row in segments) / 1000:g}秒"
    rows = [row for evidence in evidences for row in evidence["displayed_storyboard_rows"]]
    evidence = _render_evidence(table, rows, [(row["segment_id"], row["duration_s"]) for row in segments])
    evidence["request_snapshot_sha256"] = canonical_sha({"segments": [request_segment_snapshot(row) for row in segments]})
    evidence["authorization_bindings"] = [authorization_binding(root, row) for row in segments]
    evidence_rel = f"{base}/生成确认_{'_'.join(segment_ids)}_batch.json"
    if not check_only:
        atomic_write_many([(project_file(root, evidence_rel), json_text(evidence))])
    return {"written": not check_only, "evidence_file": evidence_rel, "final_parameters_text": evidence["final_parameters_text"]}


def prepare_segment(root, episode, segment_id, request_file, prompt_file, package_file=None, check_only=False, replace_generated=False):
    root = Path(root).resolve()
    context = load_segment_context(root, episode, segment_id)
    prompt_rel, request_rel = _relative(root, prompt_file), _relative(root, request_file)
    request = _lock_request(context, read_json(project_file(root, request_rel)))
    prepared = prepare_request(snapshot=request, root=root, prompt_file=prompt_rel)
    manifest_rel = f"episodes/{episode}/04_视频片段/video_manifest_{episode}.json"
    manifest_path = project_file(root, manifest_rel)
    manifest = _json(root, manifest_rel, False) or {"episode_id": episode, "revision": 1, "segments": []}
    records, required, state_refs, basis, asset_index = _input_records(root, context, prepared.snapshot, manifest_path)
    source = context["segment"]
    segment = {
        "segment_id": segment_id, "episode_segment_index": context["episode_segment_index"],
        "shot_ids": source["shot_ids"], "planned_shot_count": len(source["shot_ids"]),
        "shot_plan": copy.deepcopy(context["shots"]),
        "tool_mode": "video_edit" if any(row["role"] == "source_video_for_edit" for row in records["video"]) else "text_to_video" if prepared.snapshot["mode"] == "T2VA" else "image_to_video" if prepared.snapshot["mode"] in {"I2VA", "FL2VA", "L2VA"} else "media_to_video",
        "h3_mode": prepared.snapshot["mode"], "duration_s": source["request_duration_s"],
        "content_duration_s": source["duration_s"], "tail_handle_s": source.get("tail_handle_s", 0),
        "request_snapshot": prepared.snapshot, "h3_prompt_file": prompt_rel,
        "h3_prompt_sha256": file_sha(project_file(root, prompt_rel)),
        "compiled_prompt_file": _relative(root, package_file) if package_file else context["director_control_card"],
        "reference_inputs": records["image"], "video_inputs": records["video"], "audio_inputs": records["audio"],
        "reference_basis": basis, "state_refs": state_refs, "required_reference_roles": required,
        "audio_input_supported": bool(records["audio"]), "native_audio_supported": True,
        "speech_lines": context["speech_lines"], "speech_mode": "native_required" if context["speech_lines"] else "no_human_voice",
        "voice_inputs": [{"voice_id": (lint.split_asset_version_ref(ref) or (ref, ""))[0], "resource_id": ref} for ref in [row["resource_id"] for row in records["audio"] if row["role"] == "voice_audio_reference"]],
        "subtitle_enabled": context["locked_settings"].get("delivery_settings", {}).get("subtitle_enabled", False),
        "video_generation_subtitles": False, "incoming_seam": context["incoming_seam"] or {"seam_id": "START", "seam_mode": "START"},
        "incoming_episode_seam": None,
    }
    segment["subtitle_render_stage"] = "final_ffmpeg_burn" if segment["subtitle_enabled"] else "disabled"
    if context["episode_segment_index"] == 1 and episode != "ep_1":
        seams = _json(root, "00_制作控制/episode_seams.json")
        segment["incoming_episode_seam"] = next((row for row in seams.get("seams", []) if row.get("to_episode") == episode), None)
        if not segment["incoming_episode_seam"]:
            raise PreparationError("缺当前集入站 EPSEAM")
    if context["incoming_seam"] and context["incoming_seam"].get("seam_mode") == "continuous" and not any(row["role"] == "previous_tail_as_start_frame" for row in records["image"]):
        raise PreparationError("continuous 下段缺真实上一段尾帧输入")
    issues = []
    lint.check_voice_audio_inputs(segment, {row["role"] for row in records["audio"]}, manifest_path, issues, asset_index["approved_voice_ids"], {mode for mode, cap in load_capabilities()[0]["mode_ref_limits"].items() if cap.get("audios_max", 0)})
    lint.check_voice_anchor_resolution(segment, {row["voice_id"]: row.get("voice_anchor", "") for row in context["voices"]}, manifest_path, issues)
    lint.check_prompt_markers(project_file(root, prompt_rel), list(range(1, len(records["image"]) + 1)), list(range(1, len(records["video"]) + 1)), list(range(1, len(records["audio"]) + 1)), segment["speech_lines"], segment["subtitle_enabled"], issues, segment["h3_mode"])
    _fail_issues(issues)
    if not project_file(root, segment["compiled_prompt_file"]).is_file():
        raise PreparationError("导演卡/可选交付包文件不存在")
    existing = next((row for row in manifest["segments"] if row.get("segment_id") == segment_id), None)
    if existing:
        if "previous_results" in existing:
            segment["previous_results"] = copy.deepcopy(existing["previous_results"])
    if existing and (existing.get("output_file") or existing.get("status") in {"candidate", "accepted"}):
        unchanged = all(existing.get(key) == segment[key] for key in ("request_snapshot", "h3_prompt_file", "h3_prompt_sha256"))
        if not unchanged and not replace_generated:
            raise PreparationError("已有生成结果；如确需重新准备此段，显式 --replace-generated，随后重新取得 generate 确认")
        if unchanged:
            segment.update({key: existing[key] for key in ("output_file", "status", "tool_call_id", "tool_called_at", "generation_confirmation_id") if key in existing})
        else:
            segment["previous_results"] = existing.get("previous_results", []) + [{key: existing[key] for key in ("output_file", "status", "tool_call_id", "tool_called_at", "generation_confirmation_id", "request_snapshot", "h3_prompt_file", "h3_prompt_sha256") if key in existing}]
    if existing:
        manifest["segments"][manifest["segments"].index(existing)] = segment
    else:
        manifest["segments"].append(segment)
    manifest["segments"].sort(key=lambda row: row["episode_segment_index"])
    manifest.update(episode_id=episode, project_data_card_revision=context["project_data_card_revision"], storyboard_manifest=context["source_files"][0]["file"], duration_s=sum(to_ms(row["duration_s"], positive=True) for row in manifest["segments"]) / 1000)
    evidence = build_evidence(context, segment)
    evidence["request_snapshot_sha256"] = canonical_sha({"segments": [request_segment_snapshot(segment)]})
    evidence["authorization_bindings"] = [authorization_binding(root, segment)]
    evidence_rel = f"episodes/{episode}/04_视频片段/生成确认_{segment_id}.json"
    if not check_only:
        atomic_write_many([(manifest_path, json_text(manifest)), (project_file(root, evidence_rel), json_text(evidence))])
    return {"written": not check_only, "manifest_file": manifest_rel, "evidence_file": evidence_rel,
            "segment": segment, "final_parameters_text": evidence["final_parameters_text"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--episode", required=True)
    parser.add_argument("--segment", required=True)
    parser.add_argument("--context", action="store_true", help="只输出当前段已确认上游和真实媒体计划")
    parser.add_argument("--combine-evidence", action="store_true", help="合并已准备段的两表；--segment SEG001,SEG002")
    parser.add_argument("--request-file")
    parser.add_argument("--prompt-file")
    parser.add_argument("--package-file", help="可选已有导演卡/交付包；默认引用已确认导演卡")
    parser.add_argument("--check-only", action="store_true", help="完整校验和派生，不落盘")
    parser.add_argument("--replace-generated", action="store_true", help="显式重新准备已有结果的段；保留旧结果和确认，必须重新确认后生成")
    args = parser.parse_args(argv)
    try:
        if args.combine_evidence:
            if args.context or args.request_file or args.prompt_file or args.package_file or args.replace_generated:
                parser.error("合批模式只需 --segment SEG001,SEG002，可加 --check-only")
            result = combine_evidence(args.project_root, args.episode, args.segment.split(","), args.check_only)
        elif args.context:
            result = load_segment_context(args.project_root, args.episode, args.segment)
        else:
            if not args.request_file or not args.prompt_file:
                parser.error("准备模式需要 --request-file 与 --prompt-file")
            result = prepare_segment(args.project_root, args.episode, args.segment, args.request_file, args.prompt_file, args.package_file, args.check_only, args.replace_generated)
        if not args.context:
            result = {key: value for key, value in result.items() if key != "segment"}
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"prepare_video: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
