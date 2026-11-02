"""Asset versions, reusable states, approved voice samples and registries."""
from __future__ import annotations

import json
import math
import re
import subprocess
import wave
from pathlib import Path
from typing import Any
from h3_contract import is_url, CAPABILITIES
from .causal import validate_collective_profiles
from .common import (
    check_generation_prompt_file, check_style_anchor_contract, combined_strings, episode_dirs,
    issue, load_json, media_location_valid, relative_file,
)
from .constants import (
    ASSET_PREFIX_BY_CATEGORY, ASSET_STATUS_VALUES, PROJECT_VISUAL_MODES,
    VISUAL_REFERENCE_DECISIONS,
)


def asset_version_key(asset_id: str, version: str, separator: str = "_") -> str:
    return f"{asset_id}{separator}{version}"


def version_rank(version: str) -> int:
    match = re.search(r"\d+", version)
    return int(match.group()) if match else -1


def split_asset_version_ref(ref: Any) -> tuple[str, str] | None:
    if not isinstance(ref, str):
        return None
    for separator in ("_", ":"):
        head, sep, tail = ref.rpartition(separator)
        if sep and head and re.fullmatch(r"v\d+", tail, flags=re.I):
            return head, tail
    return None


def blank_asset_index() -> dict[str, Any]:
    return {
        "known_asset_ids": set(),
        "known_version_refs": set(),
        "approved_version_refs": set(),
        "approved_versions_by_asset": {},
        "latest_approved_version": {},
        "known_state_refs": set(),
        "approved_state_refs": set(),
    }


def remember_asset_version(index: dict[str, Any], asset_id: str, version: str, status: Any) -> None:
    index["known_asset_ids"].add(asset_id)
    if version:
        underscore_ref = asset_version_key(asset_id, version, "_")
        colon_ref = asset_version_key(asset_id, version, ":")
        index["known_version_refs"].add(underscore_ref)
        index["known_version_refs"].add(colon_ref)
        if status == "approved":
            index["approved_version_refs"].add(underscore_ref)
            index["approved_version_refs"].add(colon_ref)
            approved = index["approved_versions_by_asset"].setdefault(asset_id, set())
            approved.add(version)
            latest = index["latest_approved_version"].get(asset_id)
            if latest is None or version_rank(version) > version_rank(latest):
                index["latest_approved_version"][asset_id] = version


def state_ref_keys(asset_id: str, state_id: str, version: str = "") -> set[str]:
    refs = {f"{asset_id}:{state_id}"}
    if version:
        refs.add(f"{asset_id}:{state_id}_{version}")
        refs.add(f"{asset_id}:{state_id}:{version}")
    return refs


def remember_state_version(index: dict[str, Any], asset_id: str, state_id: str, version: str, status: Any) -> None:
    refs = state_ref_keys(asset_id, state_id, version)
    index["known_state_refs"].update(refs)
    if status == "approved":
        index["approved_state_refs"].update(refs)


def check_stale_asset_version(ref: Any, index: dict[str, Any], path: Path, issues: list[dict[str, Any]], owner: str) -> None:
    parsed = split_asset_version_ref(ref)
    if parsed is None:
        return
    asset_id, version = parsed
    latest = index["latest_approved_version"].get(asset_id)
    if latest and version_rank(version) < version_rank(latest):
        issues.append(issue("error", "downstream_asset_version_stale", f"{owner} 仍引用旧资产版本 {ref}；最新 approved 版本是 {asset_version_key(asset_id, latest)}。", path))


