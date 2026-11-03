"""Storyboard structure, coverage, references and asset reconciliation."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from timeline_core import to_ms
from .assets import blank_asset_index
from .causal import check_beat_coverage, check_causal_ledger, check_world_facts
from .common import (
    check_unique, episode_dirs, file_exists, has_meaningful_value, issue,
    load_json, markdown_table_column_counts, relative_file,
)
from .constants import ASSET_ID_PATTERN, ASSET_ROLE_COMPATIBILITY, REFERENCE_ROLES
from .prompts import marker_pattern
from .rhythm import (
    RhythmLibrary, check_episode_keyframe_request_plan, check_rhythm_reconciliation,
    check_segment_shot_count, check_shot_rhythm_fields,
)


def load_storyboard_index(root: Path, episode_id: str, issues: list[dict[str, Any]]) -> dict[str, Any]:
    path = root / f"episodes/{episode_id}/02_分镜/storyboard_{episode_id}.json"
    data = load_json(path, issues, required=False)
    if not isinstance(data, dict):
        return {
            "segments": set(),
            "shots": set(),
            "shot_durations": {},
            "segment_shots": {},
            "segment_durations": {},
            "required_reference_roles": {},
            "required_keyframe_roles": {},
            "keyframe_requests": {},
        }
    shots = data.get("shots") if isinstance(data.get("shots"), list) else []
    segments = data.get("segments") if isinstance(data.get("segments"), list) else []
    return {
        "segments": {item.get("segment_id") for item in segments if isinstance(item, dict) and isinstance(item.get("segment_id"), str)},
        "shots": {item.get("shot_id") for item in shots if isinstance(item, dict) and isinstance(item.get("shot_id"), str)},
        "shot_durations": {
            item.get("shot_id"): item.get("duration_s")
            for item in shots
            if isinstance(item, dict) and isinstance(item.get("shot_id"), str) and isinstance(item.get("duration_s"), (int, float))
        },
        "segment_shots": {
            item.get("segment_id"): item.get("shot_ids")
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("shot_ids"), list)
        },
        "segment_durations": {
            item.get("segment_id"): item.get("duration_s")
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("duration_s"), (int, float))
        },
        "segment_request_durations": {item.get("segment_id"): item.get("request_duration_s") for item in segments if isinstance(item, dict)},
        "required_reference_roles": {
            item.get("segment_id"): {role for role in item.get("required_reference_roles") if isinstance(role, str)}
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("required_reference_roles"), list)
        },
        "required_keyframe_roles": {
            item.get("segment_id"): {role for role in item.get("required_keyframe_roles") if isinstance(role, str)}
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("required_keyframe_roles"), list)
        },
        "keyframe_requests": {
            item.get("segment_id"): item.get("keyframe_requests")
            for item in segments
            if isinstance(item, dict) and isinstance(item.get("segment_id"), str) and isinstance(item.get("keyframe_requests"), list)
        },
    }


def check_storyboards(
    root: Path,
    plan: Any,
    issues: list[dict[str, Any]],
    episode_filter: str | None = None,
    asset_index: dict[str, Any] | None = None,
    rhythm: RhythmLibrary | None = None,
) -> None:
    if asset_index is None:
        asset_index = blank_asset_index()
    valid_beat_types: set[str] | None = None
    if rhythm is not None:
        if rhythm.library is not None:
            valid_beat_types = set(rhythm.library["beat_types"])
    for episode_id, episode_root in episode_dirs(root, episode_filter):
        path = episode_root / f"02_分镜/storyboard_{episode_id}.json"
        data = load_json(path, issues, required=False)
        if not isinstance(data, dict):
            continue
        if data.get("episode_id") != episode_id:
            issues.append(issue("error", "episode_id_mismatch", "storyboard episode_id 与目录不一致。", path))
        expected_director_card = f"episodes/{episode_id}/02_分镜/导演总控卡_{episode_id}.md"
        if data.get("director_control_card") != expected_director_card:
            issues.append(issue("error", "director_control_card_invalid", f"storyboard.director_control_card 必须指向 {expected_director_card}。", path))
        elif not file_exists(root, expected_director_card):
            issues.append(issue("error", "director_control_card_missing", "分镜阶段必须存在唯一导演总控卡。", path))
        expected_source_markdown = f"episodes/{episode_id}/02_分镜/分镜_完整分镜表_{episode_id}.md"
        source_markdown = relative_file(root, data.get("source_markdown"))
        if data.get("source_markdown") != expected_source_markdown:
            issues.append(issue("error", "storyboard_source_markdown_invalid", f"storyboard.source_markdown 必须指向 {expected_source_markdown}。", path))
        elif source_markdown is None or not source_markdown.is_file():
            issues.append(issue("error", "storyboard_source_markdown_missing", "十五列完整分镜表文件不存在。", path))
        else:
            try:
                table_text = source_markdown.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                issues.append(issue("error", "storyboard_source_markdown_unreadable", f"十五列完整分镜表无法读取：{exc}", source_markdown))
            else:
                if 15 not in markdown_table_column_counts(table_text):
                    issues.append(issue("error", "storyboard_fifteen_columns_missing", "完整分镜表必须包含一个十五列表格。", source_markdown))
        # scale_plan episode durations are allocation estimates; only internal shot/segment sums are exact.
        shots = data.get("shots")
        segments = data.get("segments")
        if not isinstance(shots, list) or not isinstance(segments, list):
            issues.append(issue("error", "storyboard_shape_invalid", "storyboard 必须包含 shots 和 segments 数组。", path))
            continue
        shot_ids = check_unique(shots, "shot_id", path, issues, "shots")
        segment_ids = check_unique(segments, "segment_id", path, issues, "segments")
        shot_to_segment = {
            item.get("shot_id"): item.get("segment_id")
            for item in shots
            if isinstance(item, dict) and isinstance(item.get("shot_id"), str)
        }
        scene_ids = {
            item.get("scene_id")
            for item in shots
            if isinstance(item, dict) and isinstance(item.get("scene_id"), str) and item.get("scene_id").strip()
        }
        shot_durations = {
            item.get("shot_id"): item.get("duration_s")
            for item in shots
            if isinstance(item, dict) and isinstance(item.get("shot_id"), str) and isinstance(item.get("duration_s"), (int, float))
        }
        if shot_durations and isinstance(data.get("duration_s"), (int, float)):
            try:
                if to_ms(data["duration_s"]) != sum(to_ms(v) for v in shot_durations.values()):
                    issues.append(issue("error", "shot_duration_total_mismatch", "shots.duration_s 之和必须等于 storyboard.duration_s。", path))
            except ValueError as exc:
                issues.append(issue("error", "timeline_number_invalid", str(exc), path))
        covered: list[str] = []
        for index, segment in enumerate(segments, start=1):
            if not isinstance(segment, dict):
                continue
            segment_id = segment.get("segment_id")
            segment_shots = segment.get("shot_ids")
            if not isinstance(segment_shots, list):
                issues.append(issue("error", "segment_shot_ids_invalid", f"{segment_id or index} 缺少 shot_ids 数组。", path))
                continue
            for shot_id in segment_shots:
                if shot_id not in shot_ids:
                    issues.append(issue("error", "segment_unknown_shot", f"{segment_id} 引用了不存在的 shot_id：{shot_id}", path))
                elif shot_to_segment.get(shot_id) not in {None, segment_id}:
                    issues.append(issue("error", "shot_segment_mismatch", f"{shot_id} 的 segment_id 与 segments[].shot_ids 不一致。", path))
            covered.extend(str(item) for item in segment_shots)
            # shot_mode/density 枚举门与一镜到底数量门不得依赖 duration_s 可解析，
            # 否则 SEG 漏填 duration_s 时整组门被绕过。
            check_segment_shot_count(
                segment_id,
                len(segment_shots),
                segment.get("shot_mode"),
                segment.get("density_profile"),
                path,
                issues,
            )
            if isinstance(segment.get("duration_s"), (int, float)):
                try:
                    declared = to_ms(segment["duration_s"])
                    calculated = sum(to_ms(shot_durations[s]) for s in segment_shots if s in shot_durations)
                except ValueError as exc:
                    issues.append(issue("error", "timeline_number_invalid", str(exc), path))
                    continue
                if calculated and declared != calculated:
                    issues.append(issue("error", "segment_duration_mismatch", f"{segment_id} duration_s 必须等于其 shot_ids 时长之和。", path))
            tail_mode = segment.get("tail_mode")
            if tail_mode not in {"continuous_motion", "cuttable_completion", "stable_hold", "loop_continuation"}:
                issues.append(issue("error", "segment_tail_mode_invalid", f"{segment_id or index} tail_mode 无效。", path))
            if index < len(segments) and tail_mode == "stable_hold" and not has_meaningful_value(segment.get("tail_hold_reason")):
                issues.append(issue("error", "intermediate_stable_hold_reason_missing", f"{segment_id or index} 是中间片段，使用 stable_hold 时必须填写 tail_hold_reason。", path))
            check_reference_plan(segment, path, issues)
        check_episode_keyframe_request_plan(segments, path, issues)
        check_asset_usage_reconciliation(data, asset_index, path, issues)
        check_world_facts(data, path, issues)
        check_beat_coverage(data, shot_ids, path, issues)
        check_shot_rhythm_fields(shots, path, issues, valid_beat_types)
        if rhythm is not None:
            check_rhythm_reconciliation(episode_id, episode_root, data, path, issues, rhythm)
        missing = shot_ids - set(covered)
        duplicated = {shot_id for shot_id in covered if covered.count(shot_id) > 1}
        if missing:
            issues.append(issue("error", "shots_not_covered", f"以下镜头未被任何 segment 覆盖：{sorted(missing)}", path))
        if duplicated:
            issues.append(issue("error", "shots_covered_multiple_times", f"以下镜头被多个 segment 重复覆盖：{sorted(duplicated)}", path))
        unknown_segment_refs = {seg for seg in shot_to_segment.values() if isinstance(seg, str) and seg not in segment_ids}
        if unknown_segment_refs:
            issues.append(issue("error", "shot_unknown_segment", f"shots 中引用了不存在的 segment_id：{sorted(unknown_segment_refs)}", path))
        audience_execution = data.get("audience_execution")
        if not isinstance(audience_execution, dict):
            issues.append(issue("error", "audience_execution_missing", "storyboard 必须登记从已确认 audience_plan 派生的 audience_execution。", path))
        else:
            source_revision = audience_execution.get("source_plan_revision")
            if not isinstance(source_revision, int) or isinstance(source_revision, bool) or source_revision < 1:
                issues.append(issue("error", "audience_execution_revision_invalid", "audience_execution.source_plan_revision 必须是正整数。", path))
            elif isinstance(plan, dict) and isinstance(plan.get("revision"), int) and source_revision != plan.get("revision"):
                issues.append(issue("error", "audience_execution_revision_mismatch", "audience_execution.source_plan_revision 必须等于当前已确认 drama_plan revision。", path))
            audience_plan = plan.get("audience_plan") if isinstance(plan, dict) and isinstance(plan.get("audience_plan"), dict) else {}
            for field in ("viewing_focus", "emotional_payoff", "platform_viewing_context", "expression_boundaries"):
                execution = audience_execution.get(field)
                if not isinstance(execution, dict) or not str(execution.get("contract") or "").strip():
                    issues.append(issue("error", "audience_execution_field_missing", f"audience_execution.{field} 必须填写 contract。", path))
                    continue
                expected_source = f"audience_plan.{field}"
                if execution.get("source_field") != expected_source:
                    issues.append(issue("error", "audience_execution_source_field_invalid", f"audience_execution.{field}.source_field 必须为 {expected_source}。", path))
                if execution.get("contract") != audience_plan.get(field):
                    issues.append(issue("error", "audience_execution_contract_mismatch", f"audience_execution.{field}.contract 必须逐字继承已确认 audience_plan.{field}。", path))
                refs = execution.get("scene_or_shot_ids")
                if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref.strip() for ref in refs):
                    issues.append(issue("error", "audience_execution_refs_missing", f"audience_execution.{field}.scene_or_shot_ids 必须列出落地场次或镜头。", path))
                    continue
                unknown_refs = sorted(set(refs) - shot_ids - scene_ids)
                if unknown_refs:
                    issues.append(issue("error", "audience_execution_ref_invalid", f"audience_execution.{field} 引用了不存在的场次或镜头：{unknown_refs}", path))
        script_path = episode_root / f"01_剧本/script_contract_{episode_id}.json"
        script_contract = load_json(script_path, issues, required=True)
        highlight_ledger = script_contract.get("highlight_ledger") if isinstance(script_contract, dict) else []
        if isinstance(script_contract, dict) and not isinstance(highlight_ledger, list):
            issues.append(issue("error", "highlight_ledger_invalid", "script_contract.highlight_ledger 必须是数组。", script_path))
            highlight_ledger = []
        primary_highlights = {
            item.get("highlight_id")
            for item in highlight_ledger or []
            if isinstance(item, dict) and item.get("role") == "primary" and isinstance(item.get("highlight_id"), str)
        }
        known_highlights = {
            item.get("highlight_id")
            for item in highlight_ledger or []
            if isinstance(item, dict) and isinstance(item.get("highlight_id"), str)
        }
        highlight_bindings = data.get("highlight_bindings")
        if not isinstance(highlight_bindings, list):
            issues.append(issue("error", "highlight_bindings_missing", "storyboard.highlight_bindings 必须是数组并覆盖剧本主要亮点。", path))
            highlight_bindings = []
        binding_ids = check_unique(highlight_bindings, "highlight_id", path, issues, "highlight_bindings")
        shot_positions = {
            shot_id: index
            for index, shot_id in enumerate(
                [
                    item.get("shot_id")
                    for item in shots
                    if isinstance(item, dict) and isinstance(item.get("shot_id"), str)
                ]
            )
        }
        inherited_aftereffects = data.get("inherited_aftereffect_bindings", [])
        if not isinstance(inherited_aftereffects, list):
            issues.append(issue("error", "inherited_aftereffect_bindings_invalid", "inherited_aftereffect_bindings 必须是数组。", path))
            inherited_aftereffects = []
        for inherited in inherited_aftereffects:
            if not isinstance(inherited, dict):
                issues.append(issue("error", "inherited_aftereffect_binding_invalid", "inherited_aftereffect_bindings 每项必须是对象。", path))
                continue
            binding_id = str(inherited.get("binding_id") or "")
            source_episode = str(inherited.get("source_episode_id") or "")
            source_highlight = str(inherited.get("source_highlight_id") or "")
            shot_refs = inherited.get("shot_ids")
            if not binding_id or not re.fullmatch(r"ep_[1-9]\d*", source_episode) or not source_highlight:
                issues.append(issue("error", "inherited_aftereffect_binding_fields_missing", "inherited_aftereffect_bindings 必须填写 binding_id、source_episode_id 和 source_highlight_id。", path))
            if not isinstance(shot_refs, list) or not shot_refs or not all(isinstance(ref, str) and ref.strip() for ref in shot_refs):
                issues.append(issue("error", "inherited_aftereffect_binding_shots_missing", f"{binding_id or '跨集余震承接'} 必须绑定本集真实 shot_ids。", path))
            else:
                unknown_refs = sorted(set(shot_refs) - shot_ids)
                if unknown_refs:
                    issues.append(issue("error", "inherited_aftereffect_binding_shot_invalid", f"{binding_id or '跨集余震承接'} 引用了不存在的本集镜头：{unknown_refs}", path))
            source_storyboard = load_json(root / f"episodes/{source_episode}/02_分镜/storyboard_{source_episode}.json", issues, required=False)
            source_bindings = source_storyboard.get("highlight_bindings") if isinstance(source_storyboard, dict) else []
            matching_sources = [
                item
                for item in source_bindings or []
                if isinstance(item, dict)
                and item.get("highlight_id") == source_highlight
                and isinstance(item.get("deferred_aftereffect_ref"), dict)
                and item["deferred_aftereffect_ref"].get("binding_id") == binding_id
                and item["deferred_aftereffect_ref"].get("episode_id") == episode_id
            ]
            if not matching_sources:
                issues.append(issue("error", "inherited_aftereffect_source_missing", f"{binding_id or '跨集余震承接'} 找不到来源集对应 deferred_aftereffect_ref。", path))
        for binding in highlight_bindings:
            if not isinstance(binding, dict):
                issues.append(issue("error", "highlight_binding_invalid", "highlight_bindings 每项必须是对象。", path))
                continue
            highlight_id = str(binding.get("highlight_id") or "")
            if known_highlights and highlight_id not in known_highlights:
                issues.append(issue("error", "highlight_binding_unknown", f"分镜绑定了剧本中不存在的亮点：{highlight_id}", path))
            segment_id = binding.get("segment_id")
            if segment_id not in segment_ids:
                issues.append(issue("error", "highlight_binding_segment_invalid", f"{highlight_id or '亮点绑定'} 引用了不存在的 segment_id：{segment_id}", path))
            payoff_positions: list[int] = []
            reaction_positions: list[int] = []
            for field in ("payoff_shot_ids", "reaction_shot_ids"):
                refs = binding.get(field)
                if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref.strip() for ref in refs):
                    issues.append(issue("error", "highlight_binding_shots_missing", f"{highlight_id or '亮点绑定'}.{field} 必须至少包含一个镜头。", path))
                    continue
                unknown_refs = sorted(set(refs) - shot_ids)
                if unknown_refs:
                    issues.append(issue("error", "highlight_binding_shot_invalid", f"{highlight_id or '亮点绑定'}.{field} 引用了不存在的镜头：{unknown_refs}", path))
                wrong_segment = sorted(ref for ref in refs if field == "payoff_shot_ids" and shot_to_segment.get(ref) not in {None, segment_id})
                if wrong_segment:
                    issues.append(issue("error", "highlight_binding_segment_mismatch", f"{highlight_id or '亮点绑定'} 的镜头不属于 {segment_id}：{wrong_segment}", path))
                valid_positions = [shot_positions[ref] for ref in refs if ref in shot_positions]
                if field == "payoff_shot_ids":
                    payoff_positions.extend(valid_positions)
                else:
                    reaction_positions.extend(valid_positions)
            if payoff_positions and reaction_positions and min(reaction_positions) < min(payoff_positions):
                issues.append(issue("error", "highlight_binding_reaction_before_payoff", f"{highlight_id or '亮点绑定'} 的反应镜头不得早于兑现镜头。", path))
            aftereffect_refs = binding.get("aftereffect_shot_ids")
            deferred_aftereffect_ref = binding.get("deferred_aftereffect_ref")
            if not isinstance(aftereffect_refs, list) or not all(isinstance(ref, str) and ref.strip() for ref in aftereffect_refs):
                issues.append(issue("error", "highlight_binding_aftereffect_invalid", f"{highlight_id or '亮点绑定'}.aftereffect_shot_ids 必须是数组。", path))
            elif aftereffect_refs:
                unknown_refs = sorted(set(aftereffect_refs) - shot_ids)
                if unknown_refs:
                    issues.append(issue("error", "highlight_binding_shot_invalid", f"{highlight_id or '亮点绑定'}.aftereffect_shot_ids 引用了不存在的本集镜头：{unknown_refs}", path))
                aftereffect_positions = [shot_positions[ref] for ref in aftereffect_refs if ref in shot_positions]
                preceding_positions = payoff_positions + reaction_positions
                if aftereffect_positions and preceding_positions and min(aftereffect_positions) < max(preceding_positions):
                    issues.append(issue("error", "highlight_binding_aftereffect_before_payoff", f"{highlight_id or '亮点绑定'} 的余震镜头不得早于兑现或反应镜头。", path))
                if deferred_aftereffect_ref not in (None, {}):
                    issues.append(issue("error", "highlight_binding_aftereffect_scope_conflict", f"{highlight_id or '亮点绑定'} 已填写本集余震时 deferred_aftereffect_ref 必须为空。", path))
            elif not isinstance(deferred_aftereffect_ref, dict):
                issues.append(issue("error", "highlight_binding_aftereffect_missing", f"{highlight_id or '亮点绑定'} 必须填写本集 aftereffect_shot_ids 或跨集 deferred_aftereffect_ref。", path))
            else:
                target_episode = str(deferred_aftereffect_ref.get("episode_id") or "")
                binding_id = str(deferred_aftereffect_ref.get("binding_id") or "")
                if not re.fullmatch(r"ep_[1-9]\d*", target_episode) or target_episode not in {item[0] for item in episode_dirs(root)}:
                    issues.append(issue("error", "highlight_binding_deferred_episode_invalid", f"{highlight_id or '亮点绑定'} deferred_aftereffect_ref.episode_id 必须是计划内分集。", path))
                elif int(target_episode.split("_", 1)[1]) <= int(episode_id.split("_", 1)[1]):
                    issues.append(issue("error", "highlight_binding_deferred_episode_order_invalid", f"{highlight_id or '亮点绑定'} deferred_aftereffect_ref 必须指向后续分集。", path))
                target_highlight = str(deferred_aftereffect_ref.get("highlight_id") or "")
                if not target_highlight or not binding_id:
                    issues.append(issue("error", "highlight_binding_deferred_ref_invalid", f"{highlight_id or '亮点绑定'} deferred_aftereffect_ref 必须填写 highlight_id 和 binding_id。", path))
                target_script = load_json(root / f"episodes/{target_episode}/01_剧本/script_contract_{target_episode}.json", issues, required=False)
                target_ledger = target_script.get("highlight_ledger") if isinstance(target_script, dict) else []
                target_highlight_ids = {
                    str(item.get("highlight_id"))
                    for item in target_ledger or []
                    if isinstance(item, dict) and str(item.get("highlight_id") or "").strip()
                }
                if target_highlight and target_highlight not in target_highlight_ids:
                    issues.append(issue("error", "highlight_binding_deferred_highlight_missing", f"{highlight_id or '亮点绑定'} deferred_aftereffect_ref.highlight_id 必须存在于目标集 script_contract.highlight_ledger。", path))
            for field in ("visual_execution", "performance_execution", "audio_execution", "compile_notes"):
                if not str(binding.get(field) or "").strip():
                    issues.append(issue("error", "highlight_binding_execution_missing", f"{highlight_id or '亮点绑定'} 缺少 {field}。", path))
        missing_primary = sorted(primary_highlights - binding_ids)
        if missing_primary:
            issues.append(issue("error", "primary_highlight_binding_missing", f"以下主要亮点未绑定到分镜：{missing_primary}", path))
        check_causal_ledger(
            root,
            data,
            episode_id,
            shots,
            shot_ids,
            shot_positions,
            shot_to_segment,
            [item.get("segment_id") for item in segments if isinstance(item, dict) and isinstance(item.get("segment_id"), str)],
            binding_ids,
            path,
            issues,
        )


def check_reference_plan(
    segment: dict[str, Any],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    refs = segment.get("reference_input_plan")
    if refs is None:
        issues.append(issue("error", "reference_input_plan_missing", "每个 SEG 必须填写 reference_input_plan。", path))
        return
    if not isinstance(refs, list):
        issues.append(issue("error", "reference_input_plan_invalid", "reference_input_plan 必须是数组。", path))
        return
    orders: list[int] = []
    for index, ref in enumerate(refs, start=1):
        if not isinstance(ref, dict):
            issues.append(issue("error", "reference_input_plan_invalid", f"第 {index} 条参考计划必须是对象。", path))
            continue
        order = ref.get("order")
        role = ref.get("role")
        if isinstance(order, int) and not isinstance(order, bool):
            orders.append(order)
            binding = str(ref.get("opening_binding", "") or "")
            if not re.search(marker_pattern("image", order), binding, flags=re.I):
                issues.append(issue("error", "opening_binding_marker_missing", f"第 {order} 张参考图缺少对应 <图片{order}>/<IMG{order}> 标记。", path))
        else:
            issues.append(issue("error", "reference_order_invalid", "参考图 order 必须是整数。", path))
        if role not in REFERENCE_ROLES:
            issues.append(issue("error", "reference_role_invalid", f"参考图职责无效：{role}", path))
        for field in ("planned_source", "opening_binding", "adopt", "exclude"):
            if not str(ref.get(field, "") or "").strip():
                issues.append(issue("error", "reference_input_plan_incomplete", f"参考图计划缺少 {field}。", path))
    if orders and sorted(orders) != list(range(1, len(orders) + 1)):
        issues.append(issue("error", "reference_order_not_contiguous", "参考图 order 必须从 1 连续递增。", path))


def parse_planned_source_asset(source: Any) -> tuple[str, str] | None:
    """从 planned_source 解析资产 ID 与版本。

    'PROP003_v01（毛驴）' -> ('PROP003', 'v01')；'PROP003（毛驴）' -> ('PROP003', '')；
    'CHR002:STATE01_v01' -> ('CHR002', '')（状态引用只取资产 ID）。
    """
    if not isinstance(source, str):
        return None
    match = ASSET_ID_PATTERN.match(source.strip())
    if not match:
        return None
    version = f"v{match.group(2)}" if match.group(2) else ""
    return match.group(1), version


def check_asset_usage_reconciliation(
    data: dict[str, Any],
    asset_index: dict[str, Any],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    """asset_usage_plan（需求侧台账）与各 SEG reference_input_plan（消费侧）的双向对账。

    方向1：台账登记绑定到某段的资产必须真实出现在该段输入计划中（缺一即 error）。
    方向2：输入计划使用了台账未登记的绑定时给 warning（临时增补必须回头登记）。
    只检查声明与执行的一致性，不判断资产是否应该出现。
    """
    segments = data.get("segments")
    if not isinstance(segments, list):
        return
    segment_ids_in_order = [
        s.get("segment_id")
        for s in segments
        if isinstance(s, dict) and isinstance(s.get("segment_id"), str)
    ]
    planned_by_segment: dict[str, dict[str, str]] = {}
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_id = segment.get("segment_id")
        refs = segment.get("reference_input_plan")
        if not isinstance(segment_id, str) or not isinstance(refs, list):
            continue
        planned: dict[str, str] = {}
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            parsed = parse_planned_source_asset(ref.get("planned_source"))
            if parsed is None:
                continue
            asset_id, version = parsed
            planned[asset_id] = version
            prefix_match = re.match(r"[A-Z]+", asset_id)
            compatible = ASSET_ROLE_COMPATIBILITY.get(prefix_match.group(0)) if prefix_match else None
            role = ref.get("role")
            if compatible and role not in compatible:
                issues.append(issue("error", "reference_role_asset_mismatch", f"{segment_id} 资产 {asset_id} 的职责 {role} 与资产类型不匹配。", path))
        planned_by_segment[segment_id] = planned

    usage = data.get("asset_usage_plan")
    if not isinstance(usage, list):
        issues.append(issue("error", "asset_usage_plan_missing", "storyboard 必须登记 asset_usage_plan（资产需求清单的结构化同源数据）。", path))
        return
    known_ids = asset_index.get("known_asset_ids", set())
    seen_pairs: set[tuple[str, str]] = set()
    registered_versions: dict[str, str] = {}
    for entry in usage:
        if not isinstance(entry, dict):
            issues.append(issue("error", "asset_usage_plan_invalid", "asset_usage_plan 每条必须是对象。", path))
            continue
        asset_id = entry.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            issues.append(issue("error", "asset_usage_plan_invalid", "asset_usage_plan 缺少 asset_id。", path))
            continue
        if known_ids and asset_id not in known_ids:
            issues.append(issue("error", "asset_usage_unknown_asset", f"asset_usage_plan 引用了未登记的资产：{asset_id}", path))
        version = entry.get("version")
        if isinstance(version, str) and version.strip():
            registered_versions[asset_id] = version.strip()
        seg_list = entry.get("segments")
        if not isinstance(seg_list, list) or not seg_list:
            issues.append(issue("error", "asset_usage_segments_invalid", f"{asset_id} 的 segments 必须是非空数组（可用 [\"*\"] 表示全部片段）。", path))
            continue
        expanded = segment_ids_in_order if "*" in seg_list else seg_list
        for segment_id in expanded:
            if segment_id not in planned_by_segment:
                issues.append(issue("error", "asset_usage_unknown_segment", f"{asset_id} 绑定了不存在的片段：{segment_id}", path))
                continue
            seen_pairs.add((asset_id, segment_id))
            if asset_id not in planned_by_segment[segment_id]:
                issues.append(issue("error", "asset_required_but_unplanned", f"{asset_id} 在 asset_usage_plan 中绑定 {segment_id}，但该段 reference_input_plan 未计划传入。", path))
            elif (
                asset_id in registered_versions
                and planned_by_segment[segment_id][asset_id]
                and planned_by_segment[segment_id][asset_id] != registered_versions[asset_id]
            ):
                issues.append(issue("error", "asset_version_inconsistent", f"{segment_id} 计划传入 {asset_id} {planned_by_segment[segment_id][asset_id]}，与台账登记版本 {registered_versions[asset_id]} 不一致。", path))
    for segment_id, planned in planned_by_segment.items():
        for asset_id in planned:
            if (asset_id, segment_id) not in seen_pairs:
                issues.append(issue("error", "asset_planned_but_unregistered", f"{segment_id} 计划传入 {asset_id}，但 asset_usage_plan 未登记该绑定；临时增补必须回头登记。", path))
