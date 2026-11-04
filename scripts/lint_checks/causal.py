"""World facts, beat coverage, collective profiles and causal ledgers."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from .common import check_unique, issue, load_json, read_text_file
from .constants import (
    BEAT_DISPOSITIONS, BREAKPOINT_RISKS, CAUSAL_REF_TYPES, CAUSAL_ROLES, EVIDENCE_VISIBILITIES,
    WORLD_FACT_CATEGORIES,
)


def check_world_facts(data: dict[str, Any], path: Path, issues: list[dict[str, Any]]) -> None:
    """inherited_world_facts 的结构检查：强制世界事实被显式登记并注明剧本出处。

    语义矛盾（如霜气 vs 中元节）不属于 lint 职责，由剧本-分镜对照审校步骤处理；
    本检查的意义是让审校有对照表可查。
    """
    facts = data.get("inherited_world_facts")
    if not isinstance(facts, list) or not facts:
        issues.append(issue("error", "world_facts_missing", "storyboard 必须登记 inherited_world_facts：从剧本继承的季节/节日/时辰/天气等世界事实。", path, hint='把剧本中的世界事实逐条登记（fact_id/category/statement/source 剧本出处），无出处的感官细节删除。python scripts/read_reference.py --file references/storyboard.md --section "### 世界事实承接合同（inherited_world_facts）"'))
        return
    check_unique(facts, "fact_id", path, issues, "inherited_world_facts")
    for index, fact in enumerate(facts, start=1):
        if not isinstance(fact, dict):
            issues.append(issue("error", "world_fact_invalid", f"第 {index} 条世界事实必须是对象。", path))
            continue
        if fact.get("category") not in WORLD_FACT_CATEGORIES:
            issues.append(issue("error", "world_fact_category_invalid", f"第 {index} 条世界事实 category 无效：{fact.get('category')}", path))
        if not str(fact.get("statement") or "").strip() or not str(fact.get("source") or "").strip():
            issues.append(issue("error", "world_fact_incomplete", f"第 {index} 条世界事实缺少 statement 或 source（剧本出处）。", path))


def check_beat_coverage(
    data: dict[str, Any],
    shot_ids: set[str],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    """beat_coverage 台账的结构检查：剧本每条动作/事件必须登记去向。

    dropped 必须给理由；kept/compressed/moved 必须落到真实存在的镜头。
    剧本 beat 的提取是语义工作，由分镜作者完成；lint 验证台账完整性与引用有效性。
    """
    beats = data.get("beat_coverage")
    if not isinstance(beats, list):
        issues.append(issue("error", "beat_coverage_missing", "storyboard 必须登记 beat_coverage：剧本每条动作/事件的去向台账。", path, hint='为 script_contract 每个 event_id 建一条处置行并绑定真实 target_shots；读 python scripts/read_reference.py --file references/storyboard.md --section "### 转换差异台账（beat_coverage）"'))
        return
    check_unique(beats, "beat_id", path, issues, "beat_coverage")
    for index, beat in enumerate(beats, start=1):
        if not isinstance(beat, dict):
            issues.append(issue("error", "beat_invalid", f"第 {index} 条 beat 必须是对象。", path))
            continue
        label = beat.get("beat_id") or f"第 {index} 条"
        disposition = beat.get("disposition", beat.get("status"))
        if disposition not in BEAT_DISPOSITIONS:
            issues.append(issue("error", "beat_disposition_invalid", f"{label} disposition 无效。", path))
            continue
        if not str(beat.get("summary") or "").strip() or not str(beat.get("scene") or "").strip():
            issues.append(issue("error", "beat_incomplete", f"{label} 缺少 scene 或 summary。", path))
        targets = beat.get("target_shots")
        if disposition == "dropped":
            if not str(beat.get("reason") or "").strip():
                issues.append(issue("error", "beat_drop_reason_missing", f"{label} 被 dropped 但未给理由。", path))
        else:
            if not isinstance(targets, list) or not targets:
                issues.append(issue("error", "beat_target_missing", f"{label} disposition={disposition} 时 target_shots 必须非空。", path))
            else:
                unknown = [t for t in targets if t not in shot_ids]
                if unknown:
                    issues.append(issue("error", "beat_unknown_shot", f"{label} 引用了不存在的镜头：{unknown}", path))


def collect_data_card_state_ids(root: Path, issues: list[dict[str, Any]]) -> set[str]:
    """asset_state 引用解析表：project_data_card 各主体 state_timeline 的 state_id 集合。"""
    card = load_json(root / "00_制作控制/project_data_card.json", issues, required=False)
    state_ids: set[str] = set()
    if isinstance(card, dict):
        for group in ("characters", "scenes", "props"):
            for item in card.get(group) or []:
                if not isinstance(item, dict):
                    continue
                for state in item.get("state_timeline") or []:
                    if isinstance(state, dict) and str(state.get("state_id") or "").strip():
                        state_ids.add(str(state["state_id"]).strip())
    return state_ids


def validate_collective_profiles(root: Path, issues: list[dict[str, Any]]) -> set[str]:
    """Validate the explicit visual profile contract for collective CHR records."""
    path = root / "00_制作控制/project_data_card.json"
    card = load_json(path, issues, required=False)
    collective_ids: set[str] = set()
    if not isinstance(card, dict):
        return collective_ids
    for index, item in enumerate(card.get("characters") or []):
        if not isinstance(item, dict):
            continue
        scope = item.get("entity_scope", "individual")
        if scope not in {"individual", "collective"}:
            issues.append(issue("error", "character_entity_scope_invalid", f"characters[{index}].entity_scope 必须为 individual 或 collective。", path))
            continue
        if scope != "collective":
            continue
        asset_id = str(item.get("character_id") or "")
        if not re.fullmatch(r"CHR\d+", asset_id):
            issues.append(issue("error", "collective_character_id_invalid", f"characters[{index}] 群像必须使用 CHR ID。", path))
        else:
            collective_ids.add(asset_id)
        profile = item.get("collective_profile")
        if not isinstance(profile, dict):
            issues.append(issue("error", "collective_profile_missing", f"{asset_id or f'characters[{index}]'} 必须填写 collective_profile。", path))
            continue
        if not str(profile.get("group_type") or "").strip():
            issues.append(issue("error", "collective_group_type_missing", f"{asset_id} collective_profile.group_type 不能为空。", path))
        count_range = profile.get("count_range")
        if not isinstance(count_range, dict):
            issues.append(issue("error", "collective_count_range_missing", f"{asset_id} collective_profile.count_range 必须包含 min/max。", path))
        else:
            minimum, maximum = count_range.get("min"), count_range.get("max")
            valid_ints = all(isinstance(value, int) and not isinstance(value, bool) for value in (minimum, maximum))
            if not valid_ints or minimum < 1 or maximum < minimum:
                issues.append(issue("error", "collective_count_range_invalid", f"{asset_id} collective_profile.count_range 必须满足 1 <= min <= max。", path))
        for field in ("age_and_gender_mix", "role_or_faction_mix", "wardrobe_palette_distribution", "silhouette_distinction_keys"):
            value = profile.get(field)
            if not isinstance(value, list) or not any(str(entry).strip() for entry in value):
                issues.append(issue("error", "collective_profile_field_missing", f"{asset_id} collective_profile.{field} 必须是非空数组。", path))
        for field in ("shared_props", "forbidden_features"):
            if not isinstance(profile.get(field), list):
                issues.append(issue("error", "collective_profile_field_invalid", f"{asset_id} collective_profile.{field} 必须是数组；无内容时填空数组。", path))
        if profile.get("voice_mode") not in {"none", "collective_ambience"}:
            issues.append(issue("error", "collective_voice_mode_invalid", f"{asset_id} collective_profile.voice_mode 必须为 none 或 collective_ambience。", path))
        refs = item.get("asset_refs") if isinstance(item.get("asset_refs"), dict) else {}
        if refs.get("collective_profile") != asset_id:
            issues.append(issue("error", "collective_asset_ref_mismatch", f"{asset_id} asset_refs.collective_profile 必须指向该群像 CHR。", path))
        identity = item.get("identity_locked")
        if isinstance(identity, dict) and str(identity.get("voice_id") or "").strip():
            issues.append(issue("error", "collective_individual_voice_invalid", f"{asset_id} 群像不能绑定单人 identity_locked.voice_id。", path))
    return collective_ids


def validate_causal_ref(
    ref: Any,
    owner: str,
    tables: dict[str, set[str]],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    """responds_to/trigger_source 的引用闭合：ref_type 枚举 + ref_id 按各自表查存在性。

    空表守卫：被引表整体缺失时存在性已由对应专项检查报错，此处跳过避免连锁误报。
    """
    if not isinstance(ref, dict):
        issues.append(issue("error", "causal_ref_invalid", f"{owner} 的引用必须是含 ref_type/ref_id 的对象。", path))
        return
    ref_type = ref.get("ref_type")
    if ref_type not in CAUSAL_REF_TYPES:
        issues.append(issue("error", "causal_ref_type_invalid", f"{owner} 的 ref_type 无效：{ref_type}（枚举 {sorted(CAUSAL_REF_TYPES)}）。", path))
        return
    ref_id = str(ref.get("ref_id") or "").strip()
    if not ref_id:
        issues.append(issue("error", "causal_ref_id_missing", f"{owner} 缺少 ref_id。", path))
        return
    table = tables.get(ref_type) or set()
    if table and ref_id not in table:
        issues.append(issue("error", "causal_ref_unknown", f"{owner} 引用了不存在的 {ref_type}：{ref_id}。", path))


def seam_invariant_cell(text: str, seam_id: str) -> str | None:
    """从连续性账本中提取某 SEAM 的 required_invariants 记录。

    优先按 Markdown 表格解析（表头含「必须保持/required_invariants」列，行含 seam_id）；
    否则在 seam_id 所在行起的短窗口内找 required_invariants 字样。返回 None 表示找不到记录。
    """
    lines = text.splitlines()
    header_index: int | None = None
    for line in lines:
        if "|" in line and ("必须保持" in line or "required_invariants" in line):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            for index, cell in enumerate(cells):
                if "必须保持" in cell or "required_invariants" in cell:
                    header_index = index
                    break
            if header_index is not None:
                break
    for line_no, line in enumerate(lines):
        if seam_id not in line:
            continue
        if header_index is not None and "|" in line:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if header_index < len(cells):
                return cells[header_index]
        window = lines[line_no : line_no + 8]
        for follow in window:
            if "required_invariants" in follow or "必须保持" in follow:
                return follow.strip()
        return ""
    return None


def check_causal_ledger(
    root: Path,
    data: dict[str, Any],
    episode_id: str,
    shots: list[Any],
    shot_ids: set[str],
    shot_positions: dict[str, int],
    shot_to_segment: dict[str, Any],
    segment_order: list[str],
    highlight_binding_ids: set[str],
    path: Path,
    issues: list[dict[str, Any]],
) -> None:
    """causal_ledger 与单镜因果字段的结构检查。

    只查客观项：引用闭合、shots[] 数组序时序、交叉反查必填、枚举合法。
    visibility_contract 措辞质量、遮挡是否真的看不见、反应是否合理等语义判断
    属于剧本-分镜对照审校（SKILL.md 分镜硬门五项编号清单第⑤项），不在此设卡。
    """
    beat_ids = {
        item.get("beat_id")
        for item in data.get("beat_coverage") or []
        if isinstance(item, dict) and isinstance(item.get("beat_id"), str)
    }
    fact_ids = {
        item.get("fact_id")
        for item in data.get("inherited_world_facts") or []
        if isinstance(item, dict) and isinstance(item.get("fact_id"), str)
    }
    ref_tables = {
        "beat": beat_ids,
        "shot": shot_ids,
        "asset_state": collect_data_card_state_ids(root, issues),
        "world_fact": fact_ids,
    }
    shots_by_id = {
        item.get("shot_id"): item
        for item in shots
        if isinstance(item, dict) and isinstance(item.get("shot_id"), str)
    }
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        shot_id = str(shot.get("shot_id") or "未命名镜头")
        role = shot.get("causal_role")
        if not isinstance(role, str) or not role.strip():
            issues.append(issue("error", "causal_role_missing", f"{shot_id} 缺少 causal_role（每镜必填，枚举 {sorted(CAUSAL_ROLES)}）。", path, hint='按该镜在因果链中的职责逐镜补 causal_role（五选一），transition 也要显式声明；读 python scripts/read_reference.py --file references/storyboard.md --section "## 单镜因果检查"'))
        elif role not in CAUSAL_ROLES:
            issues.append(issue("error", "causal_role_invalid", f"{shot_id} causal_role={role} 不在枚举 {sorted(CAUSAL_ROLES)} 内。", path, hint='改成五个合法枚举之一，并保证配套字段齐（reaction/result 需 responds_to，evidence 需 evidence_visibility）。python scripts/read_reference.py --file references/storyboard.md --section "## 单镜因果检查"'))
        responds_to = shot.get("responds_to")
        if role in {"reaction", "result"} and not isinstance(responds_to, dict):
            issues.append(issue("error", "causal_responds_to_missing", f"{shot_id} causal_role={role} 必须填写 responds_to。", path))
        if isinstance(responds_to, dict):
            validate_causal_ref(responds_to, f"{shot_id}.responds_to", ref_tables, path, issues)
            if not str(responds_to.get("trigger_fact") or "").strip():
                issues.append(issue("error", "causal_trigger_fact_missing", f"{shot_id}.responds_to 缺少 trigger_fact（该镜回应的已建立事实）。", path))
        visibility = shot.get("evidence_visibility")
        if visibility is not None and visibility not in EVIDENCE_VISIBILITIES:
            issues.append(issue("error", "evidence_visibility_invalid", f"{shot_id} evidence_visibility 无效：{visibility}（枚举 {sorted(EVIDENCE_VISIBILITIES)}）。", path, hint='按证据实际呈现方式选四枚举之一；选 occluded 必须在 establishes 写遮挡理由与揭示点。python scripts/read_reference.py --file references/storyboard.md --section "## 单镜因果检查"'))
        if visibility == "occluded" and not str(shot.get("establishes") or "").strip():
            issues.append(issue("error", "occluded_establishes_missing", f"{shot_id} evidence_visibility=occluded 时必须在 establishes 写明遮挡理由与揭示点。", path, hint='在 establishes 补「为何遮挡 + 在哪一镜揭示」；做不到可见承诺就改 evidence_visibility。python scripts/read_reference.py --file references/storyboard.md --section "## 单镜因果检查"'))

    ledger = data.get("causal_ledger")
    if not isinstance(ledger, list):
        issues.append(issue("error", "causal_ledger_missing", "storyboard 必须登记 causal_ledger 数组（无反应/证据依赖链的集登记空数组）。", path, hint='补 causal_ledger 字段：有跨镜证据反应链就逐条建链，没有就填空数组 []；读 python scripts/read_reference.py --file references/storyboard.md --section "### 因果链台账（causal_ledger）"'))
        ledger = []
    chain_ids = check_unique(ledger, "chain_id", path, issues, "causal_ledger")
    members: dict[str, set[str]] = {"evidence": set(), "reaction": set(), "result": set()}
    crossing_chains: list[tuple[str, set[str], set[str]]] = []
    for chain in ledger:
        if not isinstance(chain, dict):
            issues.append(issue("error", "causal_chain_invalid", "causal_ledger 每条必须是对象。", path))
            continue
        chain_id = str(chain.get("chain_id") or "未命名链")
        if not str(chain.get("trigger_fact") or "").strip():
            issues.append(issue("error", "causal_chain_trigger_fact_missing", f"{chain_id} 缺少 trigger_fact。", path))
        if not str(chain.get("visibility_contract") or "").strip():
            issues.append(issue("error", "causal_chain_visibility_contract_missing", f"{chain_id} 缺少 visibility_contract（证据在哪些镜头以什么程度必须可见/可听）。", path))
        trigger_source = chain.get("trigger_source")
        if not isinstance(trigger_source, dict):
            issues.append(issue("error", "causal_chain_trigger_source_missing", f"{chain_id} 缺少 trigger_source（ref_type/ref_id）。", path))
        else:
            validate_causal_ref(trigger_source, f"{chain_id}.trigger_source", ref_tables, path, issues)
        risk = chain.get("breakpoint_risk")
        if risk is not None and risk not in BREAKPOINT_RISKS:
            issues.append(issue("error", "causal_chain_breakpoint_risk_invalid", f"{chain_id} breakpoint_risk={risk} 不在 C1-C5 内。", path))
        binding_ref = chain.get("highlight_binding_ref")
        if binding_ref not in (None, "") and binding_ref not in highlight_binding_ids:
            issues.append(issue("error", "causal_chain_highlight_binding_ref_unknown", f"{chain_id} 的 highlight_binding_ref 指向不存在的亮点绑定：{binding_ref}。", path))
        positions: dict[str, list[int]] = {}
        shot_fields = (("evidence_shot_ids", "evidence"), ("reaction_shot_ids", "reaction"), ("result_shot_ids", "result"))
        for field, key in shot_fields:
            refs = chain.get(field)
            if refs is None:
                refs = []
            if not isinstance(refs, list) or not all(isinstance(ref, str) and ref.strip() for ref in refs):
                issues.append(issue("error", "causal_chain_shots_invalid", f"{chain_id}.{field} 必须是 shot_id 字符串数组。", path))
                refs = [ref for ref in refs if isinstance(ref, str)] if isinstance(refs, list) else []
            unknown = sorted(set(refs) - shot_ids)
            if unknown:
                issues.append(issue("error", "causal_chain_shot_unknown", f"{chain_id}.{field} 引用了不存在的本集镜头：{unknown}；跨集镜头登记 cross_episode_refs，不进本集数组。", path))
            valid = [ref for ref in refs if ref in shot_positions]
            positions[key] = [shot_positions[ref] for ref in valid]
            members[key].update(valid)
        cross_refs = chain.get("cross_episode_refs")
        if cross_refs is not None:
            if not isinstance(cross_refs, list):
                issues.append(issue("error", "causal_chain_cross_episode_refs_invalid", f"{chain_id}.cross_episode_refs 必须是数组。", path))
                cross_refs = []
            for entry in cross_refs:
                if not isinstance(entry, dict) or not re.fullmatch(r"ep_[1-9]\d*", str(entry.get("episode_id") or "")) or not str(entry.get("note") or "").strip():
                    issues.append(issue("error", "causal_chain_cross_episode_ref_invalid", f"{chain_id}.cross_episode_refs 每项必须含 episode_id（ep_N）与 note。", path))
                    continue
                target_episode = str(entry["episode_id"])
                target_storyboard = load_json(root / f"episodes/{target_episode}/02_分镜/storyboard_{target_episode}.json", issues, required=False)
                if isinstance(target_storyboard, dict):
                    target_ledger = target_storyboard.get("causal_ledger")
                    closed = isinstance(target_ledger, list) and any(
                        isinstance(target_chain, dict)
                        and any(
                            isinstance(back, dict) and back.get("episode_id") == episode_id
                            for back in (target_chain.get("cross_episode_refs") or [])
                        )
                        for target_chain in target_ledger
                    )
                    if not closed:
                        issues.append(issue("error", "causal_chain_cross_episode_not_closed", f"{chain_id} 引用 {target_episode}，但目标集 causal_ledger 没有回指 {episode_id} 的链。", path))
        if not any(positions.values()) and not cross_refs:
            issues.append(issue("error", "causal_chain_empty", f"{chain_id} 未引用任何本集镜头，也没有跨集引用（空链）。", path))
        evidence_pos = positions.get("evidence") or []
        reaction_pos = positions.get("reaction") or []
        result_pos = positions.get("result") or []
        if evidence_pos and reaction_pos and min(reaction_pos) < min(evidence_pos):
            issues.append(issue("error", "causal_chain_reaction_before_evidence", f"{chain_id} 的反应镜头早于证据镜头（按 shots[] 数组序）。", path))
        if reaction_pos and result_pos and min(result_pos) < max(reaction_pos):
            issues.append(issue("error", "causal_chain_result_before_reaction", f"{chain_id} 的结果镜头早于反应镜头（按 shots[] 数组序）。", path))
        evidence_segments = {
            shot_to_segment.get(ref)
            for ref in (chain.get("evidence_shot_ids") or [])
            if isinstance(ref, str) and shot_to_segment.get(ref)
        }
        reaction_segments = {
            shot_to_segment.get(ref)
            for ref in (chain.get("reaction_shot_ids") or [])
            if isinstance(ref, str) and shot_to_segment.get(ref)
        }
        crossing_chains.append((chain_id, evidence_segments, reaction_segments))

    for shot_id in sorted(members["evidence"]):
        shot = shots_by_id.get(shot_id) or {}
        if not str(shot.get("establishes") or "").strip():
            issues.append(issue("error", "causal_evidence_establishes_missing", f"{shot_id} 被因果链列为证据位，必须填写 establishes。", path))
        if shot.get("evidence_visibility") not in EVIDENCE_VISIBILITIES:
            issues.append(issue("error", "causal_evidence_visibility_missing", f"{shot_id} 被因果链列为证据位，必须填写 evidence_visibility（枚举 {sorted(EVIDENCE_VISIBILITIES)}）。", path))
    for shot_id in sorted(members["reaction"] | members["result"]):
        shot = shots_by_id.get(shot_id) or {}
        if not isinstance(shot.get("responds_to"), dict):
            issues.append(issue("error", "causal_reaction_responds_to_missing", f"{shot_id} 被因果链列为反应/结果位，必须填写 responds_to。", path))

    seams = data.get("seams") or []
    seam_by_pair = {
        (seam.get("from_segment"), seam.get("to_segment")): seam.get("seam_id")
        for seam in seams
        if isinstance(seam, dict)
    }
    segment_index = {segment_id: index for index, segment_id in enumerate(segment_order)}
    ledger_text: str | None = None
    ledger_path = root / f"episodes/{episode_id}/02_分镜/分镜_连续性账本_{episode_id}.md"
    for chain_id, evidence_segments, reaction_segments in crossing_chains:
        if not evidence_segments or not reaction_segments:
            continue
        evidence_max = max(segment_index.get(seg, -1) for seg in evidence_segments)
        reaction_min = min(segment_index.get(seg, len(segment_order)) for seg in reaction_segments)
        if evidence_max >= reaction_min:
            continue
        if ledger_text is None:
            ledger_text = read_text_file(ledger_path)
        for cut in range(evidence_max, reaction_min):
            pair = (segment_order[cut], segment_order[cut + 1])
            seam_id = seam_by_pair.get(pair)
            if not seam_id:
                continue
            if ledger_text is None:
                issues.append(issue("error", "causal_seam_invariant_unknown", f"{chain_id} 的证据跨 {pair[0]}->{pair[1]} 传递给反应位，但找不到连续性账本，无法核对 {seam_id}.required_invariants 派生。", ledger_path, hint='先在连续性账本为该 SEG 接缝登记 seam（含 required_invariants），再让因果链引用同 seam_id。python scripts/read_reference.py --file references/storyboard.md --section "### 因果链台账（causal_ledger）"'))
                break
            cell = seam_invariant_cell(ledger_text, str(seam_id))
            if cell is None or cell.strip() in {"", "无", "—", "-", "/"}:
                issues.append(issue("error", "causal_seam_invariant_missing", f"{chain_id} 的证据跨 {pair[0]}->{pair[1]} 传递给反应位，{seam_id}.required_invariants 必须派生写入该链 visibility_contract 条款。", path, hint='把 seam.required_invariants 逐条翻译成该链 visibility_contract 里的可见/可听承诺。python scripts/read_reference.py --file references/storyboard.md --section "### 因果链台账（causal_ledger）"'))

    card_text = read_text_file(root / f"episodes/{episode_id}/02_分镜/导演总控卡_{episode_id}.md")
    if card_text:
        for ref_id in sorted(set(re.findall(r"causal_chain_ref[^A-Za-z0-9]{0,6}([A-Za-z]{1,8}\d+)", card_text))):
            if ref_id not in chain_ids:
                issues.append(issue("error", "causal_chain_ref_unknown", f"导演总控卡台词证据链引用了不存在的链：{ref_id}。", path))
