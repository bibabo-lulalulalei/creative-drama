"""Video manifests, generation confirmations and quality acceptance."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from timeline_core import to_ms
from h3_contract import ContractError, is_url
from .common import (
    check_unique, episode_dirs, file_exists, file_sha256, issue,
    load_json, relative_file,
)
from .constants import (
    AUDIO_INPUT_ROLES, REFERENCE_ROLES, STATE_REFERENCE_ROLES, VIDEO_INPUT_ROLES,
    VIDEO_STATUS_VALUES, VIDEO_TOOL_MODES,
)
from .prompts import (
    _check_h3_prompt_purity, check_asset_ref, check_h3_prompt, check_prompt_markers,
    check_prompt_preflight, check_state_ref, check_video_generation_confirmations,
    check_video_state_refs, check_voice_anchor_consistency, check_voice_audio_inputs,
    load_keyframe_ids, ordered_inputs,
)
from .state import load_confirmation_records
from .storyboard import load_storyboard_index


def check_video(
    root: Path,
    asset_index: dict[str, Any],
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
    require_accepted: bool = True,
) -> None:
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"04_视频片段/video_manifest_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", "video_manifest episode_id 与目录不一致。", path))
        index = load_storyboard_index(root, episode_id, issues)
        keyframe_ids = load_keyframe_ids(root, episode_id, issues)
        segments = data.get("segments")
        if not isinstance(segments, list):
            issues.append(issue("error", "video_segments_invalid", "video_manifest.segments 必须是数组。", path))
            continue
        check_video_generation_confirmations(data, segments, path, issues)
        video_segment_ids = check_unique(segments, "segment_id", path, issues, "video segments")
        if index["segments"]:
            missing_segments = sorted(index["segments"] - video_segment_ids)
            extra_segments = sorted(video_segment_ids - index["segments"])
            if missing_segments:
                issues.append(issue("error", "video_segment_missing", f"video_manifest 缺少 storyboard segment：{missing_segments}", path))
            if extra_segments:
                issues.append(issue("error", "video_segment_unplanned", f"video_manifest 含 storyboard 中不存在的 segment：{extra_segments}", path))
        try:
            calculated = sum(to_ms(seg.get("duration_s"), positive=True) for seg in segments if isinstance(seg, dict))
            if to_ms(data.get("duration_s"), positive=True) != calculated:
                issues.append(issue("error", "video_duration_mismatch", "video 总长需等于各整数请求时长之和。", path))
        except ValueError as exc:
            issues.append(issue("error", "video_duration_invalid", str(exc), path))
        seen_voice_anchors: dict[str, str] = {}
        for segment in segments:
            if not isinstance(segment, dict):
                issues.append(issue("error", "video_segment_invalid", "segments 每项必须是对象。", path))
                continue
            segment_id = segment.get("segment_id")
            if isinstance(segment_id, str) and index["segments"] and segment_id not in index["segments"]:
                issues.append(issue("error", "video_unknown_segment", f"视频引用了分镜中不存在的 segment_id：{segment_id}", path))
            storyboard_duration = index.get("segment_request_durations", {}).get(segment_id)
            if storyboard_duration is not None and isinstance(segment.get("duration_s"), (int, float)):
                try:
                    if to_ms(segment["duration_s"]) != to_ms(storyboard_duration):
                        issues.append(issue("error", "video_segment_duration_mismatch", f"{segment_id} 请求时长必须与分镜 request_duration_s 一致。", path))
                except ValueError as exc:
                    issues.append(issue("error", "video_duration_invalid", str(exc), path))
            tool_mode = segment.get("tool_mode")
            image_orders, image_roles = ordered_inputs(root, segment.get("reference_inputs"), REFERENCE_ROLES, "reference", path, issues)
            video_orders, video_roles = ordered_inputs(root, segment.get("video_inputs"), VIDEO_INPUT_ROLES, "video", path, issues)
            audio_orders, audio_roles = ordered_inputs(root, segment.get("audio_inputs"), AUDIO_INPUT_ROLES, "audio", path, issues)
            required_roles = segment.get("required_reference_roles")
            if tool_mode not in VIDEO_TOOL_MODES:
                issues.append(issue("error", "video_tool_mode_invalid", f"{segment_id or 'segment'} tool_mode 无效：{tool_mode}", path))
            else:
                check_voice_anchor_consistency(segment, seen_voice_anchors, path, issues)
            # Mode selection belongs to h3-prompt-writing; check inherited production facts here.
            check_voice_audio_inputs(segment, audio_roles, path, issues)
            check_video_state_refs(segment, image_roles, asset_index, path, issues)
            planned_roles = index["required_reference_roles"].get(segment_id, set()) if isinstance(segment_id, str) else set()
            declared_roles = set(required_roles) if isinstance(required_roles, list) else set()
            if image_orders or planned_roles:
                if not isinstance(required_roles, list) or not required_roles:
                    issues.append(issue("error", "required_reference_roles_missing", f"{segment_id} 使用图片或分镜声明图片职责时必须填写 required_reference_roles。", path))
                elif any(role not in REFERENCE_ROLES for role in required_roles):
                    issues.append(issue("error", "required_reference_role_invalid", "required_reference_roles 含无效职责。", path))
                elif not declared_roles.issubset(image_roles):
                    missing = sorted(declared_roles - image_roles)
                    issues.append(issue("error", "required_reference_role_not_passed", f"required_reference_roles 未真实传入：{missing}", path))
            elif required_roles not in (None, []):
                issues.append(issue("error", "required_reference_roles_unexpected", "没有图片输入时 required_reference_roles 应为空或省略。", path))
            if not planned_roles.issubset(declared_roles):
                missing = sorted(planned_roles - declared_roles)
                issues.append(issue("error", "storyboard_required_role_not_inherited", f"{segment_id} 未继承 storyboard.required_reference_roles：{missing}", path))
            if not planned_roles.issubset(image_roles):
                missing = sorted(planned_roles - image_roles)
                issues.append(issue("error", "storyboard_required_role_not_passed", f"{segment_id} 的 storyboard.required_reference_roles 未真实传入：{missing}", path))
            if tool_mode == "video_edit":
                if video_roles != {"source_video_for_edit"} or len(video_orders) != 1:
                    issues.append(issue("error", "video_edit_source_invalid", "video_edit 必须且只能登记一个 source_video_for_edit 源视频。", path))
            for input_item in segment.get("reference_inputs") or []:
                if not isinstance(input_item, dict):
                    continue
                source_type = input_item.get("source_type")
                source_id = input_item.get("source_id")
                role = input_item.get("role")
                if role == "previous_tail_as_start_frame" and source_type != "frame":
                    issues.append(issue("error", "previous_tail_source_type_invalid", f"{segment_id} 上一段尾帧必须以 source_type=frame 真实传入。", path))
                if source_type == "asset":
                    if role in STATE_REFERENCE_ROLES:
                        check_state_ref(source_id, asset_index, path, issues, f"{segment_id or '视频片段'} reference_inputs")
                    else:
                        check_asset_ref(source_id, asset_index, path, issues, f"{segment_id or '视频片段'} reference_inputs")
                if source_type == "keyframe" and isinstance(source_id, str) and source_id not in keyframe_ids:
                    issues.append(issue("error", "video_reference_unknown_keyframe", f"{segment_id} 引用了不存在的关键帧：{source_id}", path))
            # 声线参考只能走 audio_inputs（reference_inputs 被 ordered_inputs 限定为图片），
            # 在此对真正可达的槽位执行已批准 VOICE 样音路径策略。
            check_voice_sample_paths(segment, asset_index, path, issues)
            # 提交给模型的是 H3 成稿(h3_prompt_file)；compiled_prompt_file 现指向
            # 五段交付包文件(skill 输入与返修凭证)。标记/哈希/存在性检查一律查成稿。
            prompt_file = segment.get("h3_prompt_file")
            prompt_path = relative_file(root, prompt_file)
            package_file = segment.get("compiled_prompt_file")
            package_path = relative_file(root, package_file)
            if package_path is not None and package_file and not package_path.is_file():
                issues.append(issue("error", "delivery_package_file_missing", f"{segment_id} 登记了 compiled_prompt_file（五段交付包），但文件不存在。", path))
            if package_path is not None and package_path.is_file() and file_sha256(package_path) != segment.get("prompt_sha256"):
                issues.append(issue("error", "director_package_sha256_mismatch", "导演包 SHA 与实际文件不同。", path))
            expected_shot_ids = index["segment_shots"].get(segment_id, []) if isinstance(segment_id, str) else []
            check_prompt_preflight(segment, expected_shot_ids, path, issues)
            check_h3_prompt(segment, root, path, issues)
            try:
                from preflight_video import prepare_full, validate_manifest_inputs
                current = prepare_full(root, episode_id, segment_id)[2]
                validate_manifest_inputs(segment, current.gen)
                if current.contract["binding_id"] != segment.get("binding_id") or current.contract["request_snapshot"] != segment.get("request_snapshot"):
                    raise ContractError("preflight_binding_mismatch", "当前设计/请求不符 manifest 绑定")
            except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
                issues.append(issue("error", getattr(exc, "code", "preflight_binding_mismatch"), str(exc), path))
            if prompt_path is not None:
                check_prompt_markers(
                    prompt_path,
                    image_orders,
                    video_orders,
                    audio_orders,
                    segment.get("speech_lines"),
                    segment.get("subtitle_enabled") is True,
                    issues,
                    h3_mode=segment.get("h3_mode", segment.get("mode", "T2VA")),
                )
                _check_h3_prompt_purity(prompt_path, issues, segment.get("h3_mode", segment.get("mode", "T2VA")), segment.get("duration_s", 6))
                prompt_sha256 = str(segment.get("h3_prompt_sha256") or "").strip()
                if prompt_sha256:
                    try:
                        actual_sha256 = file_sha256(prompt_path)
                    except OSError as exc:
                        issues.append(issue("error", "prompt_sha256_unreadable", f"无法读取 Prompt 计算 sha256：{exc}", prompt_path))
                    else:
                        if actual_sha256 != prompt_sha256:
                            issues.append(issue("error", "prompt_sha256_mismatch", f"{segment_id} prompt_sha256 与实际 Prompt 文件不一致。", prompt_path))
            elif prompt_file:
                issues.append(issue("error", "prompt_path_invalid", "compiled_prompt_file 必须是项目相对路径。", path))
            generated_segment = bool(str(segment.get("output_file") or "").strip()) or segment.get("status") in {"candidate", "accepted"}
            if generated_segment and (prompt_path is None or not prompt_path.is_file()):
                issues.append(issue("error", "generated_segment_prompt_missing", f"{segment_id} 已生成或进入候选/验收状态，必须登记真实存在的 H3 成稿文件。", path))
            if generated_segment and not str(segment.get("h3_prompt_sha256") or "").strip():
                issues.append(issue("error", "generated_segment_prompt_sha256_missing", f"{segment_id} 已生成或进入候选/验收状态，必须登记实际提交 Prompt 文件的 prompt_sha256。", path))
            status = segment.get("status")
            if status not in {None, *VIDEO_STATUS_VALUES}:
                issues.append(issue("error", "video_status_invalid", f"视频片段状态无效：{status}", path))
            elif require_accepted and status != "accepted":
                issues.append(issue("error", "video_segment_not_accepted", f"{segment_id or '视频片段'} 必须在进入成片阶段前登记 status=accepted。", path))
            elif not require_accepted and generated_segment and status not in {"candidate", "accepted"}:
                issues.append(issue("error", "video_segment_not_ready_for_confirmation", f"{segment_id or '视频片段'} 在发起拼接确认前必须登记 status=candidate 或 accepted。", path))
            if status == "candidate" and not file_exists(root, segment.get("output_file")):
                issues.append(issue("error", "video_segment_output_missing", f"{segment_id} 已进入候选状态，但 output_file 不存在。", path))
            if status == "accepted":
                if not file_exists(root, segment.get("output_file")):
                    issues.append(issue("error", "accepted_segment_output_missing", f"{segment_id} 已 accepted，但 output_file 不存在。", path))
                if prompt_path is None or not prompt_path.is_file():
                    issues.append(issue("error", "accepted_segment_prompt_missing", f"{segment_id} 已 accepted，但 H3 成稿文件不存在。", path))
            gate = segment.get("quality_gate")
            if not isinstance(gate, dict) or gate.get("status") not in {"pending", "pass", "blocked", "deviation_accepted"}:
                issues.append(issue("error", "video_quality_gate_invalid", f"{segment_id} 必须记录 quality_gate 状态。", path))
            else:
                blockers = gate.get("blockers", [])
                if not isinstance(blockers, list):
                    issues.append(issue("error", "video_quality_gate_blockers_invalid", f"{segment_id}.quality_gate.blockers 必须是数组。", path))
                    blockers = ["invalid"]
                if gate.get("status") in {"pass", "deviation_accepted"} and blockers:
                    issues.append(issue("error", "video_quality_gate_blocked_claim", f"{segment_id} 存在阻断项，不能标记 quality_gate=pass。", path))
                if status == "accepted" and gate.get("status") not in {"pass", "deviation_accepted"}:
                    issues.append(issue("error", "accepted_without_quality_gate", f"{segment_id} 只有通过质量门或用户接受明确偏差后才能 accepted。", path))
                if gate.get("status") == "deviation_accepted":
                    check_quality_acceptance(root, gate, episode_id, segment_id, segment.get("output_file"), path, issues)


def check_voice_sample_paths(segment: dict[str, Any], asset_index: dict[str, Any], path: Path, issues: list[dict[str, Any]]) -> None:
    """voice_audio_reference 槽位的可达路径策略：远端 URL 核资源登记，本地文件必须是已批准 VOICE 样音。"""
    segment_id = segment.get("segment_id")
    for audio_item in segment.get("audio_inputs") or []:
        if not isinstance(audio_item, dict) or audio_item.get("role") != "voice_audio_reference":
            continue
        audio_rel = str(audio_item.get("file") or "")
        if audio_rel and is_url(audio_rel):
            check_asset_ref(audio_item.get("resource_id"), asset_index, path, issues, f"{segment_id} 远端 VOICE 样音")
        elif audio_rel and "shared/03_资产/音色/" not in audio_rel.replace("\\", "/"):
            issues.append(issue(
                "error", "ref_audio_not_voice_sample",
                f"{segment_id} 的音频参考必须指向 shared/03_资产/音色/ 下已批准 VOICE 样音（路径：{audio_rel}）；禁止台词级 TTS 临时音频进入 ref_audio 槽位——正片台词由 H3 原生生成，参考只锁声线。",
                path,
            ))


def check_quality_acceptance(root, gate, episode_id, segment_id, output_file, path, issues):
    deviations = gate.get("deviations")
    output = relative_file(root, output_file)
    # 快照路径一律按项目内规范化相对 POSIX 路径比对：manifest 与确认记录由不同环节手写，
    # Windows 反斜杠/正斜杠差异不应让真实偏差接受永远过不了门；越界或无法解析的路径保持不归一化。
    resolved_root = root.resolve()
    canonical_output = output.relative_to(resolved_root).as_posix() if output is not None else None
    snapshot = {"episode_id": episode_id, "segment_id": segment_id, "output_file": canonical_output,
                "output_sha256": file_sha256(output) if output is not None and output.is_file() else None,
                "deviations": deviations}
    records = load_confirmation_records(root, issues, required=True)
    matching = [row for row in records if row.get("confirmation_id") == gate.get("user_acceptance_ref")]
    record_snapshot = None
    if len(matching) == 1 and isinstance(matching[0].get("quality_deviation_snapshot"), dict):
        record_snapshot = dict(matching[0]["quality_deviation_snapshot"])
        recorded_output = relative_file(root, record_snapshot.get("output_file"))
        if recorded_output is not None:
            record_snapshot["output_file"] = recorded_output.relative_to(resolved_root).as_posix()
    if (not isinstance(deviations, list) or not deviations or not snapshot["output_sha256"]
            or len(matching) != 1 or matching[0].get("decision") != "confirmed"
            or matching[0].get("valid", True) is False or not matching[0].get("user_message")
            or record_snapshot != snapshot):
        issues.append(issue("error", "quality_deviation_acceptance_missing", "偏差接受需回指同一结果文件/指纹、范围和明确偏差的真实确认，非空引用不能代替。", path))
