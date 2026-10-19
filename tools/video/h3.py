# -*- coding: utf-8 -*-
"""h3.py — MiniMax H3 视频生成工具（独立 CLI，AutoDL ComfyUI 封装）。

位置：tools/video/h3.py。submit_take.py 经 subprocess 调用（文件名由
gen.model 推导），也可脱离流水线单独运行。

调用契约（登记事实）：

  1. 提交：POST <base_url>/api/v1/comfyui/comfyui_workflow/<workflow_id>
     → data.task_id
  2. 轮询：GET  <base_url>/api/v1/comfyui/comfyui_workflow/result/<task_id>
     status ∈ QUEUED / RUNNING / SUCCESS / FAILED / CANCEL
  3. 鉴权：header ``Authorization: <raw token>``（不加 Bearer）；
     成功返回体 code == "Success"；results 元素
     {'type':'video','url':...,'file_type':'mp4'}，URL 有效期短，尽快下载。
  4. ref_image_* / ref_audio_* 需 URL；data URI（base64）实测可被接受
     （封装变更后需复核）。

参数面约定见 tools/README.md：
  - inputs[] 按 kind 分组、保数组序映射到 ref_image_N / ref_video_N /
    ref_audio_N 槽位；label/role 直通（标签与正文的对应由 prompt.md 承担）；
  - extra.workflow（必填）、extra.base_url / extra.resolution /
    extra.options / extra.poll_interval_s / extra.timeout_s（可选）。

凭证：环境变量 AUTODL_API_KEY。仅标准库。

CLI:
  python tools/video/h3.py --gen <gen.json> --prompt <prompt.md>
        --out <take.mp4>
inputs[].path 相对路径以当前工作目录（项目根）解析。成功后 stdout 末行
打印结果 JSON（task_id/seed/workflow/model，供 submit_take 取 provenance）。
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

_DEFAULT_BASE_URL = "https://autodl.art"  # AutoDL 默认入口
_DEFAULT_TIMEOUT_S = 1800
_DEFAULT_POLL_INTERVAL_S = 10

_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".bmp": "image/bmp", ".gif": "image/gif",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
    ".aac": "audio/aac", ".flac": "audio/flac", ".ogg": "audio/ogg",
}


class BackendError(RuntimeError):
    """Submission/polling failure with a human-readable reason."""


def _data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime = _MIME.get(ext)
    if not mime:
        raise BackendError(f"不支持的参考素材格式 {path}（无已知 MIME 映射）")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _ref_value(root, rel_path):
    """Local file → data URI; an http(s) URL passes through untouched."""
    p = (rel_path or "").replace("\\", "/")
    if p.startswith("http://") or p.startswith("https://"):
        return p
    return _data_uri(os.path.join(root, p))


def _slot_payload(gen, root):
    """inputs[] → ref_<kind>_N slot fields, order preserved within a kind."""
    slots = {}
    counters = {"image": 0, "video": 0, "audio": 0}
    for item in gen.get("inputs") or []:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        path = item.get("path")
        if kind not in counters or not path:
            continue  # schema 闸已卡 kind/path 必填；此处只静默跳过残条
        n = counters[kind]
        counters[kind] += 1
        # label/role 直通：提示词正文已按官方模板引用标签，适配器只传文件。
        slots[f"ref_{kind}_{n}"] = _ref_value(root, path)
    return slots


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
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise BackendError(f"AutoDL HTTP {e.code} {url}: {detail}") from None
    except urllib.error.URLError as e:
        raise BackendError(f"AutoDL 连接失败 {url}: {e}") from None
    return body if raw else json.loads(body.decode("utf-8"))


def _build_payload(gen, root, prompt):
    extra = gen.get("extra") or {}
    # workflow 私有字段（分辨率/时长等档位名各 workflow 不同）经 options
    # 原样直通；随后已知键覆盖，保证 gen 显式字段优先。
    payload = dict(extra.get("options") or {})
    payload["prompt"] = prompt
    payload.update(_slot_payload(gen, root))
    if extra.get("resolution"):
        payload["resolution"] = extra["resolution"]
    if gen.get("duration_s") is not None:
        payload["duration"] = gen.get("duration_s")
    if gen.get("seed") is not None:
        payload["seed"] = gen.get("seed")
    # h3.md §2 登记事实：当前工作流无 aspect_ratio 参数，画幅并入
    # extra.resolution（768p横/768p竖…）。gen.aspect 不透传——工作流
    # 私有字段一律经 extra.options 显式声明。
    return payload


def _result_video_url(body):
    data = body.get("data") or {}
    results = data.get("results") or body.get("results") or []
    for item in results:
        if isinstance(item, dict) and item.get("type") == "video" \
                and item.get("url"):
            return item["url"]
    raise BackendError("SUCCESS 返回中未找到视频结果: "
                       + json.dumps(body, ensure_ascii=False)[:500])


def _status_of(body):
    data = body.get("data")
    if isinstance(data, dict):
        return str(data.get("status") or body.get("status") or "").upper()
    return str(body.get("status") or "").upper()


def submit_and_wait(*, gen, root, prompt):
    """Submit one H3 job via AutoDL ComfyUI and wait for the mp4 bytes."""
    extra = gen.get("extra") or {}
    workflow = extra.get("workflow")
    if not workflow:
        raise BackendError(
            "gen.extra.workflow 未填（AutoDL workflow id）；"
            "图类/音类 workflow 的选取见 h3.md §2–§3")
    token = os.environ.get("AUTODL_API_KEY")
    if not token:
        raise BackendError("缺凭证：请先设置环境变量 AUTODL_API_KEY"
                           "（AutoDL 令牌，分组选 ComfyUI）")
    base = (extra.get("base_url") or _DEFAULT_BASE_URL).rstrip("/")
    poll_interval = float(extra.get("poll_interval_s")
                          or _DEFAULT_POLL_INTERVAL_S)
    timeout_s = float(extra.get("timeout_s") or _DEFAULT_TIMEOUT_S)

    payload = _build_payload(gen, root, prompt)
    submit_url = f"{base}/api/v1/comfyui/comfyui_workflow/{workflow}"
    resp = _http("POST", submit_url, token, payload=payload)
    if str(resp.get("code")) != "Success":
        raise BackendError("提交被拒: "
                           + json.dumps(resp, ensure_ascii=False)[:500])
    task_id = (resp.get("data") or {}).get("task_id") or resp.get("task_id")
    if not task_id:
        raise BackendError("提交成功但无 task_id: "
                           + json.dumps(resp, ensure_ascii=False)[:500])

    result_url = f"{base}/api/v1/comfyui/comfyui_workflow/result/{task_id}"
    deadline = time.time() + timeout_s
    while True:
        body = _http("GET", result_url, token)
        status = _status_of(body)
        if status == "SUCCESS":
            video_url = _result_video_url(body)
            mp4 = _http("GET", video_url, token, raw=True, timeout=300)
            return {"bytes": mp4, "task_id": task_id,
                    "seed": (body.get("data") or {}).get("seed")
                    if isinstance(body.get("data"), dict) else None,
                    "workflow": workflow, "model": gen.get("model")}
        if status in ("FAILED", "CANCEL"):
            raise BackendError(f"任务 {task_id} {status}: "
                               + json.dumps(body, ensure_ascii=False)[:500])
        if time.time() > deadline:
            raise BackendError(f"任务 {task_id} 轮询超时（{timeout_s}s），"
                               "可凭 task_id 到 AutoDL 控制台核对状态")
        time.sleep(poll_interval)


def main():
    ap = argparse.ArgumentParser(
        description="MiniMax H3 视频生成（独立 CLI，AutoDL ComfyUI）")
    ap.add_argument("--gen", required=True, help="gen.json 路径")
    ap.add_argument("--prompt", required=True, help="prompt.md 路径")
    ap.add_argument("--out", required=True, help="成片 mp4 落点")
    args = ap.parse_args()

    try:
        with open(args.gen, "r", encoding="utf-8") as f:
            gen = json.load(f)
        with open(args.prompt, "r", encoding="utf-8") as f:
            prompt = f.read()
        # inputs 相对路径相对 cwd 解析（runner 以项目根为 cwd）
        result = submit_and_wait(gen=gen, root=os.getcwd(), prompt=prompt)
        out = os.path.abspath(args.out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(result["bytes"])
        info = {k: result.get(k)
                for k in ("task_id", "seed", "workflow", "model")}
        print(json.dumps(info, ensure_ascii=False))
    except (OSError, ValueError, BackendError) as e:
        print(f"h3: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
