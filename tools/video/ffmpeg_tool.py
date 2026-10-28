# -*- coding: utf-8 -*-
"""Extract a frame from a video with ffmpeg.

Usage:
  python tools/video/ffmpeg_tool.py frame <video> <out.png> [--at S.SS | --tail | --first]
        -> prints the output image path (default: --first)
  python tools/video/ffmpeg_tool.py strip <video> <out.png> [--interval S] [--cols N]
        -> tiles evenly-spaced frames into one strip image (default: 0.5s, 10 cols)

doubao-creative-drama 本地 MediaKit 替代子命令（对应豆包 mediakit 能力）:
  probe  <video> [--json]                          ≈ probe-video-metadata
  trim   <video> <out.mp4> --start S --end S       ≈ trim-video（有效区间裁剪）
  concat <out.mp4> <seg1.mp4> [seg2.mp4 ...]       ≈ concat-video（成片拼接，统一 24fps）
  burn   <video> <srt> <out.mp4> [--size 36] [--pos bottom|lower_third]
        ≈ add-subtitle-to-video（字幕烧录；字幕文本来自剧本台词稿，跳过 ASR）
  erase  <video> <out.mp4> --region x,y,w,h [--region ...]
        ≈ erase-watermark（固定区域文字/水印 delogo 擦除；移动文字走返修重生）

Requires ffmpeg on PATH (https://www.gyan.dev/ffmpeg/builds/).
Used by the tail-frame chain: after a shot renders, extract its final frame
with --tail to become the next shot's first-frame anchor.
The strip command is the review tool for motion hypotheses (试拍评审 / 审片):
sparse stills misjudge event physics — only a dense frame strip shows what
actually happens across the whole clip.
"""
import argparse
import os
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def die(msg, code=1):
    print(f"ERROR: {msg}")
    sys.exit(code)


def extract_frame(path, out, mode, at=None):
    if not os.path.isfile(path):
        die(f"文件不存在: {path}")
    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)

    if mode == "tail":
        # last decoded frame near EOF (h3.md §6 convention)
        cmd = ["ffmpeg", "-y", "-sseof", "-0.1", "-i", path,
               "-frames:v", "1", out]
    elif mode == "at":
        # -ss before -i = fast seek to the closest keyframe
        cmd = ["ffmpeg", "-y", "-ss", str(at), "-i", path,
               "-frames:v", "1", out]
    else:  # first
        cmd = ["ffmpeg", "-y", "-i", path, "-frames:v", "1", out]

    p = run(cmd)
    if p.returncode != 0 or not os.path.exists(out):
        die(f"抽帧失败: {p.stderr.strip()}")
    return out


def _duration_s(path):
    p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path])
    try:
        return float(p.stdout.strip())
    except ValueError:
        die(f"无法读取视频时长: {p.stderr.strip() or p.stdout.strip()}")


def extract_strip(path, out, interval, cols):
    """Tile frames sampled every `interval` seconds into one image."""
    if not os.path.isfile(path):
        die(f"文件不存在: {path}")
    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)
    frames = max(1, int(_duration_s(path) / interval + 0.5))
    cols = max(1, min(cols, frames))
    rows = (frames + cols - 1) // cols
    vf = f"fps=1/{interval},scale=480:-1,tile={cols}x{rows}"
    p = run(["ffmpeg", "-y", "-i", path, "-vf", vf, "-frames:v", "1", out])
    if p.returncode != 0 or not os.path.exists(out):
        die(f"帧条生成失败: {p.stderr.strip()}")
    return out


