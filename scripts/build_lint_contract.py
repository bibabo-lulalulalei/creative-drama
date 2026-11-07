"""On-demand lint navigation and module catalog (stdout only)."""
from __future__ import annotations

import argparse
import ast
import json
from itertools import product
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from drama_lint import FIXES  # noqa: E402

SOURCES = ['scripts/drama_lint.py', 'scripts/build_lint_contract.py',
           'scripts/timeline_core.py', 'scripts/content_first.py',
           'scripts/video_confirmations.py', 'scripts/preflight_video.py', 'scripts/rhythm_engine.py',
           'tools/video/h3_contract.py', 'tools/video/adopted_cut.py']

# 未覆盖码的诚实回退：不造假修法；先就地处理，源码只允许报错触发的定向窄读。
FIX_TODO = {'available': False,
            'note': '修法待补：先按 issue 自带 message/hint 就地处理，字段与枚举查阶段 Reference 与 manifests 分册，不要猜字段；仍无法定位时只按本结果 file/issue_line 定向读触发行，禁止无报错整文件预读。'}

# 治理类检查函数（原 lint_checks 的 state/stages/skill 三模块，已并入 drama_lint）：
# 其报错规则不在阶段方法内，--code 结果附 governance_reload 补载命令。
# 判定来自 scan() 的静态符号目录（每条结果的 symbol 字段），不硬编码检查码。
GOVERNANCE_FUNCTIONS = {
    'drama_lint.load_confirmation_records', 'drama_lint.check_operation_log_tools',
    'drama_lint.has_confirmation', 'drama_lint.check_state',
    'drama_lint.check_episode_directories', 'drama_lint.check_episode_manifest_ids',
    'drama_lint.check_episode_entry_manifests', 'drama_lint.check_stage_artifacts',
    'drama_lint._reference_targets', 'drama_lint.anchor_heading_count',
    'drama_lint._creative_index_targets', 'drama_lint.check_skill_package',
}
GOVERNANCE_RELOAD_COMMAND = ('python scripts/read_reference.py '
                             '--stage planning --condition governance_reload --render')


def module_name(relative):
    path = Path(relative)
    if path.parts[0] == 'scripts':
        parts = list(path.with_suffix('').parts[1:])
        if parts[-1] == '__init__':
            parts.pop()
        return '.'.join(parts)
    return path.stem


def imported_module(module, relative, node):
    if not node.level:
        return node.module or ''
    package = module.split('.') if Path(relative).stem == '__init__' else module.split('.')[:-1]
    package = package[:len(package) - node.level + 1]
    return '.'.join([*package, *node.module.split('.')]) if node.module else '.'.join(package)


def string_values(expression, bindings):
    """Evaluate only finite string literals and templates, never Python source."""
    if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
        return {expression.value}
    if isinstance(expression, ast.Name):
        return bindings.get(expression.id, set())
    if isinstance(expression, ast.IfExp):
        return string_values(expression.body, bindings) | string_values(expression.orelse, bindings)
    if isinstance(expression, ast.JoinedStr):
        parts = []
        for part in expression.values:
            if isinstance(part, ast.FormattedValue):
                if part.conversion != -1 or part.format_spec is not None:
                    return set()
                values = string_values(part.value, bindings)
            else:
                values = string_values(part, bindings)
            if not values:
                return set()
            parts.append(sorted(values))
        return {''.join(values) for values in product(*parts)}
    if (isinstance(expression, ast.Call) and isinstance(expression.func, ast.Name)
            and expression.func.id == 'getattr' and len(expression.args) == 3):
        # Exceptions retain their original code; also index the literal fallback.
        return string_values(expression.args[2], bindings)
    return set()


