"""项目适配及只读对账；时间数学由 timeline_core 唯一维护。

只做“源出处”层对账：以 rhythm_input/script_contract/用户确认为源，核 beat 与台词覆盖、
派生字度同源重算、十五列阅读稿和内容审校盖章。分镜 JSON 的结构门在 drama_lint.py（原 storyboard 检查段）；
两边都碰 beat_coverage，但本文件管跨源出处、结构门管台账形状，码与依赖不同，互不替代。
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from timeline_core import (canonical_sha, compute_groups, design_projection, issue, reconcile_timeline,
                           to_ms)

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
            issues.append(issue("source_line_uncovered", "speech_lines 必须是数组，可空", hint='为每条 line_id 建 utterance 并在 timeline 用 speech 分片完整承接，台词逐字不改，再 allocate。python scripts/read_reference.py --file references/manifests/storyboard.md --section "### rhythm_input_ep_N.json"'))
            continue
        for line in lines:
            if not isinstance(line, dict):
                issues.append(issue("source_line_uncovered", "台词索引必须是对象", hint='为每条 line_id 建 utterance 并在 timeline 用 speech 分片完整承接，台词逐字不改，再 allocate。python scripts/read_reference.py --file references/manifests/storyboard.md --section "### rhythm_input_ep_N.json"'))
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
        issues.append(issue("source_line_uncovered", f"缺人声 {sorted(missing)}", hint='为每条 line_id 建 utterance 并在 timeline 用 speech 分片完整承接，台词逐字不改，再 allocate。python scripts/read_reference.py --file references/manifests/storyboard.md --section "### rhythm_input_ep_N.json"'))
    return issues


def check_review(review, expected_inputs):
    issues = []
    if not isinstance(review, dict) or review.get("reviewed_inputs") != expected_inputs:
        issues.append(issue("content_review_stale", "内容审校不对应当前设计/源/时间输入", hint='结构 error 清零后真人做五项复核，先无旗标预检 python scripts/stamp_review.py --project-root <项目根> --episode ep_N，再 python scripts/stamp_review.py --project-root <项目根> --episode ep_N --i-did-the-review；禁止手填 content_review。'))
    if not isinstance(review, dict) or not isinstance(review.get("open_issues"), list):
        issues.append(issue("content_review_open_issue", "缺内容审校记录；字段存在不证明摄影成立", hint='先按五项复核解决并清空 open_issues（改设计后重跑引擎与 lint），再重新盖章；读 python scripts/read_reference.py --file references/storyboard.md --section "### 分镜内容人工复核"'))
    elif review["open_issues"]:
        issues.append(issue("content_review_open_issue", "有未解决的内容设计问题", hint='先按五项复核解决并清空 open_issues（改设计后重跑引擎与 lint），再重新盖章；读 python scripts/read_reference.py --file references/storyboard.md --section "### 分镜内容人工复核"'))
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
