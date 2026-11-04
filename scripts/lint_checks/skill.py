"""Skill 包自洽门：校验 SKILL.md frontmatter、reference_map/creative-index 锚点与 Markdown 链接。

只在 drama_lint 的 ``--stage skill``（不传 --stage 时的默认阶段）运行，不挂七个生产阶段；
同阶段另有 rhythm.check_beat_library_desync 对账节拍库生成物，二者共同保证形态门、
确认前 lint 门等生产合同依赖的文本与锚点完整。留在生产检查而非 tests：drama_lint 随
skill 包分发到用户侧，无测试环境也能自查包损坏与引用漂移。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote
from .common import issue


def _reference_targets(spec: dict) -> dict[str, list[str]]:
    """汇总索引的全部文件与标题供完整性校验，不生成阅读内容。"""
    merged: dict[str, set[str]] = {rel: set() for rel in spec.get("full", [])}
    groups = [spec.get("sections") or {}, *(spec.get("conditional") or {}).values()]
    for group in groups:
        if isinstance(group, list):
            group = dict.fromkeys(group)
        if not isinstance(group, dict):
            continue
        for rel, anchors in group.items():
            merged.setdefault(rel, set()).update(anchors or [])
    return {rel: sorted(anchors) for rel, anchors in merged.items()}


def anchor_heading_count(text: str, anchor: str) -> int:
    """统计锚点标题在文件中的命中次数（跳过代码围栏），锚点必须恰好命中一次。"""
    count = 0
    fence_char: str | None = None
    fence_length = 0
    for line in text.splitlines():
        if fence_char is not None:
            closing = re.match(r"^\s{0,3}(`{3,}|~{3,})[ \t]*$", line)
            if closing and closing.group(1)[0] == fence_char and len(closing.group(1)) >= fence_length:
                fence_char = None
                fence_length = 0
            continue
        opening = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if opening:
            fence_char = opening.group(1)[0]
            fence_length = len(opening.group(1))
            continue
        if re.match(r"^#{1,6}\s", line) and line.strip() == anchor:
            count += 1
    return count


def _creative_index_targets(text: str) -> list[tuple[str | None, list[str]]]:
    """解析创作方法小索引：逐行记住最近声明的原文文件，返回表格中的 (文件, 标题) 对。

    文件列可写 ``同上`` 复用最近一行；表格外的单文件声明同样更新当前文件，
    使“下列标题均位于某文件”这类引导生效。
    """
    rows: list[tuple[str | None, list[str]]] = []
    current_file: str | None = None
    for line in text.splitlines():
        paths = re.findall(r"`((?:references/)[^`\s]+\.md)`", line)
        if len(paths) == 1:
            current_file = paths[0]
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", cell.replace(" ", "")) for cell in cells if cell):
            continue
        headings = re.findall(r"`(#{2,4}\s+[^`]+?)`", line)
        if headings:
            rows.append((current_file, headings))
    return rows


def check_skill_package(root: Path, issues: list[dict[str, Any]]) -> None:
    skill_path = root / "SKILL.md"
    try:
        text = skill_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        issues.append(issue("error", "skill_file_missing", "Skill 根目录缺少 SKILL.md。", skill_path))
        return
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "skill_file_unreadable", f"SKILL.md 无法读取：{exc}", skill_path))
        return

    frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if frontmatter is None:
        issues.append(issue("error", "skill_frontmatter_missing", "SKILL.md 缺少合法的 YAML frontmatter。", skill_path))
        return
    fields: dict[str, str] = {}
    for line in frontmatter.group(1).splitlines():
        match = re.fullmatch(r"([a-z_]+):\s*(.*)", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    name = fields.get("name", "")
    description = fields.get("description", "")
    if not 2 <= len(name) <= 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        issues.append(issue("error", "skill_name_invalid", "Skill name 必须是 2-64 位小写字母、数字或单连字符。", skill_path))
    if name != root.name:
        issues.append(issue("error", "skill_name_path_mismatch", "Skill name 必须与目录名一致。", skill_path))
    if not description or description[:1] in {'"', "'"} or description[-1:] in {'"', "'"}:
        issues.append(issue("error", "skill_description_invalid", "Skill description 必须是非空、未加引号的单行标量。", skill_path))
    if ": " in description or "<" in description or ">" in description or "TODO" in description:
        issues.append(issue("error", "skill_description_forbidden_text", "Skill description 含禁止的格式或占位内容。", skill_path))
    if not text[frontmatter.end():].strip():
        issues.append(issue("error", "skill_body_empty", "SKILL.md 正文不能为空。", skill_path))

    referenced_paths = set(re.findall(r"`((?:references|scripts)/[^`\s]+?\.(?:md|py))`", text))
    for relative in sorted(referenced_paths):
        target = root / relative
        if not target.is_file():
            issues.append(issue("error", "skill_reference_missing", f"SKILL.md 引用的本地文件不存在：{relative}", skill_path))

    reference_map_path = root / "references/reference_map.json"
    try:
        reference_map = json.loads(reference_map_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        issues.append(issue("error", "reference_map_missing", "缺少 references/reference_map.json 原文读取索引。", reference_map_path))
        reference_map = None
    except (OSError, ValueError) as exc:
        issues.append(issue("error", "reference_map_unreadable", f"reference_map.json 无法解析：{exc}", reference_map_path))
        reference_map = None
    if isinstance(reference_map, dict):
        for stage_name, spec in sorted((reference_map.get("stages") or {}).items()):
            if not isinstance(spec, dict):
                continue
            for rel, anchors in sorted(_reference_targets(spec).items()):
                file_path = (root / rel).resolve()
                if not file_path.is_relative_to(root.resolve()):
                    issues.append(issue("error", "reference_map_path_outside_skill", f"阶段 {stage_name} 的原文路径越出 Skill：{rel}", reference_map_path))
                    continue
                if not file_path.is_file():
                    issues.append(issue("error", "reference_map_file_missing", f"阶段 {stage_name} 的原文文件不存在：{rel}", reference_map_path))
                    continue
                try:
                    file_text = file_path.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    issues.append(issue("error", "reference_map_file_unreadable", f"reference_map 引用文件无法读取：{rel}：{exc}", reference_map_path))
                    continue
                for anchor in anchors or ():
                    if anchor_heading_count(file_text, anchor) != 1:
                        issues.append(issue("error", "reference_map_anchor_unresolved", f"阶段 {stage_name} 的锚点 {anchor!r} 在 {rel} 中命中次数不等于 1。", reference_map_path))

    creative_index_path = root / "references/creative-index.md"
    try:
        creative_index_text = creative_index_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        issues.append(issue("error", "creative_index_missing", "缺少 references/creative-index.md 创作方法小索引。", creative_index_path))
    except (OSError, UnicodeError) as exc:
        issues.append(issue("error", "creative_index_unreadable", f"creative-index.md 无法读取：{exc}", creative_index_path))
    else:
        creative_file_cache: dict[str, str | None] = {}
        for rel, headings in _creative_index_targets(creative_index_text):
            if not rel:
                issues.append(issue("error", "creative_index_file_undeclared", f"creative-index.md 标题 {headings[0]!r} 之前未声明所属原文文件。", creative_index_path))
                continue
            if rel not in creative_file_cache:
                target_path = root / rel
                try:
                    creative_file_cache[rel] = target_path.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    creative_file_cache[rel] = None
                    issues.append(issue("error", "creative_index_file_missing", f"creative-index.md 指向的原文文件不存在或不可读：{rel}", creative_index_path))
            file_text = creative_file_cache[rel]
            if file_text is None:
                continue
            for anchor in headings:
                if anchor_heading_count(file_text, anchor) != 1:
                    issues.append(issue("error", "creative_index_anchor_unresolved", f"creative-index.md 的锚点 {anchor!r} 在 {rel} 中命中次数不等于 1。", creative_index_path))

    markdown_paths = [
        path
        for path in sorted(root.glob("references/**/*.md"))
        if "references/cli" not in path.as_posix()
    ] + [skill_path]
    for markdown_path in markdown_paths:
        try:
            markdown_text = markdown_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(issue("error", "markdown_file_unreadable", f"Markdown 文件无法读取：{exc}", markdown_path))
            continue
        for match in re.finditer(r"(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)", markdown_text):
            raw_target = match.group(1).strip()
            if not raw_target or raw_target.startswith(("#", "http://", "https://", "mailto:", "app://", "codex://")):
                continue
            if " " in raw_target and not (raw_target.startswith("<") and raw_target.endswith(">")):
                raw_target = raw_target.split()[0]
            raw_target = raw_target.strip("<>")
            path_part = raw_target.split("#", 1)[0].split("?", 1)[0]
            if not path_part:
                continue
            target = markdown_path.parent / unquote(path_part)
            if not target.exists():
                issues.append(issue("error", "markdown_link_missing", f"Markdown 相对链接不存在：{raw_target}", markdown_path))
