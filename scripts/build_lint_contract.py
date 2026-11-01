"""Generate stage contracts from actual lint dispatch and its shared call graph."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['scripts/drama_lint.py', 'scripts/timeline_core.py', 'scripts/content_first.py',
           'scripts/video_confirmations.py', 'scripts/preflight_video.py', 'scripts/rhythm_engine.py',
           'tools/video/h3_contract.py', 'tools/video/adopted_cut.py']


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def build(root=ROOT):
    functions, imports, source_hashes = {}, {}, {}
    dispatch = None
    for rel in SOURCES:
        source = (root / rel).read_text(encoding='utf-8-sig')
        module = Path(rel).stem
        source_hashes[rel] = sha(source)
        tree = ast.parse(source)
        imports[module] = {alias.asname or alias.name: f'{node.module}.{alias.name}'
                           for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                           for alias in node.names}
        for node in tree.body:
            if module == 'drama_lint' and isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'STAGE_CHECKS' for t in node.targets):
                dispatch = ast.literal_eval(node.value)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[f'{module}.{node.name}'] = node
    if not isinstance(dispatch, dict):
        raise ValueError('Missing actual STAGE_CHECKS dispatch')

    def descendants(names):
        visited, pending = set(), list(names)
        while pending:
            qualified = pending.pop()
            if qualified in visited:
                continue
            if qualified not in functions:
                raise ValueError(f'Unknown stage function: {qualified}')
            visited.add(qualified)
            module = qualified.split('.')[0]
            for node in ast.walk(functions[qualified]):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    name = node.func.id
                    child = f'{module}.{name}'
                    if child not in functions:
                        child = imports[module].get(name)
                    if child in functions and child not in visited:
                        pending.append(child)
        return visited

    cards = {}
    for stage, names in dispatch.items():
        reachable = descendants([f'drama_lint.{name}' for name in names])
        entries = set()
        for qualified in reachable:
            for call in ast.walk(functions[qualified]):
                if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id not in {'issue', 'fail', 'ContractError'}:
                    continue
                strings = [arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None for arg in call.args]
                level = strings[0] if strings and strings[0] in {'error','warning','info'} else 'error'
                start = 1 if strings and strings[0] in {'error','warning','info'} else 0
                code = strings[start] if len(strings) > start else None
                message = strings[start + 1] if len(strings) > start + 1 else None
                if not code or not all(c.islower() or c.isdigit() or c == '_' for c in code):
                    continue
                entries.add((code, level, message or '动态消息；按当前对象及源码核对', qualified))
        lines = [f'# lint 检查合同 · {stage} 阶段', '',
                 '> 由 build_lint_contract.py 从实际 STAGE_CHECKS 与共享调用图生成；禁止手改。',
                 '> 只证明结构、来源、算术、依赖与技术合同；内容须按观看顺序独立审校。', '',
                 '运行：`python scripts/drama_lint.py <skill-root> --project-root <project> --stage ' + stage + '`。' if stage not in {'common','skill'} else 'common 随生产阶段运行；skill 使用 `--stage skill`。', '',
                 '轻量走同一内核和单任务预检适配，不要求伪造完整模式上游。', '',
                 '| 检查码 | 级别 | 查什么 | 来源 |', '|---|---|---|---|']
        for code, level, message, source in sorted(entries):
            lines.append(f'| `{code}` | {level} | ' + message.replace('|','\\|').replace('\n',' ') + f' | `{source}` |')
        cards[f'{stage}.md'] = '\n'.join(lines) + '\n'
    manifest = {'source_sha256': source_hashes,
                'dispatch': dispatch, 'dispatch_sha256': sha(json.dumps(dispatch, sort_keys=True)),
                'generator_sha256': sha(Path(__file__).read_text(encoding='utf-8-sig')),
                'cards_sha256': {name: sha(text) for name, text in cards.items()}}
    cards['manifest.json'] = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    return cards


def check(root, cards):
    out = root / 'references/lint-contract'
    return [name for name, expected in cards.items() if not (out/name).is_file() or (out/name).read_text(encoding='utf-8') != expected]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        cards = build()
        if args.check:
            drift = check(ROOT, cards)
            print(json.dumps({'ok': not drift, 'drift': drift}, ensure_ascii=False))
            return int(bool(drift))
        out = ROOT / 'references/lint-contract'
        out.mkdir(parents=True, exist_ok=True)
        for name, text in cards.items():
            (out/name).write_text(text, encoding='utf-8', newline='\n')
        print(json.dumps({'ok': True, 'generated': sorted(cards)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, SyntaxError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
