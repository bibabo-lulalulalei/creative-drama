# -*- coding: utf-8 -*-
"""h3.py — MiniMax H3 视频生成工具（独立 CLI，AutoDL ComfyUI 封装）。

位置：tools/video/h3.py。提供独立 CLI 和 submit_and_wait 函数入口。

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

参数面约定见 tools/README.md：
  - inputs[] 按 kind 分组、保数组序映射到 ref_image_N / ref_video_N /
    ref_audio_N 槽位；label/role 直通（标签与正文的对应由 prompt.md 承担）；
  - extra.workflow / extra.base_url 在预检时解析并写回，执行只用冻结值；extra.resolution /
    extra.options / extra.poll_interval_s / extra.timeout_s（可选）。

凭证：环境变量或 Skill 根 .env 的 AUTODL_API_KEY，环境优先。仅标准库。

CLI:
  python tools/video/h3.py --project-root <root> --gen <gen.json> --prompt <prompt.md>
        --out <take.mp4>
inputs[].path 相对路径以显式 --project-root 解析。成功后 stdout 末行
打印结果 JSON（task_id/seed/workflow/model，供调用方登记来源）。
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

from h3_contract import prepare_request, check_authorization, local_settings

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
    except urllib.error.HTTPError as e:
        # Backend bodies can echo signed URLs, tokens and full media data URIs.
        raise BackendError(f"AutoDL HTTP {e.code}；未输出可能含输入内容的响应正文") from None
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


def submit_and_wait(*, gen, root, prompt):
    """Submit one H3 job via AutoDL ComfyUI and wait for the mp4 bytes."""
    prepared = prepare_request(gen=gen, root=root, prompt=prompt)
    return _submit_prepared(prepared, root)


def _submit_prepared(prepared, root):
    """Use the caller's same validated snapshot; authorization is still checked here."""
    check_authorization(root, prepared)
    gen = prepared.gen
    extra = gen.get("extra") or {}
    workflow = extra.get("workflow")
    token = local_settings({"AUTODL_API_KEY"}).get("AUTODL_API_KEY")
    if not token:
        raise BackendError("缺凭证：请在环境变量或 Skill 根 .env 设置 AUTODL_API_KEY（AutoDL ComfyUI 令牌）")
    base = (extra.get("base_url") or _DEFAULT_BASE_URL).rstrip("/")
    poll_interval = float(extra.get("poll_interval_s")
                          or _DEFAULT_POLL_INTERVAL_S)
    timeout_s = float(extra.get("timeout_s") or _DEFAULT_TIMEOUT_S)

    payload = prepared.payload
    submit_url = f"{base}/api/v1/comfyui/comfyui_workflow/{workflow}"
    resp = _http("POST", submit_url, token, payload=payload)
    if str(resp.get("code")) != "Success":
        raise BackendError("提交被拒；请核对工作流与输入参数")
    task_id = (resp.get("data") or {}).get("task_id") or resp.get("task_id")
    if not task_id:
        raise BackendError("提交成功但无 task_id")

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
            raise BackendError(f"任务 {task_id} {status}")
        if time.time() > deadline:
            raise BackendError(f"任务 {task_id} 轮询超时（{timeout_s}s），"
                               "可凭 task_id 到 AutoDL 控制台核对状态")
        time.sleep(poll_interval)


def main():
    ap = argparse.ArgumentParser(description="MiniMax H3 生成或本地合同检查")
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--gen", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    try:
        from pathlib import Path
        root = Path(args.project_root).resolve()
        gen_path = (root / args.gen).resolve()
        prompt_path = (root / args.prompt).resolve()
        if not gen_path.is_relative_to(root) or not prompt_path.is_relative_to(root):
            raise ValueError("gen/prompt 必须位于显式项目根内")
        gen = json.loads(gen_path.read_text(encoding="utf-8"))
        prepared = prepare_request(gen=gen, root=root,
                                   prompt_file=str(prompt_path.relative_to(root)).replace("\\", "/"))
        if args.check_only:
            print(json.dumps(prepared.summary(), ensure_ascii=False))
            return 0
        if not args.out:
            ap.error("实际生成需要 --out")
        out = (root / args.out).resolve()
        if not out.is_relative_to(root):
            raise ValueError("输出必须位于项目根内")
        result = _submit_prepared(prepared, root)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(result["bytes"])
        print(json.dumps({key: result.get(key) for key in ("task_id", "seed", "workflow", "model")}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, BackendError) as exc:
        print(f"h3: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
