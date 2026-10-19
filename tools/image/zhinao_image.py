# -*- coding: utf-8 -*-
"""zhinao_image.py — 知脑中转（zhinaoapi.ai）图片生成工具（独立 CLI）。

配置取自 --config 指向的 tools/image/zhinao_image.json：
    backend / base_url / model_id / size / quality / timeout_s / max_reference_images
    extra          私有字段直通口，原样并入请求体
    base_url 可由环境变量 GROK_MODELS_BASE_URL 覆盖。

凭证：环境变量 XAI_API_KEY（自动读 skill 根 .env）。

两条路由（勿改）：
    无 --ref → POST {base}/images/generations（JSON）文生图
    有 --ref → POST {base}/images/edits（multipart，image 字段重复即多张）
    **绝不可把参考图塞进 generations 的 image[]**：返回 200 照常计费但静默忽略
    参考图，另画一张无关内容。

实测结论（gpt-image-2 通道）：
- size：仅标准三档 1024x1024 / 1536x1024 / 1024x1536 兑现；自定义尺寸被忽略，
  比例由模型按 prompt 自选。
- quality：生效，配置里写 "high" 即发送。
- input_fidelity / response_format：无效或已废弃，代码不发送。
- 模型池会换上游通道：/v1/models 只反映当前通道；model_id 失效用
  GET /v1/models/<id> 核实。

相对路径（ref/out）以当前工作目录解析。仅标准库。
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

_DEFAULT_BASE_URL = "https://api.zhinaoapi.ai/v1"
# 该中转站封禁 Python-urllib 的 UA（返回 502 upstream_error），必须伪装浏览器。
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
_MIME = {".png": "image/png", ".jpeg": "image/jpeg", ".jpg": "image/jpeg",
         ".webp": "image/webp", ".bmp": "image/bmp", ".tiff": "image/tiff",
         ".gif": "image/gif", ".heic": "image/heic", ".heif": "image/heif"}

# skill 根 .env：tools/image/ -> tools/ -> skill 根
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), ".env")


def _load_env_file():
    """读 skill 根 .env（KEY=VALUE），已存在的环境变量优先。"""
    if not os.path.exists(_ENV_PATH):
        return
    with open(_ENV_PATH, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            key, sep, value = line.partition("=")
            if sep:
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _multipart(fields, files):
    """构造 multipart/form-data 体。files 为 [(字段名, 路径)]，字段名可重复。"""
    boundary = "----zhinao-" + uuid.uuid4().hex
    out = bytearray()
    for name, value in fields:
        out += (f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n").encode("utf-8")
    for name, path in files:
        ext = os.path.splitext(path)[1].lower()
        mime = _MIME.get(ext)
        if not mime:
            raise RuntimeError(f"不支持的参考图格式 {path}")
        out += (f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{os.path.basename(path)}"\r\n'
                f"Content-Type: {mime}\r\n\r\n").encode("utf-8")
        with open(path, "rb") as f:
            out += f.read()
        out += b"\r\n"
    out += f"--{boundary}--\r\n".encode("utf-8")
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def _post(url, body, content_type, api_key, timeout):
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": content_type,
                 "Authorization": f"Bearer {api_key}",
                 "User-Agent": _UA},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        if "model_not_found" in detail or "grok_media_no_eligible_account" in detail:
            detail += ("\n  ↑ 中转站会换上游通道，model_id 可能已失效；"
                       "用 GET /v1/models/<id> 核实")
        raise RuntimeError(f"知脑中转 API HTTP {e.code}: {detail}") from None


def generate(*, prompt_text, reference_paths, asset_image):
    """返回图片 bytes（不写盘，落盘是调用方的责任）。"""
    _load_env_file()
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        raise RuntimeError("缺凭证：请先设置环境变量 XAI_API_KEY（知脑中转令牌）")

    model_id = asset_image.get("model_id")
    if not model_id:
        raise RuntimeError("配置的 model_id 未登记（如 gpt-image-2.5-sunburst）")

    refs = list(reference_paths or [])
    max_refs = asset_image.get("max_reference_images")
    if max_refs and len(refs) > max_refs:
        raise RuntimeError(f"参考图 {len(refs)} 张超过后端上限 {max_refs}")

    base = (os.environ.get("GROK_MODELS_BASE_URL") or asset_image.get("base_url")
            or _DEFAULT_BASE_URL).rstrip("/")
    timeout = asset_image.get("timeout_s") or 300

    params = {"model": model_id, "prompt": prompt_text}
    for key in ("size", "quality"):
        if asset_image.get(key):
            params[key] = asset_image[key]
    params.update(asset_image.get("extra") or {})

    if refs:
        fields = [(k, v if isinstance(v, str) else json.dumps(v))
                  for k, v in params.items()]
        body, ctype = _multipart(fields, [("image", p) for p in refs])
        url = f"{base}/images/edits"
    else:
        body = json.dumps(params).encode("utf-8")
        ctype = "application/json"
        url = f"{base}/images/generations"

    result = _post(url, body, ctype, api_key, timeout)

    data = result.get("data") or []
    if not data:
        raise RuntimeError(
            f"知脑中转返回无图片数据: {json.dumps(result, ensure_ascii=False)[:500]}")
    first = data[0]
    if first.get("error"):
        raise RuntimeError(f"知脑中转图片错误: {json.dumps(first['error'], ensure_ascii=False)}")

    if first.get("b64_json"):
        return base64.b64decode(first["b64_json"])
    if first.get("url"):
        dl = urllib.request.Request(first["url"], headers={"User-Agent": _UA})
        with urllib.request.urlopen(dl, timeout=timeout) as r:
            return r.read()
    raise RuntimeError(
        f"知脑中转返回中既无 b64_json 也无 url: {json.dumps(first, ensure_ascii=False)[:500]}")


def main():
    ap = argparse.ArgumentParser(description="知脑中转图片生成（独立 CLI）")
    ap.add_argument("--config", required=True, help="tools/image/zhinao_image.json")
    prompt = ap.add_mutually_exclusive_group(required=True)
    prompt.add_argument("--prompt-file", help="生产提示词文件（取正文）")
    prompt.add_argument("--prompt", help="生产提示词文本")
    ap.add_argument("--ref", action="append", default=[],
                    help="参考图路径，可重复（存在即走 edits 参考生图）")
    ap.add_argument("--out", required=True, help="成品落点")
    args = ap.parse_args()

    try:
        with open(args.config, "r", encoding="utf-8") as f:
            asset_image = json.load(f)
        if args.prompt_file:
            with open(args.prompt_file, "r", encoding="utf-8") as f:
                prompt_text = f.read()
        else:
            prompt_text = args.prompt
        data = generate(prompt_text=prompt_text,
                        reference_paths=[os.path.abspath(p) for p in args.ref],
                        asset_image=asset_image)
        out = os.path.abspath(args.out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(data)
    except (OSError, ValueError, RuntimeError) as e:
        print(f"zhinao_image: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
