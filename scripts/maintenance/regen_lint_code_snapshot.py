"""黄金检查码快照的唯一重生成入口；生产期不参与，测试 tests/test_lint_code_snapshot.py 钉死其产物。

数据来自 build_lint_contract.scan() 的 STAGE_CHECKS 可达图，与测试同源。
检查码增删是有意决策：先人工审计源码差异，再跑本脚本重写 fixture，禁止手编。
  校验：python scripts/maintenance/regen_lint_code_snapshot.py --check
  重写：python scripts/maintenance/regen_lint_code_snapshot.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

import build_lint_contract as contract

SNAPSHOT = ROOT / 'tests' / 'fixtures' / 'lint_code_snapshot.json'
NOTE = ('黄金快照：build_lint_contract.scan() 按 STAGE_CHECKS 可达图算出的各阶段检查码；'
        '测试钉死覆盖，变化时必须人工确认并重新生成')


def stage_code_lists() -> dict[str, list[str]]:
    """与 test_lint_code_snapshot.stage_code_sets 同图同源，输出排序列表以便确定性序列化。"""
    index = contract.scan(ROOT)
    stages: dict[str, list[str]] = {}
    for stage, reachable in index['reachable'].items():
        codes: set[str] = set()
        for qualified in reachable:
            for code, _level, _message, _issue_line in index['rules'][qualified]:
                codes.add(code)
        stages[stage] = sorted(codes)
    return stages


def build_payload() -> dict[str, object]:
    stages = stage_code_lists()
    union = set().union(*(set(codes) for codes in stages.values()))
    return {'_note': NOTE, 'union_count': len(union), 'stages': stages}


def render(payload: dict[str, object]) -> bytes:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    # 入库 fixture 固定 CRLF（仓内生成物现行风格），显式转换保证跨平台字节一致。
    return text.replace('\n', '\r\n').encode('utf-8')


def _diff(current: dict[str, object], rendered_payload: dict[str, object]) -> list[str]:
    lines = []
    current_stages = current.get('stages', {})
    for stage, codes in rendered_payload['stages'].items():
        expected = set(codes)
        existing = set(current_stages.get(stage, []))
        added = sorted(expected - existing)
        removed = sorted(existing - expected)
        if added:
            lines.append(f'{stage} 新增: {added}')
        if removed:
            lines.append(f'{stage} 丢失: {removed}')
    extra_stages = sorted(set(current_stages) - set(rendered_payload['stages']))
    if extra_stages:
        lines.append(f'多余 stage: {extra_stages}')
    if current.get('union_count') != rendered_payload['union_count']:
        lines.append(f"union_count {current.get('union_count')} -> {rendered_payload['union_count']}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description='重生成/校验 lint 检查码黄金快照')
    parser.add_argument('--check', action='store_true', help='只比对不写入，漂移即退出 1')
    parser.add_argument('--output', default=str(SNAPSHOT), help='重写目标（默认入库 fixture）')
    args = parser.parse_args()
    payload = build_payload()
    rendered = render(payload)
    target = Path(args.output)
    summary = {'ok': True, 'union_count': payload['union_count'], 'stages': len(payload['stages'])}
    if args.check:
        if not target.is_file():
            print(json.dumps({'ok': False, 'error': f'快照不存在: {target}'}, ensure_ascii=False))
            return 1
        if target.read_bytes() == rendered:
            print(json.dumps(summary, ensure_ascii=False))
            return 0
        current = json.loads(target.read_text(encoding='utf-8'))
        for line in _diff(current, payload):
            print(json.dumps({'ok': False, 'drift': line}, ensure_ascii=False))
        print(json.dumps({'ok': False, 'error': '快照与可达图漂移，人工审计后重跑本脚本（不带 --check）'},
                         ensure_ascii=False))
        return 1
    target.write_bytes(rendered)
    summary['written'] = str(target.relative_to(ROOT)) if target.is_relative_to(ROOT) else str(target)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
