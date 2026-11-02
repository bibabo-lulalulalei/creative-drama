"""Planning duration contracts and explicit confirmation bounds."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any
from timeline_core import to_ms
from .common import check_duration_pair, has_meaningful_value, issue
from .constants import STAGES
from .state import load_confirmation_records


def check_plan_durations(root: Path, plan: Any, issues: list[dict[str, Any]]) -> dict[str, int | float]:
    expected: dict[str, int | float] = {}
    if not isinstance(plan, dict):
        return expected
    path = root / "00_制作控制/drama_plan.json"
    if not isinstance(plan.get("revision"), int) or isinstance(plan.get("revision"), bool) or plan.get("revision") < 1:
        issues.append(issue("error", "plan_revision_invalid", "drama_plan.revision 必须是正整数。", path))
    objective = plan.get("objective")
    if not isinstance(objective, dict) or objective.get("target_stage") not in STAGES:
        issues.append(issue("error", "target_stage_invalid", "drama_plan.objective.target_stage 必须是有效阶段。", path))
    if not str(plan.get("selected_direction_id") or "").strip():
        issues.append(issue("error", "selected_direction_missing", "drama_plan 必须锁定 selected_direction_id。", path))
    creative_mechanism = plan.get("creative_mechanism")
    if not isinstance(creative_mechanism, dict):
        issues.append(issue("error", "creative_mechanism_missing", "drama_plan 必须填写 creative_mechanism。", path))
    else:
        selection_mode = creative_mechanism.get("selection_mode")
        if selection_mode not in {"divergent", "user_locked"}:
            issues.append(issue("error", "creative_mechanism_selection_mode_invalid", "creative_mechanism.selection_mode 必须为 divergent 或 user_locked。", path))
        candidates = creative_mechanism.get("candidates")
        candidate_primaries: list[str] = []
        if not isinstance(candidates, list) or not candidates:
            expected_text = "真实采用的"
            issues.append(issue("error", "creative_mechanism_candidates_invalid", f"当前 selection_mode 的 creative_mechanism.candidates 必须包含{expected_text}候选。", path))
        else:
            for index, candidate in enumerate(candidates, start=1):
                supporting = candidate.get("supporting") if isinstance(candidate, dict) else None
                if not isinstance(candidate, dict) or not has_meaningful_value(candidate.get("primary")):
                    issues.append(issue("error", "creative_mechanism_primary_missing", f"创意机制候选 {index} 必须填写主机制。", path))
                else:
                    candidate_primaries.append(str(candidate["primary"]).strip())
                if not isinstance(supporting, list):
                    issues.append(issue("error", "creative_mechanism_supporting_invalid", f"创意机制候选 {index} supporting 必须是实际辅助机制列表，可空。", path))
        selected_primary = str(creative_mechanism.get("primary") or "").strip()
        if not selected_primary:
            issues.append(issue("error", "creative_mechanism_selected_missing", "creative_mechanism.primary 必须锁定唯一主机制。", path))
        elif candidate_primaries and selected_primary not in candidate_primaries:
            issues.append(issue("error", "creative_mechanism_selected_unknown", "creative_mechanism.primary 必须来自当前候选主机制之一。", path))
        selected_supporting = creative_mechanism.get("supporting")
        if not isinstance(selected_supporting, list):
            issues.append(issue("error", "creative_mechanism_selected_supporting_invalid", "creative_mechanism.supporting 必须是实际辅助机制列表，可空。", path))
    rhythm_design = plan.get("rhythm_design", {})
    if not isinstance(rhythm_design, dict):
        issues.append(issue("error", "rhythm_design_invalid", "rhythm_design 是可选定性观看意图。", path))
    elif "duration_allocation" in rhythm_design:
        issues.append(issue("error", "timing_budget_input_forbidden", "规划不得预分配时间。", path))
    strategy_contracts = {
        "audience_plan": (
            "target_audience",
            "core_pain_or_desire",
            "platform",
            "evidence_status",
            "viewing_focus",
            "emotional_payoff",
            "platform_viewing_context",
            "expression_boundaries",
        ),
        "type_strategy": ("format", "subject_route", "genre", "story_engine", "audience_promise", "narrative_structure", "main_path"),
        "highlight_strategy": ("primary_story_engine_id", "project_signature", "highlight_pillars", "distribution_policy", "rejected_cliches"),
        "style_contract": ("anchor_type", "anchor", "lighting", "color", "composition", "material", "camera_tendency", "sound_tendency", "excluded_mechanisms"),
    }
    for contract_name, required_fields in strategy_contracts.items():
        contract = plan.get(contract_name)
        if not isinstance(contract, dict):
            issues.append(issue("error", f"{contract_name}_missing", f"drama_plan 缺少 {contract_name}。", path))
            continue
        for field in required_fields:
            if not has_meaningful_value(contract.get(field)):
                issues.append(issue("error", f"{contract_name}_field_missing", f"{contract_name}.{field} 必须填写。", path))
        if contract_name == "audience_plan" and isinstance(contract, dict):
            source_values = contract.get("execution_sources")
            expected_sources = {
                "viewing_focus": "audience_plan.viewing_focus",
                "emotional_payoff": "audience_plan.emotional_payoff",
                "platform_viewing_context": "audience_plan.platform_viewing_context",
                "expression_boundaries": "audience_plan.expression_boundaries",
            }
            if source_values != expected_sources:
                issues.append(issue("error", "audience_plan_execution_sources_invalid", "audience_plan.execution_sources 必须逐项锁定四个 audience_execution 源字段。", path))
    scale = plan.get("scale_plan")
    if not isinstance(scale, dict):
        issues.append(issue("error", "scale_plan_missing", "drama_plan 缺少 scale_plan。", path))
        return expected
    count = scale.get("episode_count")
    durations = scale.get("episode_durations_s")
    displays = scale.get("episode_duration_displays")
    total = scale.get("total_duration_s")
    total_display = scale.get("total_duration_display")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        issues.append(issue("error", "episode_count_invalid", "episode_count 必须是正整数。", path))
        return expected
    if not isinstance(durations, list) or len(durations) != count:
        issues.append(issue("error", "episode_durations_invalid", "episode_durations_s 数量必须等于 episode_count。", path))
        return expected
    if isinstance(displays, list) and len(displays) != count:
        issues.append(issue("error", "episode_duration_displays_invalid", "episode_duration_displays 数量必须等于 episode_count。", path))
    numeric: list[int] = []
    for index, seconds in enumerate(durations, start=1):
        try:
            milliseconds = to_ms(seconds, positive=True)
        except ValueError as exc:
            issues.append(issue("error", "episode_duration_invalid", f"第 {index} 集规划预测无效：{exc}。", path))
            continue
        numeric.append(milliseconds)
        expected[f"ep_{index}"] = seconds
        display = displays[index - 1] if isinstance(displays, list) and index - 1 < len(displays) else None
        check_duration_pair(seconds, display, path, f"ep_{index}", issues)
    try:
        total_ms = to_ms(total, positive=True)
    except ValueError as exc:
        issues.append(issue("error", "total_duration_invalid", f"total_duration_s 规划预测无效：{exc}。", path))
    else:
        if len(numeric) == count and total_ms != sum(numeric):
            issues.append(issue("error", "total_duration_mismatch", "total_duration_s 必须等于各集 episode_durations_s 之和。", path))
        check_duration_pair(total, total_display, path, "total", issues, total_display=True)
    duration_contract = plan.get("duration_contract")
    if not isinstance(duration_contract, dict):
        issues.append(issue("error", "duration_contract_missing", "新制作需显式登记 unbounded/exact/target_band 及真实来源。", path))
    else:
        try:
            duration_contract_bounds(duration_contract)
        except ValueError as exc:
            issues.append(issue("error", "duration_contract_invalid", str(exc), path))
        mode = duration_contract.get("mode")
        if mode not in {"unbounded", "exact", "target_band"} or duration_contract.get("scope") not in {"deliverable", "episode", "project"}:
            issues.append(issue("error", "duration_contract_invalid", "时长合同枚举无效。", path))
        elif mode == "unbounded":
            if any(duration_contract.get(key) is not None for key in ("target_duration_s", "tolerance_ratio", "bounds")):
                issues.append(issue("error", "duration_contract_unbounded_invalid", "未限定时 target/tolerance/bounds 需 null。", path))
        else:
            records = load_confirmation_records(root, issues, required=True)
            matching = [row for row in records if row.get("confirmation_id") == duration_contract.get("confirmation_ref")]
            if (len(matching) != 1 or matching[0].get("decision") != "confirmed" or matching[0].get("valid", True) is False
                    or not str(matching[0].get("user_message") or "").strip()
                    or matching[0].get("duration_contract_snapshot") != {key: val for key, val in duration_contract.items() if key != "confirmation_ref"}):
                issues.append(issue("error", "duration_contract_source_invalid", "真实时长约束须回指同 scope/数值/性质的实际确认，不由估时推断。", path))
    delivery = plan.get("delivery_settings")
    if isinstance(delivery, dict):
        subtitle_enabled = delivery.get("subtitle_enabled")
        if not isinstance(subtitle_enabled, bool):
            issues.append(issue("error", "subtitle_enabled_invalid", "delivery_settings.subtitle_enabled 必须是布尔值；默认 false，用户明确要求字幕时为 true。", path))
        if subtitle_enabled is False and delivery.get("subtitle_policy") != "disabled":
            issues.append(issue("error", "subtitle_disabled_policy_missing", "字幕关闭时 subtitle_policy 必须为 disabled。", path))
        expected_deliverables = ["subtitle_master"] if subtitle_enabled is True else ["clean_master"]
        if delivery.get("final_deliverables") != expected_deliverables:
            issues.append(issue("error", "final_deliverables_invalid", f"final_deliverables 必须只包含单一最终视频版本：{expected_deliverables}。", path))
    return expected


def duration_contract_bounds(contract):
    mode = contract.get("mode")
    if mode == "unbounded":
        return None
    if mode not in {"exact", "target_band"}:
        raise ValueError("未知时长合同模式")
    target = to_ms(contract.get("target_duration_s"), positive=True) / 1000
    tolerance = contract.get("tolerance_ratio")
    if mode == "exact":
        if tolerance not in (None, 0) or isinstance(tolerance, bool):
            raise ValueError("exact 不接受非零容差")
        expected = [target, target]
    else:
        if (isinstance(tolerance, bool) or not isinstance(tolerance, (int, float))
                or not math.isfinite(tolerance) or not 0 <= tolerance < 1):
            raise ValueError("target_band 需明确有限 [0,1) 容差，不默认推断")
        expected = [target * (1 - tolerance), target * (1 + tolerance)]
    bounds = contract.get("bounds")
    if (not isinstance(bounds, list) or len(bounds) != 2
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in bounds)
            or any(abs(a - b) > 1e-6 for a, b in zip(bounds, expected))):
        raise ValueError("bounds 需显式 [下限,上限] 且与目标/性质/容差一致")
    if not isinstance(contract.get("source"), str) or not contract["source"].strip():
        raise ValueError("真实时长约束需保留用户来源原文")
    return tuple(bounds)
