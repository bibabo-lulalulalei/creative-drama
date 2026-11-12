#!/usr/bin/env python3
"""确认及局部状态写入入口；常规视频准备和结果登记由 prepare_video/h3 自动完成。

为什么存在：
  项目有十余个 lint 校验码和 h3_contract 执行门，但长期只有读取方没有写入手，
  主 Agent 只能现场写临时脚本改状态，慢且易错（6d307273 会话 28 个 TEMP 脚本）。
  本命令把「组行/组对象 + 同函数校验 + 原子写入 + 落盘复检」收成一条命令，
  所有写动作默认 dry-run，只有显式 --append 才落地。

五类动作（互斥）：
  1. 阶段确认行（默认模式）：写 00_制作控制/用户确认记录.jsonl
       --stage assets --episode ep_1 --revision 2 --user-message "用户原文" [--append]
     视频生成确认：加 --video --segments SEG001[,SEG002] --confirmation-id CONF-...
       冻结快照从 video_manifest 段内 request_snapshot 派生，禁止手填。
  2. --freeze-request --episode ep_1 --segment-id SEG001 --request-file 快照.json：
       把候选请求快照冻结进 manifest 段（替代旧 preflight --write），落盘前用
       h3_contract.prepare_request 做全套客观能力/纯净度/标记校验。
  3. --video-register --episode ep_1 --segment-file 新段.json：
       把主 Agent 组装好的完整新段对象登记进 manifest（末尾追加，自动重算总长）。
  4. --video-status --episode ep_1 --segment-id SEG001 --status candidate ...：
       段状态流转 candidate/accepted/rejected/blocked 及工具事实字段。
  5. --op-append --op-stage video --op-tool ffmpeg_tool --op-summary ...：
       写 00_制作控制/操作日志.jsonl，禁用工具词用 lint 同函数复验。

退出码：0 预检通过或写入成功；2 校验未过/文件缺失（脏行不许写入）；
        3 写入后定点复检仍失败（理论上不该发生，出现即按输出修复）。
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from rhythm_engine import atomic_write, canonical_sha, file_sha, json_text, project_file, read_json, to_ms  # noqa: E402
from h3_contract import ContractError, prepare_request  # noqa: E402
from video_confirmations import (ConfirmationError, authorization_binding, load_confirmation_history,
                                 request_segment_snapshot, validate_confirmations, validate_project_confirmations)  # noqa: E402

SKILL_ROOT = SCRIPT_DIR.parent
LEDGER_REL = "00_制作控制/用户确认记录.jsonl"
OP_LOG_REL = "00_制作控制/操作日志.jsonl"


class StampError(Exception):
    """预检失败：输入不合法或前置产物缺失，退出码固定 2。"""


def now_iso_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def auto_ask_call_id() -> str:
    # 约定唯一权威：references/local-runtime.md「interaction.ask → AskUserQuestion 的执行约定」
    return "auq-" + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def load_drama_lint():
    import drama_lint  # 延迟导入：预检/帮助场景不承担 lint 模块成本

    return drama_lint


def ledger_path(root: Path) -> Path:
    return root / LEDGER_REL


def op_log_path(root: Path) -> Path:
    return root / OP_LOG_REL


def validate_candidate(drama_lint, root: Path, candidate: dict) -> list[dict]:
    """用 lint 同一个 load_confirmation_records 校验「历史行 + 候选行」，规则零复制。"""
    target = ledger_path(root)
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    issues: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="stamp_conf_") as tmp:
        mirror_dir = Path(tmp) / "00_制作控制"
        mirror_dir.mkdir()
        mirror = mirror_dir / "用户确认记录.jsonl"
        payload = existing
        if payload and not payload.endswith("\n"):
            payload += "\n"
        payload += json.dumps(candidate, ensure_ascii=False, allow_nan=False) + "\n"
        mirror.write_text(payload, encoding="utf-8", newline="\n")
        drama_lint.load_confirmation_records(Path(tmp), issues, required=True)
    if candidate.get("confirmation_purpose") == "video_generation":
        try:
            rows = [json.loads(line) for line in existing.splitlines() if line.strip()] + [candidate]
            issues.extend(validate_project_confirmations(root, candidate["episode_id"], ledger_rows=rows, check_outputs=False))
        except (ValueError, OSError) as exc:
            issues.append({"severity": "error", "code": "confirmation_log_unreadable", "message": str(exc)})
    return issues


def validate_op_candidate(drama_lint, root: Path, candidate: dict) -> list[dict]:
    """操作日志只用 lint 的 check_operation_log_tools 同函数复验（禁用工具词）。"""
    target = op_log_path(root)
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    issues: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="stamp_op_") as tmp:
        mirror_dir = Path(tmp) / "00_制作控制"
        mirror_dir.mkdir()
        mirror = mirror_dir / "操作日志.jsonl"
        payload = existing
        if payload and not payload.endswith("\n"):
            payload += "\n"
        payload += json.dumps(candidate, ensure_ascii=False, allow_nan=False) + "\n"
        mirror.write_text(payload, encoding="utf-8", newline="\n")
        drama_lint.check_operation_log_tools(Path(tmp), issues)
    return issues


# ---------- video_manifest 读写助手 ----------

def manifest_path_for(root: Path, episode: str) -> Path:
    return root / f"episodes/{episode}/04_视频片段/video_manifest_{episode}.json"


def load_video_manifest(root: Path, episode: str) -> tuple[Path, dict]:
    path = manifest_path_for(root, episode)
    if not path.is_file():
        raise StampError(f"缺少 {path}；先用 --video-register 登记首段（会自动建 manifest 骨架）。")
    data = read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("segments"), list):
        raise StampError(f"{path} 结构无效：顶层需为含 segments 数组的对象。")
    return path, data


def find_segment(manifest: dict, segment_id: str) -> dict:
    matches = [seg for seg in manifest.get("segments", [])
               if isinstance(seg, dict) and seg.get("segment_id") == segment_id]
    if len(matches) != 1:
        raise StampError(f"{segment_id} 在 video_manifest 中不存在或重复。")
    return matches[0]


def total_segment_duration(manifest: dict) -> float:
    return sum(to_ms(seg.get("duration_s"), positive=True) for seg in manifest["segments"]
               if isinstance(seg, dict)) / 1000


def write_manifest(path: Path, data: dict) -> None:
    atomic_write(path, json_text(data))


def readback_manifest(path: Path) -> dict:
    return read_json(path)


# ---------- 动作 2：冻结请求 ----------

def run_freeze_request(args, drama_lint, root: Path) -> int:
    path, manifest = load_video_manifest(root, args.episode)
    segment = find_segment(manifest, args.segment_id)
    request_path = Path(args.request_file)
    if not request_path.is_absolute():
        request_path = root / request_path
    snapshot = read_json(request_path)
    if not isinstance(snapshot, dict):
        raise StampError("--request-file 必须是请求快照 JSON 对象。")
    try:
        if to_ms(snapshot.get("duration_s"), positive=True) != to_ms(segment.get("duration_s"), positive=True):
            raise StampError("快照 duration_s 与 manifest 段登记时长不一致，先对齐分镜请求时长。")
    except ValueError as exc:
        raise StampError(str(exc)) from None
    prompt_file = segment.get("h3_prompt_file")
    if not isinstance(prompt_file, str) or not (root / prompt_file).is_file():
        raise StampError(f"{args.segment_id} 缺真实存在的 h3_prompt_file，无法校验冻结请求。")
    try:
        prepared = prepare_request(snapshot=snapshot, root=root, prompt_file=prompt_file, encode_media=False)
    except ContractError as exc:
        raise StampError(f"冻结请求客观校验未过 [{exc.code}]：{exc}") from None
    prompt_sha = file_sha(root / prompt_file)
    preview = {
        "segment_id": args.segment_id,
        "mode": prepared.snapshot["mode"],
        "duration_s": prepared.snapshot["duration_s"],
        "inputs": [{"kind": item.get("kind"), "slot": item.get("slot"), "path": item.get("path")}
                   for item in prepared.media],
        "h3_prompt_sha256": prompt_sha,
    }
    print(json.dumps(preview, ensure_ascii=False, indent=2, allow_nan=False))
    if not args.append:
        print("预检通过，未写入任何文件；确认无误后加 --append 冻结进 manifest。")
        return 0
    segment["request_snapshot"] = prepared.snapshot
    segment["h3_prompt_sha256"] = prompt_sha
    write_manifest(path, manifest)
    reread = readback_manifest(path)
    resegment = find_segment(reread, args.segment_id)
    if resegment.get("request_snapshot") != prepared.snapshot or resegment.get("h3_prompt_sha256") != prompt_sha:
        print("落盘复检失败：manifest 回读内容与冻结目标不一致，请人工核对。", file=sys.stderr)
        return 3
    print(f"已冻结：{path}（{args.segment_id} request_snapshot + h3_prompt_sha256）")
    return 0


# ---------- 动作 3：登记新段 ----------

def run_video_register(args, drama_lint, root: Path) -> int:
    candidate = read_json(Path(args.segment_file))
    if not isinstance(candidate, dict):
        raise StampError("--segment-file 必须是完整段对象 JSON。")
    segment_id = candidate.get("segment_id")
    if not isinstance(segment_id, str) or not segment_id.strip():
        raise StampError("段对象必须填写非空 segment_id。")
    index = candidate.get("episode_segment_index")
    if type(index) is not int or index < 1:
        raise StampError("段对象 episode_segment_index 必须是从 1 起的正整数。")
    try:
        duration_ms = to_ms(candidate.get("duration_s"), positive=True)
    except ValueError as exc:
        raise StampError(str(exc)) from None
    if duration_ms % 1000:
        raise StampError("段 duration_s 必须是整数秒。")
    path = manifest_path_for(root, args.episode)
    if path.is_file():
        manifest = read_json(path)
        if not isinstance(manifest, dict) or not isinstance(manifest.get("segments"), list):
            raise StampError(f"{path} 结构无效：顶层需为含 segments 数组的对象。")
        if any(isinstance(seg, dict) and seg.get("segment_id") == segment_id for seg in manifest["segments"]):
            raise StampError(f"{segment_id} 已存在，登记只能追加新段。")
        expected_index = len(manifest["segments"]) + 1
        if index != expected_index:
            raise StampError(f"新段索引必须接续末尾：期望 {expected_index}，实际 {index}。")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        manifest = {"episode_id": args.episode, "revision": 1, "duration_s": 0,
                    "segments": []}
    manifest["segments"].append(candidate)
    manifest["duration_s"] = total_segment_duration(manifest)
    print(json.dumps({"register": segment_id, "index": index,
                      "manifest_duration_s": manifest["duration_s"]},
                     ensure_ascii=False, indent=2, allow_nan=False))
    if not args.append:
        print("预检通过，未写入任何文件；确认无误后加 --append 登记。")
        return 0
    write_manifest(path, manifest)
    reread = readback_manifest(path)
    if find_segment(reread, segment_id) != candidate or reread.get("duration_s") != manifest["duration_s"]:
        print("落盘复检失败：manifest 回读内容与登记目标不一致，请人工核对。", file=sys.stderr)
        return 3
    print(f"已登记：{path}（{segment_id}，当前共 {len(reread['segments'])} 段）")
    return 0


# ---------- 动作 4：段状态流转 ----------

def run_video_status(args, drama_lint, root: Path) -> int:
    if args.status not in drama_lint.VIDEO_STATUS_VALUES:
        raise StampError(f"--status 必须是 {sorted(drama_lint.VIDEO_STATUS_VALUES)} 之一。")
    path, manifest = load_video_manifest(root, args.episode)
    segment = find_segment(manifest, args.segment_id)
    tool_facts = {"tool_call_id": args.tool_call_id, "tool_called_at": args.tool_called_at,
                  "generation_confirmation_id": args.confirmation_id}
    if args.status in {"candidate", "accepted"}:
        missing = [name for name, value in tool_facts.items() if not str(value or "").strip()]
        if missing:
            raise StampError(f"进入 {args.status} 必须同时提供工具事实：{missing}（lint 门 video_confirmation_after_tool_call / confirmation_not_latest）。")
        if not args.output_file or not (root / args.output_file).is_file():
            raise StampError("进入 candidate/accepted 的 --output-file 必须指向项目内真实存在的 mp4。")
    if args.status == "accepted":
        facts = dict(tool_facts, output_file=args.output_file.replace("\\", "/"))
        if any(segment.get(key) != value for key, value in facts.items()):
            raise StampError("accepted 只能接受当前已登记产物，不能在接受时替换工具事实或视频版本。")
        records_issues = []
        records = drama_lint.load_confirmation_records(root, records_issues, required=True)
        if records_issues:
            raise StampError("视频产物确认台账无效，不能登记 accepted。")
        accepted = [row for row in records if row.get("stage") == "video" and row.get("episode_id") == args.episode
                    and row.get("confirmation_purpose") != "video_generation" and row.get("valid", True) is not False]
        if not accepted:
            raise StampError("accepted 需要真实视频产物确认；generate 授权不代表用户接受产物。")
        verify_video_acceptance(root, max(accepted, key=lambda row: drama_lint.parse_iso_time(row["confirmed_at"])), drama_lint)
    preview = {"segment_id": args.segment_id, "status": args.status}
    if not args.append:
        print(json.dumps(preview, ensure_ascii=False, indent=2, allow_nan=False))
        print("预检通过，未写入任何文件；确认无误后加 --append 流转。")
        return 0
    segment["status"] = args.status
    if args.output_file:
        segment["output_file"] = args.output_file.replace("\\", "/")
    for name, value in tool_facts.items():
        if value:
            segment[name] = value
    write_manifest(path, manifest)
    reread = readback_manifest(path)
    resegment = find_segment(reread, args.segment_id)
    if resegment.get("status") != args.status:
        print("落盘复检失败：状态未生效，请人工核对。", file=sys.stderr)
        return 3
    print(f"已流转：{path}（{args.segment_id} → {args.status}）")
    return 0


def verify_video_acceptance(root: Path, row: dict, drama_lint) -> None:
    """阶段接受前核本集全部真实结果；沿用当前版本与实际调用/确认时间。"""
    episode = row.get("episode_id")
    _, manifest = load_video_manifest(root, episode)
    storyboard = read_json(root / f"episodes/{episode}/02_分镜/storyboard_{episode}.json")
    planned = [seg.get("segment_id") for seg in storyboard.get("segments", []) if isinstance(seg, dict)]
    segments = manifest.get("segments", [])
    if not planned or [seg.get("segment_id") for seg in segments] != planned:
        raise StampError("视频产物确认前必须完成本集全部已确认 SEG，数量和顺序须与分镜一致。")
    errors = validate_project_confirmations(root, episode, manifest)
    if errors:
        raise StampError("视频产物缺当前有效生成事实：" + errors[0]["message"])
    confirmed = drama_lint.parse_iso_time(row.get("confirmed_at"))
    if row.get("revision") != manifest.get("revision"):
        raise StampError("视频产物确认 revision 必须等于当前 video_manifest revision。")
    for segment in segments:
        output = project_file(root, segment.get("output_file", ""))
        called = drama_lint.parse_iso_time(segment.get("tool_called_at"))
        if (segment.get("status") not in {"candidate", "accepted"} or not output.is_file()
                or output.stat().st_size == 0 or not called or not confirmed or confirmed <= called):
            raise StampError("视频产物确认前全部 SEG 必须是已生成的非空 candidate/accepted，且确认晚于实际调用。")
    plan = read_json(root / "00_制作控制/drama_plan.json")
    if (plan.get("objective") or {}).get("target_stage") != "video":
        if (row.get("confirmation_purpose") != "video_acceptance_and_final_assembly"
                or row.get("interaction_ask_result") != "proceed_assembly"
                or not row.get("interaction_ask_call_id")):
            raise StampError("继续成片需要真实 proceed_assembly 产物接受与拼接确认。")
    elif row.get("confirmation_purpose") not in (None, "", "video_acceptance") or row.get("interaction_ask_result"):
        raise StampError("目标止于视频时只登记普通视频产物确认，不创建拼接授权。")


# ---------- 动作 5：操作日志 ----------

def next_operation_id(root: Path) -> str:
    path = op_log_path(root)
    highest = 0
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            op_id = str(row.get("operation_id") or "")
            if op_id.startswith("OP") and op_id[2:].isdigit():
                highest = max(highest, int(op_id[2:]))
    return f"OP{highest + 1:03d}"


def run_op_append(args, drama_lint, root: Path) -> int:
    if not str(args.op_summary or "").strip():
        raise StampError("--op-append 需要 --op-summary 登记本次操作摘要。")
    if args.op_tool and args.op_tool.strip().lower() in drama_lint.FORBIDDEN_TOOL_TERMS:
        raise StampError(f"工具 {args.op_tool} 在禁用清单内；媒体处理必须走 tools/video/ffmpeg_tool.py。")
    candidate = {
        "operation_id": next_operation_id(root),
        "input_revision": args.op_revision,
        "stage": args.op_stage,
        "target_ids": args.op_target,
        "tool": args.op_tool or "",
        "tool_call_id": args.op_call_id or "",
        "params_summary": {"summary": args.op_summary},
        "attempt": args.op_attempt,
        "status": args.op_status,
        "outputs": args.op_output,
        "output_metadata": {},
        "tool_calls": [],
        "recovery_action": "",
        "timestamp": now_iso_local(),
    }
    issues = validate_op_candidate(drama_lint, root, candidate)
    if issues:
        print(f"校验未过：{len(issues)} 个问题，禁止写入：")
        for item in issues:
            print(f"  [{item['code']}] {item['message']}")
        return 2
    print(json.dumps(candidate, ensure_ascii=False, indent=2, allow_nan=False))
    if not args.append:
        print("预检通过，未写入任何文件；确认无误后加 --append 追加。")
        return 0
    target = op_log_path(root)
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    payload = existing
    if payload and not payload.endswith("\n"):
        payload += "\n"
    payload += json.dumps(candidate, ensure_ascii=False, allow_nan=False) + "\n"
    atomic_write(target, payload)
    post_issues: list[dict] = []
    drama_lint.check_operation_log_tools(root, post_issues)
    if post_issues:
        print("追加后定点复检失败（不应发生），行已写入但请先修复再推进：", file=sys.stderr)
        for item in post_issues:
            print(f"  [{item['code']}] {item['message']}", file=sys.stderr)
        return 3
    print(f"已追加：{target}（{candidate['operation_id']}）")
    return 0


# ---------- 动作 1：阶段确认行 ----------

def build_video_parts(root: Path, episode: str, segment_ids: list[str]) -> dict:
    _path, manifest = load_video_manifest(root, episode)
    selected = []
    for sid in segment_ids:
        selected.append(find_segment(manifest, sid))
    for seg in selected:
        missing = [key for key in ("request_snapshot", "episode_segment_index", "duration_s")
                   if not seg.get(key) and seg.get(key) != 0]
        if missing:
            raise StampError(
                f"{seg.get('segment_id')} 缺冻结字段 {missing}；先跑 "
                f"python scripts/stamp_confirmation.py --project-root <根> --freeze-request "
                f"--episode {episode} --segment-id {seg.get('segment_id')} --request-file <快照.json>。"
            )
        if not isinstance(seg.get("request_snapshot"), dict):
            raise StampError(f"{seg.get('segment_id')} request_snapshot 必须是对象。")
    if not 1 <= len(selected) <= 2:
        raise StampError("每批只允许连续 1-2 个 SEG（video-batch-confirmation 批次边界）。")
    indexes = [seg["episode_segment_index"] for seg in selected]
    if indexes != list(range(indexes[0], indexes[0] + len(indexes))):
        raise StampError(f"批次 SEG 索引必须连续，实际 {indexes}。")
    for seg in selected:
        prepared = prepare_request(snapshot=seg["request_snapshot"], root=root, prompt_file=seg.get("h3_prompt_file"), encode_media=False)
        if prepared.snapshot != seg["request_snapshot"]:
            raise StampError("请求尚未冻结实际部署参数；请先重新准备。")
    snapshot = {"segments": [request_segment_snapshot(seg) for seg in selected]}
    try:
        history = load_confirmation_history(root, episode, manifest)
        history_issues = validate_confirmations({"generation_confirmations": history}, [], check_outputs=False)
        if history_issues:
            raise StampError(f"已有视频确认不完整：{history_issues[0]['message']}")
        prior = {}
        for record in history:
            if record.get("valid", True) is False:
                continue
            for part in (record.get("request_snapshot") or {}).get("segments", []):
                if isinstance(part, dict):
                    prior[part.get("segment_id")] = record
        overlapping = {prior[sid]["confirmation_id"] for sid in segment_ids if sid in prior}
        attempt = 1 + max((prior[sid].get("attempt", 0) for sid in segment_ids if sid in prior), default=0)
        bindings = [authorization_binding(root, seg) for seg in selected]
    except (ConfirmationError, TypeError, ValueError) as exc:
        raise StampError(str(exc)) from None
    return {"request_snapshot": snapshot, "request_snapshot_sha256": canonical_sha(snapshot),
            "batch_start_segment_index": indexes[0], "batch_end_segment_index": indexes[-1],
            "planned_video_count": len(selected), "segment_durations": [
                {"segment_id": seg["segment_id"], "duration_s": seg["duration_s"]} for seg in selected],
            "duration_s": sum(to_ms(seg["duration_s"], positive=True) for seg in selected) / 1000,
            "attempt": attempt, "supersedes_confirmation_ids": sorted(overlapping),
            "authorization_version": 2, "authorization_bindings": bindings}


def build_row(args, drama_lint) -> dict:
    stage = args.stage
    episode_id = args.episode or ""
    if stage == "planning" and episode_id:
        raise StampError("planning 是项目级确认，禁止填写 --episode。")
    if stage in set(drama_lint.EPISODE_STAGES) - {"script"} and not episode_id:
        raise StampError(f"{stage} 阶段确认必须填写 --episode ep_N。")
    if episode_id and not drama_lint.re.fullmatch(r"ep_[1-9]\d*", episode_id):
        raise StampError(f"--episode 形状无效：{episode_id}（合法形如 ep_1）。")
    if not isinstance(args.revision, int):
        raise StampError("台账确认必须填写整数 --revision。")
    if not str(args.user_message or "").strip():
        raise StampError("--user-message 必须是用户明确回复原文，不能为空。")
    mode = args.confirmation_mode
    if mode == "incremental":
        if not isinstance(args.base_revision, int):
            raise StampError("incremental 必须填写整数 --base-revision。")
        if not args.changed_artifacts or not args.impact_scope:
            raise StampError("incremental 必须填写至少一个 --changed-artifacts 和 --impact-scope。")
    elif args.base_revision is not None:
        raise StampError("--base-revision 只允许在 --confirmation-mode incremental 时使用。")

    ask_call_id = args.ask_call_id or ""
    if ask_call_id == "auto":
        ask_call_id = auto_ask_call_id()
    row = {
        "stage": stage,
        "episode_id": episode_id,
        "revision": args.revision,
        "decision": "confirmed",
        "confirmation_mode": mode,
        "changed_artifacts": args.changed_artifacts,
        "impact_scope": args.impact_scope,
        "confirmation_purpose": args.confirmation_purpose or "",
        "interaction_ask_call_id": ask_call_id,
        "interaction_ask_result": args.interaction_ask_result or "",
        "user_message": args.user_message,
        "confirmed_at": args.confirmed_at or now_iso_local(),
    }
    if mode == "incremental":
        row["base_revision"] = args.base_revision
    if args.video:
        if stage != "video":
            raise StampError("--video 只允许 --stage video。")
        if not args.confirmation_id:
            raise StampError("视频确认必须填写本次唯一 --confirmation-id（完整记录只写用户确认台账）。")
        if not args.segments:
            raise StampError("视频确认必须填写 --segments SEG001[,SEG002]。")
        parts = build_video_parts(Path(args.project_root).resolve(), episode_id, args.segments)
        row["confirmation_purpose"] = "video_generation"
        row["interaction_ask_result"] = "generate"
        if not row["interaction_ask_call_id"]:
            row["interaction_ask_call_id"] = auto_ask_call_id()
        row["confirmation_id"] = args.confirmation_id
        if args.supersedes and set(args.supersedes) != set(parts["supersedes_confirmation_ids"]):
            raise StampError("--supersedes 必须精确匹配本次覆盖的最新有效确认；默认由命令自动派生。")
        evidence_path = getattr(args, "evidence_file", None)
        if not evidence_path:
            raise StampError("视频确认需要 --evidence-file（准备工具生成的实际展示两表和完整文本）。")
        evidence_path = Path(evidence_path)
        if not evidence_path.is_absolute():
            evidence_path = Path(args.project_root) / evidence_path
        evidence = read_json(evidence_path)
        evidence_keys = {"displayed_parameter_table", "displayed_storyboard_rows", "final_parameters_text"}
        binding_keys = {"request_snapshot_sha256", "authorization_bindings"}
        if not isinstance(evidence, dict) or not evidence_keys <= evidence.keys():
            raise StampError("确认展示证据缺 displayed_parameter_table/displayed_storyboard_rows/final_parameters_text。")
        if not binding_keys <= evidence.keys():
            raise StampError("确认展示证据缺准备时的请求/素材指纹；请用 prepare_video.py 重新准备。")
        for key in binding_keys:
            if evidence[key] != parts[key]:
                raise StampError("准备展示后请求、Prompt 或本地素材已改变；请重新准备并确认。")
        row.update(parts)
        row.update({key: evidence[key] for key in evidence_keys})
    if args.source_snapshot:
        if stage != "script":
            raise StampError("--source-snapshot 只允许 --stage script 的分集剧本确认。")
        if not args.confirmation_id:
            raise StampError("带 source_snapshot 的剧本确认必须填写 --confirmation-id（节奏引擎回指要用）。")
        row["confirmation_id"] = args.confirmation_id
        row["source_snapshot"] = build_source_snapshot(Path(args.project_root).resolve(), args.source_snapshot)
    if args.duration_contract:
        if stage != "planning":
            raise StampError("--duration-contract 只允许 --stage planning。")
        if not args.confirmation_id:
            raise StampError("exact/target_band 时长合同确认必须填写 --confirmation-id（drama_plan 回指要用）。")
        row["confirmation_id"] = args.confirmation_id
        row["duration_contract_snapshot"] = build_duration_snapshot(Path(args.project_root).resolve())
    return row


def build_source_snapshot(root: Path, rel_path: str) -> dict:
    target = root / rel_path
    if not target.is_file():
        raise StampError(f"--source-snapshot 文件不存在：{rel_path}")
    snapshot = {"file": rel_path.replace("\\", "/"), "sha256": file_sha(target)}
    try:
        contract = read_json(target)
        if isinstance(contract.get("revision"), int) and not isinstance(contract["revision"], bool):
            snapshot["revision"] = contract["revision"]
    except (OSError, ValueError):
        pass
    return snapshot


def build_duration_snapshot(root: Path) -> dict:
    plan = read_json(root / "00_制作控制/drama_plan.json")
    contract = plan.get("duration_contract")
    if not isinstance(contract, dict):
        raise StampError("drama_plan.json 缺 duration_contract 对象，无法派生快照。")
    return {key: val for key, val in contract.items() if key != "confirmation_ref"}


def print_issues(issues: list[dict]) -> None:
    for item in issues:
        loc = f" {item['path']}" if item.get("path") else ""
        print(f"  [{item.get('code')}] {item.get('message')}{loc}")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    drama_lint = load_drama_lint()
    parser = argparse.ArgumentParser(description="确认与局部状态写入；正常直接加 --append，内部校验、原子写入并回读。")
    parser.add_argument("--project-root", required=True, help="项目根目录")
    # 动作选择（互斥）
    parser.add_argument("--freeze-request", action="store_true", help="把候选请求快照冻结进 video_manifest 段")
    parser.add_argument("--video-register", action="store_true", help="把完整新段对象登记进 video_manifest")
    parser.add_argument("--video-status", action="store_true", help="段状态流转 candidate/accepted/rejected/blocked")
    parser.add_argument("--op-append", action="store_true", help="追加 00_制作控制/操作日志.jsonl")
    # 动作 1：台账确认参数
    parser.add_argument("--stage", choices=drama_lint.STAGES, help="确认所属阶段（台账模式必填）")
    parser.add_argument("--episode", help="分集 ID；planning 禁填，script 项目级确认留空，其余阶段必填")
    parser.add_argument("--revision", type=int, help="本次确认绑定的 revision 整数（台账模式必填）")
    parser.add_argument("--confirmation-mode", choices=tuple(sorted(drama_lint.CONFIRMATION_MODES)), default="full")
    parser.add_argument("--base-revision", type=int, help="incremental 模式必填：上一全量确认 revision")
    parser.add_argument("--changed-artifacts", action="append", default=[], help="incremental 变化文件，可重复")
    parser.add_argument("--impact-scope", action="append", default=[], help="incremental 影响范围，可重复")
    parser.add_argument("--confirmation-purpose", help="普通确认留空；项目执行确认填 project_execution")
    parser.add_argument("--interaction-ask-result", help="如 proceed_project / proceed_assembly；视频行自动为 generate")
    parser.add_argument("--ask-call-id", help="AskUserQuestion 调用 ID；填 auto 按 auq-<UTC> 约定自动生成")
    parser.add_argument("--user-message", help="触发确认的用户回复原文（台账模式必填）")
    parser.add_argument("--confirmed-at", help="带时区 ISO-8601；默认当前本地时间")
    parser.add_argument("--video", action="store_true", help="视频生成确认：从 manifest 冻结快照派生")
    parser.add_argument("--confirmation-id", help="视频确认必填，本次确认唯一 ID")
    parser.add_argument("--segments", help="视频确认覆盖的 SEG，逗号分隔，连续 1-2 个")
    parser.add_argument("--evidence-file", help="视频准备工具生成的展示证据 JSON；机器字段自动派生")
    parser.add_argument("--supersedes", action="append", default=[], help="被替代的旧 confirmation_id，可重复")
    parser.add_argument("--source-snapshot", help="script 分集确认：项目内剧本合同相对路径，SHA 由本命令计算")
    parser.add_argument("--duration-contract", action="store_true",
                        help="planning 确认：从 drama_plan.duration_contract 派生 exact/target_band 快照")
    # 动作 2/3/4 参数
    parser.add_argument("--segment-id", help="--freeze-request/--video-status：目标视频段 ID，如 SEG001")
    parser.add_argument("--request-file", help="--freeze-request：候选请求快照 JSON 路径（项目内或绝对路径）")
    parser.add_argument("--segment-file", help="--video-register：完整新段对象 JSON 路径")
    parser.add_argument("--status", help="--video-status：目标状态 candidate/accepted/rejected/blocked")
    parser.add_argument("--output-file", help="--video-status：成片 mp4 项目内相对路径")
    parser.add_argument("--tool-call-id", help="--video-status：实际工具调用 ID")
    parser.add_argument("--tool-called-at", help="--video-status：实际工具调用时间（带时区 ISO-8601）")
    # 动作 5 参数
    parser.add_argument("--op-stage", choices=drama_lint.STAGES, help="--op-append：操作所属阶段")
    parser.add_argument("--op-tool", default="", help="--op-append：工具名（禁用词由 lint 同函数拦截）")
    parser.add_argument("--op-call-id", help="--op-append：工具调用 ID")
    parser.add_argument("--op-summary", help="--op-append：操作摘要")
    parser.add_argument("--op-target", action="append", default=[], help="--op-append：目标 ID，可重复")
    parser.add_argument("--op-output", action="append", default=[], help="--op-append：产出文件相对路径，可重复")
    parser.add_argument("--op-revision", type=int, default=1, help="--op-append：input_revision，默认 1")
    parser.add_argument("--op-attempt", type=int, default=1, help="--op-append：attempt，默认 1")
    parser.add_argument("--op-status", default="succeeded", help="--op-append：状态，默认 succeeded")
    parser.add_argument("--append", action="store_true", help="实际原子写入；无此旗标只预检并打印待写内容")
    args = parser.parse_args(argv or sys.argv[1:])
    try:
        if args.segments:
            args.segments = [item.strip() for item in args.segments.split(",") if item.strip()]
        project_root = Path(args.project_root).resolve()
        if not project_root.is_dir():
            raise StampError(f"项目根不存在：{project_root}")
        actions = [args.freeze_request, args.video_register, args.video_status, args.op_append]
        if sum(1 for flag in actions if flag) > 1:
            raise StampError("--freeze-request/--video-register/--video-status/--op-append 互斥，一次只做一个动作。")
        if args.freeze_request:
            if not args.episode or not args.segment_id or not args.request_file:
                raise StampError("--freeze-request 需要 --episode、--segment-id、--request-file。")
            return run_freeze_request(args, drama_lint, project_root)
        if args.video_register:
            if not args.episode or not args.segment_file:
                raise StampError("--video-register 需要 --episode 和 --segment-file。")
            return run_video_register(args, drama_lint, project_root)
        if args.video_status:
            if not args.episode or not args.segment_id or not args.status:
                raise StampError("--video-status 需要 --episode、--segment-id、--status。")
            return run_video_status(args, drama_lint, project_root)
        if args.op_append:
            if not args.op_stage:
                raise StampError("--op-append 需要 --op-stage。")
            return run_op_append(args, drama_lint, project_root)
        if not args.stage:
            raise StampError("台账确认模式需要 --stage；状态写动作请用 --freeze-request/--video-register/--video-status/--op-append。")
        return run_ledger(args, drama_lint, project_root)
    except (StampError, ConfirmationError, OSError, ValueError) as exc:
        print(str(exc))
        return 2


def run_ledger(args, drama_lint, project_root: Path) -> int:
    row = build_row(args, drama_lint)
    if row.get("stage") == "video" and row.get("confirmation_purpose") != "video_generation":
        verify_video_acceptance(project_root, row, drama_lint)
    issues = validate_candidate(drama_lint, project_root, row)
    if issues:
        print(f"校验未过：{len(issues)} 个问题，禁止写入。先修复再重跑：")
        print_issues(issues)
        return 2

    print(json.dumps(row, ensure_ascii=False, indent=2, allow_nan=False))
    if not args.append:
        print("预检通过，未写入任何文件；确认无误后加 --append 原子追加。")
        return 0

    target = ledger_path(project_root)
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    payload = existing
    if payload and not payload.endswith("\n"):
        payload += "\n"
    payload += json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"
    atomic_write(target, payload)
    post_issues: list[dict] = []
    drama_lint.load_confirmation_records(project_root, post_issues, required=True)
    if args.video:
        post_issues.extend(validate_project_confirmations(project_root, args.episode, check_outputs=False))
    if post_issues:
        print("追加后定点复检失败（不应发生），行已写入但请先修复再推进：")
        print_issues(post_issues)
        return 3
    print(f"已追加：{target}")
    if args.video:
        print(f"视频确认 {args.confirmation_id} 覆盖 {len(args.segments)} 个 SEG 的冻结请求快照。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
