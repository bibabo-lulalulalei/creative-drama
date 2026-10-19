# -*- coding: utf-8 -*-
"""img.py — 统一生图入口（唯一后端：zhinao 知脑中转 gpt-image）。

位置：tools/image/img.py。文档与流水线只引用本入口（短名 `img`）。
（短名不用 `gen`：项目里 `gen.json` 是 h3 视频的既有契约名，会撞车。）

后端：tools/image/zhinao_image.py，配置 tools/image/zhinao_image.json。

── 比例（ratio）────────────────────────────────────────────────
`--ratio 16:9` 映射到最接近的标准档（1024x1024 / 1536x1024 / 1024x1536），
标准档实测兑现，自定义尺寸不兑现（依据见 zhinao_image.py 文件头）。

相对路径（--ref/--out）以当前工作目录解析。仅标准库。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zhinao_image as _zhinao       # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_CONFIG = os.path.join(_HERE, "zhinao_image.json")

_STANDARD_SIZES = ((1, 1, "1024x1024"), (3, 2, "1536x1024"), (2, 3, "1024x1536"))


def _size_for_ratio(text):
    """'16:9' -> 最接近的标准档；非法输入即报错（不静默兜底）。"""
    raw = (text or "").strip().replace("：", ":")
    parts = raw.split(":")
    if len(parts) != 2:
        raise ValueError(f"--ratio 应为 '宽:高' 形式，收到 {text!r}")
    try:
        w, h = float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"--ratio 数值非法：{text!r}") from None
    if w <= 0 or h <= 0:
        raise ValueError(f"--ratio 数值须为正：{text!r}")
    return min(_STANDARD_SIZES, key=lambda s: abs(w / h - s[0] / s[1]))[2]


def main():
    ap = argparse.ArgumentParser(description="统一生图入口（zhinao 知脑中转 gpt-image）")
    ap.add_argument("--config", help=f"后端配置路径（缺省 {_CONFIG}）")
    prompt = ap.add_mutually_exclusive_group(required=True)
    prompt.add_argument("--prompt-file", help="生产提示词文件（取正文）")
    prompt.add_argument("--prompt", help="生产提示词文本")
    ap.add_argument("--ref", action="append", default=[], help="参考图路径，可重复")
    ap.add_argument("--ratio", help="画幅比例，如 16:9（映射到最接近的标准档）")
    ap.add_argument("--out", required=True, help="成品落点")
    args = ap.parse_args()

    config_path = args.config or _CONFIG

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            asset_image = json.load(f)
        if args.prompt_file:
            with open(args.prompt_file, "r", encoding="utf-8") as f:
                prompt_text = f.read()
        else:
            prompt_text = args.prompt

        if args.ratio:
            asset_image = dict(asset_image)
            asset_image["size"] = _size_for_ratio(args.ratio)

        # generate() 返回图片 bytes，落盘是调用方的责任。
        data = _zhinao.generate(prompt_text=prompt_text,
                                reference_paths=[os.path.abspath(p) for p in args.ref],
                                asset_image=asset_image)
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "wb") as f:
            f.write(data)
        print(f"img: backend=zhinao size={asset_image.get('size')} out={args.out}")
    except (OSError, ValueError, RuntimeError) as e:
        print(f"img: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