def make_contact(out, images, cols):
    """Tile a group of existing images into one sheet (seam review)."""
    images = list(images)
    if not images:
        die("contact 需要至少一张图片")
    for p in images:
        if not os.path.isfile(p):
            die(f"文件不存在: {p}")
    out_dir = os.path.dirname(os.path.abspath(out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    n = len(images)
    cols = max(1, min(cols, n))
    rows = (n + cols - 1) // cols
    cell = 480, 270
    # Every cell normalized to one size so hstack/vstack can join them.
    norm = (f"scale={cell[0]}:{cell[1]}:force_original_aspect_ratio=decrease,"
            f"pad={cell[0]}:{cell[1]}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=rgba")
    chain = []
    for i in range(rows * cols):
        if i < n:
            chain.append(f"[{i}:v]{norm}[g{i}]")
        else:  # pad the last row with black cells (vstack needs a full grid)
            chain.append(f"color=c=black:s={cell[0]}x{cell[1]}:d=1[g{i}]")
    row_labels = []
    for j in range(rows):
        cells = [f"g{j * cols + k}" for k in range(cols)]
        if len(cells) == 1:
            row_labels.append(cells[0])
            continue
        label = f"r{j}"
        chain.append("".join(f"[{c}]" for c in cells) + f"hstack=inputs={cols}[{label}]")
        row_labels.append(label)
    if len(row_labels) == 1:
        final = row_labels[0]
    else:
        chain.append("".join(f"[{l}]" for l in row_labels)
                     + f"vstack=inputs={rows}[stacked]")
        final = "stacked"

    cmd = ["ffmpeg", "-y"]
    for p in images:
        cmd += ["-i", p]
    cmd += ["-filter_complex", ";".join(chain), "-map", f"[{final}]",
            "-frames:v", "1", out]
    p = run(cmd)
    if p.returncode != 0 or not os.path.exists(out):
        die(f"contact sheet 生成失败: {p.stderr.strip()}")
    return out


def probe(path, as_json):
    """Print codec/resolution/duration/audio facts (≈ mediakit probe-video-metadata)."""
    if not os.path.isfile(path):
        die(f"文件不存在: {path}")
    p = run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
             "-of", "json", path])
    if p.returncode != 0:
        die(f"探测失败: {p.stderr.strip()}")
    if as_json:
        print(p.stdout.strip())
        return path
    import json
    info = json.loads(p.stdout)
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), {})
    dur = float(info.get("format", {}).get("duration", 0))
    print(f"container: {info.get('format', {}).get('format_name', '?')}")
    print(f"duration_s: {dur:.3f}")
    if v:
        fps = v.get("avg_frame_rate", "0/1")
        num, _, den = fps.partition("/")
        fps_f = (float(num) / float(den)) if den and float(den) else 0.0
        print(f"video: {v.get('codec_name', '?')} {v.get('width')}x{v.get('height')} "
              f"@ {fps_f:.2f}fps")
    else:
        print("video: 无视频流")
    print(f"audio: {a.get('codec_name', '无音频流')}"
          + (f" {a.get('sample_rate')}Hz {a.get('channels')}ch" if a else ""))
    return path


def trim(path, out, start, end):
    """Cut [start, end) with stream copy when possible (≈ mediakit trim-video)."""
    if not os.path.isfile(path):
        die(f"文件不存在: {path}")
    if end is not None and start is not None and end <= start:
        die(f"--end ({end}) 必须大于 --start ({start})")
    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)
    cmd = ["ffmpeg", "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", path]
    if end is not None:
        dur = end - (start or 0)
        cmd += ["-t", str(dur)]
    # 重编码保证切点精确（流拷贝只能切在关键帧上，接缝会偏）
    cmd += ["-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k", out]
    p = run(cmd)
    if p.returncode != 0 or not os.path.exists(out):
        die(f"裁剪失败: {p.stderr.strip()}")
    return out