def check_voice_sample(root, asset, path, issues):
    if asset.get("category") != "voice" or asset.get("status") != "approved":
        return
    label = asset.get("asset_id") or "VOICE"
    files = asset.get("files")
    value = asset.get("file") or (files[0] if isinstance(files, list) and len(files) == 1 else None)
    try:
        if files and (not isinstance(files, list) or files != [value]):
            raise ValueError("音色必须指向唯一真实样音，file/files 不得冲突")
        if isinstance(value, str) and is_url(value):
            # URL identity remains the original string; never fetch it for lint.
            duration = asset.get("duration_s")
        else:
            audio = relative_file(root, value)
            if audio is None or not audio.is_file():
                raise ValueError("缺真实音色文件或有效 HTTP(S) URL")
            if audio.suffix.lower() == ".wav":
                with wave.open(str(audio), "rb") as sample:
                    if sample.getframerate() <= 0:
                        raise ValueError("WAV 采样率无效")
                    duration = sample.getnframes() / sample.getframerate()
                    expected = sample.getnframes() * sample.getnchannels() * sample.getsampwidth()
                    if len(sample.readframes(sample.getnframes())) != expected:
                        raise ValueError("WAV 数据截断，不能只凭头部时长批准")
            else:
                result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                    "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(audio)],
                    capture_output=True, text=True, encoding="utf-8", timeout=30)
                metadata = json.loads(result.stdout)
                if result.returncode or not metadata.get("streams"):
                    raise ValueError("未探测到可用音频流")
                duration = float(metadata["format"]["duration"])
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
            raise ValueError("需有效音频时长；URL 从已知媒体事实登记 duration_s，lint 不下载")
        profile = json.loads(CAPABILITIES.read_text(encoding="utf-8"))["capabilities"]
        ranges = [limits["audio_per_clip_s"] for limits in profile["mode_ref_limits"].values()
                  if limits.get("audios_max", 0) and "audio_per_clip_s" in limits]
        if not ranges or not any(low <= duration <= high for low, high in ranges):
            issues.append(issue("error", "voice_sample_duration_invalid",
                f"{label} 音色 {duration:g}s 不满足能力档案的音频参考范围 {ranges}；资产阶段处理后试听，不自动补静音或批准。", path))
        if "duration_s" in asset and (isinstance(asset["duration_s"], bool)
                or not isinstance(asset["duration_s"], (int, float))
                or not math.isfinite(asset["duration_s"]) or abs(asset["duration_s"] - duration) > .001):
            issues.append(issue("error", "voice_sample_duration_mismatch", f"{label} 登记时长与本地音频实测不同。", path))
    except (OSError, ValueError, TypeError, KeyError, wave.Error, EOFError, subprocess.TimeoutExpired) as exc:
        issues.append(issue("error", "voice_sample_invalid", f"{label} 音色技术核验失败：{exc}", path))


def check_reused_voice_sample(root, asset, source_episode, cache, issues):
    """Resolve a current episode's VOICE to its original approved record, without copying it."""
    asset_id = str(asset.get("asset_id") or "")
    if not asset_id.startswith("VOICE"):
        return
    origin = source_episode
    record = asset
    while record.get("source_episode_id"):
        previous = record["source_episode_id"]
        path = root / f"episodes/{origin}/03_资产/asset_usage_{origin}.json"
        if (not isinstance(previous, str) or not re.fullmatch(r"ep_[1-9]\d*", previous)
                or int(previous.split("_")[1]) >= int(origin.split("_")[1])):
            issues.append(issue("error", "voice_sample_source_invalid", f"{asset_id} 音色复用来源必须指向更早分集。", path))
            return
        if previous not in cache:
            source_path = root / f"episodes/{previous}/03_资产/asset_usage_{previous}.json"
            cache[previous] = load_json(source_path, issues, required=False)
        source = cache[previous]
        candidates = []
        if isinstance(source, dict):
            for field in ("episode_assets", "reused_episode_assets"):
                rows = source.get(field)
                if isinstance(rows, list):
                    candidates.extend(row for row in rows if isinstance(row, dict)
                        and row.get("asset_id") == asset_id and row.get("status") == "approved"
                        and str(row.get("state_id") or "") == str(record.get("state_id") or "")
                        and row.get("version") == record.get("version"))
        if len(candidates) != 1 or candidates[0].get("files", []) != record.get("files", []):
            issues.append(issue("error", "voice_sample_source_invalid", f"{asset_id} 音色复用链缺唯一、文件一致的 approved 来源。", path))
            return
        record, origin = candidates[0], previous
    path = root / f"episodes/{origin}/03_资产/asset_usage_{origin}.json"
    if record.get("category") != "voice":
        issues.append(issue("error", "voice_sample_source_invalid", f"{asset_id} 原批准记录未登记为 voice。", path))
        return
    check_voice_sample(root, record, path, issues)


