"""Media inputs, reference markers, prompt contracts and generation preflight."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from content_first import read_json
from video_confirmations import validate_confirmations
from h3_contract import prepare_request, check_purity, ContractError, is_url, media_marker_orders
from .assets import check_stale_asset_version
from .common import file_exists, file_sha256, issue, load_json, relative_file
from .constants import IMAGE_INPUT_SUFFIXES, STATE_REFERENCE_ROLES


def ordered_inputs(root: Path, items: Any, allowed_roles: set[str], kind: str, path: Path, issues: list[dict[str, Any]]) -> tuple[list[int], set[str]]:
    if items is None:
        return [], set()
    if not isinstance(items, list):
        issues.append(issue("error", f"{kind}_inputs_invalid", f"{kind}_inputs 必须是数组。", path))
        return [], set()
    orders: list[int] = []
    roles: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            issues.append(issue("error", f"{kind}_input_invalid", f"{kind}_inputs 每项必须是对象。", path))
            continue
        order = item.get("order")
        if isinstance(order, int) and not isinstance(order, bool):
            orders.append(order)
        else:
            issues.append(issue("error", f"{kind}_input_order_invalid", f"{kind}_inputs.order 必须是整数。", path))
        role = item.get("role")
        if role in allowed_roles:
            roles.add(role)
        elif allowed_roles:
            issues.append(issue("error", f"{kind}_input_role_invalid", f"{kind}_inputs.role 无效：{role}", path))
        required_fields = ("source_id", "file", "adopt", "exclude") if kind == "reference" else ("resource_id", "file", "adopt", "exclude")
        for field in required_fields:
            if not str(item.get(field) or "").strip():
                issues.append(issue("error", f"{kind}_input_field_missing", f"{kind}_inputs.{field} 必须填写。", path))
        file_value = item.get("file")
        remote = isinstance(file_value, str) and is_url(file_value)
        if file_value and not remote and not file_exists(root, file_value):
            issues.append(issue("error", f"{kind}_input_file_missing", f"输入文件不存在或不是项目相对路径：{file_value}", path))
        if kind == "reference" and isinstance(file_value, str) and not remote and Path(file_value).suffix.lower() not in IMAGE_INPUT_SUFFIXES:
            issues.append(issue("error", "reference_input_file_suffix_invalid", f"reference_inputs.file 必须是图片文件：{file_value}", path))
    if orders and sorted(orders) != list(range(1, len(orders) + 1)):
        issues.append(issue("error", f"{kind}_input_order_not_contiguous", f"{kind}_inputs.order 必须从 1 连续递增。", path))
    return orders, roles


def check_asset_ref(ref: Any, index: dict[str, Any], path: Path, issues: list[dict[str, Any]], owner: str) -> None:
    if not isinstance(ref, str) or not ref.strip():
        issues.append(issue("error", "asset_ref_invalid", f"{owner} 的 asset_refs 必须是非空字符串。", path))
        return
    if ref in index["known_asset_ids"]:
        issues.append(issue("error", "asset_ref_version_missing", f"{owner} 引用资产 {ref} 时必须带版本号。", path))
        return
    if ref not in index["known_version_refs"]:
        issues.append(issue("error", "asset_ref_unknown", f"{owner} 引用了不存在的资产版本：{ref}", path))
        return
    if ref not in index["approved_version_refs"]:
        issues.append(issue("error", "downstream_asset_not_approved", f"{owner} 引用了未 approved 的资产版本：{ref}", path))
        return
    check_stale_asset_version(ref, index, path, issues, owner)


def check_state_ref(ref: Any, index: dict[str, Any], path: Path, issues: list[dict[str, Any]], owner: str) -> None:
    if not isinstance(ref, str) or not ref.strip():
        issues.append(issue("error", "state_ref_invalid", f"{owner} 的 state_refs 必须是非空字符串。", path))
        return
    if ref not in index["known_state_refs"]:
        issues.append(issue("error", "state_ref_unknown", f"{owner} 引用了不存在的状态资产：{ref}", path))
        return
    if ref not in index["approved_state_refs"]:
        issues.append(issue("error", "downstream_state_not_approved", f"{owner} 引用了未 approved 的状态资产：{ref}", path))
        return
    check_stale_asset_version(ref, index, path, issues, owner)


def load_keyframe_ids(root: Path, episode_id: str, issues: list[dict[str, Any]]) -> set[str]:
    path = root / f"episodes/{episode_id}/03_资产/keyframe_manifest_{episode_id}.json"
    data = load_json(path, issues, required=False)
    keyframes = data.get("keyframes") if isinstance(data, dict) else None
    if not isinstance(keyframes, list):
        return set()
    return {item.get("keyframe_id") for item in keyframes if isinstance(item, dict) and item.get("status") == "approved" and isinstance(item.get("keyframe_id"), str)}


def marker_pattern(kind: str, order: int) -> str:
    patterns = {
        "image": rf"<(?:图片\s*{order}(?:\s*-\s*第\s*\d+\s*格)?|IMG\s*{order}(?:\s*-\s*Cell\s*\d+)?)\s*>",
        "video": rf"<(?:视频|VID)\s*{order}\s*>",
        "audio": rf"<(?:音频|AUD)\s*{order}\s*>",
    }
    return patterns[kind]


def extract_subject_marker_orders(text: str) -> set[int]:
    orders: set[int] = set()
    pattern = r"<(?:主体\s*(\d+)|SUBJ\s*(\d+))\s*>"
    for cn_order, en_order in re.findall(pattern, text, flags=re.I):
        orders.add(int(cn_order or en_order))
    return orders


def check_prompt_markers(
    prompt_path: Path,
    image_orders: list[int],
    video_orders: list[int],
    audio_orders: list[int],
    speech_lines: Any,
    subtitle_enabled: bool,
    issues: list[dict[str, Any]],
    h3_mode: str = "T2VA",
) -> None:
    """校验提交给模型的 Prompt 成稿携带了全部已登记输入与台词。

    成稿格式以 h3-prompt-writing 为准，媒体序号识别与 H3 提交共用同一函数，
    包含合法锚帧首行；每条 spoken_text 必须逐字存在于发声块。
    另核素材标记语言不混用及【】字幕源规则。
    五段式是独立导演包的组装规则，不适用于纯 H3 成稿。"""
    if not prompt_path.is_file():
        issues.append(issue("error", "prompt_missing", "Prompt 文件不存在。", prompt_path))
        return
    try:
        text = prompt_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "prompt_unreadable", f"Prompt 无法读取：{exc}", prompt_path))
        return
    expected_by_kind = {"image": sorted(image_orders), "video": sorted(video_orders), "audio": sorted(audio_orders)}
    for kind, expected in expected_by_kind.items():
        label = {"image": "图片", "video": "视频", "audio": "音频"}[kind]
        # 与提交入口共用识别规则，含 FL2VA 合法首行的无尖括号 Picture 标记。
        actual = sorted(media_marker_orders(text, h3_mode, kind))
        if actual != expected:
            issues.append(issue("error", f"prompt_{kind}_markers_mismatch", f"Prompt 中{label}标记 {actual} 必须与实际输入 order {expected} 一致（写法以 h3-prompt-writing 为准）。", prompt_path))
    cn = re.search(r"<(?:图片\s*\d+(?:\s*-\s*第\s*\d+\s*格)?|视频\s*\d+|音频\s*\d+|主体\s*\d+)\s*>", text)
    en = re.search(r"<(?:IMG\s*\d+(?:\s*-\s*Cell\s*\d+)?|VID\s*\d+|AUD\s*\d+|SUBJ\s*\d+)\s*>", text, flags=re.I)
    if cn and en:
        issues.append(issue("error", "prompt_marker_language_mixed", "同一 Prompt 不要混用中文和英文多媒体标记。", prompt_path))
    for order in sorted(extract_subject_marker_orders(text)):
        cn_labeled = rf"<\s*主体\s*{order}\s*>\s*[（(][^（）()\n]+[）)]"
        en_labeled = rf"<\s*SUBJ\s*{order}\s*>\s*[（(][^（）()\n]+[）)]"
        if not re.search(cn_labeled, text) and not re.search(en_labeled, text, flags=re.I):
            issues.append(issue("error", "prompt_subject_marker_label_missing", f"Prompt 使用 <主体{order}>/<SUBJ{order}> 时，必须至少一次写成 <主体{order}>(名称) 或 <SUBJ{order}>(name) 绑定主体身份。", prompt_path))
    if ("【" in text or "】" in text) and not subtitle_enabled:
        issues.append(issue("error", "prompt_subtitle_bracket_invalid", "未启用字幕时，最终视频 Prompt 不允许出现【】字幕源标识。", prompt_path))
    expected_speech: set[str] = set()
    if isinstance(speech_lines, list):
        for index, line in enumerate(speech_lines, start=1):
            if not isinstance(line, dict):
                issues.append(issue("error", "speech_line_invalid", f"speech_lines 第 {index} 条必须是对象。", prompt_path))
                continue
            spoken = str(line.get("spoken_text") or "").strip()
            if not spoken:
                issues.append(issue("error", "speech_line_spoken_text_missing", f"speech_lines 第 {index} 条缺少 spoken_text。", prompt_path))
                continue
            expected_speech.add(spoken)
            if not any(spoken in block for block in re.findall(r"<d>(.*?)</d>", text, re.S)):
                issues.append(issue("error", "prompt_speech_line_missing", f"Prompt 缺少当前 SEG 台词原文：{spoken}", prompt_path))


def check_h3_prompt(segment: dict[str, Any], root: Path, path: Path, issues: list[dict[str, Any]]) -> None:
    """H3 成稿只核存在、非空与哈希一致；其内部结构由 h3-prompt-writing skill 负责，本脚本不查。"""
    segment_id = segment.get("segment_id") or "视频片段"
    h3_file = segment.get("h3_prompt_file")
    h3_path = relative_file(root, h3_file)
    if h3_file and h3_path is None:
        issues.append(issue("error", "h3_prompt_path_invalid", f"{segment_id} h3_prompt_file 必须是项目相对路径。", path))
        h3_path = None
    if h3_path is not None and not h3_path.is_file():
        issues.append(issue("error", "h3_prompt_missing", f"{segment_id} 登记的 h3_prompt_file 不存在。", h3_path))
        h3_path = None
    if h3_path is not None:
        try:
            if not h3_path.read_text(encoding="utf-8").strip():
                issues.append(issue("error", "h3_prompt_empty", f"{segment_id} 的 H3 成稿为空。", h3_path))
        except (OSError, UnicodeError) as exc:
            issues.append(issue("error", "h3_prompt_unreadable", f"{segment_id} 的 H3 成稿无法读取：{exc}", h3_path))
            h3_path = None
    h3_sha256 = str(segment.get("h3_prompt_sha256") or "").strip()
    if h3_path is not None and h3_sha256:
        try:
            actual = file_sha256(h3_path)
        except OSError as exc:
            issues.append(issue("error", "h3_prompt_sha256_unreadable", f"无法读取 H3 成稿计算 sha256：{exc}", h3_path))
        else:
            if actual != h3_sha256:
                issues.append(issue("error", "h3_prompt_sha256_mismatch", f"{segment_id} h3_prompt_sha256 与实际 H3 成稿不一致。", h3_path))
    generated_segment = bool(str(segment.get("output_file") or "").strip()) or segment.get("status") in {"candidate", "accepted"}
    if generated_segment:
        if h3_path is None and not h3_file:
            issues.append(issue("error", "generated_segment_h3_prompt_missing", f"{segment_id} 已生成或进入候选/验收状态，必须登记真实存在的 h3_prompt_file。", path))
        if not h3_sha256:
            issues.append(issue("error", "generated_segment_h3_prompt_sha256_missing", f"{segment_id} 已生成或进入候选/验收状态，必须登记提交给模型的 H3 成稿 h3_prompt_sha256。", path))


def check_video_state_refs(segment: dict[str, Any], image_roles: set[str], asset_index: dict[str, Any], path: Path, issues: list[dict[str, Any]]) -> None:
    if not (image_roles & STATE_REFERENCE_ROLES):
        return
    state_refs = segment.get("state_refs")
    if not isinstance(state_refs, list) or not state_refs:
        issues.append(issue("error", "video_state_refs_missing", f"{segment.get('segment_id') or 'segment'} 传入角色/道具状态参考图时必须登记 approved state_refs。", path))
        return
    for ref in state_refs:
        check_state_ref(ref, asset_index, path, issues, str(segment.get("segment_id") or "视频片段"))


def _check_h3_prompt_purity(prompt_path, issues, mode="T2VA", duration=6):
    try:
        check_purity(prompt_path.read_text(encoding="utf-8"), mode, duration)
    except (OSError, ValueError) as exc:
        issues.append(issue("error", "h3_prompt_impure", str(exc), prompt_path))


def check_video_generation_confirmations(data, segments, path, issues):
    issues.extend(dict(row, path=str(path)) for row in validate_confirmations(data, segments))


def check_voice_audio_inputs(segment: dict[str, Any], audio_roles: set[str], path: Path, issues: list[dict[str, Any]]) -> None:
    speech_lines = segment.get("speech_lines")
    if not isinstance(speech_lines, list) or not speech_lines:
        return
    segment_label = str(segment.get("segment_id") or "segment")
    audio_input_supported = segment.get("audio_input_supported") is True
    has_voice_audio_reference = "voice_audio_reference" in audio_roles
    voice_inputs = segment.get("voice_inputs")

    if not audio_input_supported and not has_voice_audio_reference:
        if isinstance(voice_inputs, list) and voice_inputs:
            issues.append(issue("error", "voice_inputs_without_audio_reference", f"{segment_label} 未传 VOICE 音频时不得登记 voice_inputs；文字音色锚点以 project_data_card.json voices[].voice_anchor 单定义为准，按 voice_id 解析，不在台词行复制。", path))
        # 锚点缺失/未知 voice_id 统一由 check_voice_anchor_resolution 按数据卡单定义裁决，此处不重复发射。
        return

    if audio_input_supported and not has_voice_audio_reference:
        issues.append(issue("error", "voice_audio_input_missing", f"{segment_label} 支持音频输入且有 speech_lines 时必须上传 approved VOICE 音频。", path))
    if has_voice_audio_reference and not audio_input_supported:
        issues.append(issue("error", "voice_audio_support_flag_missing", f"{segment_label} 已传 voice_audio_reference 时 audio_input_supported 必须为 true。", path))
    if not isinstance(voice_inputs, list) or not voice_inputs:
        issues.append(issue("error", "voice_inputs_missing", f"{segment_label} 有 speech_lines 时必须登记 voice_inputs。", path))
        return
    voice_ids = {
        item.get("voice_id")
        for item in voice_inputs
        if isinstance(item, dict) and isinstance(item.get("voice_id"), str) and item.get("voice_id").strip()
    }
    resource_ids = {
        item.get("resource_id")
        for item in voice_inputs
        if isinstance(item, dict) and isinstance(item.get("resource_id"), str) and item.get("resource_id").strip()
    }
    if not voice_ids or not resource_ids:
        issues.append(issue("error", "voice_inputs_incomplete", f"{segment_label} voice_inputs 必须填写 voice_id 和 resource_id。", path))
    for index, line in enumerate(speech_lines, start=1):
        if not isinstance(line, dict):
            continue
        voice_id = line.get("voice_id")
        if isinstance(voice_id, str) and voice_id.strip() and voice_id not in voice_ids:
            issues.append(issue("error", "speech_line_voice_input_missing", f"{segment_label} speech_lines 第 {index} 条 voice_id 未在 voice_inputs 中登记：{voice_id}", path))


def load_voice_anchor_map(root: Path, issues: list[dict[str, Any]]) -> dict[str, str]:
    """voice_id→voice_anchor 单定义解析表；唯一权威是 project_data_card.json 的 voices[]。"""
    card = load_json(root / "00_制作控制/project_data_card.json", issues, required=False)
    anchors: dict[str, str] = {}
    if isinstance(card, dict):
        for item in card.get("voices") or []:
            if not isinstance(item, dict):
                continue
            voice_id = str(item.get("voice_id") or "").strip()
            if voice_id:
                anchors[voice_id] = str(item.get("voice_anchor") or "").strip()
    return anchors


def check_voice_anchor_resolution(segment: dict[str, Any], voice_anchors: dict[str, str], path: Path, issues: list[dict[str, Any]]) -> None:
    """台词行只存 voice_id；声音锚点由数据卡 voices[] 单定义解析，行级副本不再参与校验。"""
    speech_lines = segment.get("speech_lines")
    if not isinstance(speech_lines, list):
        return
    segment_label = str(segment.get("segment_id") or "segment")
    for index, line in enumerate(speech_lines, start=1):
        if not isinstance(line, dict):
            continue
        voice_id = str(line.get("voice_id") or "").strip()
        if not voice_id:
            continue
        if voice_id not in voice_anchors:
            issues.append(issue("error", "speech_line_voice_unknown", f"{segment_label} speech_lines 第 {index} 条 voice_id={voice_id} 在 project_data_card.json voices[] 中不存在。", path))
        elif not voice_anchors[voice_id]:
            issues.append(issue("error", "speech_line_voice_anchor_missing", f"{segment_label} voice_id={voice_id} 已在 voices[] 登记但 voice_anchor 为空，无法约束声线。", path))


def check_prompt_preflight(segment, expected_shot_ids, path, issues):
    root = path.parents[3]
    try:
        gen = read_json(root / segment["gen_file"])
        prepared = prepare_request(gen=gen, root=root, prompt_file=segment.get("h3_prompt_file"))
        if prepared.contract["binding_id"] != segment.get("binding_id"):
            raise ContractError("preflight_binding_mismatch", "manifest binding_id 不符")
        if [row["shot_id"] for row in prepared.contract["compilation_map"]] != expected_shot_ids:
            raise ContractError("h3_compilation_mismatch", "编译映射镜头集合/顺序不符")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        issues.append(issue("error", getattr(exc, "code", "preflight_binding_mismatch"), str(exc), path))
