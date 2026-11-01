"""Content-first 时间核算：保留声明的安排，只检查结构与算术。无文件或网络操作。"""
from __future__ import annotations

import copy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

ENGINE_VERSION = 3
TIMING_MODEL = "content_first_v1"
ANNOTATIONS = {"beat_type", "intensity", "speech_pace", "note"}
BUDGET_KEYS = {"total_duration_s", "segment_budgets", "target_duration_s", "beat_duration_overrides",
               "action_units", "reaction_units", "merge", "merge_with_next", "duration_s"}
TOP_KEYS = {"schema_version", "timing_model", "engine_version", "episode_id", "source_script", "utterances", "scenes"}
SCENE_KEYS = {"scene_id", "shots", "beat_groups"}
SHOT_KEYS = {"shot_id", "timeline"}
EVENT_KEYS = {"event_id", "kind", "process", "source_refs", "start_s", "duration_s", "after",
              "utterance_id", "utterance_offset_s"}
UTTERANCE_KEYS = {"utterance_id", "line_id", "speaker_ref", "estimated_duration_s", "timing_basis"}
DESIGN_EXCLUSIONS = {"content_review", "preflight", "confirmations", "generation_confirmations", "task_id",
                     "status", "quality_gate", "quality_review", "output_file", "generated_at", "validated_at"}
TIMING_ANNOTATION_FIELDS = ANNOTATIONS


def issue(code, message, path=""):
    return {"level": "error", "code": code, "message": message, "path": path}


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+(?:\.\d+)*", value):
        return ()
    return tuple(int(part) for part in value.split("."))


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def timing_projection(data):
    def project(value):
        if isinstance(value, dict):
            return {key: project(val) for key, val in value.items() if key not in TIMING_ANNOTATION_FIELDS}
        if isinstance(value, list):
            return [project(val) for val in value]
        return value
    return project(data)


def design_projection(data):
    # 排除集只作用于容器字段；不递归删除人物/资产内容里同名的语义字段。
    return {key: copy.deepcopy(val) for key, val in data.items() if key not in DESIGN_EXCLUSIONS}


