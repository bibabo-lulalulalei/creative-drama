"""由叙事词汇源表生成 ID/名称；不提供时间参数或生产 fallback。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

DEFAULT_OUTPUT = Path(__file__).with_name('beat_types.json')


SECTION_RE = re.compile(r'(?ms)^## §2 beat_type 总表\s*$(.*?)(?=^## §3 )')
HEADING_RE = re.compile(r'(?m)^### ([a-z][a-z_0-9]*)\s+(\S.*?)\s*$')


def build(library_md):
    text = Path(library_md).read_text(encoding='utf-8-sig')
    sections = SECTION_RE.findall(text)
    if len(sections) != 1:
        raise ValueError('缺少唯一 beat_type 总表（§2）')
    section = sections[0]
    for line in section.splitlines():
        if line.startswith('### ') and not HEADING_RE.match(line):
            raise ValueError('beat_type 标题必须为「### id 名称」: ' + line)
    beats = {}
    for match in HEADING_RE.finditer(section):
        beat_id, name = match.group(1), match.group(2)
        if beat_id in beats:
            raise ValueError('无效或重复词汇 ID/名称')
        beats[beat_id] = {'name': name}
    if not beats:
        raise ValueError('词汇表不能为空')
    return {'_generated_by': 'build_beat_types.py — 由叙事词汇源表生成，禁止手改', 'beat_types': beats}


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
        print(json.dumps({'ok': True, 'beats': len(data['beat_types'])}, ensure_ascii=False))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
