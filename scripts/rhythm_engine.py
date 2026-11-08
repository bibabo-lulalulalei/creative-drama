"""Content-first 节奏引擎：时间核算（原 timeline_core）、源出处只读对账
（原 content_first）与 CLI 写回（原 rhythm_engine）三合一，横幅保留模块边界。

保留声明的安排，只检查结构与算术；CLI 只写派生数据，不生成叙事正文。
外部方（drama_lint/preflight/stamp_review/drama_rollback、tools/video）统一从本文件导入。
"""

from __future__ import annotations

# python -I（隔离模式）不把脚本目录加入 sys.path，入口必须自举同目录兄弟模块。
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# ===== 原 timeline_core.py =====

import copy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

ANNOTATIONS = {"beat_type", "intensity", "speech_pace", "note"}
BUDGET_KEYS = {"total_duration_s", "segment_budgets", "target_duration_s", "beat_duration_overrides",
               "action_units", "reaction_units", "merge", "merge_with_next", "duration_s"}
TOP_KEYS = {"episode_id", "source_script", "utterances", "scenes"}
SCENE_KEYS = {"scene_id", "shots", "beat_groups"}
SHOT_KEYS = {"shot_id", "timeline"}
EVENT_KEYS = {"event_id", "kind", "process", "source_refs", "start_s", "duration_s", "after",
              "utterance_id", "utterance_offset_s"}
UTTERANCE_KEYS = {"utterance_id", "line_id", "speaker_ref", "estimated_duration_s", "timing_basis"}
DESIGN_EXCLUSIONS = {"content_review", "preflight", "confirmations", "generation_confirmations", "task_id",
                     "status", "quality_gate", "quality_review", "output_file", "generated_at", "validated_at"}
TIMING_ANNOTATION_FIELDS = ANNOTATIONS