def local_bindings(function, parameter_values=None):
    """Find finite local strings and dictionary keys used by diagnostic templates."""
    bindings = {name: set(values) for name, values in (parameter_values or {}).items()}
    dictionaries = {}
    changed = True
    while changed:
        changed = False
        for node in ast.walk(function):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if isinstance(node.value, ast.Dict):
                        keys = set().union(*(string_values(key, bindings) for key in node.value.keys))
                        previous = dictionaries.setdefault(target.id, set())
                    else:
                        keys = string_values(node.value, bindings)
                        previous = bindings.setdefault(target.id, set())
                    if keys - previous:
                        previous.update(keys)
                        changed = True
            elif isinstance(node, ast.For):
                iterator, target = node.iter, node.target
                if (isinstance(iterator, ast.Call) and isinstance(iterator.func, ast.Attribute)
                        and iterator.func.attr in {'items', 'keys'}
                        and isinstance(iterator.func.value, ast.Name)):
                    keys = dictionaries.get(iterator.func.value.id, set())
                    if iterator.func.attr == 'items' and isinstance(target, (ast.Tuple, ast.List)):
                        target = target.elts[0]
                    if isinstance(target, ast.Name):
                        previous = bindings.setdefault(target.id, set())
                        if keys - previous:
                            previous.update(keys)
                            changed = True
    return bindings


def message_text(expression, bindings):
    """Keep the complete message; unresolved runtime values remain named placeholders."""
    if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
        return expression.value
    if isinstance(expression, ast.JoinedStr):
        pieces = []
        for part in expression.values:
            if isinstance(part, ast.Constant):
                pieces.append(str(part.value))
            else:
                values = string_values(part.value, bindings)
                pieces.append(next(iter(values)) if len(values) == 1 else '{' + ast.unparse(part.value) + '}')
        return ''.join(pieces)
    return '运行时说明表达式：' + ast.unparse(expression) + '；运行结果给出实际对象与详情，按定位核对完整函数及依赖。'


def rule_entries(function, bindings=None):
    """Yield exact literal/finite dynamic codes and complete diagnostic descriptions."""
    bindings = local_bindings(function, bindings)
    for call in ast.walk(function):
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id not in {'issue', 'fail', 'ContractError'}:
            continue
        strings = [arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None for arg in call.args]
        has_level = bool(strings and strings[0] in {'error', 'warning', 'info'})
        level = strings[0] if has_level else 'error'
        start = 1 if has_level else 0
        if len(call.args) <= start:
            continue
        expression = call.args[start]
        codes = string_values(expression, bindings)
        if not codes and isinstance(expression, ast.JoinedStr):
            raise ValueError(f'Unresolved diagnostic template in {function.name}:{call.lineno}: {ast.unparse(expression)}')
        variants = [(code, bindings) for code in sorted(codes)]
        if isinstance(expression, ast.JoinedStr):
            names = sorted({part.id for part in ast.walk(expression) if isinstance(part, ast.Name)})
            variants = []
            for values in product(*(sorted(bindings.get(name, set())) for name in names)):
                selected = {**bindings, **{name: {value} for name, value in zip(names, values)}}
                variants.extend((code, selected) for code in sorted(string_values(expression, selected)))
        for code, selected in variants:
            if code and all(character.islower() or character.isdigit() or character == '_' for character in code):
                message = message_text(call.args[start + 1], selected) if len(call.args) > start + 1 else '运行结果给出实际对象与错误详情；按对应阶段 Reference 核对产物。'
                yield code, level, message, call.lineno


