"""H3 离线请求组装与执行授权。无凭证、HTTP、上传或媒体编辑。

职责边界：
  - 只做客观能力校验、媒体装配、成稿纯净度/标记核对与 generate 授权核对；
  - 授权记录绑定真实 Prompt/本地输入；h3.py 只执行 manifest 内经准备工具冻结的
    request_snapshot，不从其他请求文件推导或补读执行参数。
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import math
import mimetypes
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from rhythm_engine import canonical_sha, to_ms
from rhythm_engine import project_file

# h3.json 能力档案物理留在 tools/video，虚拟路径 @skill/tools/video/h3.json 不变。
CAPABILITIES = Path(__file__).resolve().parents[1] / "tools" / "video" / "h3.json"
LOCAL_ENV = Path(__file__).resolve().parents[1] / ".env"
DEFAULT_BASE = "https://autodl.art"
SNAPSHOT_KEYS = {"model", "mode", "duration_s", "content_duration_s", "tail_handle_s",
                 "aspect", "seed", "workflow", "base_url", "resolution", "options",
                 "poll_interval_s", "timeout_s", "inputs"}
EXTRA_KEYS = {"workflow", "base_url", "resolution", "options", "poll_interval_s", "timeout_s"}
INPUT_KEYS = {"kind", "path", "role", "label", "slot", "duration_s", "source_ref"}
RESERVED = {"prompt", "duration", "duration_s", "seed", "resolution", "mode", "model", "workflow", "base_url", "inputs"}


class ContractError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(f"{code}: {message}")


def fail(code, message):
    raise ContractError(code, message)


def is_url(value):
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def local_settings(keys):
    """Read only requested settings; environment overrides the Skill-local .env."""
    values = {key: os.environ[key] for key in keys if key in os.environ}
    missing = set(keys) - values.keys()
    if missing and LOCAL_ENV.is_file():
        for line in LOCAL_ENV.read_text(encoding="utf-8-sig").splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key.strip() in missing:
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                values[key.strip()] = value
    return values


def resolve_deployment(snapshot, deployment):
    """冻结快照缺省 workflow/base_url 时只从 .env 或能力档补，不接受环境漂移。"""
    extra = {key: snapshot.get(key) for key in EXTRA_KEYS if key in snapshot}
    fields = (("workflow", "H3_WORKFLOW"), ("base_url", "H3_BASE_URL"))
    settings = local_settings({name for field, name in fields if not extra.get(field)})
    for field, name in fields:
        if not extra.get(field):
            extra[field] = settings.get(name, deployment.get(field))
    if not isinstance(extra.get("workflow"), str) or not extra["workflow"].strip():
        fail("h3_deployment_missing", "缺 workflow：在 Skill .env 设置 H3_WORKFLOW、h3.json.deployment.workflow 或快照 workflow 字段")
    snapshot["workflow"] = extra["workflow"]
    if "base_url" in extra or extra.get("base_url") is not None:
        snapshot["base_url"] = extra.get("base_url", DEFAULT_BASE)
    else:
        snapshot["base_url"] = DEFAULT_BASE
    for key in ("resolution", "options", "poll_interval_s", "timeout_s"):
        if key in extra:
            snapshot[key] = extra[key]


def check_purity(prompt, mode, duration):
    if not isinstance(prompt, str) or not prompt.strip():
        fail("h3_prompt_impure", "H3 正文为空")
    for bad in ("===== H3 FINAL PROMPT =====", "**①", "**②", "起复制", "```", "导演交付包", "导演总控卡"):
        if bad in prompt:
            fail("h3_prompt_impure", "混入交付包/分隔符/围栏；不提取子串提交")
    text = prompt.lstrip()
    lines = text.splitlines()
    first = lines[0]
    if mode == "I2VA":
        expected = "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced."
        valid = first == expected
    elif mode == "FL2VA":
        valid = re.fullmatch(r"How the reference pictures align with the target video — Picture 1 \(from Shot 1\) aligns with the 0\.00-second mark of the target video; Picture 2 \(from Shot [1-9]\d*\) aligns with the " + re.escape(f"{duration:.2f}") + r"-second mark of the target video\.", first) is not None
    elif mode == "L2VA":
        valid = re.fullmatch(r"How the reference pictures align with the target video — <Picture 1> \(from \[Shot [1-9]\d*\]\) aligns with the " + re.escape(f"{duration:.2f}") + r"-second mark of the target video\.", first) is not None
    else:
        valid = first.startswith("subject_definitions:" if mode == "Ref2VA" else "integrated_multimodal_description:")
    if not valid:
        fail("h3_prompt_impure", "首行不符合当前 H3 模式；合法锚帧指令须保持官方格式")
    if mode in {"I2VA", "FL2VA", "L2VA"}:
        if len(lines) < 3 or lines[1].strip():
            fail("h3_prompt_impure", "锚帧首行后需空行和 H3 正文")
        text = "\n".join(lines[2:])
    fields = (["subject_definitions", "summary", "retention_analysis", "detailed_description", "overall_soundscape", "non_diegetic_music"]
              if mode == "Ref2VA" else ["integrated_multimodal_description", "overall_soundscape", "non_diegetic_music"])
    markers = list(re.finditer(r"(?m)^([a-z_]+):", text))
    if [match.group(1) for match in markers] != fields:
        fail("h3_prompt_impure", "H3 字段缺失、重复、未知或顺序不符")
    if any(not text[match.end():markers[i + 1].start() if i + 1 < len(markers) else len(text)].strip() for i, match in enumerate(markers)):
        fail("h3_prompt_impure", "H3 字段正文为空")
    if re.search(r"(?m)^\s*(?:#{1,6}\s|\|.*\||(?:说明|备注|注|Note|Explanation|Here is|Here are)[:： ])", text):
        fail("h3_prompt_impure", "混入标题、表格或独立说明；只允许 H3 字段正文")


def _parameters(snapshot, cap):
    if not isinstance(snapshot, dict) or set(snapshot) - SNAPSHOT_KEYS:
        fail("h3_request_invalid", "请求快照只能包含已声明字段")
    if snapshot.get("model") not in {"H3", "MiniMax H3"}:
        fail("h3_request_invalid", "模型必须是当前 H3 能力档")
    try:
        duration_ms = to_ms(snapshot.get("duration_s"), positive=True)
    except ValueError:
        fail("tool_duration_unrepresentable", "请求时长必须为合法整数秒")
    if duration_ms % 1000 or not cap["min_duration_s"] * 1000 <= duration_ms <= cap["max_duration_s"] * 1000:
        fail("tool_duration_unrepresentable", "请求时长不在真实整数能力范围；不自动取整")
    if not isinstance(snapshot.get("workflow"), str) or not snapshot["workflow"].strip():
        fail("h3_request_invalid", "快照需冻结 workflow")
    base = snapshot.get("base_url", DEFAULT_BASE)
    if not isinstance(base, str) or not is_url(base):
        fail("h3_request_invalid", "base_url 需 HTTP(S) URL")
    resolution = snapshot.get("resolution")
    if resolution is not None and resolution not in cap.get("resolutions", []):
        fail("h3_request_invalid", "resolution 不符合能力档")
    if snapshot.get("aspect") is not None and snapshot["aspect"] not in cap.get("aspect_ratios", []):
        fail("h3_request_invalid", "aspect 不符合能力档")
    if snapshot.get("aspect") is not None:
        # This deployment has no independent aspect parameter. Never imply one was sent.
        width, height = (int(part) for part in snapshot["aspect"].split(":"))
        orientation = "横" if width > height else "竖" if width < height else "(1:1)"
        if resolution is None or not resolution.endswith(orientation):
            fail("h3_request_invalid", "当前封装的画幅方向由 resolution 承载；aspect 需与实际 resolution 一致")
    if "content_duration_s" in snapshot or "tail_handle_s" in snapshot:
        try:
            if (to_ms(snapshot.get("content_duration_s"), positive=True) + to_ms(snapshot.get("tail_handle_s")) != duration_ms):
                raise ValueError("内容 + 技术尾余量不等于请求")
        except ValueError as exc:
            fail("h3_request_invalid", str(exc))
    options = snapshot.get("options", {})
    if not isinstance(options, dict) or any(key in RESERVED or re.match(r"ref_(image|video|audio)_", key) for key in options):
        fail("h3_reserved_option", "options 不能覆盖正文、时长、已知参数或媒体槽位")
    try:
        canonical_sha(options)
    except (TypeError, ValueError):
        fail("h3_request_invalid", "options 必须是有限 JSON")
    for key, default in (("poll_interval_s", 10), ("timeout_s", 1800)):
        value = snapshot.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            fail("h3_runtime_invalid", f"{key} 必须是有限正数")
    if snapshot.get("seed") is not None and (not isinstance(snapshot["seed"], int) or isinstance(snapshot["seed"], bool)):
        fail("h3_request_invalid", "seed 必须整数或 null（随机种子）")
    return duration_ms // 1000


def _media(snapshot, root, cap):
    inputs = snapshot.get("inputs")
    if not isinstance(inputs, list):
        fail("h3_input_invalid", "inputs 必须是数组，可空")
    counts = {"image": 0, "video": 0, "audio": 0}
    media = []
    slots = {}
    for item in inputs:
        if not isinstance(item, dict) or set(item) - INPUT_KEYS:
            fail("h3_input_invalid", "输入条目或字段无效，不静默丢弃")
        kind, path = item.get("kind"), item.get("path")
        if kind not in counts or not isinstance(path, str) or not path:
            fail("h3_input_invalid", "每项需要有效 kind/path")
        n = counts[kind]
        if "slot" in item and (type(item["slot"]) is not int or item["slot"] != n):
            fail("h3_input_invalid", "显式 slot 必须匹配该模态数组顺序")
        counts[kind] += 1
        record = dict(item, slot=n)
        if is_url(path):
            # URL 原字符串进入 payload，不请求远端/本地副本，不编码，不声称远端字节不可变。
            record.update(identity="url_string_only", remote_bytes_verified=False)
            value = path
        else:
            if urlsplit(path).scheme:
                fail("h3_input_invalid", "只支持项目内文件或 HTTP(S) URL")
            local = project_file(root, path)
            raw = local.read_bytes()
            mime = mimetypes.guess_type(path)[0]
            if not mime or not mime.startswith(kind + "/"):
                fail("h3_input_invalid", "本地媒体扩展名与 kind 不符")
            record.update(identity="local_bytes", sha256=hashlib.sha256(raw).hexdigest())
            value = f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
        media.append(record)
        slots[f"ref_{kind}_{n}"] = value
    mode = snapshot.get("mode")
    if mode not in cap["modes"]:
        fail("h3_mode_invalid", "未知 H3 模式")
    # The selected mode comes from h3-prompt-writing. Do not infer it from modalities.
    if mode == "Ref2VA" and not inputs:
        fail("h3_input_invalid", "已选全参考模式缺实际参考输入；交回 h3-prompt-writing 核对")
    if mode == "FL2VA" and counts["image"] != 2 or mode in {"I2VA", "L2VA"} and not 1 <= counts["image"] <= cap["mode_ref_limits"][mode]["images_max"]:
        fail("h3_mode_invalid", "锚帧数与当前模式不符")
    limits = cap["mode_ref_limits"][mode]
    for kind, plural in (("image", "images"), ("video", "videos"), ("audio", "audios")):
        if counts[kind] > limits.get(plural + "_max", 0):
            fail("h3_input_invalid", "输入超真实模态槽位上限")
    if len(inputs) > limits.get("total_files_max", 1000000):
        fail("h3_input_invalid", "输入超真实总文件上限")
    if counts["audio"] and limits.get("audio_requires_visual_input") and not (counts["image"] or counts["video"]):
        fail("h3_input_invalid", "音频参考需要真实视觉输入")
    for kind in ("video", "audio"):
        entries = [item for item in inputs if item["kind"] == kind]
        total = 0
        for item in entries:
            try:
                duration = to_ms(item.get("duration_s"), positive=True)
            except ValueError:
                fail("h3_input_invalid", "音视频参考需登记已探测时长；URL 不在预检时下载")
            low, high = limits[kind + "_per_clip_s"]
            if not low * 1000 <= duration <= high * 1000:
                fail("h3_input_invalid", "参考单条时长超能力")
            total += duration
        if total > limits.get(kind + "_total_s", 0) * 1000:
            fail("h3_input_invalid", "参考累计时长超能力")
    return media, slots


def media_marker_orders(text, mode, kind):
    label = {"image": "Picture", "video": "Video", "audio": "Audio"}[kind]
    actual = {int(value) for value in re.findall(r"<\s*" + label + r"\s*(\d+)\s*>", text, re.I)}
    if kind == "image" and mode == "FL2VA" and text.strip():
        actual.update(int(value) for value in re.findall(r"\bPicture\s+(\d+)\s+\(", text.lstrip().splitlines()[0]))
    return actual


def check_media_markers(text, mode, media):
    for kind in ("image", "video", "audio"):
        actual = media_marker_orders(text, mode, kind)
        expected = set(range(1, sum(item["kind"] == kind for item in media) + 1))
        if actual != expected:
            fail("h3_input_marker_mismatch", "成稿媒体标记必须逐项对应实际输入槽位，无遗漏或未知引用")


@dataclass(frozen=True)
class PreparedRequest:
    payload: dict
    snapshot: dict
    media: list

    def summary(self):
        return {"ok": True, "mode": self.snapshot["mode"], "duration_s": self.snapshot["duration_s"],
                "remote_url_count": sum(item.get("identity") == "url_string_only" for item in self.media),
                "remote_identity_boundary": "URL 字符串已冻结；未验证远端内容字节",
                "aspect_transport": "封装仅提交 resolution；aspect 是方向兼容的创作意图，未独立提交精确比例"}


def load_capabilities():
    profile = json.loads(CAPABILITIES.read_text(encoding="utf-8"))
    return profile["capabilities"], profile.get("deployment", {})


def prepare_request(*, snapshot, root, prompt_file):
    """从 manifest 冻结快照组装实际请求；全部校验为客观结构/能力检查，不产生回执。"""
    snapshot = json.loads(json.dumps(snapshot, allow_nan=False))
    root = Path(root).resolve()
    cap, deployment = load_capabilities()
    resolve_deployment(snapshot, deployment)
    duration = _parameters(snapshot, cap)
    rel_prompt = project_file(root, prompt_file).relative_to(root).as_posix()
    text = project_file(root, rel_prompt).read_text(encoding="utf-8")
    check_purity(text, snapshot["mode"], duration)
    media, slots = _media(snapshot, root, cap)
    check_media_markers(text, snapshot["mode"], media)
    extra_options = snapshot.get("options", {})
    payload = dict(extra_options, prompt=text, **slots)
    payload["duration"] = duration
    if snapshot.get("resolution") is not None:
        payload["resolution"] = snapshot["resolution"]
    if snapshot.get("seed") is not None:
        payload["seed"] = snapshot["seed"]
    return PreparedRequest(payload=payload, snapshot=snapshot, media=media)


def check_authorization(root, segment_id, episode=None):
    """与 lint 共用确认读取器，执行前核对当前请求、Prompt 和本地输入。"""
    from video_confirmations import ConfirmationError, load_confirmation_history, validate_confirmations

    root = Path(root).resolve()
    if episode is not None and not re.fullmatch(r"ep_[1-9]\d*", episode):
        fail("video_generation_confirmation_episode_mismatch", "episode 必须形如 ep_1")
    paths = ([root / f"episodes/{episode}/04_视频片段/video_manifest_{episode}.json"] if episode else
             list((root / "episodes").glob("ep_*/04_视频片段/video_manifest_ep_*.json")))
    matches = []
    for path in paths:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            fail("video_manifest_unreadable", "生成授权需要可读取的视频 manifest")
        segments = manifest.get("segments")
        if not isinstance(segments, list):
            fail("video_segments_invalid", "视频 manifest 需要 segments 数组")
        for segment in segments:
            if isinstance(segment, dict) and segment.get("segment_id") == segment_id:
                matches.append((path.parent.parent.name, manifest, segment))
    if len(matches) != 1:
        fail("video_generation_confirmation_episode_mismatch", "SEG 不存在、重复或跨集同名；请显式指定 episode")
    episode, manifest, segment = matches[0]
    try:
        records = load_confirmation_history(root, episode, manifest)
        issues, active = validate_confirmations({"generation_confirmations": records}, manifest["segments"],
                                              root=root, check_outputs=False, return_active=True)
    except ConfirmationError as exc:
        fail(exc.code, str(exc))
    if issues:
        fail(issues[0]["code"], issues[0]["message"])
    latest = active.get(segment.get("episode_segment_index"))
    if latest is None:
        fail("video_generation_confirmation_missing", f"{episode}/{segment_id} 缺真实 generate 确认")
    return latest
