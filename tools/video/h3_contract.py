"""H3 离线合同与同次快照请求准备。无凭证、HTTP、上传或媒体编辑。"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from rhythm_engine import canonical_sha, design_projection, to_ms
from rhythm_engine import project_file
from adopted_cut import validate_inbound

CAPABILITIES = Path(__file__).with_name("h3.json")
LOCAL_ENV = Path(__file__).resolve().parents[2] / ".env"
DEFAULT_BASE = "https://autodl.art"
REQUEST_KEYS = {"model", "mode", "duration_s", "content_duration_s", "tail_handle_s", "aspect", "seed", "inputs", "extra", "preflight"}
EXTRA_KEYS = {"workflow", "base_url", "resolution", "options", "poll_interval_s", "timeout_s"}
INPUT_KEYS = {"kind", "path", "role", "label", "slot", "duration_s", "source_ref"}
RESERVED = {"prompt", "duration", "duration_s", "seed", "resolution", "mode", "model", "workflow", "base_url", "inputs"}
ALLOWED_DEPENDENCY_ROLES = {"director_package", "timing_input", "storyboard_design", "planning_design",
                            "source_script", "script_markdown", "source_confirmation", "asset_facts", "adopted_cut_out", "capabilities"}


class ContractError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(f"{code}: {message}")


def fail(code, message):
    raise ContractError(code, message)


def snapshot_bytes(path):
    path = Path(path)
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        fail("preflight_binding_mismatch", "读取时检测到文件变化")
    return raw


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


def resolve_deployment(gen, deployment, *, verify):
    if not isinstance(gen, dict):
        fail("h3_request_invalid", "gen 必须是对象")
    extra = gen.get("extra", {})
    if not isinstance(extra, dict) or set(extra) - EXTRA_KEYS:
        fail("h3_request_invalid", "extra 必须是已声明配置字段的对象")
    if verify:
        # Confirmed requests cannot acquire new settings from the environment.
        if not extra.get("workflow") or not extra.get("base_url"):
            fail("preflight_binding_mismatch", "执行请求缺冻结的 workflow/base_url；先预检写回再确认")
    else:
        fields = (("workflow", "H3_WORKFLOW"), ("base_url", "H3_BASE_URL"))
        settings = local_settings({name for field, name in fields if field not in extra})
        for field, name in fields:
            if field not in extra:
                extra[field] = settings.get(name, deployment.get(field))
    if not isinstance(extra.get("workflow"), str) or not extra["workflow"].strip():
        fail("h3_deployment_missing", "缺 workflow：在 Skill .env 设置 H3_WORKFLOW、h3.json.deployment.workflow 或 gen.extra.workflow")
    gen["extra"] = extra


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


def scoped_design(data, shot_ids):
    """Dependency projection for one SEG; runtime history and unrelated shots stay outside it."""
    if not isinstance(shot_ids, list) or not shot_ids or len(shot_ids) != len(set(shot_ids)):
        fail("preflight_dependency_invalid", "依赖镜头范围无效")
    selected = set(shot_ids)
    shots = [dict((k, v) for k, v in row.items() if k != "segment_id")
             for row in data.get("shots", []) if row.get("shot_id") in selected]
    if [row["shot_id"] for row in shots] != shot_ids:
        fail("preflight_dependency_invalid", "依赖镜头不存在或顺序已变")
    segments = [{k: v for k, v in row.items() if k not in {"content_review", "preflight", "status", "task_id"}}
                for row in data.get("segments", []) if selected.intersection(row.get("shot_ids", []))]
    chains = [row for row in data.get("causal_ledger", []) if selected.intersection(
        row.get("evidence_shot_ids", []) + row.get("reaction_shot_ids", []) + row.get("result_shot_ids", []))]
    return {"episode_id": data.get("episode_id"), "shots": shots, "segments": segments, "causal_ledger": chains,
            "audience_execution": data.get("audience_execution")}


def scoped_timing(data, shot_ids):
    from rhythm_engine import timing_projection
    selected = set(shot_ids)
    scenes = []
    utterances = set()
    for scene in data["scenes"]:
        shots = [row for row in scene["shots"] if row["shot_id"] in selected]
        for shot in shots:
            utterances.update(row["utterance_id"] for row in shot["timeline"] if row["kind"] == "speech")
        if shots:
            scenes.append({"scene_id": scene["scene_id"], "shots": shots,
                "beat_groups": [row for row in scene.get("beat_groups", []) if selected.intersection(row["shot_ids"])]})
    return timing_projection({"scenes": scenes, "utterances": [row for row in data["utterances"] if row["utterance_id"] in utterances]})


def _parameters(gen, cap):
    if not isinstance(gen, dict) or set(gen) - REQUEST_KEYS:
        fail("h3_request_invalid", "gen 必须是对象，且只能包含已声明字段")
    if gen.get("model") not in {"H3", "MiniMax H3"}:
        fail("h3_request_invalid", "模型必须是当前 H3 能力档")
    try:
        duration_ms = to_ms(gen.get("duration_s"), positive=True)
    except ValueError:
        fail("tool_duration_unrepresentable", "请求时长必须为合法整数秒")
    if duration_ms % 1000 or not cap["min_duration_s"] * 1000 <= duration_ms <= cap["max_duration_s"] * 1000:
        fail("tool_duration_unrepresentable", "请求时长不在真实整数能力范围；不自动取整")
    extra = gen.get("extra")
    if not isinstance(extra, dict) or set(extra) - EXTRA_KEYS or not isinstance(extra.get("workflow"), str) or not extra["workflow"].strip():
        fail("h3_request_invalid", "extra 需 workflow，未知字段不得静默忽略")
    base = extra.get("base_url", DEFAULT_BASE)
    if not isinstance(base, str) or not is_url(base):
        fail("h3_request_invalid", "base_url 需 HTTP(S) URL")
    resolution = extra.get("resolution")
    if resolution is not None and resolution not in cap.get("resolutions", []):
        fail("h3_request_invalid", "resolution 不符合能力档")
    if gen.get("aspect") is not None and gen["aspect"] not in cap.get("aspect_ratios", []):
        fail("h3_request_invalid", "aspect 不符合能力档")
    if gen.get("aspect") is not None:
        # This deployment has no independent aspect parameter. Never imply one was sent.
        width, height = (int(part) for part in gen["aspect"].split(":"))
        orientation = "横" if width > height else "竖" if width < height else "(1:1)"
        if resolution is None or not resolution.endswith(orientation):
            fail("h3_request_invalid", "当前封装的画幅方向由 resolution 承载；aspect 需与实际 resolution 一致")
    if "content_duration_s" in gen or "tail_handle_s" in gen:
        try:
            if (to_ms(gen.get("content_duration_s"), positive=True) + to_ms(gen.get("tail_handle_s")) != duration_ms):
                raise ValueError("内容 + 技术尾余量不等于请求")
        except ValueError as exc:
            fail("h3_request_invalid", str(exc))
    options = extra.get("options", {})
    if not isinstance(options, dict) or any(key in RESERVED or re.match(r"ref_(image|video|audio)_", key) for key in options):
        fail("h3_reserved_option", "options 不能覆盖正文、时长、已知参数或媒体槽位")
    try:
        canonical_sha(options)
    except (TypeError, ValueError):
        fail("h3_request_invalid", "options 必须是有限 JSON")
    for key, default in (("poll_interval_s", 10), ("timeout_s", 1800)):
        value = extra.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            fail("h3_runtime_invalid", f"{key} 必须是有限正数")
    if "seed" in gen and (not isinstance(gen["seed"], int) or isinstance(gen["seed"], bool)):
        fail("h3_request_invalid", "seed 必须整数")
    return extra, duration_ms // 1000


def _media(gen, root, cap):
    inputs = gen.get("inputs")
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
            raw = snapshot_bytes(local)
            mime = mimetypes.guess_type(path)[0]
            if not mime or not mime.startswith(kind + "/"):
                fail("h3_input_invalid", "本地媒体扩展名与 kind 不符")
            record.update(identity="local_bytes", sha256=hashlib.sha256(raw).hexdigest())
            value = f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
        media.append(record)
        slots[f"ref_{kind}_{n}"] = value
    mode = gen.get("mode")
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


def dependency_snapshot(root, spec):
    if not isinstance(spec, dict) or spec.get("role") not in ALLOWED_DEPENDENCY_ROLES:
        fail("preflight_dependency_invalid", "未知依赖角色")
    role, rel = spec["role"], spec.get("file")
    path = CAPABILITIES if role == "capabilities" and rel == "@skill/tools/video/h3.json" else project_file(root, rel)
    rel = "@skill/tools/video/h3.json" if role == "capabilities" else path.relative_to(Path(root).resolve()).as_posix()
    raw = snapshot_bytes(path)
    value = raw
    record = {"role": role, "file": rel}
    if role in {"storyboard_design", "planning_design"}:
        data = json.loads(raw.decode("utf-8-sig"))
        scoped = role == "storyboard_design" and spec.get("shot_ids") is not None
        value = json.dumps(scoped_design(data, spec["shot_ids"]) if scoped else design_projection(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        record["projection"] = "segment_design" if scoped else "design"
        if scoped:
            record["shot_ids"] = spec["shot_ids"]
    elif role == "timing_input" and spec.get("shot_ids") is not None:
        record.update(projection="segment_timing", shot_ids=spec["shot_ids"])
        value = json.dumps(scoped_timing(json.loads(raw.decode("utf-8-sig")), spec["shot_ids"]), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    elif role == "source_confirmation":
        rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        selected = [row for row in rows if row.get("confirmation_id") == spec.get("confirmation_id")]
        if len(selected) != 1:
            fail("source_revision_mismatch", "源确认 ID 不存在或重复")
        record["confirmation_id"] = spec["confirmation_id"]
        value = json.dumps(selected[0], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    record["sha256"] = hashlib.sha256(value).hexdigest()
    return record


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
    contract: dict
    gen: dict

    def summary(self):
        return {"ok": True, "binding_id": self.contract["binding_id"], "mode": self.gen["mode"], "duration_s": self.gen["duration_s"],
                "remote_url_count": sum(item.get("identity") == "url_string_only" for item in self.contract["media"]),
                "remote_identity_boundary": "URL 字符串已冻结；未验证远端内容字节",
                "aspect_transport": "封装仅提交 resolution；aspect 是方向兼容的创作意图，未独立提交精确比例"}


def prepare_request(*, gen, root, prompt=None, prompt_file=None, verify=True, dependency_specs=None,
                    content_review_ref=None, compilation_map=None, inbound=None):
    try:
        gen = json.loads(json.dumps(gen, allow_nan=False))
    except (ValueError, TypeError):
        fail("h3_request_invalid", "gen 必须为有限 JSON")
    root = Path(root).resolve()
    cap_raw = snapshot_bytes(CAPABILITIES)
    profile = json.loads(cap_raw.decode("utf-8"))
    cap = profile["capabilities"]
    resolve_deployment(gen, profile.get("deployment", {}), verify=verify)
    extra, duration = _parameters(gen, cap)
    receipt = gen.get("preflight") or {}
    if not isinstance(receipt, dict) or verify and not receipt:
        fail("preflight_binding_mismatch", "preflight 必须为完整回执对象")
    rel_prompt = prompt_file or receipt.get("h3_prompt_file")
    if not rel_prompt:
        fail("preflight_binding_mismatch", "缺独立 H3 文件路径")
    raw = snapshot_bytes(project_file(root, rel_prompt))
    rel_prompt = project_file(root, rel_prompt).relative_to(root).as_posix()
    text = raw.decode("utf-8")
    if prompt is not None and prompt != text:
        fail("preflight_binding_mismatch", "调用方正文与当前 H3 文件不同")
    check_purity(text, gen["mode"], duration)
    media, slots = _media(gen, root, cap)
    check_media_markers(text, gen["mode"], media)
    specs = dependency_specs if dependency_specs is not None else receipt.get("dependencies", [])
    if not isinstance(specs, list) or any(not isinstance(spec, dict) for spec in specs):
        fail("preflight_dependency_invalid", "dependencies 必须为对象数组")
    dependencies = [dependency_snapshot(root, spec) for spec in specs]
    roles = {dep["role"] for dep in dependencies}
    if "director_package" not in roles or "storyboard_design" not in roles:
        fail("preflight_dependency_invalid", "需导演包和实际分镜设计依赖")
    if any(dep["role"] == "director_package" and dep["file"] == rel_prompt for dep in dependencies):
        fail("preflight_dependency_invalid", "导演包与纯 H3 成稿必须是两个独立文件")
    dependencies = [dep for dep in dependencies if dep["role"] != "capabilities"]
    dependencies.append({"role": "capabilities", "file": "@skill/tools/video/h3.json", "sha256": hashlib.sha256(cap_raw).hexdigest()})
    inbound = inbound if inbound is not None else receipt.get("inbound")
    if inbound:
        validate_inbound(root, inbound["cut_file"], inbound["cut_id"], gen["inputs"])
        if not any(dep["role"] == "adopted_cut_out" and dep["file"] == inbound["cut_file"] for dep in dependencies):
            fail("preflight_dependency_invalid", "入站出点必须登记依赖")
    request = {"model": gen["model"], "mode": gen["mode"], "duration_s": duration, "aspect": gen.get("aspect"),
               "seed": gen.get("seed"), "workflow": extra["workflow"], "base_url": extra.get("base_url", DEFAULT_BASE),
               "resolution": extra.get("resolution"), "options": extra.get("options", {}), "inputs": media,
               "content_duration_s": gen.get("content_duration_s"), "tail_handle_s": gen.get("tail_handle_s")}
    review = content_review_ref if content_review_ref is not None else receipt.get("content_review_ref")
    mapping = compilation_map if compilation_map is not None else receipt.get("compilation_map")
    if not isinstance(review, str) or not review or not isinstance(mapping, list) or not mapping:
        fail("preflight_dependency_invalid", "缺当前内容对照引用或实际编译映射")
    for row in mapping:
        if (not isinstance(row, dict) or not row.get("shot_id") or not isinstance(row.get("text_excerpt"), str)
                or not row["text_excerpt"] or row["text_excerpt"] not in text):
            fail("h3_compilation_mismatch", "编译映射需指向成稿实际段落；引用不证明语义保真")
        for spoken in row.get("spoken_texts", []):
            if not any(spoken in block for block in re.findall(r"<d>(.*?)</d>", row["text_excerpt"], re.S)):
                fail("source_line_uncovered", "已知台词未出现在对应发声块")
    contract = {"h3_prompt_file": rel_prompt,
                "h3_prompt_sha256": hashlib.sha256(raw).hexdigest(), "request_sha256": canonical_sha(request),
                "request_snapshot": request, "dependencies": dependencies, "media": media,
                "content_review_ref": review, "compilation_map": mapping, "inbound": inbound}
    contract["binding_id"] = canonical_sha(contract)
    if verify:
        saved = {key: value for key, value in receipt.items() if key != "validated_at"}
        if saved != contract:
            fail("preflight_binding_mismatch", "预检缺失或当前文件/参数/输入/出点/源依赖已变，POST 前阻断")
    payload = dict(extra.get("options", {}), prompt=text, **slots)
    payload["duration"] = duration
    if extra.get("resolution") is not None:
        payload["resolution"] = extra["resolution"]
    if gen.get("seed") is not None:
        payload["seed"] = gen["seed"]
    return PreparedRequest(payload=payload, contract=contract, gen=gen)


def preflight_receipt(prepared):
    return dict(prepared.contract, validated_at=datetime.now(timezone.utc).isoformat())


def check_authorization(root, prepared):
    path = Path(root) / "00_制作控制/用户确认记录.jsonl"
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError):
        fail("video_generation_confirmation_missing", "实际执行需真实 generate 确认；预检不是授权")
    binding = prepared.contract["binding_id"]
    rows = [row for row in rows if isinstance(row, dict)]
    matches = [row for row in rows if row.get("confirmation_purpose") == "video_generation"
               and row.get("valid", True) is not False
               and isinstance(row.get("binding_ids"), list)
               and binding in row.get("binding_ids", [])]
    latest = matches[-1] if matches else {}
    def scope(record, selected_binding=None):
        snapshot = record.get("request_snapshot", {})
        parts = snapshot.get("segments", []) if isinstance(snapshot, dict) else None
        if (not isinstance(parts, list) or any(not isinstance(seg, dict)
                or not isinstance(seg.get("segment_id"), str) or type(seg.get("episode_segment_index")) is not int for seg in parts)):
            fail("video_generation_confirmation_missing", "执行确认的冻结请求范围无效")
        return {(seg["segment_id"], seg["episode_segment_index"]) for seg in parts
                if selected_binding is None or seg.get("binding_id") == selected_binding}
    old_scope = scope(latest, binding)
    for row in rows[rows.index(latest) + 1:] if latest else []:
        supersedes = row.get("supersedes_confirmation_ids", [])
        if (isinstance(supersedes, list) and latest.get("confirmation_id") in supersedes
                and row.get("decision") == "confirmed" and row.get("valid", True) is not False):
            new_scope = scope(row)
            superseded_bindings = row.get("superseded_binding_ids", [])
            if not isinstance(superseded_bindings, list):
                fail("video_generation_confirmation_missing", "执行确认的替代范围无效")
            if (len(latest.get("binding_ids", [])) == 1 or old_scope.intersection(new_scope)
                    or binding in superseded_bindings):
                fail("video_generation_confirmation_missing", "该 SEG 请求确认已被替代，不能执行历史绑定")
    snapshots = latest.get("request_snapshots", {})
    if (latest.get("decision") != "confirmed" or latest.get("interaction_ask_result") != "generate"
            or not latest.get("interaction_ask_call_id") or not latest.get("confirmation_id")
            or not str(latest.get("user_message") or "").strip()
            or not isinstance(snapshots, dict) or snapshots.get(binding) != prepared.contract["request_snapshot"]):
        fail("video_generation_confirmation_missing", "缺覆盖同一 binding_id/冻结请求的 generate 确认")
