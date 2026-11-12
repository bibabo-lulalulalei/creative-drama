#!/usr/bin/env python3
"""分镜内容人工复核盖章：storyboard.content_review 的唯一合法写手。

为什么存在：
  content_review 三元指纹（源剧本 / 分镜设计投影 / 时间输入）必须机器计算，
  模型手算哈希多次出错且改一帧设计即失效。本命令把「算指纹 + 写章 + 复检」收成一条命令。

用法：
  # 按 storyboard-review.md 完成整场内容复核、解决问题后直接运行（内含结构检查）：
  python scripts/stamp_review.py --project-root <项目根> --episode ep_1 --i-did-the-review
  # 需要查看指引时可不带旗标；这不是盖章前置步骤，不写任何文件
  python scripts/stamp_review.py --project-root <项目根> --episode ep_1

退出码：0 已打印指引或盖章成功；2 结构门未过/文件缺失（脏设计不许盖章）；
        3 盖章后定点复检仍失败（理论上不该发生，出现即按输出修复）。
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

from rhythm_engine import check_review, full_review_inputs, read_json  # noqa: E402
from rhythm_engine import atomic_write  # noqa: E402

SKILL_ROOT = SCRIPT_DIR.parent

# 盖章前允许存在的 error：这两个码的含义就是「章不存在/过期」，正是本命令要修的东西。
PRE_STAMP_EXPECTED_CODES = {"content_review_stale", "content_review_open_issue"}

# 内容复核唯一权威在 references/storyboard-review.md「分镜内容人工复核」，
# 命令内不保留镜像文本，避免双源漂移。
CHECKLIST_POINTER = """\
结构检查已过。内容复核方法：references/storyboard-review.md「分镜内容人工复核」。
按观众视角整场顺读，检查观看关系、切点、摄影动机与连续性；实际完成并解决问题后使用旗标。
改动后复核受影响场及前后交界；时间设计改变时更新节奏输入并重算。
本命令内含结构检查，无需另跑同一轮 drama_lint 或再次无旗标预检：
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
        help="实际完成整场内容复核并解决问题后使用；命令内含结构检查。无此旗标只打印方法指针不写文件。",
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
        print("\n按具体问题修复后直接重跑本命令；改了内容时先复核受影响场及前后交界。")
        return 2

    if not args.i_did_the_review:
        print(CHECKLIST_POINTER.format(root=project_root, episode=args.episode))
        stale = [i for i in report["lint"].get("issues", []) if i.get("code") in PRE_STAMP_EXPECTED_CODES]
        if stale:
            print("当前状态：结构门已过，content_review 尚未盖章（或已过期），审校完成后用上述旗标命令盖章。")
        else:
            print("当前状态：章仍对应当前设计/源/时间输入；只有改了设计才需要重新审校盖章。")
        return 0

    stamp(report)
    # 盖章只写 content_review 一个字段；预检已放行除两个 content_review 码外的全部 error，
    # 故全量重跑在数学上不可能新增失败，这里只对实际写入字段做同函数定点复检。
    reviewed = full_review_inputs(
        report["root"], report["storyboard"], report["inp"], report["timing_path"]
    )
    residual = check_review(read_json(report["storyboard_path"]).get("content_review"), reviewed)
    if residual:
        print("盖章后定点复检失败（不应发生），章已写入但请先修复再推进：")
        print_issues(residual)
        return 3
    print(f"已盖章：{report['storyboard_path']}")
    print("content_review.reviewed_inputs 已绑定当前源剧本 / 分镜设计投影 / 时间输入三元指纹，open_issues 为空。")
    print("之后任何设计/时间输入改动都会使章过期，需重新审校盖章。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