def to_ms(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("时间必须是数字，bool 不算数字")
    try:
        number = Decimal(str(value))
        milliseconds = number * 1000
        if not number.is_finite() or number < 0 or (positive and number <= 0):
            raise ValueError("时间必须有限；起点非负，持续时间为正")
        if milliseconds != milliseconds.to_integral_value():
            raise ValueError("时间最多三位小数；不自动舍入")
        return int(milliseconds)
    except (InvalidOperation, OverflowError):
        raise ValueError("非法时间数值") from None


def seconds(ms):
    return ms // 1000 if ms % 1000 == 0 else ms / 1000


def _unknown(obj, allowed, path, issues, *, budgets=False):
    if not isinstance(obj, dict):
        issues.append(issue("timeline_shape_invalid", "必须是对象", path))
        return False
    for key in sorted(set(obj) - allowed - ANNOTATIONS):
        code = "timing_budget_input_forbidden" if budgets and key in BUDGET_KEYS else "timeline_field_unknown"
        issues.append(issue(code, f"不支持字段 {key}；核算不接受预算或动作/反应计数", path))
    return True


def validate_timeline_shape(data):
    issues = []
    if not _unknown(data, TOP_KEYS, "$", issues, budgets=True):
        return issues
    if (version_tuple(data.get("schema_version")) != (2, 0) or data.get("timing_model") != TIMING_MODEL
            or type(data.get("engine_version")) is not int or data["engine_version"] != ENGINE_VERSION):
        issues.append(issue("timing_model_unsupported", "时间输入必须使用 schema 2.0 / content_first_v1 / engine 3"))
    if not isinstance(data.get("episode_id"), str) or not re.fullmatch(r"ep_[1-9]\d*", data["episode_id"]):
        issues.append(issue("timeline_shape_invalid", "episode_id 必须为 ep_N"))
    source = data.get("source_script")
    if source is not None:
        if (not isinstance(source, dict) or set(source) != {"file", "revision", "sha256"}
                or not isinstance(source.get("file"), str) or not source["file"]
                or type(source.get("revision")) is not int or source["revision"] < 1
                or not isinstance(source.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"])):
            issues.append(issue("source_revision_mismatch", "source_script 需 file/revision/sha256"))
    utterances = data.get("utterances")
    if not isinstance(utterances, list):
        issues.append(issue("timeline_shape_invalid", "utterances 必须为数组，可空"))
    else:
        for i, utterance in enumerate(utterances):
            if _unknown(utterance, UTTERANCE_KEYS, f"utterances[{i}]", issues):
                if any(not isinstance(utterance.get(key), str) or not utterance[key].strip()
                       for key in ("utterance_id", "line_id", "speaker_ref")):
                    issues.append(issue("timeline_shape_invalid", "utterance/line/speaker 需非空 ID"))
                basis = utterance.get("timing_basis")
                allowed = {"method", "note"} if isinstance(basis, dict) and basis.get("method") == "director_estimate" else {"method", "file", "sha256", "range_s", "evidence"}
                if not isinstance(basis, dict) or set(basis) - allowed:
                    issues.append(issue("speech_timing_basis_invalid", "timing_basis 字段无效"))
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        issues.append(issue("timeline_shape_invalid", "scenes 必须是非空数组"))
        return issues
    for i, scene in enumerate(scenes):
        path = f"scenes[{i}]"
        if not _unknown(scene, SCENE_KEYS, path, issues, budgets=True):
            continue
        if not isinstance(scene.get("scene_id"), str) or not scene["scene_id"].strip():
            issues.append(issue("timeline_shape_invalid", "scene_id 必须非空字符串", path))
        if "beat_groups" in scene and not isinstance(scene["beat_groups"], list):
            issues.append(issue("pack_drift", "beat_groups 必须为数组", path))
        shots = scene.get("shots")
        if not isinstance(shots, list) or not shots:
            issues.append(issue("timeline_shape_invalid", "场次必须有 shots", path))
            continue
        for j, shot in enumerate(shots):
            sp = f"{path}.shots[{j}]"
            if not _unknown(shot, SHOT_KEYS, sp, issues, budgets=True):
                continue
            if not isinstance(shot.get("shot_id"), str) or not shot["shot_id"].strip():
                issues.append(issue("timeline_shape_invalid", "shot_id 必须非空字符串", sp))
            events = shot.get("timeline")
            if not isinstance(events, list) or not events:
                issues.append(issue("timeline_shape_invalid", "每镜至少一个时间过程", sp))
                continue
            for k, event in enumerate(events):
                if _unknown(event, EVENT_KEYS, f"{sp}.timeline[{k}]", issues):
                    kind = event.get("kind")
                    if not isinstance(kind, str) or kind not in {"visual", "speech", "camera", "hold"}:
                        issues.append(issue("timeline_shape_invalid", "未知过程 kind", sp))
                    elif kind == "speech":
                        if not isinstance(event.get("utterance_id"), str) or "utterance_offset_s" not in event:
                            issues.append(issue("timeline_shape_invalid", "speech 需 utterance_id/utterance_offset_s", sp))
                        if "process" in event or "source_refs" in event:
                            issues.append(issue("timeline_field_unknown", "speech 文本只回指 utterance，不另建权威", sp))
                    else:
                        if not isinstance(event.get("process"), str) or not event["process"].strip():
                            issues.append(issue("timeline_shape_invalid", "非 speech 需非空 process", sp))
                        if "utterance_id" in event or "utterance_offset_s" in event:
                            issues.append(issue("timeline_field_unknown", "非 speech 不能携带 utterance", sp))
                    for field in ("after", "source_refs"):
                        if field == "source_refs" and kind == "speech":
                            continue
                        refs = event.get(field, [])
                        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
                            issues.append(issue("timeline_shape_invalid", f"{field} 必须为字符串数组", sp))
    return issues


def reconcile_timeline(data, source_index=None):
    issues = validate_timeline_shape(data)
    result = {"ok": False, "issues": issues, "shots": [], "scenes": [], "events": [],
              "total_s": 0, "engine_version": ENGINE_VERSION, "timing_model": TIMING_MODEL}
    if issues:
        return result
    source_index = source_index or {}
    seen = {"scene": set(), "shot": set(), "event": set(), "utterance": set()}

    def unique(kind, value):
        if not isinstance(value, str) or not value.strip():
            issues.append(issue("timeline_shape_invalid", f"{kind} ID 必须非空"))
            return False
        if value in seen[kind]:
            issues.append(issue("timeline_id_duplicate", f"重复 {kind} ID: {value}"))
            return False
        seen[kind].add(value)
        return True

    def number(value, path, positive=False):
        try:
            return to_ms(value, positive=positive)
        except ValueError as exc:
            issues.append(issue("timeline_number_invalid", str(exc), path))
            return 0

    utterances = {}
    for utterance in data["utterances"]:
        uid = utterance.get("utterance_id")
        if not unique("utterance", uid):
            continue
        duration = number(utterance.get("estimated_duration_s"), uid, True)
        line_id = utterance.get("line_id")
        line = source_index.get("line:" + str(line_id))
        if not isinstance(line, dict):
            issues.append(issue("timeline_ref_unknown", f"{uid} 找不到 line:{line_id}"))
        elif utterance.get("speaker_ref") != line.get("speaker_ref"):
            issues.append(issue("source_line_uncovered", f"{uid} 说话者与源台词不符"))
        basis = utterance.get("timing_basis")
        if not isinstance(basis, dict) or basis.get("method") not in {"director_estimate", "existing_measurement"}:
            issues.append(issue("speech_timing_basis_invalid", f"{uid} 缺演读依据"))
        elif basis["method"] == "director_estimate":
            if not isinstance(basis.get("note"), str) or not basis["note"].strip():
                issues.append(issue("speech_timing_basis_invalid", f"{uid} 需说明本次演读估计"))
        else:
            evidence = source_index.get("measurement:" + str(basis.get("file")))
            if (not isinstance(evidence, dict) or evidence.get("line_id") != line_id
                    or evidence.get("purpose") != "utterance_measurement" or basis.get("sha256") != evidence.get("sha256")
                    or basis.get("range_s") != evidence.get("range_s")
                    or number(evidence.get("duration_s"), uid, True) != duration):
                issues.append(issue("speech_timing_basis_invalid", f"{uid} 测量需本句实存音频/指纹/范围；音色样音不算"))
        utterances[uid] = {"duration_ms": duration, "fragments": [], "line_id": line_id}
    cursor = 0
    by_event = {}
    for scene in data["scenes"]:
        unique("scene", scene.get("scene_id"))
        scene_start = cursor
        for shot in scene["shots"]:
            sid = shot.get("shot_id")
            unique("shot", sid)
            local_events = []
            end = 0
            for event in shot["timeline"]:
                eid = event.get("event_id")
                if not unique("event", eid):
                    continue
                start = number(event.get("start_s"), eid)
                duration = number(event.get("duration_s"), eid, True)
                end = max(end, start + duration)
                for ref in event.get("source_refs", []):
                    if ref not in source_index:
                        issues.append(issue("timeline_ref_unknown", f"{eid} 找不到源引用 {ref}"))
                rec = {"event_id": eid, "shot_id": sid, "kind": event["kind"],
                       "local_range_s": [seconds(start), seconds(start + duration)],
                       "absolute_range_s": [seconds(cursor + start), seconds(cursor + start + duration)],
                       "source_refs": event.get("source_refs", []), "after": event.get("after", [])}
                if event["kind"] == "speech":
                    uid = event["utterance_id"]
                    offset = number(event.get("utterance_offset_s"), eid)
                    rec.update(utterance_id=uid, utterance_offset_s=seconds(offset))
                    if uid not in utterances:
                        issues.append(issue("timeline_ref_unknown", f"{eid} 找不到 utterance {uid}"))
                    else:
                        utterances[uid]["fragments"].append((offset, offset + duration, cursor + start, cursor + start + duration))
                else:
                    rec["process"] = event["process"]
                by_event[eid] = (rec, cursor + start, cursor + start + duration)
                local_events.append(rec)
            result["shots"].append({"shot_id": sid, "scene_id": scene["scene_id"], "duration_s": seconds(end),
                                    "time_range_s": [seconds(cursor), seconds(cursor + end)], "timing_events": local_events,
                                    "duration_basis": {"model": TIMING_MODEL, "end_event_ids": [e["event_id"] for e in local_events if to_ms(e["local_range_s"][1]) == end], "duration_s": seconds(end)}})
            result["events"].extend(local_events)
            cursor += end
        result["scenes"].append({"scene_id": scene["scene_id"], "duration_s": seconds(cursor - scene_start),
                                  "time_range_s": [seconds(scene_start), seconds(cursor)]})
    # Kahn 检环避免深图递归溢出；核验区间，不重新排程。
    indegree = {eid: 0 for eid in by_event}
    dependents = {eid: [] for eid in by_event}
    for eid, (rec, start, _) in by_event.items():
        for ref in rec["after"]:
            if ref not in by_event:
                issues.append(issue("timeline_ref_unknown", f"{eid} after 引用不存在: {ref}"))
                continue
            indegree[eid] += 1
            dependents[ref].append(eid)
            if start < by_event[ref][2]:
                issues.append(issue("timeline_dependency_conflict", f"{eid} 开始早于 {ref} 结束；返回导演设计，不自动移动"))
    queue = [eid for eid, degree in indegree.items() if degree == 0]
    visited = 0
    while queue:
        current = queue.pop()
        visited += 1
        for child in dependents[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if visited != len(indegree):
        issues.append(issue("timeline_dependency_cycle", "after 中存在自依赖或循环"))
    for uid, utterance in utterances.items():
        expected = 0
        previous_end = None
        for offset, end, absolute_start, absolute_end in sorted(utterance["fragments"]):
            if offset != expected or end > utterance["duration_ms"]:
                issues.append(issue("speech_span_incomplete", f"{uid} 分片遗漏/重叠/越界"))
            if previous_end is not None and absolute_start != previous_end:
                issues.append(issue("speech_span_discontinuous", f"{uid} 跨镜连续发声的绝对时间不连续"))
            expected = end
            previous_end = absolute_end
        if expected != utterance["duration_ms"]:
            issues.append(issue("speech_span_incomplete", f"{uid} 分片未覆盖完整演读估计"))
    result.update(ok=not issues, total_s=seconds(cursor))
    if not issues:
        result["timing_input_sha256"] = canonical_sha(timing_projection(data))
    return result


def compute_groups(result, beat_groups, capabilities, design_shots=None):
    issues = []
    out = {"ok": False, "issues": issues, "segments": []}
    if not result.get("ok"):
        issues.extend(result.get("issues", []))
        return out
    cap = capabilities.get("capabilities", capabilities)
    try:
        minimum = to_ms(cap["min_duration_s"], positive=True)
        maximum = to_ms(cap["max_duration_s"], positive=True)
        if minimum > maximum or cap.get("duration_integer_only") is not True:
            raise ValueError("首版要求整数秒能力合同")
    except (KeyError, TypeError, ValueError) as exc:
        issues.append(issue("tool_capabilities_invalid", f"真实工具能力缺失或损坏: {exc}"))
        return out
    shots = {shot["shot_id"]: shot for shot in result["shots"]}
    order = list(shots)
    if not isinstance(beat_groups, list) or not beat_groups:
        issues.append(issue("pack_drift", "需要导演声明的合法镜头组，不自动制造切点"))
        return out
    flat = []
    group_ids = set()
    cursor = 0
    for i, group in enumerate(beat_groups, 1):
        if not isinstance(group, dict) or set(group) - {"group_id", "segment_id", "shot_ids", "tail_handle", "note"}:
            issues.append(issue("pack_drift", "镜头组字段非法"))
            continue
        gids = group.get("shot_ids")
        gid = group.get("group_id")
        if not isinstance(gid, str) or not gid or gid in group_ids:
            issues.append(issue("pack_drift", "group_id 必须唯一且非空"))
        if isinstance(gid, str):
            group_ids.add(gid)
        if not isinstance(gids, list) or not gids or any(not isinstance(sid, str) or sid not in shots for sid in gids):
            issues.append(issue("pack_drift", f"组 {gid} 含未知/空镜头"))
            continue
        flat.extend(gids)
        content = sum(to_ms(shots[sid]["duration_s"]) for sid in gids)
        request = max(minimum, ((content + 999) // 1000) * 1000)
        if request > maximum:
            issues.append(issue("tool_duration_unrepresentable", f"组 {gid} 内容 {seconds(content)}s 超真实能力；保留设计，返回导演/用户处理"))
        handle = group.get("tail_handle")
        if request > content:
            events = shots[gids[-1]]["timing_events"]
            matching = [event for event in events if isinstance(handle, dict) and event["event_id"] == handle.get("source_event_id")]
            if (not isinstance(handle, dict) or handle.get("mode") != "continue_existing_process"
                    or not isinstance(handle.get("description"), str) or not handle["description"].strip()
                    or not matching or matching[0]["kind"] == "speech"
                    or to_ms(matching[0]["local_range_s"][1]) != to_ms(shots[gids[-1]]["duration_s"])):
                issues.append(issue("technical_handle_unresolved", f"组 {gid} 的技术尾余量需末镜结束处非 speech 过程延续设计"))
        segment = {"segment_id": group.get("segment_id") or f"SEG{i:03d}", "group_id": gid, "shot_ids": gids,
                   "duration_s": seconds(content), "request_duration_s": seconds(request),
                   "tail_handle_s": seconds(request - content), "time_range_s": [seconds(cursor), seconds(cursor + content)]}
        if request > content:
            segment["tail_handle"] = handle
        # Bind actual director design as well as arithmetic. SEG ownership is derived by pack.
        designs = {shot["shot_id"]: {k: v for k, v in shot.items() if k != "segment_id"}
                   for shot in (design_shots or [])}
        segment["design_sha256"] = canonical_sha({"shots": [shots[sid] for sid in gids],
            "director_design": [designs.get(sid) for sid in gids] if design_shots is not None else None,
            "tail_handle": handle})
        out["segments"].append(segment)
        cursor += content
    if flat != order:
        issues.append(issue("pack_drift", "组必须按正式顺序恰好覆盖所有镜头，无重漏"))
    segment_ids = [seg["segment_id"] for seg in out["segments"]]
    if any(not isinstance(sid, str) or not sid for sid in segment_ids):
        issues.append(issue("pack_drift", "segment_id 必须为非空字符串"))
    elif len(segment_ids) != len(set(segment_ids)):
        issues.append(issue("pack_drift", "segment_id 重复"))
    out["ok"] = not issues
    return out