def scan(root=ROOT):
    """Inspect sources internally; callers receive locations, never source text."""
    root = Path(root)
    functions, imports, modules = {}, {}, {}
    # 修法卡 FIXES 是 --code 的 fix 字段数据（定义在 drama_lint 内），不产 issue、不进规则图。
    sources = [*SOURCES]
    dispatch = None
    for relative in sources:
        source = (root / relative).read_text(encoding='utf-8-sig')
        module = module_name(relative)
        tree = ast.parse(source)
        imports[module] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                owner = imported_module(module, relative, node)
                imports[module].update({alias.asname or alias.name: f'{owner}.{alias.name}' for alias in node.names})
            elif isinstance(node, ast.Import):
                imports[module].update({alias.asname or alias.name.split('.')[0]: alias.name if alias.asname else alias.name.split('.')[0] for alias in node.names})
        symbols = {}
        for node in tree.body:
            if module == 'drama_lint' and isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'STAGE_CHECKS' for target in node.targets):
                dispatch = ast.literal_eval(node.value)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qualified = f'{module}.{node.name}'
                symbols[node.name] = {'file': relative, 'symbol': qualified,
                                      'line': node.lineno, 'end_line': node.end_lineno}
                if not isinstance(node, ast.ClassDef):
                    functions[qualified] = node
        modules[module] = {'path': relative, 'summary': (ast.get_docstring(tree) or '').split('\n')[0],
                           'line_count': len(source.splitlines()), 'symbols': symbols}
    if not isinstance(dispatch, dict):
        raise ValueError('Missing actual STAGE_CHECKS dispatch')

    def resolve(qualified):
        visited = set()
        while qualified not in functions:
            if qualified in visited:
                return None
            visited.add(qualified)
            module, _, name = qualified.rpartition('.')
            qualified = imports.get(module, {}).get(name)
            if not qualified:
                return None
        return qualified

    def called_function(module, expression):
        if isinstance(expression, ast.Name):
            return resolve(f'{module}.{expression.id}')
        if isinstance(expression, ast.Attribute) and isinstance(expression.value, ast.Name):
            owner = imports.get(module, {}).get(expression.value.id)
            if owner:
                return resolve(f'{owner}.{expression.attr}')
        return None

    def descendants(names):
        visited, pending = set(), []
        for name in names:
            qualified = resolve(name)
            if qualified is None:
                raise ValueError(f'Unknown stage function: {name}')
            pending.append(qualified)
        while pending:
            qualified = pending.pop()
            if qualified in visited:
                continue
            visited.add(qualified)
            module = qualified.rpartition('.')[0]
            for node in ast.walk(functions[qualified]):
                if isinstance(node, ast.Call):
                    child = called_function(module, node.func)
                    if child and child not in visited:
                        pending.append(child)
        return visited

    entrypoints = {stage: [resolve(f'drama_lint.{name}') for name in names] for stage, names in dispatch.items()}
    reachable = {stage: descendants([f'drama_lint.{name}' for name in names]) for stage, names in dispatch.items()}
    # Only parameter names used inside code templates need call-site enumeration.
    # Generic pass-through helpers (fail(code, message), exception propagation)
    # keep their concrete diagnostic at the original caller, not a wildcard code.
    parameter_values = {qualified: {} for qualified in functions}
    template_parameters = {}
    for qualified, function in functions.items():
        parameters = {arg.arg for arg in [*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs]}
        names = set()
        for node in ast.walk(function):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in {'issue', 'fail', 'ContractError'}):
                for argument in node.args:
                    # Skip the optional level, then inspect the code argument only.
                    if isinstance(argument, ast.Constant) and argument.value in {'error', 'warning', 'info'}:
                        continue
                    if isinstance(argument, ast.JoinedStr):
                        names.update(part.id for part in ast.walk(argument) if isinstance(part, ast.Name))
                    break
        template_parameters[qualified] = parameters & names
    changed = True
    while changed:
        changed = False
        for qualified, function in functions.items():
            bindings = local_bindings(function, parameter_values[qualified])
            module = qualified.rpartition('.')[0]
            for node in ast.walk(function):
                if not isinstance(node, ast.Call):
                    continue
                child = called_function(module, node.func)
                if not child or not template_parameters[child]:
                    continue
                target = functions[child]
                positional = [*target.args.posonlyargs, *target.args.args]
                arguments = {parameter.arg: value for parameter, value in zip(positional, node.args)}
                arguments.update({keyword.arg: keyword.value for keyword in node.keywords if keyword.arg})
                for name in template_parameters[child]:
                    if name not in arguments:
                        continue
                    values = string_values(arguments[name], bindings)
                    previous = parameter_values[child].setdefault(name, set())
                    if values - previous:
                        previous.update(values)
                        changed = True
    rules = {qualified: list(rule_entries(function, parameter_values[qualified]))
             for qualified, function in functions.items()}
    return {'modules': modules, 'functions': functions,
            'dispatch': dispatch, 'entrypoints': entrypoints, 'reachable': reachable, 'rules': rules}