def issue(code, message, path="", hint=""):
    data = {"level": "error", "code": code, "message": message, "path": path}
    if hint:
        data["hint"] = hint
    return data


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
        issues.append(issue("timeline_shape_invalid", "必须是对象", path, hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
        return False
    for key in sorted(set(obj) - allowed - ANNOTATIONS):
        code = "timing_budget_input_forbidden" if budgets and key in BUDGET_KEYS else "timeline_field_unknown"
        issues.append(issue(code, f"不支持字段 {key}；核算不接受预算或动作/反应计数", path))
    return True


def validate_timeline_shape(data):
    issues = []
    if not _unknown(data, TOP_KEYS, "$", issues, budgets=True):
        return issues
    if not isinstance(data.get("episode_id"), str) or not re.fullmatch(r"ep_[1-9]\d*", data["episode_id"]):
        issues.append(issue("timeline_shape_invalid", "episode_id 必须为 ep_N", hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
    source = data.get("source_script")
    if source is not None:
        if (not isinstance(source, dict) or set(source) != {"file", "revision", "sha256"}
                or not isinstance(source.get("file"), str) or not source["file"]
                or type(source.get("revision")) is not int or source["revision"] < 1
                or not isinstance(source.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"])):
            issues.append(issue("source_revision_mismatch", "source_script 需 file/revision/sha256", hint='以最新已确认 script_contract 为准回填 source_script 三元与带 source_snapshot 的剧本确认记录（不伪造确认），再 allocate。python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
    utterances = data.get("utterances")
    if not isinstance(utterances, list):
        issues.append(issue("timeline_shape_invalid", "utterances 必须为数组，可空", hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
    else:
        for i, utterance in enumerate(utterances):
            if _unknown(utterance, UTTERANCE_KEYS, f"utterances[{i}]", issues):
                if any(not isinstance(utterance.get(key), str) or not utterance[key].strip()
                       for key in ("utterance_id", "line_id", "speaker_ref")):
                    issues.append(issue("timeline_shape_invalid", "utterance/line/speaker 需非空 ID", hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
                basis = utterance.get("timing_basis")
                allowed = {"method", "note"} if isinstance(basis, dict) and basis.get("method") == "director_estimate" else {"method", "file", "sha256", "range_s", "evidence"}
                if not isinstance(basis, dict) or set(basis) - allowed:
                    issues.append(issue("speech_timing_basis_invalid", "timing_basis 字段无效"))
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        issues.append(issue("timeline_shape_invalid", "scenes 必须是非空数组", hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
        return issues
    for i, scene in enumerate(scenes):
        path = f"scenes[{i}]"
        if not _unknown(scene, SCENE_KEYS, path, issues, budgets=True):
            continue
        if not isinstance(scene.get("scene_id"), str) or not scene["scene_id"].strip():
            issues.append(issue("timeline_shape_invalid", "scene_id 必须非空字符串", path, hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
        if "beat_groups" in scene and not isinstance(scene["beat_groups"], list):
            issues.append(issue("pack_drift", "beat_groups 必须为数组", path, hint='按报错修正 beat_groups 镜头组设计，SEG 派生字段（design_sha256/请求秒/尾余量）一律重跑 pack，禁止手填：python scripts/rhythm_engine.py pack --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write'))
        shots = scene.get("shots")
        if not isinstance(shots, list) or not shots:
            issues.append(issue("timeline_shape_invalid", "场次必须有 shots", path, hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
            continue
        for j, shot in enumerate(shots):
            sp = f"{path}.shots[{j}]"
            if not _unknown(shot, SHOT_KEYS, sp, issues, budgets=True):
                continue
            if not isinstance(shot.get("shot_id"), str) or not shot["shot_id"].strip():
                issues.append(issue("timeline_shape_invalid", "shot_id 必须非空字符串", sp, hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
            events = shot.get("timeline")
            if not isinstance(events, list) or not events:
                issues.append(issue("timeline_shape_invalid", "每镜至少一个时间过程", sp, hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
                continue
            for k, event in enumerate(events):
                if _unknown(event, EVENT_KEYS, f"{sp}.timeline[{k}]", issues):
                    kind = event.get("kind")
                    if not isinstance(kind, str) or kind not in {"visual", "speech", "camera", "hold"}:
                        issues.append(issue("timeline_shape_invalid", "未知过程 kind", sp, hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
                    elif kind == "speech":
                        if not isinstance(event.get("utterance_id"), str) or "utterance_offset_s" not in event:
                            issues.append(issue("timeline_shape_invalid", "speech 需 utterance_id/utterance_offset_s", sp, hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
                        if "process" in event or "source_refs" in event:
                            issues.append(issue("timeline_field_unknown", "speech 文本只回指 utterance，不另建权威", sp, hint='按 kind 删掉越权字段（speech 只写 utterance_id/utterance_offset_s，台词不进 timeline）；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
                    else:
                        if not isinstance(event.get("process"), str) or not event["process"].strip():
                            issues.append(issue("timeline_shape_invalid", "非 speech 需非空 process", sp, hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
                        if "utterance_id" in event or "utterance_offset_s" in event:
                            issues.append(issue("timeline_field_unknown", "非 speech 不能携带 utterance", sp, hint='按 kind 删掉越权字段（speech 只写 utterance_id/utterance_offset_s，台词不进 timeline）；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
                    for field in ("after", "source_refs"):
                        if field == "source_refs" and kind == "speech":
                            continue
                        refs = event.get(field, [])
                        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
                            issues.append(issue("timeline_shape_invalid", f"{field} 必须为字符串数组", sp, hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
    return issues


def reconcile_timeline(data, source_index=None):
    issues = validate_timeline_shape(data)
    result = {"ok": False, "issues": issues, "shots": [], "scenes": [], "events": [],
              "total_s": 0}
    if issues:
        return result
    source_index = source_index or {}
    seen = {"scene": set(), "shot": set(), "event": set(), "utterance": set()}

    def unique(kind, value):
        if not isinstance(value, str) or not value.strip():
            issues.append(issue("timeline_shape_invalid", f"{kind} ID 必须非空", hint='按 schema 修 rhythm_input 结构后重跑 allocate；schema：python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
            return False
        if value in seen[kind]:
            issues.append(issue("timeline_id_duplicate", f"重复 {kind} ID: {value}", hint='给冲突项改唯一非空 ID（源合同侧改动需重新走剧本确认链），再重跑 allocate。'))
            return False
        seen[kind].add(value)
        return True

    def number(value, path, positive=False):
        try:
            return to_ms(value, positive=positive)
        except ValueError as exc:
            issues.append(issue("timeline_number_invalid", str(exc), path, hint='把时间值改成非负 start、正且有限的 duration（≤3 位小数，内部整数毫秒），再 allocate --write。'))
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
            issues.append(issue("timeline_ref_unknown", f"{uid} 找不到 line:{line_id}", hint='先在 script_contract/utterances/causal_ledger 里建立被引用事实，或把引用改成已存在 ID，再重跑 allocate。'))
        elif utterance.get("speaker_ref") != line.get("speaker_ref"):
            issues.append(issue("source_line_uncovered", f"{uid} 说话者与源台词不符", hint='为每条 line_id 建 utterance 并在 timeline 用 speech 分片完整承接，台词逐字不改，再 allocate。python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
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
                        issues.append(issue("timeline_ref_unknown", f"{eid} 找不到源引用 {ref}", hint='先在 script_contract/utterances/causal_ledger 里建立被引用事实，或把引用改成已存在 ID，再重跑 allocate。'))
                rec = {"event_id": eid, "shot_id": sid, "kind": event["kind"],
                       "local_range_s": [seconds(start), seconds(start + duration)],
                       "absolute_range_s": [seconds(cursor + start), seconds(cursor + start + duration)],
                       "source_refs": event.get("source_refs", []), "after": event.get("after", [])}
                if event["kind"] == "speech":
                    uid = event["utterance_id"]
                    offset = number(event.get("utterance_offset_s"), eid)
                    rec.update(utterance_id=uid, utterance_offset_s=seconds(offset))
                    if uid not in utterances:
                        issues.append(issue("timeline_ref_unknown", f"{eid} 找不到 utterance {uid}", hint='先在 script_contract/utterances/causal_ledger 里建立被引用事实，或把引用改成已存在 ID，再重跑 allocate。'))
                    else:
                        utterances[uid]["fragments"].append((offset, offset + duration, cursor + start, cursor + start + duration))
                else:
                    rec["process"] = event["process"]
                by_event[eid] = (rec, cursor + start, cursor + start + duration)
                local_events.append(rec)
            result["shots"].append({"shot_id": sid, "scene_id": scene["scene_id"], "duration_s": seconds(end),
                                    "time_range_s": [seconds(cursor), seconds(cursor + end)], "timing_events": local_events,
                                    "duration_basis": {"end_event_ids": [e["event_id"] for e in local_events if to_ms(e["local_range_s"][1]) == end], "duration_s": seconds(end)}})
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
                issues.append(issue("timeline_ref_unknown", f"{eid} after 引用不存在: {ref}", hint='先在 script_contract/utterances/causal_ledger 里建立被引用事实，或把引用改成已存在 ID，再重跑 allocate。'))
                continue
            indegree[eid] += 1
            dependents[ref].append(eid)
            if start < by_event[ref][2]:
                issues.append(issue("timeline_dependency_conflict", f"{eid} 开始早于 {ref} 结束；返回导演设计，不自动移动", hint='按真实先后改声明区间或解除错误 after，再 allocate；程序不自动排程。python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
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
        issues.append(issue("timeline_dependency_cycle", "after 中存在自依赖或循环", hint='打断 after 环：保留真实先后、删掉错误回指，再重跑 allocate。'))
    for uid, utterance in utterances.items():
        expected = 0
        previous_end = None
        for offset, end, absolute_start, absolute_end in sorted(utterance["fragments"]):
            if offset != expected or end > utterance["duration_ms"]:
                issues.append(issue("speech_span_incomplete", f"{uid} 分片遗漏/重叠/越界", hint='按 utterance_offset 顺序重排分片，逐字拼回一次完整源台词，跨 SEG 另补 speech_bridge，再重跑引擎。python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
            if previous_end is not None and absolute_start != previous_end:
                issues.append(issue("speech_span_discontinuous", f"{uid} 跨镜连续发声的绝对时间不连续", hint='补齐时间缝隙或在跨 SEG 处写 speech_bridge 实施与审校引用；无可靠实施返回导演层。python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
            expected = end
            previous_end = absolute_end
        if expected != utterance["duration_ms"]:
            issues.append(issue("speech_span_incomplete", f"{uid} 分片未覆盖完整演读估计", hint='按 utterance_offset 顺序重排分片，逐字拼回一次完整源台词，跨 SEG 另补 speech_bridge，再重跑引擎。python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
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
            raise ValueError("能力档案需声明有效的整数秒请求范围")
    except (KeyError, TypeError, ValueError) as exc:
        issues.append(issue("tool_capabilities_invalid", f"真实工具能力缺失或损坏: {exc}"))
        return out
    shots = {shot["shot_id"]: shot for shot in result["shots"]}
    order = list(shots)
    if not isinstance(beat_groups, list) or not beat_groups:
        issues.append(issue("pack_drift", "需要导演声明的合法镜头组，不自动制造切点", hint='按报错修正 beat_groups 镜头组设计，SEG 派生字段（design_sha256/请求秒/尾余量）一律重跑 pack，禁止手填：python scripts/rhythm_engine.py pack --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write'))
        return out
    flat = []
    group_ids = set()
    cursor = 0
    for i, group in enumerate(beat_groups, 1):
        if not isinstance(group, dict) or set(group) - {"group_id", "segment_id", "shot_ids", "tail_handle", "note"}:
            issues.append(issue("pack_drift", "镜头组字段非法", hint='按报错修正 beat_groups 镜头组设计，SEG 派生字段（design_sha256/请求秒/尾余量）一律重跑 pack，禁止手填：python scripts/rhythm_engine.py pack --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write'))
            continue
        gids = group.get("shot_ids")
        gid = group.get("group_id")
        if not isinstance(gid, str) or not gid or gid in group_ids:
            issues.append(issue("pack_drift", "group_id 必须唯一且非空", hint='按报错修正 beat_groups 镜头组设计，SEG 派生字段（design_sha256/请求秒/尾余量）一律重跑 pack，禁止手填：python scripts/rhythm_engine.py pack --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write'))
        if isinstance(gid, str):
            group_ids.add(gid)
        if not isinstance(gids, list) or not gids or any(not isinstance(sid, str) or sid not in shots for sid in gids):
            issues.append(issue("pack_drift", f"组 {gid} 含未知/空镜头", hint='按报错修正 beat_groups 镜头组设计，SEG 派生字段（design_sha256/请求秒/尾余量）一律重跑 pack，禁止手填：python scripts/rhythm_engine.py pack --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write'))
            continue
        flat.extend(gids)
        content = sum(to_ms(shots[sid]["duration_s"]) for sid in gids)
        request = max(minimum, ((content + 999) // 1000) * 1000)
        if request > maximum:
            issues.append(issue("tool_duration_unrepresentable", f"组 {gid} 内容 {seconds(content)}s 超真实能力；保留设计，返回导演/用户处理", hint='超能力是设计问题不是数字问题：调整镜头设计/过程拆分后重跑 pack，禁止改预算或自动切镜。python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
        handle = group.get("tail_handle")
        if request > content:
            events = shots[gids[-1]]["timing_events"]
            matching = [event for event in events if isinstance(handle, dict) and event["event_id"] == handle.get("source_event_id")]
            if (not isinstance(handle, dict) or handle.get("mode") != "continue_existing_process"
                    or not isinstance(handle.get("description"), str) or not handle["description"].strip()
                    or not matching or matching[0]["kind"] == "speech"
                    or to_ms(matching[0]["local_range_s"][1]) != to_ms(shots[gids[-1]]["duration_s"])):
                issues.append(issue("technical_handle_unresolved", f"组 {gid} 的技术尾余量需末镜结束处非 speech 过程延续设计", hint='在该 beat_group 补合法 tail_handle（末镜非 speech 过程延续），再 pack --write；读 python scripts/read_reference.py --file references/storyboard.md --section "### 尾态选择算法"'))
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
        issues.append(issue("pack_drift", "组必须按正式顺序恰好覆盖所有镜头，无重漏", hint='按报错修正 beat_groups 镜头组设计，SEG 派生字段（design_sha256/请求秒/尾余量）一律重跑 pack，禁止手填：python scripts/rhythm_engine.py pack --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write'))
    segment_ids = [seg["segment_id"] for seg in out["segments"]]
    if any(not isinstance(sid, str) or not sid for sid in segment_ids):
        issues.append(issue("pack_drift", "segment_id 必须为非空字符串", hint='按报错修正 beat_groups 镜头组设计，SEG 派生字段（design_sha256/请求秒/尾余量）一律重跑 pack，禁止手填：python scripts/rhythm_engine.py pack --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write'))
    elif len(segment_ids) != len(set(segment_ids)):
        issues.append(issue("pack_drift", "segment_id 重复", hint='按报错修正 beat_groups 镜头组设计，SEG 派生字段（design_sha256/请求秒/尾余量）一律重跑 pack，禁止手填：python scripts/rhythm_engine.py pack --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write'))
    out["ok"] = not issues
    return out

# ===== 原 content_first.py =====


DERIVED_FIELDS = ("duration_s", "time_range_s", "timing_events", "duration_basis")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def project_file(root, value):
    if not isinstance(value, str) or not value:
        raise ValueError("缺项目内相对文件路径")
    path = (Path(root) / value).resolve()
    if not path.is_relative_to(Path(root).resolve()) or Path(value).is_absolute():
        raise ValueError("路径必须在项目根内")
    return path


def source_index_from_contract(contract, script_text, issues):
    index = {}
    scenes = contract.get("scenes")
    if not isinstance(scenes, list):
        issues.append(issue("source_revision_mismatch", "script contract 缺 scenes", hint='以最新已确认 script_contract 为准回填 source_script 三元与带 source_snapshot 的剧本确认记录（不伪造确认），再 allocate。python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
        return index
    positions = []
    scene_ids = set()
    for scene in scenes:
        sid = scene.get("scene_id") if isinstance(scene, dict) else None
        if not isinstance(sid, str) or not sid or sid in scene_ids:
            issues.append(issue("source_revision_mismatch", "源场次 ID 必须唯一且非空", hint='以最新已确认 script_contract 为准回填 source_script 三元与带 source_snapshot 的剧本确认记录（不伪造确认），再 allocate。python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
        if isinstance(sid, str):
            scene_ids.add(sid)
        matches = list(re.finditer(r"(?m)^#{1,6}\s+" + re.escape(str(sid)) + r"(?:\s|[：:|]|$)", script_text))
        if len(matches) != 1:
            issues.append(issue("source_revision_mismatch", f"{sid} 需唯一场次标题以定位源原文", hint='以最新已确认 script_contract 为准回填 source_script 三元与带 source_snapshot 的剧本确认记录（不伪造确认），再 allocate。python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
        positions.append(matches[0].start() if len(matches) == 1 else None)
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        pos = positions[i]
        later = [p for p in positions[i + 1:] if p is not None and pos is not None and p > pos]
        scene_text = script_text[pos:min(later) if later else len(script_text)] if pos is not None else ""
        events = scene.get("events")
        if not isinstance(events, list):
            issues.append(issue("source_event_uncovered", f"{scene.get('scene_id')} 需 events 源索引（不设数量）", hint='给每条未覆盖 beat 补 beat_coverage 处置行（kept/compressed/moved/dropped，dropped 需真实确认），再重跑 lint。python scripts/read_reference.py --file references/storyboard.md --section "### 转换差异台账（beat_coverage）"'))
            events = []
        for event in events:
            if not isinstance(event, dict):
                issues.append(issue("source_event_uncovered", "事件索引必须是对象", hint='给每条未覆盖 beat 补 beat_coverage 处置行（kept/compressed/moved/dropped，dropped 需真实确认），再重跑 lint。python scripts/read_reference.py --file references/storyboard.md --section "### 转换差异台账（beat_coverage）"'))
                continue
            eid = event.get("event_id")
            excerpt = event.get("source_excerpt")
            ref = "beat:" + str(eid)
            if not isinstance(eid, str) or not eid or ref in index:
                issues.append(issue("timeline_id_duplicate", f"无效/重复源事件 {eid}", hint='给冲突项改唯一非空 ID（源合同侧改动需重新走剧本确认链），再重跑 allocate。'))
            if not isinstance(excerpt, str) or not excerpt or excerpt not in scene_text:
                issues.append(issue("source_revision_mismatch", f"{eid} source_excerpt 不在对应场次原文", hint='以最新已确认 script_contract 为准回填 source_script 三元与带 source_snapshot 的剧本确认记录（不伪造确认），再 allocate。python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
            if not isinstance(event.get("summary"), str) or not event["summary"].strip():
                issues.append(issue("source_event_uncovered", f"{eid} 缺必要事实摘要", hint='给每条未覆盖 beat 补 beat_coverage 处置行（kept/compressed/moved/dropped，dropped 需真实确认），再重跑 lint。python scripts/read_reference.py --file references/storyboard.md --section "### 转换差异台账（beat_coverage）"'))
            index[ref] = event
        lines = scene.get("speech_lines", [])
        if not isinstance(lines, list):
            issues.append(issue("source_line_uncovered", "speech_lines 必须是数组，可空", hint='为每条 line_id 建 utterance 并在 timeline 用 speech 分片完整承接，台词逐字不改，再 allocate。python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
            continue
        for line in lines:
            if not isinstance(line, dict):
                issues.append(issue("source_line_uncovered", "台词索引必须是对象", hint='为每条 line_id 建 utterance 并在 timeline 用 speech 分片完整承接，台词逐字不改，再 allocate。python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
                continue
            lid = line.get("line_id")
            ref = "line:" + str(lid)
            text = line.get("spoken_text")
            if not isinstance(lid, str) or not lid or ref in index:
                issues.append(issue("timeline_id_duplicate", f"无效/重复 line_id {lid}", hint='给冲突项改唯一非空 ID（源合同侧改动需重新走剧本确认链），再重跑 allocate。'))
            if not isinstance(text, str) or not text or text not in scene_text:
                issues.append(issue("source_revision_mismatch", f"{lid} 台词不在对应源场次", hint='以最新已确认 script_contract 为准回填 source_script 三元与带 source_snapshot 的剧本确认记录（不伪造确认），再 allocate。python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
            index[ref] = dict(line, speaker_ref=line.get("speaker", line.get("speaker_ref")))
    return index


def load_source(root, inp, storyboard=None, *, require_confirmation=True):
    issues = []
    index = {}
    try:
        source = inp.get("source_script") or {}
        path = project_file(root, source.get("file"))
        raw = path.read_bytes()
        contract = json.loads(raw.decode("utf-8-sig"))
        if source.get("sha256") != hashlib.sha256(raw).hexdigest() or source.get("revision") != contract.get("revision"):
            issues.append(issue("source_revision_mismatch", "时间输入不是当前源剧本文件/版本", hint='以最新已确认 script_contract 为准回填 source_script 三元与带 source_snapshot 的剧本确认记录（不伪造确认），再 allocate。python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
        markdown = project_file(root, contract.get("source_markdown"))
        if file_sha(markdown) != contract.get("source_sha256"):
            issues.append(issue("source_revision_mismatch", "剧本正文与源索引 SHA 不一致", hint='以最新已确认 script_contract 为准回填 source_script 三元与带 source_snapshot 的剧本确认记录（不伪造确认），再 allocate。python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
        index = source_index_from_contract(contract, markdown.read_text(encoding="utf-8-sig"), issues)
        if require_confirmation:
            records_path = Path(root) / "00_制作控制/用户确认记录.jsonl"
            records = [json.loads(row) for row in records_path.read_text(encoding="utf-8").splitlines() if row.strip()]
            candidates = [record for record in records if isinstance(record, dict) and record.get("stage") == "script"
                          and record.get("episode_id") == inp.get("episode_id") and record.get("decision") == "confirmed"
                          and record.get("valid", True) is not False]
            current = candidates[-1] if candidates else {}
            snapshot = current.get("source_snapshot", {})
            if (current.get("revision") != contract.get("revision") or snapshot.get("file") != source.get("file")
                    or snapshot.get("sha256") != source.get("sha256") or not current.get("confirmation_id")
                    or not str(current.get("user_message") or "").strip()):
                issues.append(issue("source_revision_mismatch", "缺当前源剧本 SHA/版本对应的真实确认来源", hint='以最新已确认 script_contract 为准回填 source_script 三元与带 source_snapshot 的剧本确认记录（不伪造确认），再 allocate。python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
        for utterance in inp.get("utterances", []):
            basis = utterance.get("timing_basis", {})
            if basis.get("method") == "existing_measurement":
                media = project_file(root, basis.get("file"))
                evidence = basis.get("evidence", {})
                if media.is_file() and file_sha(media) == basis.get("sha256"):
                    index["measurement:" + basis["file"]] = dict(evidence, sha256=file_sha(media), range_s=basis.get("range_s"))
        if storyboard:
            for chain in storyboard.get("causal_ledger", []):
                if isinstance(chain, dict) and chain.get("chain_id"):
                    index["chain:" + chain["chain_id"]] = chain
            card_path = Path(root) / "00_制作控制/project_data_card.json"
            if card_path.is_file():
                card = read_json(card_path)
                id_keys = {"characters": "character_id", "scenes": "scene_id", "props": "prop_id"}
                for kind, id_key in id_keys.items():
                    for asset in card.get(kind, []):
                        if not isinstance(asset, dict):
                            continue
                        aid = asset.get(id_key)
                        for state in asset.get("state_timeline", []):
                            if isinstance(state, dict) and state.get("state_id"):
                                index[f"asset_state:{aid}:{state['state_id']}"] = state
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError) as exc:
        issues.append(issue("source_revision_mismatch", f"无法核对源剧本: {exc}", hint='以最新已确认 script_contract 为准回填 source_script 三元与带 source_snapshot 的剧本确认记录（不伪造确认），再 allocate。python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
    return index, issues


def validate_coverage(storyboard, inp, source_index, confirmations=()):
    issues = []
    expected = {key[5:] for key in source_index if key.startswith("beat:")}
    rows = storyboard.get("beat_coverage")
    if not isinstance(rows, list):
        return [issue("source_event_uncovered", "需要 beat_coverage 多对多承接", hint='给每条未覆盖 beat 补 beat_coverage 处置行（kept/compressed/moved/dropped，dropped 需真实确认），再重跑 lint。python scripts/read_reference.py --file references/storyboard.md --section "### 转换差异台账（beat_coverage）"')]
    shots = {shot["shot_id"] for scene in inp["scenes"] for shot in scene["shots"]}
    refs_by_shot = {shot["shot_id"]: {ref for event in shot["timeline"] for ref in event.get("source_refs", [])}
                    for scene in inp["scenes"] for shot in scene["shots"]}
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            issues.append(issue("source_event_uncovered", "覆盖行必须是对象", hint='给每条未覆盖 beat 补 beat_coverage 处置行（kept/compressed/moved/dropped，dropped 需真实确认），再重跑 lint。python scripts/read_reference.py --file references/storyboard.md --section "### 转换差异台账（beat_coverage）"'))
            continue
        bid = row.get("beat_id")
        if bid not in expected or bid in seen:
            issues.append(issue("source_event_uncovered", f"未知/重复处置 {bid}", hint='给每条未覆盖 beat 补 beat_coverage 处置行（kept/compressed/moved/dropped，dropped 需真实确认），再重跑 lint。python scripts/read_reference.py --file references/storyboard.md --section "### 转换差异台账（beat_coverage）"'))
        seen.add(bid)
        status = row.get("status", row.get("disposition"))
        targets = row.get("target_shots", [])
        if status in {"kept", "compressed", "moved"}:
            if (not isinstance(targets, list) or not targets or any(sid not in shots for sid in targets)
                    or any("beat:" + str(bid) not in refs_by_shot.get(sid, set()) for sid in targets)):
                issues.append(issue("source_event_uncovered", f"{bid} 未被真实目标镜头的时间项承接", hint='给每条未覆盖 beat 补 beat_coverage 处置行（kept/compressed/moved/dropped，dropped 需真实确认），再重跑 lint。python scripts/read_reference.py --file references/storyboard.md --section "### 转换差异台账（beat_coverage）"'))
        elif status == "dropped":
            ref = row.get("confirmation_ref")
            valid = any(record.get("confirmation_id") == ref and record.get("decision") == "confirmed"
                        and bid in record.get("approved_dropped_events", [])
                        and record.get("source_snapshot") == inp.get("source_script") for record in confirmations)
            if not valid:
                issues.append(issue("source_event_uncovered", f"{bid} dropped 需对应源版本的明确删戏授权，reason 不解除覆盖", hint='给每条未覆盖 beat 补 beat_coverage 处置行（kept/compressed/moved/dropped，dropped 需真实确认），再重跑 lint。python scripts/read_reference.py --file references/storyboard.md --section "### 转换差异台账（beat_coverage）"'))
        else:
            issues.append(issue("source_event_uncovered", f"{bid} 处置枚举无效", hint='给每条未覆盖 beat 补 beat_coverage 处置行（kept/compressed/moved/dropped，dropped 需真实确认），再重跑 lint。python scripts/read_reference.py --file references/storyboard.md --section "### 转换差异台账（beat_coverage）"'))
    if seen != expected:
        issues.append(issue("source_event_uncovered", f"源事件处置集合不符，缺失 {sorted(expected - seen)}", hint='给每条未覆盖 beat 补 beat_coverage 处置行（kept/compressed/moved/dropped，dropped 需真实确认），再重跑 lint。python scripts/read_reference.py --file references/storyboard.md --section "### 转换差异台账（beat_coverage）"'))
    used = {"line:" + str(utterance.get("line_id")) for utterance in inp.get("utterances", [])}
    missing = {key for key in source_index if key.startswith("line:")} - used
    if missing:
        issues.append(issue("source_line_uncovered", f"缺人声 {sorted(missing)}", hint='为每条 line_id 建 utterance 并在 timeline 用 speech 分片完整承接，台词逐字不改，再 allocate。python scripts/read_reference.py --file references/manifests.md --section "### rhythm_input_ep_N.json"'))
    return issues


def check_review(review, expected_inputs):
    issues = []
    if not isinstance(review, dict) or review.get("reviewed_inputs") != expected_inputs:
        issues.append(issue("content_review_stale", "内容审校不对应当前设计/源/时间输入", hint='结构 error 清零后真人做五项复核，先无旗标预检 python scripts/stamp_review.py --project-root <项目根> --episode ep_N，再 python scripts/stamp_review.py --project-root <项目根> --episode ep_N --i-did-the-review；禁止手填 content_review。'))
    if not isinstance(review, dict) or not isinstance(review.get("open_issues"), list):
        issues.append(issue("content_review_open_issue", "缺内容审校记录；字段存在不证明摄影成立", hint='先按五项复核解决并清空 open_issues（改设计后重跑引擎与 lint），再重新盖章；读 python scripts/read_reference.py --file references/storyboard.md --section "## 分镜内容人工复核"'))
    elif review["open_issues"]:
        issues.append(issue("content_review_open_issue", "有未解决的内容设计问题", hint='先按五项复核解决并清空 open_issues（改设计后重跑引擎与 lint），再重新盖章；读 python scripts/read_reference.py --file references/storyboard.md --section "## 分镜内容人工复核"'))
    return issues


def full_review_inputs(root, storyboard, inp, timing_path):
    return [dict(role="script", **inp["source_script"]),
            {"role": "storyboard", "sha256": canonical_sha(design_projection(storyboard))},
            {"role": "timing_input", "file": str(Path(timing_path).resolve().relative_to(Path(root).resolve())).replace("\\", "/"),
             "sha256": file_sha(timing_path)}]


def reconcile_storyboard(root, storyboard, inp, timing_path, capabilities, *, require_review=True):
    index, issues = load_source(root, inp, storyboard)
    result = reconcile_timeline(inp, index)
    issues.extend(result["issues"])
    if not result["ok"]:
        return result, None, issues
    if [shot.get("shot_id") for shot in storyboard.get("shots", [])] != [shot["shot_id"] for shot in result["shots"]]:
        issues.append(issue("timeline_shot_set_mismatch", "分镜与时间输入的镜头集合/顺序不一致", hint='先对齐 rhythm_input、storyboard JSON 与十五列表三处的镜头编号/顺序，再重跑 allocate 与 pack --write；三处必须同源：python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
    else:
        for actual, expected in zip(storyboard["shots"], result["shots"]):
            for field in DERIVED_FIELDS:
                if actual.get(field) != expected[field]:
                    issues.append(issue("timing_output_drift", f"{expected['shot_id']} {field} 与同源重算不符", hint='改 rhythm_input 后必须重跑核算写回派生字度（禁止手填 duration_s/time_range_s）：python scripts/rhythm_engine.py allocate --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write'))
    if storyboard.get("timing_input_sha256") != result.get("timing_input_sha256") or storyboard.get("duration_s") != result["total_s"]:
        issues.append(issue("timing_output_drift", "分镜总长/规范时间指纹不符", hint='改 rhythm_input 后必须重跑核算写回派生字度（禁止手填 duration_s/time_range_s）：python scripts/rhythm_engine.py allocate --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write'))
    groups = [group for scene in inp["scenes"] for group in scene.get("beat_groups", [])]
    pack = compute_groups(result, groups, capabilities, storyboard.get("shots", []))
    issues.extend(pack["issues"])
    if pack["ok"]:
        actual = storyboard.get("segments", [])
        # IDs survive unchanged group membership; generated defaults are not new identity claims.
        if (len(actual) != len(pack["segments"]) or
            any(any(a.get(key) != value for key, value in b.items() if key != "segment_id")
                or (g.get("segment_id") and a.get("segment_id") != g["segment_id"])
                for a, b, g in zip(actual, pack["segments"], groups)) or
            any(not isinstance(a.get("segment_id"), str) for a in actual) or
            len({a.get("segment_id") for a in actual}) != len(actual)):
            issues.append(issue("pack_drift", "SEG 内容/请求/尾余量/设计依赖不符", hint='按报错修正 beat_groups 镜头组设计，SEG 派生字段（design_sha256/请求秒/尾余量）一律重跑 pack，禁止手填：python scripts/rhythm_engine.py pack --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write'))
    records_path = Path(root) / "00_制作控制/用户确认记录.jsonl"
    try:
        confirmations = [json.loads(row) for row in records_path.read_text(encoding="utf-8").splitlines() if row.strip()]
    except (OSError, ValueError):
        confirmations = []
    issues.extend(validate_coverage(storyboard, inp, index, confirmations))
    if require_review:
        issues.extend(check_review(storyboard.get("content_review"), full_review_inputs(root, storyboard, inp, timing_path)))
    md = storyboard.get("source_markdown")
    if md:
        try:
            issues.extend(check_reading_times(project_file(root, md).read_text(encoding="utf-8-sig"), result))
        except (OSError, ValueError) as exc:
            issues.append(issue("timeline_shot_set_mismatch", f"分镜阅读稿不可用: {exc}", hint='先对齐 rhythm_input、storyboard JSON 与十五列表三处的镜头编号/顺序，再重跑 allocate 与 pack --write；三处必须同源：python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"'))
    return result, pack, issues


def reading_rows(text):
    """Read actual fifteen-column tables using their header, never a SHOT-name heuristic."""
    rows, layout = [], None
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not line.strip().startswith("|"):
            layout = None
            continue
        if len(cells) == 15 and cells[2] == "镜号" and cells[4] == "时长":
            layout = "director"
            continue
        if len(cells) == 15 and cells[0] in {"镜头", "镜号", "镜头编号", "镜头 ID", "shot_id"}:
            layout = "split_time"
            continue
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        if layout:
            if len(cells) != 15:
                raise ValueError("timeline_shot_set_mismatch: 分镜数据行不是十五列")
            ident = re.sub(r"[（(].*$", "", cells[2] if layout == "director" else cells[0]).strip()
            rows.append((ident, cells, layout))
    return rows


def reading_time_ms(value):
    match = re.fullmatch(r"\s*([\d:.]+)\s*[-–—]\s*([\d:.]+)\s*[（(]\s*([\d.]+)\s*s?\s*[）)]\s*", value)
    if not match:
        raise ValueError("时长列需完整绝对起止（持续秒数）")
    def clock(token):
        parts = token.split(":")
        if len(parts) > 3:
            raise ValueError("时间码格式无效")
        number = Decimal(0)
        for part in parts:
            number = number * 60 + Decimal(part)
        return to_ms(number)
    return [clock(match[1]), clock(match[2]), to_ms(Decimal(match[3]), positive=True)]


def clock_text(value):
    ms = to_ms(value)
    minutes, rest = divmod(ms, 60000)
    sec, fraction = divmod(rest, 1000)
    return f"{minutes:02d}:{sec:02d}" + (f".{fraction:03d}" if fraction else "")


def check_reading_times(text, result):
    rows = reading_rows(text)
    if [row[0] for row in rows] != [shot["shot_id"] for shot in result["shots"]]:
        return [issue("timeline_shot_set_mismatch", "十五列阅读稿的镜头集合/顺序需与同源时间输入一致", hint='先对齐 rhythm_input、storyboard JSON 与十五列表三处的镜头编号/顺序，再重跑 allocate 与 pack --write；三处必须同源：python scripts/read_reference.py --file references/storyboard.md --section "### 节奏流水线（rhythm_input → 引擎 → 写回）"')]
    issues = []
    for (_, row, layout), shot in zip(rows, result["shots"]):
        expected = f"{shot['time_range_s'][0]:g}–{shot['time_range_s'][1]:g}"
        try:
            valid = (reading_time_ms(row[4]) == [to_ms(v) for v in [*shot['time_range_s'], shot['duration_s']]] if layout == "director"
                     else row[1].removesuffix("s").strip() == expected and row[2].removesuffix("s").strip() == f"{shot['duration_s']:g}")
        except (ValueError, ArithmeticError):
            valid = False
        if not valid:
            issues.append(issue("timing_output_drift", f"{shot['shot_id']} 阅读稿时间列不符，需同源渲染", hint='改 rhythm_input 后必须重跑核算写回派生字度（禁止手填 duration_s/time_range_s）：python scripts/rhythm_engine.py allocate --project-root <项目根> --input episodes/ep_N/02_分镜/rhythm_input_ep_N.json --storyboard episodes/ep_N/02_分镜/storyboard_ep_N.json --write'))
    return issues


def render_reading_times(text, result):
    by_id = {shot["shot_id"]: shot for shot in result["shots"]}
    rows = reading_rows(text)
    if [row[0] for row in rows] != list(by_id):
        raise ValueError("timeline_shot_set_mismatch: 阅读稿镜头集合/顺序不符，拒绝部分更新")
    seen = []
    output = []
    for line in text.splitlines(keepends=True):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        identity = re.sub(r"[（(].*$", "", cells[2] if len(cells) == 15 else "").strip()
        if line.strip().startswith("|") and len(cells) == 15 and (cells[0] in by_id or identity in by_id):
            official = identity in by_id
            shot = by_id[identity if official else cells[0]]
            seen.append(shot['shot_id'])
            if official:
                cells[4] = f"{clock_text(shot['time_range_s'][0])}–{clock_text(shot['time_range_s'][1])}（{shot['duration_s']:g}s）"
            else:
                cells[1] = f"{shot['time_range_s'][0]:g}–{shot['time_range_s'][1]:g}s"
                cells[2] = f"{shot['duration_s']:g}s"
            line = "| " + " | ".join(cells) + " |\n"
        output.append(line)
    if seen != list(by_id):
        raise ValueError("timeline_shot_set_mismatch: 阅读稿镜头集合/顺序不符，拒绝部分更新")
    return "".join(output)

# ===== 原 rhythm_engine.py =====

import argparse
import os
import tempfile


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