def concat(out, segments):
    """Join segments into one master file (≈ mediakit concat-video).

    All segments are re-encoded to a uniform stream first, so clips with
    different codecs/sizes/fps still join cleanly.
    """
    segments = list(segments)
    if len(segments) < 2:
        die("concat 需要至少 2 个片段")
    for s in segments:
        if not os.path.isfile(s):
            die(f"文件不存在: {s}")
    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)
    # 统一拉到第一个片段的分辨率（letterbox 适配），帧率 24（与 h3.json fps:24
    # 和 delivery_settings.output_fps 默认 24 对齐），音频 48k 立体声
    w, h = _wh(segments[0])
    w, h = w - w % 2, h - h % 2
    cmd = ["ffmpeg", "-y"]
    for s in segments:
        cmd += ["-i", s]
    n = len(segments)
    chain = []
    for i in range(n):
        chain.append(f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                     f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
                     f"fps=24,format=yuv420p[v{i}]")
        chain.append(f"[{i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0[a{i}]")
    chain.append("".join(f"[v{i}][a{i}]" for i in range(n))
                 + f"concat=n={n}:v=1:a=1[v][a]")
    cmd += ["-filter_complex", ";".join(chain),
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    p = run(cmd)
    if p.returncode != 0 or not os.path.exists(out):
        die(f"拼接失败: {p.stderr.strip()}")
    return out


def burn(path, srt, out, size, pos):
    """Hard-burn an SRT subtitle file into the video (≈ mediakit add-subtitle-to-video).

    字幕文本来自剧本台词稿人工/脚本整理成的 SRT，不做 ASR。
    默认对齐豆包交付合同：思源黑体 36px 白色；9:16 用 lower_third（70% 高度）。
    """
    if not os.path.isfile(path):
        die(f"文件不存在: {path}")
    if not os.path.isfile(srt):
        die(f"字幕文件不存在: {srt}")
    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)
    # subtitles filter 需要 libass；路径里的 \ : ' 要转义
    srt_esc = os.path.abspath(srt).replace("\\", "/").replace(":", "\\:")
    style = (f"FontName=Source Han Sans SC,FontSize={size},"
             "PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,"
             "BorderStyle=1,Outline=2,Shadow=0,Alignment=2")
    if pos == "lower_third":
        # Alignment=2（底部居中）+ MarginV 抬到约 70% 画面高度处
        style += ",MarginV=" + str(int(_height(path) * 0.25))
    vf = f"subtitles='{srt_esc}':force_style='{style}'"
    p = run(["ffmpeg", "-y", "-i", path, "-vf", vf,
             "-c:v", "libx264", "-crf", "18", "-preset", "fast",
             "-c:a", "copy", out])
    if p.returncode != 0 or not os.path.exists(out):
        die(f"字幕烧录失败（需 ffmpeg 带 libass）: {p.stderr.strip()}")
    return out


def _height(path):
    return _wh(path)[1]


def erase(path, out, regions):
    """Erase fixed-area subtitles/watermarks via delogo interpolation.

    仅适用于位置固定的文字/水印（字幕带、角标）：delogo 用矩形邻域插值覆盖。
    移动文字、大面积文字或擦除后仍可见污损时，应按返修重生处理（本工具不承诺
    修复此类残留）。输出写新文件（调用方建 _vNN 版本），不覆盖原片。
    """
    if not os.path.isfile(path):
        die(f"文件不存在: {path}")
    if not regions:
        die("erase 至少需要一个 --region x,y,w,h")
    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)
    vf_parts = []
    for i, (x, y, w, h) in enumerate(regions):
        vf_parts.append(f"delogo=x={x}:y={y}:w={w}:h={h}")
    vf = ",".join(vf_parts)
    p = run(["ffmpeg", "-y", "-i", path, "-vf", vf,
             "-c:v", "libx264", "-crf", "18", "-preset", "fast",
             "-c:a", "copy", out])
    if p.returncode != 0 or not os.path.exists(out):
        die(f"擦除失败: {p.stderr.strip()}")
    return out


def _parse_region(text):
    """'x,y,w,h' -> (int, int, int, int)；delogo 坐标基于输入分辨率左上原点。"""
    try:
        x, y, w, h = (int(part) for part in text.split(","))
    except ValueError:
        die(f"--region 格式应为 x,y,w,h（左上角坐标与宽高，像素）: {text}")
    if w <= 0 or h <= 0:
        die(f"--region 宽高必须为正: {text}")
    return x, y, w, h


def _wh(path):
    p = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", path])
    try:
        w, h = p.stdout.strip().split(",")[:2]
        return int(w), int(h)
    except (ValueError, AttributeError):
        return 1920, 1080


