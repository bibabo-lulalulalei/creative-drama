"""Workflow state, user confirmations and operation-log checks."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from .common import (
    episode_dirs, issue, load_json,
    parse_iso_time, plan_revision, target_stage,
)
from .constants import (
    CONFIRMATION_MODES, CURRENT_STAGE_ACTIVE_VALUES, EPISODE_STAGES, FORBIDDEN_TOOL_TERMS,
    STAGES, STATUS_VALUES,
)


def load_confirmation_records(
    root: Path,
    issues: list[dict[str, Any]],
    required: bool,
    require_planning_interaction: bool = False,
) -> list[dict[str, Any]]:
    path = root / "00_制作控制/用户确认记录.jsonl"
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if required:
            issues.append(issue("error", "confirmation_log_missing", "阶段已确认或推进到后续阶段时必须存在用户确认记录。", path))
        return []
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "confirmation_log_unreadable", f"用户确认记录无法读取：{exc}", path))
        return []

    records: list[dict[str, Any]] = []
    full_revisions_by_scope: dict[tuple[str, str], set[int]] = {}
    interaction_call_ids: dict[str, tuple[str, str, str]] = {}
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            issues.append(issue("error", "confirmation_log_blank_line", f"用户确认记录第 {line_number} 行为空行。", path))
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(issue("error", "confirmation_log_json_invalid", f"用户确认记录第 {line_number} 行不是有效 JSON：{exc}", path))
            continue
        if not isinstance(data, dict):
            issues.append(issue("error", "confirmation_log_row_invalid", f"用户确认记录第 {line_number} 行必须是对象。", path))
            continue
        stage = data.get("stage")
        if stage not in STAGES:
            issues.append(issue("error", "confirmation_stage_invalid", f"用户确认记录第 {line_number} 行 stage 无效。", path))
        episode_id = str(data.get("episode_id") or "")
        if episode_id and not re.fullmatch(r"ep_[1-9]\d*", episode_id):
            issues.append(issue("error", "confirmation_episode_id_invalid", f"用户确认记录第 {line_number} 行 episode_id 无效。", path))
        if stage == "planning" and episode_id:
            issues.append(issue("error", "project_confirmation_has_episode", f"用户确认记录第 {line_number} 行 planning 阶段不得填写 episode_id。", path))
        if stage in EPISODE_STAGES - {"script"} and not episode_id:
            issues.append(issue("error", "episode_confirmation_missing_episode_id", f"用户确认记录第 {line_number} 行 {stage} 阶段必须填写 episode_id。", path))
        if data.get("decision") != "confirmed":
            issues.append(issue("error", "confirmation_decision_invalid", f"用户确认记录第 {line_number} 行 decision 必须是 confirmed。", path))
        if data.get("confirmation_mode") not in CONFIRMATION_MODES:
            issues.append(issue("error", "confirmation_mode_invalid", f"用户确认记录第 {line_number} 行 confirmation_mode 无效。", path))
        if not isinstance(data.get("revision"), int) or isinstance(data.get("revision"), bool):
            issues.append(issue("error", "confirmation_revision_invalid", f"用户确认记录第 {line_number} 行 revision 必须是整数。", path))
        if not str(data.get("user_message") or "").strip():
            issues.append(issue("error", "confirmation_user_message_missing", f"用户确认记录第 {line_number} 行 user_message 不能为空。", path))
        confirmed_at = str(data.get("confirmed_at") or "")
        if parse_iso_time(confirmed_at) is None:
            issues.append(issue("error", "confirmation_time_invalid", f"用户确认记录第 {line_number} 行 confirmed_at 必须是带时区 ISO-8601 时间。", path))
        call_id = str(data.get("interaction_ask_call_id") or "").strip()
        if call_id:
            purpose_key = (str(data.get("confirmation_purpose") or ""), str(data.get("interaction_ask_result") or ""), f"{stage}:{episode_id}")
            previous_purpose = interaction_call_ids.get(call_id)
            if previous_purpose is not None and previous_purpose != purpose_key:
                issues.append(issue("error", "interaction_call_id_reused", f"用户确认记录第 {line_number} 行 interaction_ask_call_id 已被其他用途使用。", path))
            interaction_call_ids[call_id] = purpose_key
        if data.get("confirmation_mode") == "incremental":
            base_revision = data.get("base_revision")
            if not isinstance(base_revision, int) or isinstance(base_revision, bool):
                issues.append(issue("error", "confirmation_base_revision_invalid", f"用户确认记录第 {line_number} 行 incremental 必须填写整数 base_revision。", path))
            elif base_revision not in full_revisions_by_scope.get((str(stage), episode_id), set()):
                issues.append(issue("error", "confirmation_base_revision_missing", f"用户确认记录第 {line_number} 行找不到同阶段对应的全量确认 base_revision。", path))
            if not isinstance(data.get("changed_artifacts"), list) or not data.get("changed_artifacts"):
                issues.append(issue("error", "confirmation_changed_artifacts_missing", f"用户确认记录第 {line_number} 行 incremental 必须填写 changed_artifacts。", path))
            if not isinstance(data.get("impact_scope"), list) or not data.get("impact_scope"):
                issues.append(issue("error", "confirmation_impact_scope_missing", f"用户确认记录第 {line_number} 行 incremental 必须填写 impact_scope。", path))
        elif data.get("confirmation_mode") == "full" and isinstance(data.get("revision"), int) and not isinstance(data.get("revision"), bool):
            full_revisions_by_scope.setdefault((str(stage), episode_id), set()).add(data["revision"])
        records.append(data)
    if require_planning_interaction:
        planning_records = [record for record in records if record.get("stage") == "planning"]
        latest_revision = max(
            (
                record.get("revision")
                for record in planning_records
                if isinstance(record.get("revision"), int) and not isinstance(record.get("revision"), bool)
            ),
            default=None,
        )
        latest_records = [record for record in planning_records if record.get("revision") == latest_revision]
        expected_purpose = "project_execution"
        expected_result = "proceed_project"
        if not any(
            record.get("confirmation_purpose") == expected_purpose
            and str(record.get("interaction_ask_call_id") or "").strip()
            and record.get("interaction_ask_result") == expected_result
            for record in latest_records
        ):
            issues.append(issue("error", "planning_interaction_confirmation_missing", f"最新 planning 确认必须记录 {expected_purpose}、真实 interaction_ask_call_id 和 {expected_result}。", path))
    return records


def check_operation_log_tools(root: Path, issues: list[dict[str, Any]]) -> None:
    path = root / "00_制作控制/操作日志.jsonl"
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "operation_log_unreadable", f"操作日志无法读取：{exc}", path))
        return
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        tool_name = str(data.get("tool") or "").strip().lower()
        if tool_name in FORBIDDEN_TOOL_TERMS:
            issues.append(issue("error", "forbidden_media_tool_used", f"操作日志第 {line_number} 行登记了禁用工具 {tool_name}；媒体处理必须使用 tools/video/ffmpeg_tool.py 本地链路。", path))


def has_confirmation(
    records: list[dict[str, Any]],
    stage: str,
    revision: int | None,
    episode_id: str | None = None,
) -> bool:
    for record in records:
        if record.get("stage") != stage or record.get("decision") != "confirmed":
            continue
        if revision is not None and record.get("revision") != revision:
            continue
        record_episode = str(record.get("episode_id") or "")
        if episode_id is not None and record_episode != episode_id:
            continue
        if episode_id is None and record_episode:
            continue
        if str(record.get("user_message") or "").strip():
            return True
    return False


def check_state(root: Path, plan: Any, issues: list[dict[str, Any]]) -> None:
    state_path = root / "00_制作控制/制作状态.json"
    state = load_json(state_path, issues, required=False)
    if not isinstance(state, dict):
        return
    current = state.get("current_stage")
    current_episode = state.get("current_episode")
    phases = state.get("phases")
    if current not in STAGES:
        issues.append(issue("error", "current_stage_invalid", "current_stage 不是有效阶段。", state_path))
    if not isinstance(phases, dict):
        issues.append(issue("error", "phases_invalid", "phases 必须是对象。", state_path))
        return
    revision = plan_revision(plan, state)
    target = target_stage(plan)
    # objective.target_stage 合法性由随各阶段运行的 check_plan_durations 统一上报，此处不重复。
    episode_ids = [episode_id for episode_id, _ in episode_dirs(root)]
    needs_confirmations = False
    for stage in STAGES:
        value = phases.get(stage)
        if value not in STATUS_VALUES:
            issues.append(issue("error", "phase_status_invalid", f"{stage} 状态无效。", state_path))
        if value == "confirmed":
            needs_confirmations = True
    project_level_stage = current == "planning" or (current == "script" and current_episode in {None, ""})
    if project_level_stage:
        if current_episode not in {None, ""}:
            issues.append(issue("error", "current_episode_must_be_empty", f"current_stage={current} 时 current_episode 必须为空。", state_path))
        current_index = STAGES.index(current)
        for index, stage in enumerate(STAGES):
            value = phases.get(stage)
            if index < current_index and value != "confirmed":
                issues.append(issue("error", "phase_order_invalid", f"{stage} 应先完成后再进入 {current}。", state_path))
            if index > current_index and value not in {"pending", "invalidated"}:
                issues.append(issue("error", "future_phase_status_invalid", f"{stage} 晚于 current_stage={current}，只能是 pending 或 invalidated。", state_path))
            if index == current_index:
                allowed_current = set(CURRENT_STAGE_ACTIVE_VALUES)
                if current == "final" or current == target:
                    allowed_current.add("confirmed")
                if value not in allowed_current:
                    issues.append(issue("error", "current_phase_status_invalid", f"{stage} 是 current_stage，状态不能是 {value}。", state_path))
        if current_index > 0:
            needs_confirmations = True
    elif current in EPISODE_STAGES:
        if current_episode not in episode_ids:
            issues.append(issue("error", "current_episode_invalid", "逐集生产阶段必须把 current_episode 指向计划内分集。", state_path))
        if target in STAGES and STAGES.index(current) > STAGES.index(target):
            issues.append(issue("error", "current_stage_beyond_target", f"current_stage={current} 不得晚于 objective.target_stage={target}。", state_path))
        if phases.get("planning") != "confirmed":
            issues.append(issue("error", "project_prerequisite_not_confirmed", "进入逐集生产前 phases.planning 必须为 confirmed。", state_path))
        if phases.get("script") != "confirmed":
            issues.append(issue("error", "project_prerequisite_not_confirmed", "进入逐集生产前项目级 phases.script 必须为 confirmed。", state_path))
        needs_confirmations = True
    confirmations = load_confirmation_records(
        root,
        issues,
        needs_confirmations,
        require_planning_interaction=target in {"video", "final"},
    )
    for stage in ("planning", "script"):
        value = phases.get(stage)
        required_revision = revision if stage == current and current_episode in {None, ""} else None
        if value == "confirmed" and not has_confirmation(confirmations, stage, required_revision):
            detail = "同阶段、同 revision" if stage == current else "同阶段"
            issues.append(issue("error", "phase_confirmation_missing", f"{stage} 已 confirmed，但缺少{detail}的有效用户确认记录。", state_path))
    episodes = state.get("episodes")
    if not isinstance(episodes, dict):
        issues.append(issue("error", "episode_states_invalid", "制作状态.json.episodes 必须是对象并覆盖全部计划分集。", state_path))
        return
    state_episode_ids = set(episodes)
    expected_episode_ids = set(episode_ids)
    if state_episode_ids != expected_episode_ids:
        missing = sorted(expected_episode_ids - state_episode_ids)
        extra = sorted(state_episode_ids - expected_episode_ids)
        if missing:
            issues.append(issue("error", "episode_states_missing", f"制作状态.json.episodes 缺少计划分集：{missing}", state_path))
        if extra:
            issues.append(issue("error", "episode_states_unplanned", f"制作状态.json.episodes 包含计划外分集：{extra}", state_path))
    if isinstance(episodes, dict):
        for episode_id, episode_state in episodes.items():
            if not re.fullmatch(r"ep_[1-9]\d*", str(episode_id)):
                issues.append(issue("error", "episode_id_invalid", f"分集 ID 无效：{episode_id}", state_path))
            statuses = episode_state.get("stage_status") if isinstance(episode_state, dict) else None
            if not isinstance(statuses, dict):
                issues.append(issue("error", "episode_stage_statuses_invalid", f"{episode_id}.stage_status 必须是对象。", state_path))
                continue
            missing_stages = [stage for stage in EPISODE_STAGES if stage not in statuses]
            if missing_stages:
                issues.append(issue("error", "episode_stage_statuses_missing", f"{episode_id}.stage_status 缺少阶段：{missing_stages}", state_path))
            if isinstance(statuses, dict):
                for stage, value in statuses.items():
                    if stage in EPISODE_STAGES and value not in STATUS_VALUES:
                        issues.append(issue("error", "episode_stage_status_invalid", f"{episode_id}.{stage} 状态无效。", state_path))
                if current == "planning":
                    for stage in EPISODE_STAGES:
                        value = statuses.get(stage)
                        if value is not None and value not in {"pending", "invalidated"}:
                            issues.append(issue("error", "episode_stage_before_planning_confirmed", f"项目仍在 planning，{episode_id}.{stage} 只能是 pending 或 invalidated。", state_path))
                elif current == "script" and current_episode in {None, ""}:
                    script_value = statuses.get("script")
                    if script_value not in {"pending", "invalidated"}:
                        issues.append(issue("error", "episode_script_started_before_global_confirmation", f"{episode_id}.script 在项目级故事包确认前只能是 pending 或 invalidated。", state_path))
                    for stage in STAGES[2:]:
                        value = statuses.get(stage)
                        if value is not None and value not in {"pending", "invalidated"}:
                            issues.append(issue("error", "episode_stage_before_script_confirmed", f"项目级故事包尚未确认，{episode_id}.{stage} 只能是 pending 或 invalidated。", state_path))
                elif current in EPISODE_STAGES and current_episode in episode_ids:
                    episode_position = episode_ids.index(episode_id) if episode_id in episode_ids else -1
                    active_position = episode_ids.index(str(current_episode))
                    if episode_position < active_position:
                        completed_through = STAGES.index(target) if target in EPISODE_STAGES else STAGES.index("final")
                        for stage in EPISODE_STAGES:
                            stage_index = STAGES.index(stage)
                            if stage_index <= completed_through:
                                if statuses.get(stage) != "confirmed":
                                    issues.append(issue("error", "previous_episode_incomplete", f"{episode_id}.{stage} 必须完成后才能推进 {current_episode}。", state_path))
                            elif statuses.get(stage) not in {"pending", "invalidated"}:
                                issues.append(issue("error", "previous_episode_beyond_target", f"{episode_id}.{stage} 超出 target_stage={target}，只能是 pending 或 invalidated。", state_path))
                    elif episode_position > active_position:
                        if statuses.get("script") not in {"pending", "invalidated"}:
                            issues.append(issue("error", "future_episode_script_started_early", f"{episode_id}.script 在该集开始制作前只能是 pending 或 invalidated。", state_path))
                        for stage in STAGES[2:]:
                            if statuses.get(stage) not in {"pending", "invalidated"}:
                                issues.append(issue("error", "future_episode_started_early", f"{episode_id}.{stage} 在 {current_episode} 达到目标前只能是 pending 或 invalidated。", state_path))
                    else:
                        current_episode_index = STAGES.index(current)
                        if current != "script" and statuses.get("script") != "confirmed":
                            issues.append(issue("error", "current_episode_script_incomplete", f"{episode_id}.script 必须在后续生产前确认为 confirmed。", state_path))
                        for stage in EPISODE_STAGES:
                            value = statuses.get(stage)
                            index = STAGES.index(stage)
                            if index < current_episode_index and value != "confirmed":
                                issues.append(issue("error", "episode_phase_order_invalid", f"{episode_id}.{stage} 应先完成后再进入 {current}。", state_path))
                            if index > current_episode_index and value not in {"pending", "invalidated"}:
                                issues.append(issue("error", "episode_future_phase_status_invalid", f"{episode_id}.{stage} 晚于当前集 current_stage={current}，只能是 pending 或 invalidated。", state_path))
                            if index == current_episode_index:
                                allowed_current = set(CURRENT_STAGE_ACTIVE_VALUES)
                                current_is_last_episode = episode_position == len(episode_ids) - 1
                                if current_is_last_episode and current in {"final", target}:
                                    allowed_current.add("confirmed")
                                if value not in allowed_current:
                                    issues.append(issue("error", "episode_current_phase_status_invalid", f"{episode_id}.{stage} 是当前集阶段，状态不能是 {value}。", state_path))
                for stage in EPISODE_STAGES:
                    if statuses.get(stage) != "confirmed":
                        continue
                    if stage == "script":
                        if not has_confirmation(confirmations, "script", None, episode_id):
                            issues.append(issue("error", "episode_script_confirmation_missing", f"{episode_id}.script 已 confirmed，但缺少绑定该集的详细剧本确认记录。", state_path))
                        continue
                    required_revision = revision if episode_id == current_episode and stage == current else None
                    if not has_confirmation(
                        confirmations,
                        stage,
                        required_revision,
                        episode_id,
                    ):
                        issues.append(issue("error", "episode_confirmation_missing", f"{episode_id}.{stage} 已 confirmed，但缺少绑定该集的有效确认记录。", state_path))
        for stage in STAGES[2:]:
            if phases.get(stage) != "confirmed":
                continue
            stage_values = [
                episode_state.get("stage_status", {}).get(stage)
                for episode_state in episodes.values()
                if isinstance(episode_state, dict) and isinstance(episode_state.get("stage_status"), dict)
            ]
            if not stage_values or any(value != "confirmed" for value in stage_values):
                issues.append(issue("error", "aggregate_phase_confirmed_early", f"phases.{stage} 只有在全部分集该阶段完成后才能写 confirmed。", state_path))
        if current in EPISODE_STAGES and current_episode in episodes:
            current_statuses = episodes[current_episode].get("stage_status") if isinstance(episodes[current_episode], dict) else {}
            current_index = STAGES.index(current)
            for stage in STAGES[2:]:
                phase_value = phases.get(stage)
                stage_index = STAGES.index(stage)
                completed_values = {"confirmed"}
                all_completed = all(
                    isinstance(episode_state, dict)
                    and isinstance(episode_state.get("stage_status"), dict)
                    and episode_state["stage_status"].get(stage) in completed_values
                    for episode_state in episodes.values()
                )
                any_completed = any(
                    isinstance(episode_state, dict)
                    and isinstance(episode_state.get("stage_status"), dict)
                    and episode_state["stage_status"].get(stage) in completed_values
                    for episode_state in episodes.values()
                )
                if all_completed:
                    if phase_value != "confirmed":
                        issues.append(issue("error", "aggregate_phase_status_mismatch", f"phases.{stage} 必须反映全部分集已完成。", state_path))
                elif stage == current:
                    current_value = current_statuses.get(stage) if isinstance(current_statuses, dict) else None
                    if phase_value != current_value:
                        issues.append(issue("error", "aggregate_current_phase_mismatch", f"phases.{stage} 必须与 {current_episode}.{stage} 当前活动状态一致。", state_path))
                elif stage_index > current_index and phase_value not in ({"pending", "invalidated", "in_progress"} if any_completed else {"pending", "invalidated"}):
                    issues.append(issue("error", "aggregate_future_phase_started", f"phases.{stage} 与已完成分集的聚合状态不一致。", state_path))
                elif stage_index < current_index and phase_value not in {"in_progress", "confirmed"}:
                    issues.append(issue("error", "aggregate_previous_phase_invalid", f"phases.{stage} 已有分集完成但尚未全量完成，必须保持 in_progress 或合法完成态。", state_path))
