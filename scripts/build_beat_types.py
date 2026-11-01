"""由叙事词汇源表生成 ID/名称；不提供时间参数或生产 fallback。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

DEFAULT_OUTPUT = Path(__file__).with_name('beat_types.json')


def build(library_md):
    text = Path(library_md).read_text(encoding='utf-8-sig')
    versions = re.findall(r'(?m)^library_version:\s*(\d+)\s*$', text)
    if len(versions) != 1 or int(versions[0]) < 3:
        raise ValueError('词汇源需唯一 library_version >= 3；旧时间库不用于新生产')
    headers = list(re.finditer(r'(?m)^## §4 机读映射表\s*$', text))
    if len(headers) != 1:
        raise ValueError('缺少唯一词汇机读映射表')
    section = re.split(r'(?m)^## ', text[headers[0].end():], maxsplit=1)[0]
    rows = [[cell.strip() for cell in line.strip().strip('|').split('|')]
            for line in section.splitlines() if line.strip().startswith('|')]
    if len(rows) < 3 or rows[0] != ['id', 'name']:
        raise ValueError('词汇表仅允许 id/name 两列')
    beats = {}
    for row in rows[2:]:
        if len(row) != 2 or not re.fullmatch(r'[a-z][a-z_0-9]*', row[0]) or not row[1] or row[0] in beats:
            raise ValueError('无效或重复词汇 ID/名称')
        if len(re.findall(r'(?m)^### ' + re.escape(row[0]) + r'\s+', text)) != 1:
            raise ValueError('词汇 ID 需对应唯一源定义')
        beats[row[0]] = {'name': row[1]}
    if not beats:
        raise ValueError('词汇表不能为空')
    return {'_generated_by': 'build_beat_types.py — 由叙事词汇源表生成，禁止手改',
            'version': int(versions[0]), 'beat_types': beats}


def main():
    parser = argparse.ArgumentParser(description='生成可选叙事词汇，不含时间处方')
    parser.add_argument('--library-md', required=True)
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        data = build(args.library_md)
        target = Path(args.output)
        if args.check:
            if json.loads(target.read_text(encoding='utf-8-sig')) != data:
                raise ValueError('词汇生成物与源定义不一致')
        else:
            target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'ok': True, 'version': data['version'], 'beats': len(data['beat_types'])}, ensure_ascii=False))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