def main():
    ap = argparse.ArgumentParser(description="ffmpeg 抽帧工具")
    sub = ap.add_subparsers(dest="command", required=True)

    p_frame = sub.add_parser("frame", help="抽取一帧为图片")
    p_frame.add_argument("video")
    p_frame.add_argument("out", help="输出图片路径，如 09-takes/S001/S001_tail.png")
    where = p_frame.add_mutually_exclusive_group()
    where.add_argument("--at", help="指定时间点（秒）")
    where.add_argument("--tail", action="store_true", help="片尾最后一帧")
    where.add_argument("--first", action="store_true", help="首帧（默认）")

    p_strip = sub.add_parser("strip", help="等距抽帧拼成一张帧条图（审片用）")
    p_strip.add_argument("video")
    p_strip.add_argument("out", help="输出图片路径，如 09-takes/S001/strip.png")
    p_strip.add_argument("--interval", type=float, default=0.5,
                         help="抽帧间隔秒（默认 0.5；核物理用 0.2 或更密）")
    p_strip.add_argument("--cols", type=int, default=10, help="每行帧数（默认 10）")

    p_contact = sub.add_parser(
        "contact", help="把一组已有图片拼成一张核连接缝的 contact sheet")
    p_contact.add_argument("out", help="输出图片路径，如 09-takes/seam.png")
    p_contact.add_argument("images", nargs="+", help="按片段顺序排列的边界帧图片")
    p_contact.add_argument("--cols", type=int, default=4, help="每行格数（默认 4）")

    p_probe = sub.add_parser("probe", help="探测编码/分辨率/时长/音频（≈ mediakit probe）")
    p_probe.add_argument("video")
    p_probe.add_argument("--json", action="store_true", help="输出 ffprobe 原始 JSON")

    p_trim = sub.add_parser("trim", help="有效区间裁剪（≈ mediakit trim-video）")
    p_trim.add_argument("video")
    p_trim.add_argument("out", help="输出 mp4 路径")
    p_trim.add_argument("--start", type=float, help="起点秒（缺省从头）")
    p_trim.add_argument("--end", type=float, help="终点秒（缺省到尾）")

    p_concat = sub.add_parser("concat", help="按顺序拼接成片（≈ mediakit concat-video；片段须带音频流）")
    p_concat.add_argument("out", help="输出成片 mp4 路径")
    p_concat.add_argument("segments", nargs="+", help="按剧情顺序排列的分段 mp4")

    p_burn = sub.add_parser("burn", help="把 SRT 字幕烧进视频（≈ mediakit add-subtitle-to-video，需 libass）")
    p_burn.add_argument("video")
    p_burn.add_argument("srt", help="SRT 字幕文件（来自剧本台词稿，非 ASR）")
    p_burn.add_argument("out", help="输出 mp4 路径")
    p_burn.add_argument("--size", type=int, default=36, help="字号（默认 36，对齐豆包合同）")
    p_burn.add_argument("--pos", choices=["bottom", "lower_third"], default="bottom",
                        help="bottom=底部居中(16:9)；lower_third=70%% 高度(9:16)")

    p_erase = sub.add_parser("erase", help="擦除固定区域文字/水印（delogo 插值；输出新版本不覆盖原片）")
    p_erase.add_argument("video")
    p_erase.add_argument("out", help="输出 mp4 路径（建议带 _vNN 版本号）")
    p_erase.add_argument("--region", action="append", required=True, metavar="x,y,w,h",
                         help="擦除区域，可重复多次；坐标基于输入分辨率左上原点")

    args = ap.parse_args()
    if args.command == "probe":
        print(probe(args.video, args.json))
        return
    if args.command == "trim":
        print(trim(args.video, args.out, args.start, args.end))
        return
    if args.command == "concat":
        print(concat(args.out, args.segments))
        return
    if args.command == "burn":
        print(burn(args.video, args.srt, args.out, args.size, args.pos))
        return
    if args.command == "erase":
        regions = [_parse_region(text) for text in args.region]
        print(erase(args.video, args.out, regions))
        return
    if args.command == "strip":
        print(extract_strip(args.video, args.out, args.interval, args.cols))
        return
    if args.command == "contact":
        print(make_contact(args.out, args.images, args.cols))
        return
    mode = "tail" if args.tail else ("at" if args.at is not None else "first")
    print(extract_frame(args.video, args.out, mode, args.at))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
