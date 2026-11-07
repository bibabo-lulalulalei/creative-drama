"""实际采用出点合同。只核指纹/坐标，不判断该帧是否是理想切点。"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from rhythm_engine import canonical_sha, to_ms
from rhythm_engine import project_file


class CutError(ValueError):
    pass


def validate_cut(root, cut):
    try:
        if not isinstance(cut, dict):
            raise ValueError("adopted_cut_out 必须是对象")
        source = project_file(root, cut["source_video_file"])
        frame = project_file(root, cut["frame_file"])
        if hashlib.sha256(source.read_bytes()).hexdigest() != cut["source_video_sha256"]:
            raise ValueError("源视频指纹已变")
        if hashlib.sha256(frame.read_bytes()).hexdigest() != cut["frame_sha256"]:
            raise ValueError("对应入站帧指纹已变")
        point = to_ms(cut["timecode_s"])
        start = to_ms(cut["adopted_in_s"])
        measured = to_ms(cut["measured_duration_s"], positive=True)
        if not start < point <= measured:
            raise ValueError("出点不在实测视频/采用区间")
        fps = cut.get("fps")
        frame_number = cut.get("frame_number")
        if (not isinstance(fps, int) or isinstance(fps, bool) or fps <= 0
                or not isinstance(frame_number, int) or isinstance(frame_number, bool) or frame_number < 0):
            raise ValueError("需实际帧率及对应帧号")
        # trim end 为排他边界；入站必须取该边界前最后一个保留帧。
        # PTS 保留 ffprobe 的十进制原文，不用平均 fps 反推或舍入帧身份。
        pts = Decimal(cut["frame_timecode_s"])
        next_value = cut["next_frame_timecode_s"]
        next_pts = Decimal(next_value) if next_value is not None else None
        boundary = Decimal(point) / 1000
        if (not pts.is_finite() or pts < Decimal(start) / 1000 or pts >= boundary
                or next_pts is not None and (not next_pts.is_finite() or next_pts <= pts or next_pts < boundary)):
            raise ValueError("对应帧必须是采用区间内、排他出点之前最后保留的帧")
        fields = {key: cut[key] for key in ("source_video_file", "source_video_sha256", "timecode_s",
                  "adopted_in_s", "measured_duration_s", "frame_file", "frame_sha256", "fps", "frame_number",
                  "frame_timecode_s", "next_frame_timecode_s")}
        return canonical_sha(fields)
    except (OSError, KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise CutError(f"adopted_cut_out_invalid: {exc}") from None


def validate_inbound(root, cut_file, expected_cut_id, inputs):
    path = project_file(root, cut_file)
    cut = json.loads(path.read_text(encoding="utf-8"))
    actual = validate_cut(root, cut)
    if actual != expected_cut_id:
        raise CutError("adopted_cut_out_changed: 出点变化使后段帧/请求绑定失效")
    matching = [item for item in inputs if item.get("role") == "previous_tail_as_start_frame"]
    if len(matching) != 1 or matching[0].get("path") != cut["frame_file"]:
        raise CutError("adopted_cut_out_invalid: 后段入站帧必须来自锁定采用出点")
    return cut, actual


def trim_args(root, cut_file, cut_id, source_file, start_s, end_s):
    cut = json.loads(project_file(root, cut_file).read_text(encoding="utf-8"))
    if validate_cut(root, cut) != cut_id or source_file != cut["source_video_file"]:
        raise CutError("adopted_cut_out_changed: 最终 trim 依赖的源/出点已变")
    if to_ms(start_s) != to_ms(cut["adopted_in_s"]) or to_ms(end_s) != to_ms(cut["timecode_s"]):
        raise CutError("adopted_cut_out_invalid: 最终 trim 必须使用同一采用区间")
    return {"start_s": cut["adopted_in_s"], "end_s": cut["timecode_s"]}
