# -*- coding: utf-8 -*-
"""h3.py — MiniMax H3 视频生成工具（独立 CLI，AutoDL ComfyUI 封装）。

位置：tools/video/h3.py。提供独立 CLI 入口；离线合同库 h3_contract
与节奏引擎 rhythm_engine 在 scripts/（引擎/合同层），本入口单向向下依赖。

调用契约（登记事实）：

  1. 提交：POST <base_url>/api/v1/comfyui/comfyui_workflow/<workflow_id>
     → data.task_id
  2. 轮询：GET  <base_url>/api/v1/comfyui/comfyui_workflow/result/<task_id>
     status ∈ QUEUED / RUNNING / SUCCESS / FAILED / CANCEL
  3. 鉴权：header ``Authorization: <raw token>``（不加 Bearer）；
     成功返回体 code == "Success"；results 元素
     {'type':'video','url':...,'file_type':'mp4'}，URL 有效期短，尽快下载。
  4. HTTP(S) 输入原样进入 ref_image_* / ref_video_* / ref_audio_*；
     本地路径读取同一 bytes 并转 data URI（base64），不自动上传。

请求以 video_manifest 段内 request_snapshot 为唯一冻结来源，由 prepare_video.py
准备；缺少有效冻结快照即停止执行。

凭证：环境变量或 Skill 根 .env 的 AUTODL_API_KEY，环境优先。仅标准库。

CLI:
  python tools/video/h3.py --project-root <root> --episode ep_1 --segment SEG001
        [--check-only] [--out take.mp4] [--resume] [--submit-only] [--new-task]
提交后立即保留任务；重复执行恢复同一任务，不重复提交。可播放检查通过后自动登记
candidate，stdout 只返回任务、文件与客观媒体事实；人工审片不由本工具代替。
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
import urllib.error
import urllib.request
from pathlib import Path

# python -I（隔离模式）不把脚本目录加入 sys.path；合同/引擎层在 scripts/，入口一次性指回。
SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from h3_contract import (  # noqa: E402
    ContractError,
    check_authorization,
    local_settings,
    prepare_request,
)
from stamp_confirmation import (  # noqa: E402
    StampError,
    find_segment,
    load_video_manifest,
    write_manifest,
)

_DEFAULT_BASE_URL = "https://autodl.art"  # AutoDL 默认入口
_DEFAULT_TIMEOUT_S = 1800
_DEFAULT_POLL_INTERVAL_S = 10


class BackendError(RuntimeError):
    """Submission/polling failure with a human-readable reason."""


def _http(method, url, token, payload=None, timeout=120, raw=False):
    headers = {"Authorization": token}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.HTTPError:
        # Backend bodies can echo signed URLs, tokens and full media data URIs.
        raise BackendError("AutoDL HTTP 失败；未输出可能含输入内容的响应正文") from None
    except urllib.error.URLError:
        raise BackendError("AutoDL 连接失败；请核对连接配置") from None
    return body if raw else json.loads(body.decode("utf-8"))


def _result_video_url(body):
    data = body.get("data") or {}
    results = data.get("results") or body.get("results") or []
    for item in results:
        if isinstance(item, dict) and item.get("type") == "video" \
                and item.get("url"):
            return item["url"]
    raise BackendError("SUCCESS 返回中未找到视频结果")


def _status_of(body):
    data = body.get("data")
    if isinstance(data, dict):
        return str(data.get("status") or body.get("status") or "").upper()
    return str(body.get("status") or "").upper()


def load_segment(root: Path, episode: str, segment_id: str) -> dict:
    manifest_path = root / f"episodes/{episode}/04_视频片段/video_manifest_{episode}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    matches = [seg for seg in manifest.get("segments", [])
               if isinstance(seg, dict) and seg.get("segment_id") == segment_id]
    if len(matches) != 1:
        raise BackendError(f"{segment_id} 在 video_manifest 中不存在或重复")
    return matches[0]


def segment_snapshot(segment: dict) -> dict:
    """只读取本段有效冻结快照，不从其他请求文件推导参数。"""
    snapshot = segment.get("request_snapshot")
    if isinstance(snapshot, dict) and snapshot:
        return snapshot
    raise BackendError("该段缺少有效 request_snapshot；请先运行 prepare_video.py 冻结请求")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _file_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _binding(prepared, confirmation, episode, segment_id, prompt_file, output_file):
    confirmation_id = confirmation.get("confirmation_id")
    if not isinstance(confirmation_id, str) or not confirmation_id:
        raise BackendError("生成确认缺 confirmation_id")
    return {"episode_id": episode, "segment_id": segment_id,
            "request_sha256": _sha(prepared.snapshot),
            "prompt_sha256": hashlib.sha256(prepared.payload["prompt"].encode("utf-8")).hexdigest(),
            "media_sha256": _sha(prepared.media),
            "confirmation_id": confirmation_id, "prompt_file": prompt_file,
            "output_file": output_file}


def _save_task(path, task):
    task["updated_at"] = _now()
    write_manifest(path, task)


def _token():
    token = local_settings({"AUTODL_API_KEY"}).get("AUTODL_API_KEY")
    if not token:
        raise BackendError("缺凭证：请在环境变量或 Skill 根 .env 设置 AUTODL_API_KEY（AutoDL ComfyUI 令牌）")
    return token


def _validate_video(path, *, require_audio=False, expected_duration=None):
    """只检查真实视频流与解码，不做内容或审美评分。失败保留下载文件。"""
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height,duration:format=duration",
             "-of", "json", str(path)], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120)
        if probe.returncode:
            raise BackendError("ffprobe 未识别有效视频；下载文件已保留，可恢复检查")
        data = json.loads(probe.stdout)
        videos = [stream for stream in data.get("streams", [])
                  if stream.get("codec_type") == "video" and stream.get("codec_name")
                  and int(stream.get("width", 0)) > 0 and int(stream.get("height", 0)) > 0]
        if not videos:
            raise BackendError("下载结果不含有效视频流；未登记 candidate")
        stream = videos[0]
        duration = float((data.get("format") or {}).get("duration") or stream.get("duration") or 0)
        if not math.isfinite(duration) or duration <= 0:
            raise BackendError("视频时长无效；未登记 candidate")
        if expected_duration is not None and abs(duration - expected_duration) > 0.5:
            raise BackendError("视频时长与冻结请求不符；下载文件保留，未登记 candidate")
        has_audio = any(item.get("codec_type") == "audio" for item in data.get("streams", []))
        if require_audio and not has_audio:
            raise BackendError("计划有人声但结果缺音频流；下载文件保留，未登记 candidate")
        decode = subprocess.run(
            ["ffmpeg", "-v", "error", "-xerror", "-i", str(path),
             "-map", "0:v:0", "-map", "0:a?", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        if decode.returncode:
            raise BackendError("视频解码失败；下载文件已保留，未登记 candidate")
        return {"duration_s": duration, "width": int(stream["width"]),
                "height": int(stream["height"]), "codec": stream["codec_name"],
                "has_audio": has_audio, "decode_ok": True}
    except FileNotFoundError:
        raise BackendError("缺少 ffprobe 或 ffmpeg；任务和已下载文件保留，安装后用 --resume 继续") from None
    except subprocess.TimeoutExpired:
        raise BackendError("媒体检查超时；任务和已下载文件保留，可用 --resume 继续") from None
    except (ValueError, TypeError, KeyError):
        raise BackendError("ffprobe 返回无效媒体事实；未登记 candidate") from None


def _publish(part, out):
    # Windows rename refuses an existing destination. On POSIX use an atomic,
    # exclusive hard link so a racing output cannot be overwritten there either.
    if os.name == "nt":
        os.rename(part, out)
    else:
        os.link(part, out)
        part.unlink()


def _current_bound_segment(root, episode, segment_id, expected_binding):
    path, manifest = load_video_manifest(root, episode)
    segment = find_segment(manifest, segment_id)
    prepared = prepare_request(snapshot=segment_snapshot(segment), root=root,
                               prompt_file=segment["h3_prompt_file"])
    confirmation = check_authorization(root, segment_id, episode=episode)
    current = _binding(prepared, confirmation, episode, segment_id,
                       segment["h3_prompt_file"], expected_binding["output_file"])
    if current != expected_binding:
        raise BackendError("请求、Prompt、素材或授权已改变；停止执行，保留已有任务与产物")
    return path, manifest, segment


def _register_candidate(root, episode, segment_id, task, expected_binding):
    path, manifest, segment = _current_bound_segment(root, episode, segment_id, expected_binding)
    facts = {"tool_call_id": task["task_id"], "tool_called_at": task["submitted_at"],
             "generation_confirmation_id": expected_binding["confirmation_id"],
             "output_file": expected_binding["output_file"]}
    # A resumed completed task must not undo a human's later accepted/rejected status.
    already_registered = (all(segment.get(key) == value for key, value in facts.items())
                          and segment.get("status") in {"candidate", "accepted", "rejected", "blocked"})
    if not already_registered:
        segment.update(facts, status="candidate")
        write_manifest(path, manifest)
        _, reread = load_video_manifest(root, episode)
        if any(find_segment(reread, segment_id).get(key) != value for key, value in facts.items()):
            raise BackendError("candidate 登记回读失败；任务保留，可恢复登记")
    return segment.get("status")


def _archive_task(state_path, task):
    def safe(value):
        return re.sub(r"[^A-Za-z0-9_-]", "_", str(value))[:48] or "unknown"
    binding = task.get("binding") or {}
    name = (f"{state_path.stem}.history_{safe(task.get('task_id'))}_"
            f"{safe(binding.get('confirmation_id'))}_{_sha(task)[:12]}.json")
    _publish(state_path, state_path.with_name(name))


def _run_task(prepared, root, episode, segment_id, prompt_file, out, *,
              resume=False, submit_only=False, new_task=False):
    confirmation = check_authorization(root, segment_id, episode=episode)
    output_file = out.relative_to(root).as_posix()
    binding = _binding(prepared, confirmation, episode, segment_id, prompt_file, output_file)
    manifest_path, _ = load_video_manifest(root, episode)
    state_path = manifest_path.parent / f"h3_task_{segment_id}.json"
    part = out.with_name(out.name + ".h3-download.part")
    snapshot = prepared.snapshot
    workflow = snapshot["workflow"]
    base = (snapshot.get("base_url") or _DEFAULT_BASE_URL).rstrip("/")
    poll_interval = float(snapshot.get("poll_interval_s") or _DEFAULT_POLL_INTERVAL_S)
    timeout_s = float(snapshot.get("timeout_s") or _DEFAULT_TIMEOUT_S)
    for archive in state_path.parent.glob(f"{state_path.stem}.history_*.json"):
        historical = json.loads(archive.read_text(encoding="utf-8-sig"))
        if not isinstance(historical, dict):
            raise BackendError("历史任务记录损坏；停止提交，保留历史供核对")
        if (historical.get("binding") or {}).get("confirmation_id") == binding["confirmation_id"]:
            raise BackendError("该生成确认已提交过历史任务；拒绝再次 POST，请取得新生成确认")
    if new_task:
        if not state_path.is_file():
            raise BackendError("--new-task 需要已有任务；首次生成直接执行即可")
        previous = json.loads(state_path.read_text(encoding="utf-8-sig"))
        old_binding = previous.get("binding") if isinstance(previous, dict) else None
        if not isinstance(old_binding, dict):
            raise BackendError("旧任务记录损坏；停止提交，保留原文件")
        if old_binding.get("confirmation_id") == binding["confirmation_id"]:
            raise BackendError("重生需要新的有效生成确认；相同确认不会再次 POST")
        if old_binding.get("output_file") == output_file:
            raise BackendError("重生需要新的输出版本路径；旧成片必须保留")
        if out.exists() or part.exists():
            raise BackendError("新输出版本或临时文件已存在；拒绝覆盖")
        _current_bound_segment(root, episode, segment_id, binding)
        _archive_task(state_path, previous)
    if state_path.exists():
        task = json.loads(state_path.read_text(encoding="utf-8-sig"))
        if not isinstance(task, dict) or task.get("binding") != binding:
            raise BackendError("已有任务绑定不同的请求、Prompt、素材、授权或输出；拒绝重复提交")
        if task.get("phase") == "failed":
            raise BackendError(f"任务 {task.get('task_id', '')} 已终止失败；不会自动重新生成")
        if not task.get("task_id"):
            raise BackendError("上次提交状态不确定且未记录 task_id；请核对服务端任务，不会自动重复 POST")
    else:
        if resume:
            raise BackendError("没有已登记任务可恢复；未提交新任务")
        if out.exists() or part.exists():
            raise BackendError("输出或下载临时文件已存在；拒绝覆盖或重新提交")
        token = _token()
        task = {"version": 1, "binding": binding, "phase": "submission_pending",
                "workflow": workflow, "model": snapshot.get("model"), "submitted_at": _now()}
        # Exclusive creation also prevents two simultaneous invocations from POSTing.
        with state_path.open("x", encoding="utf-8") as stream:
            json.dump(task, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            _current_bound_segment(root, episode, segment_id, binding)
            resp = _http("POST", f"{base}/api/v1/comfyui/comfyui_workflow/{workflow}",
                         token, payload=prepared.payload)
            if str(resp.get("code")) != "Success":
                task["phase"] = "failed"
                raise BackendError("提交被拒；不会自动重提，请核对工作流与输入参数")
            task_id = (resp.get("data") or {}).get("task_id") or resp.get("task_id")
            if not isinstance(task_id, (str, int)) or not str(task_id):
                raise BackendError("提交响应未含有效 task_id；核对服务端任务后再处理，禁止自动重提")
            task.update(task_id=str(task_id), phase="submitted")
        except (BackendError, OSError, ValueError) as exc:
            task["last_error"] = str(exc)
            _save_task(state_path, task)
            raise
        _save_task(state_path, task)

    if out.exists():
        if not task.get("output_sha256") or _file_sha(out) != task["output_sha256"]:
            raise BackendError("目标 mp4 已存在且不匹配已验证任务产物；拒绝覆盖")
        status = _register_candidate(root, episode, segment_id, task, binding)
        task["phase"] = "complete"
        _save_task(state_path, task)
        return dict(task_id=task["task_id"], output_file=output_file, status=status,
                    media=task.get("media"), resumed=True)
    if task.get("phase") in {"published", "complete"}:
        raise BackendError("任务已完成但产物缺失；不会自动重提或替换已登记视频")
    if submit_only:
        return {"task_id": task["task_id"], "status": task["phase"],
                "task_file": state_path.relative_to(root).as_posix()}
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        if task.get("phase") not in {"downloaded", "validated"} or not part.is_file():
            token = _token()
            _current_bound_segment(root, episode, segment_id, binding)
            result_url = f"{base}/api/v1/comfyui/comfyui_workflow/result/{task['task_id']}"
            deadline = time.monotonic() + timeout_s
            while True:
                body = _http("GET", result_url, token)
                status = _status_of(body)
                if status == "SUCCESS":
                    video_url = _result_video_url(body)
                    part.write_bytes(_http("GET", video_url, token, raw=True, timeout=300))
                    data = body.get("data") or {}
                    task.update(phase="downloaded", seed=data.get("seed") if isinstance(data, dict) else None)
                    _save_task(state_path, task)
                    break
                if status in {"FAILED", "CANCEL", "CANCELLED", "CANCELED"}:
                    task.update(phase="failed", backend_status=status)
                    raise BackendError(f"任务 {task['task_id']} {status}；不会自动重新生成")
                if time.monotonic() >= deadline:
                    raise BackendError(f"任务 {task['task_id']} 轮询超时；用 --resume 继续同一任务")
                time.sleep(poll_interval)
        _, _, current_segment = _current_bound_segment(root, episode, segment_id, binding)
        task["media"] = _validate_video(
            part, require_audio=bool(current_segment.get("speech_lines")),
            expected_duration=snapshot["duration_s"])
        task.update(phase="validated", output_sha256=_file_sha(part))
        _save_task(state_path, task)
        _publish(part, out)
        task["phase"] = "published"
        _save_task(state_path, task)
        status = _register_candidate(root, episode, segment_id, task, binding)
        task["phase"] = "complete"
        task.pop("last_error", None)
        _save_task(state_path, task)
        return {"task_id": task["task_id"], "seed": task.get("seed"),
                "workflow": workflow, "model": snapshot.get("model"),
                "output_file": output_file, "status": status, "media": task["media"]}
    except (BackendError, StampError, OSError, ValueError) as exc:
        task["last_error"] = str(exc)
        _save_task(state_path, task)
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description="MiniMax H3 生成或本地合同检查（manifest 直读）")
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--episode", required=True, help="分集 ID，形如 ep_1")
    ap.add_argument("--segment", required=True, help="视频段 ID，形如 SEG001")
    ap.add_argument("--out", help="实际生成的输出 mp4（项目内相对路径）")
    ap.add_argument("--check-only", action="store_true",
                    help="只做离线能力/纯净度/标记核对并打印摘要，不发起 HTTP、不查授权")
    ap.add_argument("--resume", action="store_true", help="恢复已登记任务，禁止提交新任务")
    ap.add_argument("--submit-only", action="store_true", help="仅提交并保留 task_id，随后用 --resume 取回")
    ap.add_argument("--new-task", action="store_true", help="新确认与新输出版本重生，自动归档旧任务；不覆盖旧成片")
    args = ap.parse_args(argv)
    try:
        if args.new_task and args.resume:
            raise ValueError("--new-task 和 --resume 互斥")
        root = Path(args.project_root).resolve()
        if not root.is_dir():
            raise ValueError("项目根不存在或不是目录")
        if not re.fullmatch(r"ep_[1-9]\d*", args.episode) or not re.fullmatch(r"SEG\d+", args.segment):
            raise ValueError("episode/segment 必须是 ep_N / SEG编号")
        segment = load_segment(root, args.episode, args.segment)
        snapshot = segment_snapshot(segment)
        prompt_file = segment.get("h3_prompt_file")
        if not isinstance(prompt_file, str) or not prompt_file:
            raise ContractError("h3_request_invalid", "该段缺 h3_prompt_file，无法组装请求")
        prepared = prepare_request(snapshot=snapshot, root=root, prompt_file=prompt_file)
        if args.check_only:
            print(json.dumps(prepared.summary(), ensure_ascii=False))
            return 0
        if not args.out:
            ap.error("实际生成需要 --out")
        out = (root / args.out).resolve()
        if not out.is_relative_to(root):
            raise ValueError("输出必须位于项目根内")
        if out.suffix.lower() != ".mp4":
            raise ValueError("输出扩展名必须为 .mp4")
        result = _run_task(prepared, root, args.episode, args.segment, prompt_file, out,
                           resume=args.resume, submit_only=args.submit_only, new_task=args.new_task)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, BackendError, StampError) as exc:
        print(f"h3: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
