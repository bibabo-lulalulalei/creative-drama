#!/usr/bin/env python3
"""分镜内容人工复核盖章：storyboard.content_review 的唯一合法写手。

为什么存在：
  content_review 三元指纹（源剧本 / 分镜设计投影 / 时间输入）必须机器计算，
  模型手算哈希多次出错且改一帧设计即失效。本命令把「算指纹 + 写章 + 复检」收成一条命令。

用法：
  # 不带旗标：只打印五项人工复核清单，不写任何文件
  python scripts/stamp_review.py --project-root <项目根> --episode ep_1
  # 真人逐项复核完、无未解决问题后：
  python scripts/stamp_review.py --project-root <项目根> --episode ep_1 --i-did-the-review

退出码：0 已打印清单或盖章成功；2 结构门未过/文件缺失（脏设计不许盖章）；
        3 盖章后复检仍有 error（理论上不该发生，出现即按输出修复）。
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from content_first import full_review_inputs, read_json  # noqa: E402
from rhythm_engine import atomic_write  # noqa: E402

SKILL_ROOT = SCRIPT_DIR.parent

# 盖章前允许存在的 error：这两个码的含义就是「章不存在/过期」，正是本命令要修的东西。
PRE_STAMP_EXPECTED_CODES = {"content_review_stale", "content_review_open_issue"}

# 五项以 references/skill-details.md「阶段内容硬门 · storyboard」为唯一权威，此处只做命令侧镜像，
# 改动必须同步该文件，避免双源漂移。
CHECKLIST = """\
剧本-分镜对照审校五项（语义审校唯一权威清单，全量结构检查通过后再做）：

1. beat 覆盖：逐条核对 beat_coverage——剧本每条 beat 都有镜头承接，无丢失、无凭空新增剧情。
2. 世界事实：季节/天气/时辰/节日类感官细节逐条回指 inherited_world_facts，无出处的删除或回剧本补写。
3. 台词逐字：十五列分镜表每句台词与已确认剧本逐字一致，无改写、拆并或新增。
4. 结构顺读：按观众视角顺读一遍十五列分镜——剧情可理解、因果不断裂、每镜职责可说清；
   顺读时同时核对观看过程：空间/路线连续、串并行与演读估计可信、等待停留有观看对象、
   道具/身份/状态/声音进入当前设计。
5. 三锚对照：逐条对照 causal_ledger——反应必有源、证据必可达、指称必有锚；
   命中断点按 C1-C5 分类，修复后才可提交确认。

发现问题：先改分镜设计/时间输入，重跑节奏引擎与 drama_lint，再重新逐项复核。
全部通过后，运行（旗标语义：声明这五项确由真人完成）：
  python scripts/stamp_review.py --project-root {root} --episode {episode} --i-did-the-review
"""


def episode_paths(root: Path, episode: str) -> tuple[Path, Path]:
    episode_root = root / f"episodes/{episode}/02_分镜"
    return (
        episode_root / f"rhythm_input_{episode}.json",
        episode_root / f"storyboard_{episode}.json",
    )


def run_storyboard_lint(project_root: Path) -> dict:
    """跑 storyboard 阶段 lint，返回解析后的 payload（复用入口，保证与模型所见同一裁决）。"""
    import drama_lint

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            drama_lint.main([str(SKILL_ROOT), "--project-root", str(project_root), "--stage", "storyboard"])
        except SystemExit:
            pass
    return json.loads(buf.getvalue())


def evaluate(project_root: Path, episode: str) -> dict:
    """结构门预检：除「缺章/章过期」外任何 error 都阻断盖章。"""
    timing_path, storyboard_path = episode_paths(project_root, episode)
    missing = [str(p) for p in (timing_path, storyboard_path) if not p.is_file()]
    if missing:
        return {"fatal": f"缺少必需文件：{missing}；先完成节奏输入与分镜落盘。"}
    storyboard = read_json(storyboard_path)
    inp = read_json(timing_path)
    payload = run_storyboard_lint(project_root)
    blocking = [
        item for item in payload.get("issues", [])
        if item.get("level") == "error" and item.get("code") not in PRE_STAMP_EXPECTED_CODES
    ]
    review = storyboard.get("content_review")
    open_issues = review.get("open_issues") if isinstance(review, dict) else None
    if isinstance(open_issues, list) and open_issues:
        blocking.append({
            "level": "error",
            "code": "content_review_open_issue",
            "message": f"content_review.open_issues 有 {len(open_issues)} 条未解决问题，必须先修并清空，不能带问题盖章。",
            "path": str(storyboard_path),
        })
    return {
        "root": project_root,
        "timing_path": timing_path,
        "storyboard_path": storyboard_path,
        "storyboard": storyboard,
        "inp": inp,
        "lint": payload,
        "blocking": blocking,
    }


def stamp(report: dict) -> None:
    storyboard = report["storyboard"]
    reviewed_inputs = full_review_inputs(
        report["root"], storyboard, report["inp"], report["timing_path"]
    )
    storyboard["content_review"] = {"reviewed_inputs": reviewed_inputs, "open_issues": []}
    atomic_write(
        report["storyboard_path"],
        json.dumps(storyboard, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )


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
    parser = argparse.ArgumentParser(description="分镜内容人工复核盖章（content_review 唯一合法写手）。")
    parser.add_argument("--project-root", required=True, help="项目根目录")
    parser.add_argument("--episode", default="ep_1", help="分集 ID，默认 ep_1")
    parser.add_argument(
        "--i-did-the-review",
        action="store_true",
        help="真人已完成五项复核并解决全部问题后才允许使用；无此旗标只打印清单不写文件。",
    )
    args = parser.parse_args(argv or sys.argv[1:])
    project_root = Path(args.project_root).resolve()

    report = evaluate(project_root, args.episode)
    if report.get("fatal"):
        print(report["fatal"])
        return 2
    if report["blocking"]:
        print(f"结构门未过：{len(report['blocking'])} 个阻断项，脏设计不许盖章。先修以下问题：")
        print_issues(report["blocking"])
        print("\n修完重跑 drama_lint --stage storyboard，再执行本命令。")
        return 2

    if not args.i_did_the_review:
        print(CHECKLIST.format(root=project_root, episode=args.episode))
        stale = [i for i in report["lint"].get("issues", []) if i.get("code") in PRE_STAMP_EXPECTED_CODES]
        if stale:
            print("当前状态：结构门已过，content_review 尚未盖章（或已过期），复核完成后用上述旗标命令盖章。")
        else:
            print("当前状态：章仍对应当前设计/源/时间输入；只有改了设计才需要重新复核盖章。")
        return 0

    stamp(report)
    post = run_storyboard_lint(project_root)
    if not post.get("release_ready"):
        print("盖章后复检仍有 error（不应发生），章已写入但请先修复再推进：")
        print_issues([i for i in post.get("issues", []) if i.get("level") == "error"])
        return 3
    print(f"已盖章：{report['storyboard_path']}")
    print("content_review.reviewed_inputs 已绑定当前源剧本 / 分镜设计投影 / 时间输入三元指纹，open_issues 为空。")
    print("storyboard 阶段复检 release_ready=true。之后任何设计/时间输入改动都会使章过期，需重新复核盖章。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