def check_assets(root: Path, issues: list[dict[str, Any]], episode_filter: str | None = None) -> dict[str, Any]:
    registry_path = root / "shared/03_资产/asset_registry.json"
    registry = load_json(registry_path, issues, required=False)
    collective_ids = validate_collective_profiles(root, issues)
    index = blank_asset_index()
    source_usage_cache: dict[str, dict[str, Any] | None] = {}
    if isinstance(registry, dict):
        assets = registry.get("assets")
        if isinstance(assets, list):
            version_keys: set[tuple[str, str]] = set()
            for asset in assets:
                if not isinstance(asset, dict):
                    continue
                asset_id = asset.get("asset_id")
                category = asset.get("category")
                entity_scope = asset.get("entity_scope", "individual")
                version = str(asset.get("version") or "")
                if category == "character":
                    if entity_scope not in {"individual", "collective"}:
                        issues.append(issue("error", "asset_entity_scope_invalid", f"{asset_id or '角色资产'} entity_scope 必须为 individual 或 collective。", registry_path))
                    elif isinstance(asset_id, str) and asset_id in collective_ids and entity_scope != "collective":
                        issues.append(issue("error", "collective_asset_scope_mismatch", f"{asset_id} 在项目数据卡中是群像，registry 必须登记 entity_scope=collective。", registry_path))
                    elif entity_scope == "collective" and asset_id not in collective_ids:
                        issues.append(issue("error", "collective_asset_data_card_missing", f"{asset_id or '群像资产'} 登记为 collective，但项目数据卡没有对应群像角色记录。", registry_path))
                elif "entity_scope" in asset:
                    issues.append(issue("error", "asset_entity_scope_not_character", f"{asset_id or '资产'} 只有 character 类资产可填写 entity_scope。", registry_path))
                if isinstance(asset_id, str) and asset_id.strip():
                    remember_asset_version(index, asset_id, version, asset.get("status"))
                    key = (asset_id, version)
                    if key in version_keys:
                        issues.append(issue("error", "asset_version_duplicate", f"asset_id + version 重复：{asset_id} {version}", registry_path))
                    version_keys.add(key)
                    expected_prefix = ASSET_PREFIX_BY_CATEGORY.get(str(category))
                    if expected_prefix and not asset_id.startswith(expected_prefix):
                        issues.append(issue("error", "asset_id_prefix_mismatch", f"{asset_id} 与 category={category} 的前缀不一致。", registry_path))
                else:
                    issues.append(issue("error", "asset_id_missing", "资产缺少 asset_id。", registry_path))
                status = asset.get("status")
                check_voice_sample(root, asset, registry_path, issues)
                if status is not None and status not in ASSET_STATUS_VALUES:
                    issues.append(issue("error", "asset_status_invalid", f"资产状态无效：{status}", registry_path))
                state_id = str(asset.get("state_id") or "")
                if isinstance(asset_id, str) and asset_id.strip() and state_id:
                    remember_state_version(index, asset_id, state_id, version, status)
                for file_value in asset.get("files") or []:
                    if not media_location_valid(root, file_value):
                        issues.append(issue("error", "asset_file_missing", f"资产缺本地文件或有效 HTTP(S) 引用：{file_value}", registry_path))
                generation = asset.get("generation") if isinstance(asset.get("generation"), dict) else {}
                tool = generation.get("tool")
                refs = [*asset.get("reference_asset_ids", [])] if isinstance(asset.get("reference_asset_ids"), list) else []
                available_visual_refs = []
                for field_owner in (asset, generation):
                    value = field_owner.get("available_visual_reference_ids") if isinstance(field_owner, dict) else None
                    if isinstance(value, list):
                        available_visual_refs.extend(item for item in value if isinstance(item, str) and item.strip())
                visual_reference_decision = asset.get("visual_reference_decision") or generation.get("visual_reference_decision")
                if visual_reference_decision is not None and visual_reference_decision not in VISUAL_REFERENCE_DECISIONS:
                    issues.append(issue("error", "visual_reference_decision_invalid", f"{asset_id} visual_reference_decision 无效：{visual_reference_decision}", registry_path))
                visual_inputs = []
                for field in ("reference_inputs", "input_files", "input_images"):
                    value = generation.get(field)
                    if isinstance(value, list):
                        visual_inputs.extend(value)
                style_anchor_refs = combined_strings(asset, generation, field="style_anchor_reference_ids")
                style_terms = combined_strings(asset, generation, field="style_prompt_terms")
                project_visual_mode = asset.get("project_visual_mode") or generation.get("project_visual_mode")
                if category in {"character", "scene", "prop", "style"} and status == "approved":
                    if project_visual_mode not in PROJECT_VISUAL_MODES:
                        issues.append(issue("error", "project_visual_mode_missing_or_invalid", f"{asset_id or '资产'} approved 图片资产必须登记有效 project_visual_mode。", registry_path))
                if tool == "image_gen" and (refs or visual_inputs):
                    issues.append(issue("error", "image_gen_should_not_have_visual_inputs", f"{asset_id} 使用 image_gen 时不应登记图片参考输入。", registry_path))
                if tool == "image_gen" and available_visual_refs and visual_reference_decision != "explicit_user_override":
                    issues.append(issue("error", "image_gen_visual_reference_available", f"{asset_id} 已登记可用视觉参考，必须使用 image_edit；除非用户明确要求不参考并记录 explicit_user_override。", registry_path))
                if tool == "image_gen" and visual_reference_decision == "used":
                    issues.append(issue("error", "image_gen_visual_reference_decision_conflict", f"{asset_id} visual_reference_decision=used 时不能使用 image_gen。", registry_path))
                if tool == "image_edit" and not (refs or visual_inputs or style_anchor_refs):
                    issues.append(issue("error", "image_edit_reference_missing", f"{asset_id} 使用 image_edit 时必须登记实际参考来源。", registry_path))
                if tool == "image_edit" and visual_reference_decision == "none_available":
                    issues.append(issue("error", "image_edit_visual_reference_decision_conflict", f"{asset_id} 使用 image_edit 时 visual_reference_decision 不能写 none_available。", registry_path))
                if category == "character" and state_id and tool == "image_gen" and visual_reference_decision != "explicit_user_override":
                    issues.append(issue("error", "character_state_asset_requires_image_edit", f"{asset_id or '角色状态资产'} 是人物状态资产时必须基于已批准人物图使用 image_edit；除非用户明确要求重做并记录 explicit_user_override。", registry_path))
                check_generation_prompt_file(root, registry_path, str(asset_id or "资产"), tool, generation.get("prompt_path"), issues)
                check_style_anchor_contract(
                    root,
                    registry_path,
                    str(asset_id or "资产"),
                    tool,
                    generation.get("prompt_path"),
                    style_anchor_refs,
                    style_terms,
                    combined_strings(asset, generation, field="style_adopt"),
                    combined_strings(asset, generation, field="style_exclude"),
                    issues,
                    visual_reference_decision,
                )
                if category == "style" and asset_id == "STYLE001":
                    style_asset_type = asset.get("style_asset_type") or generation.get("style_asset_type")
                    if status == "approved" and style_asset_type is None:
                        issues.append(issue("error", "style_asset_type_missing", "STYLE001 approved 前必须登记 style_asset_type=global_visual_language_moodboard。", registry_path))
                    if style_asset_type is not None and style_asset_type != "global_visual_language_moodboard":
                        issues.append(issue("error", "style_asset_type_invalid", "STYLE001 必须登记为 global_visual_language_moodboard。", registry_path))
                    scene_links = asset.get("style_scene_atmosphere_links") or generation.get("style_scene_atmosphere_links")
                    if status == "approved" and (not isinstance(scene_links, list) or not any(str(item).strip() for item in scene_links)):
                        issues.append(issue("error", "style_scene_atmosphere_links_missing", "STYLE001 approved 时 style_scene_atmosphere_links 必须是非空数组。", registry_path))
                    visual_language = asset.get("style_visual_language") or generation.get("style_visual_language")
                    if status == "approved":
                        if not isinstance(visual_language, dict):
                            issues.append(issue("error", "style_visual_language_missing", "STYLE001 必须登记色彩、光线、构图、材质或空间氛围等视觉语言。", registry_path))
                        else:
                            filled = [
                                key
                                for key, value in visual_language.items()
                                if isinstance(value, list) and any(str(item).strip() for item in value)
                            ]
                            if not filled:
                                issues.append(issue("error", "style_visual_language_missing", "STYLE001 需记录本项目实际采用的视觉语言；字段数量不证明风格质量。", registry_path))
                    if asset.get("contains_story_characters") is not False and generation.get("contains_story_characters") is not False:
                        issues.append(issue("error", "style_moodboard_contains_characters_unknown", "STYLE001 全局风格 moodboard 必须明确 contains_story_characters=false。", registry_path))
                    if asset.get("contains_story_props") is not False and generation.get("contains_story_props") is not False:
                        issues.append(issue("error", "style_moodboard_contains_props_unknown", "STYLE001 全局风格 moodboard 必须明确 contains_story_props=false。", registry_path))
        elif assets is not None:
            issues.append(issue("error", "assets_invalid", "asset_registry.assets 必须是数组。", registry_path))
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"03_资产/asset_usage_{episode_id}.json"
        usage = load_json(path, issues, required=False)
        if not isinstance(usage, dict):
            continue
        shared = usage.get("shared_assets")
        reused_episode_assets = usage.get("reused_episode_assets")
        episode_assets = usage.get("episode_assets")
        for field in ("shared_assets", "episode_assets", "reused_episode_assets"):
            values = usage.get(field)
            if not isinstance(values, list):
                continue
            for item in values:
                if not isinstance(item, dict):
                    continue
                asset_id = str(item.get("asset_id") or "")
                if asset_id in collective_ids and item.get("entity_scope") != "collective":
                    issues.append(issue("error", "collective_usage_scope_mismatch", f"{episode_id} 的 {asset_id} 必须以 entity_scope=collective 登记。", path))
        if isinstance(shared, list):
            seen_shared: set[tuple[str, str]] = set()
            for item in shared:
                if not isinstance(item, dict):
                    continue
                asset_id = item.get("asset_id")
                version = str(item.get("version") or "")
                if isinstance(asset_id, str):
                    if index["known_asset_ids"] and asset_id not in index["known_asset_ids"]:
                        issues.append(issue("error", "asset_usage_unknown_shared_asset", f"{episode_id} 引用了 registry 中不存在的共享资产：{asset_id}", path))
                    if not version:
                        issues.append(issue("error", "asset_usage_shared_version_missing", f"{episode_id} 共享资产必须填写 version：{asset_id}", path))
                    else:
                        refs = {asset_version_key(asset_id, version, "_"), asset_version_key(asset_id, version, ":")}
                        if index["known_version_refs"] and not (refs & index["known_version_refs"]):
                            issues.append(issue("error", "asset_usage_unknown_shared_version", f"{episode_id} 引用了 registry 中不存在的共享资产版本：{asset_id} {version}", path))
                        elif index["known_version_refs"] and not (refs & index["approved_version_refs"]):
                            issues.append(issue("error", "asset_usage_shared_not_approved", f"{episode_id} 只能引用 registry 中 approved 的共享资产版本：{asset_id} {version}", path))
                    key = (asset_id, version)
                    if key in seen_shared:
                        issues.append(issue("error", "asset_usage_duplicate", f"{episode_id} 共享资产重复：{asset_id} {version}", path))
                    seen_shared.add(key)
        if reused_episode_assets is not None and not isinstance(reused_episode_assets, list):
            issues.append(issue("error", "reused_episode_assets_invalid", f"{episode_id} reused_episode_assets 必须是数组。", path))
        if isinstance(reused_episode_assets, list):
            seen_reused: set[tuple[str, str, str, str]] = set()
            for item in reused_episode_assets:
                if not isinstance(item, dict):
                    issues.append(issue("error", "reused_episode_asset_invalid", f"{episode_id} reused_episode_assets 每项必须是对象。", path))
                    continue
                source_episode_id = str(item.get("source_episode_id") or "")
                asset_id = str(item.get("asset_id") or "")
                state_id = str(item.get("state_id") or "")
                version = str(item.get("version") or "")
                status = item.get("status")
                source_valid = True
                if not source_episode_id:
                    issues.append(issue("error", "reused_episode_source_missing", f"{episode_id} 复用分集资产必须填写 source_episode_id。", path))
                    source_valid = False
                elif not re.fullmatch(r"ep_[1-9]\d*", source_episode_id) or int(source_episode_id.split("_", 1)[1]) >= int(episode_id.split("_", 1)[1]):
                    issues.append(issue("error", "reused_episode_source_invalid", f"{episode_id} 只能复用更早分集的 approved 资产：{source_episode_id}", path))
                    source_valid = False
                if not asset_id or not version:
                    issues.append(issue("error", "reused_episode_asset_ref_missing", f"{episode_id} 复用分集资产必须填写 asset_id 和 version。", path))
                    source_valid = False
                if status != "approved":
                    issues.append(issue("error", "reused_episode_asset_not_approved", f"{episode_id} 只能复用 approved 分集资产：{asset_id} {state_id} {version}", path))
                    source_valid = False
                if source_valid:
                    if source_episode_id not in source_usage_cache:
                        source_path = root / f"episodes/{source_episode_id}/03_资产/asset_usage_{source_episode_id}.json"
                        source_usage = load_json(source_path, issues, required=False)
                        source_usage_cache[source_episode_id] = source_usage if isinstance(source_usage, dict) else None
                    source_usage = source_usage_cache[source_episode_id]
                    source_candidates = []
                    if isinstance(source_usage, dict):
                        for field in ("episode_assets", "reused_episode_assets"):
                            values = source_usage.get(field)
                            if isinstance(values, list):
                                source_candidates.extend(candidate for candidate in values if isinstance(candidate, dict))
                    matching_source = next(
                        (
                            candidate
                            for candidate in source_candidates
                            if str(candidate.get("asset_id") or "") == asset_id
                            and str(candidate.get("state_id") or "") == state_id
                            and str(candidate.get("version") or "") == version
                            and candidate.get("status") == "approved"
                        ),
                        None,
                    )
                    if matching_source is None:
                        issues.append(issue("error", "reused_episode_asset_source_not_found", f"{episode_id} 复用资产在 {source_episode_id} 中找不到一致的 approved 来源：{asset_id} {state_id} {version}", path))
                        source_valid = False
                    elif sorted(item.get("files") or []) != sorted(matching_source.get("files") or []):
                        issues.append(issue("error", "reused_episode_asset_files_mismatch", f"{episode_id} 复用资产文件必须与 {source_episode_id} 来源记录一致：{asset_id} {state_id} {version}", path))
                        source_valid = False
                if source_valid and episode_filter:
                    check_reused_voice_sample(root, matching_source, source_episode_id, source_usage_cache, issues)
                if asset_id and source_valid:
                    remember_asset_version(index, asset_id, version, "approved" if status == "approved" else status)
                if asset_id and state_id and source_valid:
                    remember_state_version(index, asset_id, state_id, version, status)
                key = (source_episode_id, asset_id, state_id, version)
                if key in seen_reused:
                    issues.append(issue("error", "reused_episode_asset_duplicate", f"{episode_id} 复用分集资产重复：{source_episode_id} {asset_id} {state_id} {version}", path))
                seen_reused.add(key)
                for file_value in item.get("files") or []:
                    if not media_location_valid(root, file_value):
                        issues.append(issue("error", "reused_episode_asset_file_missing", f"复用分集资产缺本地文件或有效 HTTP(S) 引用：{file_value}", path))
        if isinstance(episode_assets, list):
            state_keys: set[tuple[str, str, str]] = set()
            for item in episode_assets:
                if not isinstance(item, dict):
                    continue
                asset_id = str(item.get("asset_id") or "")
                state_id = str(item.get("state_id") or "")
                version = str(item.get("version") or "")
                if asset_id:
                    remember_asset_version(index, asset_id, version, item.get("status"))
                if asset_id and state_id:
                    remember_state_version(index, asset_id, state_id, version, item.get("status"))
                key = (asset_id, state_id, version)
                if key in state_keys:
                    issues.append(issue("error", "episode_asset_duplicate", f"{episode_id} 分集资产重复：{asset_id} {state_id} {version}", path))
                state_keys.add(key)
                check_voice_sample(root, item, path, issues)
                if item.get("status") is not None and item.get("status") not in ASSET_STATUS_VALUES:
                    issues.append(issue("error", "episode_asset_status_invalid", f"分集资产状态无效：{item.get('status')}", path))
                generation = item.get("generation") if isinstance(item.get("generation"), dict) else {}
                tool = generation.get("tool")
                refs = [*item.get("reference_asset_ids", [])] if isinstance(item.get("reference_asset_ids"), list) else []
                available_visual_refs = []
                for field_owner in (item, generation):
                    value = field_owner.get("available_visual_reference_ids") if isinstance(field_owner, dict) else None
                    if isinstance(value, list):
                        available_visual_refs.extend(ref for ref in value if isinstance(ref, str) and ref.strip())
                visual_reference_decision = item.get("visual_reference_decision") or generation.get("visual_reference_decision")
                if visual_reference_decision is not None and visual_reference_decision not in VISUAL_REFERENCE_DECISIONS:
                    issues.append(issue("error", "episode_visual_reference_decision_invalid", f"{asset_id or '分集资产'} visual_reference_decision 无效：{visual_reference_decision}", path))
                visual_inputs = []
                for field in ("reference_inputs", "input_files", "input_images"):
                    value = generation.get(field)
                    if isinstance(value, list):
                        visual_inputs.extend(value)
                style_anchor_refs = combined_strings(item, generation, field="style_anchor_reference_ids")
                style_terms = combined_strings(item, generation, field="style_prompt_terms")
                project_visual_mode = item.get("project_visual_mode") or generation.get("project_visual_mode")
                category = item.get("category")
                if category in {"character", "scene", "prop", "style"} and item.get("status") == "approved":
                    if project_visual_mode not in PROJECT_VISUAL_MODES:
                        issues.append(issue("error", "episode_project_visual_mode_missing_or_invalid", f"{asset_id or '分集资产'} approved 图片资产必须登记有效 project_visual_mode。", path))
                if tool == "image_gen" and (refs or visual_inputs or style_anchor_refs):
                    issues.append(issue("error", "episode_image_gen_should_not_have_visual_inputs", f"{asset_id or '分集资产'} 使用 image_gen 时不应登记图片参考输入。", path))
                if tool == "image_gen" and available_visual_refs and visual_reference_decision != "explicit_user_override":
                    issues.append(issue("error", "episode_image_gen_visual_reference_available", f"{asset_id or '分集资产'} 已登记可用视觉参考，必须使用 image_edit；除非用户明确要求不参考并记录 explicit_user_override。", path))
                if tool == "image_gen" and visual_reference_decision == "used":
                    issues.append(issue("error", "episode_image_gen_visual_reference_decision_conflict", f"{asset_id or '分集资产'} visual_reference_decision=used 时不能使用 image_gen。", path))
                if tool == "image_edit" and not (refs or visual_inputs or style_anchor_refs):
                    issues.append(issue("error", "episode_image_edit_reference_missing", f"{asset_id or '分集资产'} 使用 image_edit 时必须登记实际参考来源。", path))
                if tool == "image_edit" and visual_reference_decision == "none_available":
                    issues.append(issue("error", "episode_image_edit_visual_reference_decision_conflict", f"{asset_id or '分集资产'} 使用 image_edit 时 visual_reference_decision 不能写 none_available。", path))
                state_id = str(item.get("state_id") or "")
                if category == "character" and state_id and tool == "image_gen" and visual_reference_decision != "explicit_user_override":
                    issues.append(issue("error", "episode_character_state_asset_requires_image_edit", f"{asset_id or '角色状态资产'} 是人物状态资产时必须基于已批准人物图使用 image_edit；除非用户明确要求重做并记录 explicit_user_override。", path))
                check_generation_prompt_file(root, path, str(asset_id or "分集资产"), tool, generation.get("prompt_path"), issues)
                for file_value in item.get("files") or []:
                    if not media_location_valid(root, file_value):
                        issues.append(issue("error", "episode_asset_file_missing", f"分集资产缺本地文件或有效 HTTP(S) 引用：{file_value}", path))
    return index
