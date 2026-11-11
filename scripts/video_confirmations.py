"""冻结的历史生成确认与当前请求分开核对；只读，不删除历史。"""
from __future__ import annotations

from datetime import datetime
import copy
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from rhythm_engine import canonical_sha, issue, project_file, to_ms


class ConfirmationError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _error(code, message):
    raise ConfirmationError(code, message)


def load_confirmation_history(root, episode, manifest=None, ledger_rows=None):
    """只从本集视频生成确认台账读取记录，不合并其他来源。"""
    if not isinstance(episode, str) or not re.fullmatch(r"ep_[1-9]\d*", episode):
        _error("video_generation_confirmation_episode_mismatch", "episode 必须形如 ep_1")
    if manifest is not None and (not isinstance(manifest, dict) or manifest.get("episode_id") != episode):
        _error("video_generation_confirmation_episode_mismatch", "视频 manifest 的 episode_id 与当前分集不一致")
    if ledger_rows is None:
        ledger = Path(root) / "00_制作控制/用户确认记录.jsonl"
        try:
            ledger_rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        except FileNotFoundError:
            ledger_rows = []
        except (OSError, ValueError) as exc:
            _error("confirmation_log_unreadable", f"确认台账无法读取：{exc}")
    records, ids = [], set()
    for row in ledger_rows:
        if not isinstance(row, dict):
            _error("video_generation_confirmation_invalid", "确认记录必须为对象")
        if row.get("episode_id") != episode or row.get("confirmation_purpose") != "video_generation":
            continue
        cid = row.get("confirmation_id")
        if not isinstance(cid, str) or not cid or cid in ids:
            _error("video_generation_confirmation_id_duplicate", "视频确认需唯一非空 ID")
        ids.add(cid)
        records.append(copy.deepcopy(row))
    return records


def authorization_binding(root, segment):
    """绑定实际 Prompt 和本地输入字节；HTTP(S) 只冻结 URL 字符串身份。"""
    root = Path(root).resolve()
    prompt = segment.get("h3_prompt_file")
    if not isinstance(prompt, str) or not prompt:
        _error("video_authorization_binding_invalid", "视频段缺 h3_prompt_file")
    try:
        binding = {"segment_id": segment.get("segment_id"), "h3_prompt_file": prompt,
                   "h3_prompt_sha256": hashlib.sha256(project_file(root, prompt).read_bytes()).hexdigest(), "inputs": []}
        snapshot = segment.get("request_snapshot")
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("inputs"), list):
            _error("video_authorization_binding_invalid", "视频段缺冻结 inputs 数组")
        for item in snapshot["inputs"]:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                _error("video_authorization_binding_invalid", "冻结输入必须含路径")
            path = item["path"]
            parsed = urlsplit(path)
            entry = {"kind": item.get("kind"), "path": path}
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                entry["identity"] = "url_string_only"
            else:
                entry.update(identity="local_bytes", sha256=hashlib.sha256(project_file(root, path).read_bytes()).hexdigest())
            binding["inputs"].append(entry)
        return binding
    except (OSError, ValueError) as exc:
        if isinstance(exc, ConfirmationError):
            raise
        _error("video_authorization_binding_invalid", f"无法核对 Prompt 或本地输入：{exc}")


def validate_project_confirmations(root, episode, manifest=None, *, ledger_rows=None, check_outputs=True):
    if manifest is None:
        path = Path(root) / f"episodes/{episode}/04_视频片段/video_manifest_{episode}.json"
        try:
            manifest = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            return [issue("video_manifest_unreadable", str(exc))]
    try:
        records = load_confirmation_history(root, episode, manifest, ledger_rows)
        return validate_confirmations({"generation_confirmations": records}, manifest.get("segments", []), root=root, check_outputs=check_outputs)
    except ConfirmationError as exc:
        return [issue(exc.code, str(exc))]


def request_segment_snapshot(segment):
    keys = ("segment_id", "episode_segment_index", "duration_s", "request_snapshot")
    return copy.deepcopy({key: segment.get(key) for key in keys})


def _time(value):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


