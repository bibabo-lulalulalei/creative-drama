"""Accepted segment ordering, continuity reports and final adopted delivery."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any
from content_first import read_json
from .common import (
    check_duration_pair, episode_dirs, file_exists, file_inside, issue, load_json, parse_iso_time,
    relative_file,
)
from .constants import IMAGE_INPUT_SUFFIXES
from .planning import duration_contract_bounds
from .state import load_confirmation_records
from .video import check_quality_acceptance


def accepted_video_segment_order(
    root: Path,
    episode_id: str,
    issues: list[dict[str, Any]],
    allow_candidate: bool = False,
) -> list[str]:
    path = root / f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json"
    data = load_json(path, issues, required=False)
    segments = data.get("segments") if isinstance(data, dict) else None
    if not isinstance(segments, list):
        return []
    return [
        item["segment_id"]
        for item in segments
        if isinstance(item, dict)
        and isinstance(item.get("segment_id"), str)
        and item.get("status") in ({"candidate", "accepted"} if allow_candidate else {"accepted"})
    ]


def delivery_segment_refs(data: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    direct_fields = ("source_segments", "segment_ids", "used_segments", "video_segments", "accepted_segments")
    for field in direct_fields:
        value = data.get(field)
        if isinstance(value, list):
            refs.update(item for item in value if isinstance(item, str))
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("segment_id"), str):
                    refs.add(item["segment_id"])
    for field in ("segments", "segment_outputs", "outputs"):
        value = data.get(field)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("segment_id"), str):
                    refs.add(item["segment_id"])
    return refs


def output_values(data: dict[str, Any]) -> list[str] | None:
    outputs = data.get("outputs")
    if not isinstance(outputs, list):
        return None
    values: list[str] = []
    for item in outputs:
        if isinstance(item, str):
            values.append(item)
        elif isinstance(item, dict) and isinstance(item.get("file"), str):
            values.append(item["file"])
        else:
            return None
    return values


def report_is_blocked(root: Path, entry: Any) -> bool:
    if isinstance(entry, dict):
        return entry.get("status") == "blocked" or entry.get("result") == "blocked"
    target = relative_file(root, entry)
    if target is None or not target.is_file() or target.suffix.lower() != ".json":
        return False
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and (data.get("status") == "blocked" or data.get("result") == "blocked")


def check_report_entries(root: Path, entries: Any, expected_count: int, path: Path, issues: list[dict[str, Any]]) -> None:
    if not isinstance(entries, list):
        issues.append(issue("error", "basic_qc_reports_invalid", "basic_qc_reports 必须是数组。", path))
        return
    if len(entries) != expected_count:
        issues.append(issue("error", "basic_qc_reports_count_invalid", f"basic_qc_reports 数量应为 {expected_count}。", path))
    for entry in entries:
        if isinstance(entry, str):
            if not file_exists(root, entry):
                issues.append(issue("error", "basic_qc_report_missing", f"基础质检报告不存在：{entry}", path))
        elif isinstance(entry, dict):
            report_file = entry.get("file")
            if report_file and not file_exists(root, report_file):
                issues.append(issue("error", "basic_qc_report_missing", f"基础质检报告不存在：{report_file}", path))
        else:
            issues.append(issue("error", "basic_qc_report_invalid", "basic_qc_reports 每项必须是路径或对象。", path))
        if report_is_blocked(root, entry):
            issues.append(issue("error", "basic_qc_report_blocked", "基础媒体可用性检查结果为 blocked，不得交付。", path))


def check_continuity_for_delivery(root: Path, episode_id: str, accepted_order: list[str], issues: list[dict[str, Any]]) -> None:
    path = root / f"episodes/{episode_id}/04_视频片段/continuity_{episode_id}.json"
    data = load_json(path, issues, required=bool(accepted_order))
    if not isinstance(data, dict):
        return
    if data.get("episode_id") != episode_id:
        issues.append(issue("error", "episode_id_mismatch", "continuity episode_id 与目录不一致。", path))
    video_manifest = load_json(root / f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json", issues, required=False)
    frames = data.get("frames")
    if not isinstance(frames, list):
        issues.append(issue("error", "continuity_frames_invalid", "continuity.frames 必须是数组。", path))
        frames = []
    roles_by_segment: dict[str, set[str]] = {}
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        segment_id = frame.get("segment_id")
        role = frame.get("role")
        if isinstance(segment_id, str) and isinstance(role, str):
            roles_by_segment.setdefault(segment_id, set()).add(role)
        file_value = frame.get("file")
        if file_value and not file_exists(root, file_value):
            issues.append(issue("error", "continuity_frame_file_missing", f"连续性抽帧文件不存在：{file_value}", path))
        if isinstance(file_value, str) and Path(file_value).suffix.lower() not in IMAGE_INPUT_SUFFIXES:
            issues.append(issue("error", "continuity_frame_suffix_invalid", f"连续性抽帧必须是图片文件：{file_value}", path))
    for segment_id in accepted_order:
        roles = roles_by_segment.get(segment_id, set())
        missing = sorted({"start", "scene", "tail"} - roles)
        if missing:
            issues.append(issue("error", "continuity_frame_roles_missing", f"{segment_id} 连续性抽帧缺少 start|scene|tail：{missing}。", path))
    seams = data.get("seams")
    if not isinstance(seams, list):
        issues.append(issue("error", "continuity_seams_invalid", "continuity.seams 必须是数组。", path))
        seams = []
    seams_by_pair = {
        (item.get("from_segment"), item.get("to_segment")): item
        for item in seams
        if isinstance(item, dict)
    }
    for left, right in zip(accepted_order, accepted_order[1:]):
        seam = seams_by_pair.get((left, right))
        if not isinstance(seam, dict):
            issues.append(issue("error", "continuity_seam_missing", f"缺少 {left} -> {right} 的 seam 记录。", path))
            continue
        if seam.get("status") != "verified":
            issues.append(issue("error", "continuity_seam_not_verified", f"{left} -> {right} seam 必须通过检查后才能作为合格成片接缝。", path))
        segments = video_manifest.get("segments", []) if isinstance(video_manifest, dict) else []
        successor = next((row for row in segments if row.get("segment_id") == right), {})
        if successor.get("seam_type") == "continuous" or successor.get("inbound"):
            try:
                from adopted_cut import validate_inbound
                inbound = successor["inbound"]
                if (seam.get("adopted_cut_out_file") != inbound["cut_file"] or seam.get("cut_id") != inbound["cut_id"]):
                    raise ValueError("continuity 与后段不是同一采用出点")
                gen = read_json(root / successor["gen_file"])
                validate_inbound(root, inbound["cut_file"], inbound["cut_id"], gen["inputs"])
            except (OSError, ValueError, KeyError, TypeError) as exc:
                issues.append(issue("error", "adopted_cut_out_invalid", str(exc), path))
        if not isinstance(seam.get("selected_cut"), dict) or not seam.get("selected_cut"):
            issues.append(issue("error", "continuity_seam_cut_missing", f"{left} -> {right} 关键接缝缺少 selected_cut。", path))
        for field in ("outgoing_window_frames", "incoming_window_frames"):
            value = seam.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 12:
                issues.append(issue("error", "continuity_seam_window_invalid", f"{left} -> {right} {field} 必须至少覆盖 12 帧，才能验证并选定安全剪切点。", path))


def check_delivery(
    root: Path,
    plan: Any,
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
) -> None:
    measured_durations: dict[str, float] = {}
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"05_成片/delivery_manifest_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", "delivery_manifest episode_id 与目录不一致。", path))
        assembly_confirmation = data.get("assembly_confirmation")
        if not isinstance(assembly_confirmation, dict):
            issues.append(issue("error", "assembly_confirmation_missing", "delivery_manifest 必须登记进入成片拼接的 interaction.ask 确认。", path))
            assembly_confirmation = {}
        if assembly_confirmation.get("confirmation_purpose") != "final_assembly":
            issues.append(issue("error", "assembly_confirmation_purpose_invalid", "assembly_confirmation.confirmation_purpose 必须为 final_assembly。", path))
        if not str(assembly_confirmation.get("interaction_ask_call_id") or "").strip():
            issues.append(issue("error", "assembly_confirmation_call_id_missing", "assembly_confirmation 必须记录 interaction_ask_call_id。", path))
        if assembly_confirmation.get("interaction_ask_result") != "proceed_assembly":
            issues.append(issue("error", "assembly_confirmation_result_invalid", "assembly_confirmation.interaction_ask_result 必须为 proceed_assembly。", path))
        if not str(assembly_confirmation.get("user_message") or "").strip():
            issues.append(issue("error", "assembly_confirmation_user_message_missing", "assembly_confirmation.user_message 不能为空。", path))
        if parse_iso_time(assembly_confirmation.get("confirmed_at")) is None:
            issues.append(issue("error", "assembly_confirmation_time_invalid", "assembly_confirmation.confirmed_at 必须是带时区 ISO-8601 时间。", path))
        confirmation_records = load_confirmation_records(root, issues, required=True)
        matching_video_confirmations = [
            record
            for record in confirmation_records
            if record.get("stage") == "video"
            and record.get("episode_id") == episode_id
            and record.get("confirmation_purpose") == "video_acceptance_and_final_assembly"
            and record.get("interaction_ask_call_id") == assembly_confirmation.get("interaction_ask_call_id")
            and record.get("interaction_ask_result") == "proceed_assembly"
        ]
        if not matching_video_confirmations:
            issues.append(issue("error", "assembly_confirmation_video_record_missing", "assembly_confirmation 必须与同集 stage=video 用户确认记录使用同一 interaction.ask 调用 ID 和 proceed_assembly 结果。", path))
        subtitle_enabled = data.get("subtitle_enabled")
        if not isinstance(subtitle_enabled, bool):
            issues.append(issue("error", "subtitle_enabled_invalid", "subtitle_enabled 必须是布尔值；默认 false，用户明确要求字幕时为 true。", path))
        if data.get("status") not in {"deliverable", "candidate"}:
            issues.append(issue("error", "delivery_status_not_deliverable", "delivery_manifest.status 必须为 deliverable 或 candidate；blocked 不得交付。", path))
        gate = data.get("content_quality_gate")
        if not isinstance(gate, dict) or gate.get("status") not in {"pass", "blocked", "deviation_accepted"}:
            issues.append(issue("error", "delivery_quality_gate_invalid", "delivery_manifest 必须记录 content_quality_gate。", path))
        else:
            blockers = gate.get("blockers", [])
            if not isinstance(blockers, list):
                issues.append(issue("error", "delivery_quality_gate_blockers_invalid", "content_quality_gate.blockers 必须是数组。", path))
                blockers = ["invalid"]
            if data.get("status") == "deliverable" and (gate.get("status") not in {"pass", "deviation_accepted"} or blockers):
                issues.append(issue("error", "delivery_without_quality_pass", "deliverable 必须通过整片内容质量门且无阻断项。", path))
            if gate.get("status") == "deviation_accepted":
                check_quality_acceptance(root, gate, episode_id, None, data.get("subtitle_master") if data.get("subtitle_enabled") else data.get("clean_master"), path, issues)
        duration = data.get("duration_s")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool) and math.isfinite(duration) and duration > 0:
            measured_durations[episode_id] = float(duration)
            check_duration_pair(duration, data.get("duration_display"), path, "delivery", issues)
        else:
            issues.append(issue("error", "delivery_duration_invalid", "delivery_manifest.duration_s 必须是数字。", path))
        if not file_inside(root, data.get("clean_master"), episode_root):
            issues.append(issue("error", "clean_master_missing", "clean_master 必须指向当前分集目录下真实媒体文件。", path))
        if subtitle_enabled is True and not file_inside(root, data.get("subtitle_master"), episode_root):
            issues.append(issue("error", "subtitle_master_missing", "字幕开启时 subtitle_master 必须指向当前分集目录下真实媒体文件。", path))
        if subtitle_enabled is False:
            for field in ("subtitle_master", "asr_source", "subtitle_final", "subtitle_source", "subtitle_burn_params", "subtitle_alignment_report"):
                if str(data.get(field) or "").strip():
                    issues.append(issue("error", "subtitle_disabled_field_not_empty", f"字幕关闭时 {field} 必须留空。", path))
        outputs = output_values(data)
        if outputs is None:
            issues.append(issue("error", "outputs_invalid", "outputs 必须是路径数组，或每项包含 file。", path))
        elif subtitle_enabled is False and outputs != [data.get("clean_master")]:
            issues.append(issue("error", "outputs_mismatch", "outputs 必须与用户可见正式交付文件精确一致：字幕关闭时只交付 [clean_master]。", path))
        elif subtitle_enabled is True and outputs != [data.get("subtitle_master")]:
            issues.append(issue("error", "outputs_mismatch", "outputs 必须与用户可见正式交付文件精确一致：字幕开启时只交付 [subtitle_master]。", path))
        reports = data.get("basic_qc_reports")
        if reports not in (None, []):
            if isinstance(reports, list):
                check_report_entries(root, reports, len(reports), path, issues)
            else:
                issues.append(issue("error", "basic_qc_reports_invalid", "basic_qc_reports 必须是数组。", path))
        if subtitle_enabled is True:
            subtitle_alignment_report = data.get("subtitle_alignment_report")
            if not str(subtitle_alignment_report or "").strip():
                issues.append(issue("error", "subtitle_alignment_report_missing", "字幕开启时必须存在 subtitle_alignment_report（字幕对齐报告）。", path))
            elif not file_inside(root, subtitle_alignment_report, episode_root) or report_is_blocked(root, subtitle_alignment_report):
                issues.append(issue("error", "subtitle_alignment_report_invalid", "subtitle_alignment_report 必须指向当前分集目录下未 blocked 的内部追溯文件。", path))
            subtitle_source = data.get("subtitle_source")
            if not file_inside(root, subtitle_source, episode_root):
                issues.append(issue("error", "subtitle_source_missing", "字幕开启时必须存在当前分集目录下的 subtitle_source。", path))
            elif isinstance(subtitle_source, str) and not re.search(r"字幕_时间轴_v\d+_ep_[1-9]\d*\.srt$", subtitle_source):
                issues.append(issue("error", "subtitle_source_name_invalid", "subtitle_source 应指向 字幕_时间轴_vNN_ep_N.srt。", path))
            subtitle_final = data.get("subtitle_final")
            if not file_inside(root, subtitle_final, episode_root):
                issues.append(issue("error", "subtitle_final_missing", "字幕开启时必须存在当前分集目录下的 subtitle_final。", path))
            elif isinstance(subtitle_final, str) and not re.search(r"字幕_最终版_v\d+_ep_[1-9]\d*\.json$", subtitle_final):
                issues.append(issue("error", "subtitle_final_name_invalid", "subtitle_final 应指向 字幕_最终版_vNN_ep_N.json。", path))
        accepted_order = accepted_video_segment_order(root, episode_id, issues)
        accepted = set(accepted_order)
        if assembly_confirmation.get("segment_ids") != accepted_order:
            issues.append(issue("error", "assembly_confirmation_segments_mismatch", "assembly_confirmation.segment_ids 必须按顺序精确等于当前成片采用的 accepted SEG。", path))
        for segment_id in sorted(delivery_segment_refs(data)):
            if segment_id not in accepted:
                issues.append(issue("error", "delivery_non_accepted_segment", f"delivery 使用了未验收（accepted）的视频片段：{segment_id}", path))
        check_continuity_for_delivery(root, episode_id, accepted_order, issues)
        check_adopted_delivery(root, episode_id, data, issues)
    contract = plan.get("duration_contract") if isinstance(plan, dict) else None
    if isinstance(contract, dict):
        mode = contract.get("mode")
        scope = contract.get("scope")
        measured = list(measured_durations.values())
        try:
            bounds = duration_contract_bounds(contract)
        except ValueError as exc:
            issues.append(issue("error", "duration_contract_invalid", str(exc), root / "00_制作控制/drama_plan.json"))
            bounds = None
        if bounds is not None and measured:
            if scope == "episode":
                values = [(episode_id, value) for episode_id, value in measured_durations.items()]
            elif episode_filter is None:
                values = [("全项目" if scope == "project" else "交付物", sum(measured))]
            else:
                values = []
            lower, upper = bounds
            for label, value in values:
                if value < lower - 1e-6 or value > upper + 1e-6:
                    issues.append(issue("error", "delivery_duration_out_of_contract", f"{label} 实测 {value:g}s 不在 duration_contract {mode} 范围 [{lower:g}, {upper:g}]s；不得以计划时长代替实测。", root / "00_制作控制/drama_plan.json"))


def check_adopted_delivery(root, episode_id, delivery, issues):
    """Final trim must consume precisely the cut that supplied each continuous successor."""
    from adopted_cut import trim_args
    path = root / f"episodes/{episode_id}/05_成片/delivery_manifest_{episode_id}.json"
    video = load_json(root / f"episodes/{episode_id}/04_视频片段/video_manifest_{episode_id}.json", issues, required=True)
    if not isinstance(video, dict):
        return
    adopted = delivery.get("adopted_segments", [])
    if not isinstance(adopted, list) or any(not isinstance(row, dict) for row in adopted):
        issues.append(issue("error", "adopted_cut_out_invalid", "adopted_segments 必须是实际采用区间数组", path))
        return
    for successor in video.get("segments", []):
        inbound = successor.get("inbound")
        if not inbound:
            continue
        try:
            cut = read_json(root / inbound["cut_file"])
            rows = [row for row in adopted if row.get("source_video_file") == cut["source_video_file"]]
            if len(rows) != 1 or rows[0].get("cut_file") != inbound["cut_file"] or rows[0].get("cut_id") != inbound["cut_id"]:
                raise ValueError("最终采用记录缺失或不对应后段实际入站出点")
            row = rows[0]
            trim_args(root, row["cut_file"], row["cut_id"], row["source_video_file"], row["start_s"], row["end_s"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            issues.append(issue("error", "adopted_cut_out_invalid", str(exc), path))