def location(index, qualified):
    module, _, symbol = qualified.rpartition('.')
    return dict(index['modules'][module]['symbols'][symbol])


def render_modules(index):
    """Catalog every lint module (the former source-index.md table) as compact live JSON."""
    rows = [{'module': name, 'path': spec['path'], 'summary': spec['summary']}
            for name, spec in sorted(index['modules'].items())]
    return json.dumps({'modules': rows}, ensure_ascii=False, indent=2) + '\n'


def render_lookup(payload):
    """Keep one compact location per line while retaining valid JSON."""
    metadata = {key: value for key, value in payload.items() if key != 'results'}
    lines = ['{']
    for key, value in metadata.items():
        lines.append('  ' + json.dumps(key) + ': ' + json.dumps(value, ensure_ascii=False) + ',')
    lines.append('  "results": [')
    for number, result in enumerate(payload['results']):
        suffix = ',' if number < len(payload['results']) - 1 else ''
        lines.append('    ' + json.dumps(result, ensure_ascii=False, separators=(',', ':')) + suffix)
    lines += ['  ]', '}']
    return '\n'.join(lines) + '\n'


def lookup(root, kind, value, offset=0, limit=None):
    """Scan internally and return matching locations; pagination is optional."""
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ValueError('offset must be a nonnegative integer')
    if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 1):
        raise ValueError('limit must be a positive integer when supplied')
    if len(value.encode('utf-8')) > 512:
        raise ValueError('query must be at most 512 bytes')
    index = scan(root)
    results = []
    if kind == 'code':
        for qualified in sorted(index['functions']):
            for code, level, message, issue_line in index['rules'][qualified]:
                if code == value:
                    card = FIXES.get(code)
                    fix = ({'available': True, **card} if card else FIX_TODO)
                    item = {**location(index, qualified), 'issue_line': issue_line,
                            'code': code, 'level': level, 'message': message, 'fix': fix}
                    if item['symbol'] in GOVERNANCE_FUNCTIONS:
                        item['governance_reload'] = GOVERNANCE_RELOAD_COMMAND
                    results.append(item)
    elif kind == 'stage':
        results = [location(index, qualified) for qualified in index['entrypoints'].get(value, [])]
    else:
        raise ValueError(f'Unknown query kind: {kind}')
    total = len(results)
    page = results[offset:] if limit is None else results[offset:offset + limit]
    payload = {'ok': bool(total), kind: value, 'total': total, 'offset': offset,
               'next_offset': (offset + len(page) if offset + len(page) < total else None) if limit is not None else None,
               'results': page}
    if kind == 'stage' and value in index['dispatch'] and value not in {'skill', 'common'}:
        payload['shared_stage'] = 'common'
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--code', help='locate one exact issue code and its complete rule descriptions')
    action.add_argument('--stage', help='locate the actual entrypoints for one stage')
    action.add_argument('--modules', action='store_true', help='list every lint module with path and summary')
    parser.add_argument('--offset', type=int, default=0, help='skip this many matched locations')
    parser.add_argument('--limit', type=int, help='optional number of locations to return')
    args = parser.parse_args()
    try:
        if args.modules:
            sys.stdout.buffer.write(render_modules(scan(ROOT)).encode('utf-8'))
            return 0
        for kind in ('code', 'stage'):
            value = getattr(args, kind)
            if value is not None:
                payload = lookup(ROOT, kind, value, args.offset, args.limit)
                sys.stdout.write(render_lookup(payload))
                return 0 if payload['ok'] else 1
        if args.offset != 0 or args.limit is not None:
            raise ValueError('--offset and --limit require a query option')
        parser.error('导航现场生成不入库；请选择 --code/--stage/--modules')
    except (OSError, ValueError, SyntaxError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