def validate_confirmations(data, segments, *, root=None, check_outputs=True, return_active=False):
    issues = []
    records = data.get("generation_confirmations", [])
    if not isinstance(records, list):
        return [issue("video_generation_confirmations_missing", "generation_confirmations 必须为数组")]
    ids = set()
    active = {}
    previous_time = None
    by_index = {}
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        index = seg.get("episode_segment_index")
        if type(index) is not int or index < 1 or index in by_index:
            issues.append(issue("episode_segment_index_invalid", "视频段索引需从 1 起唯一正整数"))
        else:
            by_index[index] = seg
    if sorted(by_index) != list(range(1, len(by_index) + 1)):
        issues.append(issue("episode_segment_index_not_contiguous", "视频段索引必须连续"))
    for rec in records:
        if not isinstance(rec, dict):
            issues.append(issue("video_generation_confirmation_invalid", "历史确认必须是对象"))
            continue
        cid = rec.get("confirmation_id")
        issue_start = len(issues)
        time = _time(rec.get("confirmed_at"))
        if not isinstance(cid, str) or not cid or cid in ids:
            issues.append(issue("video_generation_confirmation_id_duplicate", "确认需唯一稳定 ID"))
        if isinstance(cid, str):
            ids.add(cid)
        if time is None or previous_time is not None and time <= previous_time:
            issues.append(issue("video_generation_confirmation_time_invalid", "历史确认必须按带时区实际时间递增"))
        if time is not None:
            previous_time = time
        if rec.get("interaction_ask_result") != "generate" or not rec.get("interaction_ask_call_id") or not str(rec.get("user_message") or "").strip():
            issues.append(issue("video_generation_interaction_confirmation_missing", "执行确认需真实 AskUserQuestion generate 和用户原文"))
        if (rec.get("decision") != "confirmed" or rec.get("confirmation_purpose") != "video_generation"
                or rec.get("stage") != "video"):
            issues.append(issue("video_generation_interaction_confirmation_missing", "执行确认需明确 confirmed / video_generation"))
        snapshot = rec.get("request_snapshot")
        frozen = snapshot.get("segments") if isinstance(snapshot, dict) else None
        if (not isinstance(frozen, list) or not 1 <= len(frozen) <= 2
                or any(not isinstance(seg, dict) for seg in frozen)):
            issues.append(issue("video_generation_snapshot_invalid", "每次确认需冻结本批连续 1-2 段请求"))
            continue
        try:
            snapshot_sha = canonical_sha(snapshot)
        except (ValueError, TypeError):
            issues.append(issue("video_generation_snapshot_invalid", "冻结快照必须是有限数值组成的合法 JSON"))
            continue
        if rec.get("request_snapshot_sha256") != snapshot_sha:
            issues.append(issue("video_generation_snapshot_mismatch", "历史确认快照 SHA 不符，不能用当前 SEG 覆盖历史"))
        segment_ids = [seg.get("segment_id") for seg in frozen]
        if (any(not isinstance(sid, str) or not sid.strip() for sid in segment_ids)
                or len(set(segment_ids)) != len(segment_ids)):
            issues.append(issue("video_generation_snapshot_invalid", "冻结请求的 SEG ID 必须非空且唯一"))
        bindings = rec.get("authorization_bindings")
        if (type(rec.get("authorization_version")) is not int or rec.get("authorization_version") != 2 or not isinstance(bindings, list)
                    or len(bindings) != len(frozen) or any(not isinstance(item, dict) for item in bindings)
                    or [item.get("segment_id") for item in bindings] != segment_ids
                    or any(not isinstance(item.get("h3_prompt_file"), str)
                           or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("h3_prompt_sha256", "")))
                           or not isinstance(item.get("inputs"), list) for item in bindings)):
            issues.append(issue("video_authorization_binding_invalid", "生成确认需 authorization_version=2 及逐 SEG Prompt 和输入指纹"))
        indexes = [seg.get("episode_segment_index") for seg in frozen]
        if any(type(index) is not int or index < 1 for index in indexes) or indexes != list(range(indexes[0], indexes[0] + len(indexes))):
            issues.append(issue("video_generation_confirmation_range_invalid", "冻结请求索引必须连续整数"))
            continue
        if rec.get("batch_start_segment_index") != indexes[0] or rec.get("batch_end_segment_index") != indexes[-1] or rec.get("planned_video_count") != len(frozen):
            issues.append(issue("video_generation_count_mismatch", "批次范围/数量不符冻结请求"))
        supersedes = rec.get("supersedes_confirmation_ids", [])
        prior_ids = {active[index]["confirmation_id"] for index in indexes if index in active}
        if (not isinstance(supersedes, list) or any(not isinstance(value, str) for value in supersedes)
                or set(supersedes) != prior_ids):
            issues.append(issue("video_generation_confirmation_overlap", "重新确认需显式替代覆盖各 SEG 的最新有效确认，历史保留"))
        attempt = rec.get("attempt")
        prior_attempt = max((active[index].get("attempt", 0) for index in indexes if index in active), default=0)
        if type(attempt) is not int or attempt <= prior_attempt:
            issues.append(issue("video_generation_confirmation_attempt_invalid", "实际生成尝试需递增"))
        durations = []
        for seg in frozen:
            request = seg.get("request_snapshot")
            try:
                ms = to_ms(seg.get("duration_s"), positive=True)
                if ms % 1000 or not isinstance(request, dict) or request.get("duration_s") != seg["duration_s"]:
                    raise ValueError("请求时长不符")
                durations.append(ms)
            except ValueError:
                issues.append(issue("video_generation_snapshot_invalid", "快照每段需整数请求时长和对应实际参数"))
        expected_durations = [{"segment_id": seg.get("segment_id"), "duration_s": seg.get("duration_s")} for seg in frozen]
        if rec.get("segment_durations") != expected_durations or rec.get("duration_s") != sum(durations) / 1000:
            issues.append(issue("video_generation_segment_duration_mismatch", "历史确认时长按各自冻结请求核验"))
        table = rec.get("displayed_parameter_table")
        if not isinstance(table, dict):
            issues.append(issue("video_generation_parameter_table_missing", "需保存实际展示参数"))
            table = {}
        for field in ("task_type", "delivery_format", "total_duration", "aspect_ratio_and_resolution", "model", "visual_and_continuity", "audio_and_subtitles", "reference_materials"):
            if not str(table.get(field) or "").strip():
                issues.append(issue("video_generation_parameter_table_field_missing", f"展示参数缺 {field}"))
        if table.get("quantity") != len(frozen):
            issues.append(issue("video_generation_displayed_quantity_mismatch", "展示数量不符冻结请求"))
        display = str(rec.get("final_parameters_text") or "")
        for seg in frozen:
            duration = seg.get("duration_s")
            if (str(seg.get("segment_id")) not in display or not re.search(rf"(?<![\d.]){re.escape(str(duration))}\s*(?:秒|s\b)", display)):
                issues.append(issue("video_generation_segment_details_not_displayed", "确认文本需展示每段冻结请求长度"))
        rows = rec.get("displayed_storyboard_rows")
        if not isinstance(rows, list) or not rows or len(rows) > len(frozen):
            issues.append(issue("video_generation_storyboard_rows_invalid", "需保存实际五列预览"))
        elif any(not isinstance(row, dict) for row in rows):
            issues.append(issue("video_generation_storyboard_rows_invalid", "预览行必须是对象"))
        else:
            if len(rows) != len(frozen) or any(row.get("segment_id") != seg.get("segment_id") or row.get("duration_s") != seg.get("duration_s") for row, seg in zip(rows, frozen)):
                issues.append(issue("video_generation_storyboard_segment_mismatch", "历史五列表按冻结请求核验"))
            for row in rows:
                for field in ("visual_content", "subject_action", "audio", "camera_and_materials"):
                    if not isinstance(row.get(field), str) or not row[field].strip() or row[field] not in display:
                        issues.append(issue("video_generation_storyboard_field_missing", f"预览缺实际 {field}"))
        if len(issues) == issue_start and rec.get("valid", True) is not False:
            for index in indexes:
                active[index] = rec
    for index, seg in by_index.items():
        rec = active.get(index)
        generated = check_outputs and (bool(seg.get("output_file")) or seg.get("status") in {"candidate", "accepted"})
        if rec is None:
            if generated:
                issues.append(issue("video_generation_confirmation_missing", f"{seg.get('segment_id')} 缺有效生成确认"))
            continue
        frozen = next(row for row in rec["request_snapshot"]["segments"] if row["episode_segment_index"] == index)
        if request_segment_snapshot(seg) != frozen:
            issues.append(issue("video_generation_current_snapshot_mismatch", f"{seg.get('segment_id')} 只与覆盖它的最新有效确认比较；参数变更须重新确认"))
        bindings = rec["authorization_bindings"]
        expected = next(item for item in bindings if item["segment_id"] == seg["segment_id"])
        if root is not None:
            try:
                if authorization_binding(root, seg) != expected:
                    issues.append(issue("video_authorization_binding_mismatch", f"{seg.get('segment_id')} 的 Prompt 或本地输入已变化，须重新确认"))
            except ConfirmationError as exc:
                issues.append(issue(exc.code, str(exc)))
        if generated:
            if seg.get("generation_confirmation_id") != rec.get("confirmation_id"):
                issues.append(issue("video_generation_confirmation_not_latest", "生成结果须引用最新有效确认"))
            called = _time(seg.get("tool_called_at"))
            confirmed = _time(rec.get("confirmed_at"))
            if not seg.get("tool_call_id") or not called or not confirmed or called <= confirmed:
                issues.append(issue("video_confirmation_after_tool_call", "工具事实和时间需在确认之后"))
    return (issues, active) if return_active else issues
