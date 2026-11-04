"""Production coordinates into references/*.md must resolve to unique headings.

Covers three coordinate sources:
1. concrete ``--file references/x.md --section "## 标题"`` CLI coordinates written
   in scripts/ (including lint fix-card ``doc`` fields and checker hints),
   SKILL.md and references/*.md prose (quote or backtick delimiters);
2. every section value in references/reference_map.json (stage sections and all
   conditional groups, including the repair profile's affected_* blocks);
3. whole-file entries in each stage's ``full`` list must exist on disk.

Placeholder coordinates such as ``references/<x>.md`` / ``"### <stage>"`` are
templates and intentionally skipped.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts import read_reference

ROOT = read_reference.ROOT

_QUOTE = r"""["'`]"""
_FILE = r"references/[^\s\"'`)]+?\.md"
_HEAD = r"#{1,6}[^\n\"'`]{1,160}?"
# --file first, then --section on the same physical line
_RE_FORWARD = re.compile(
    r"--file\s+(?P<file>" + _FILE + r")[^\n]{0,400}?"
    r"--section\s+" + _QUOTE + r"(?P<head>" + _HEAD + r")" + _QUOTE
)
# --section first, then --file
_RE_BACKWARD = re.compile(
    r"--section\s+" + _QUOTE + r"(?P<head>" + _HEAD + r")" + _QUOTE
    + r"[^\n]{0,400}?--file\s+(?P<file>" + _FILE + r")"
)


def _is_placeholder(text: str) -> bool:
    return "<" in text or "{" in text or "<" in text


def _text_coordinates():
    """Yield (file, heading, source_label) from CLI-form coordinates on disk."""
    scan_files = list((ROOT / "scripts").rglob("*.py"))
    scan_files.append(ROOT / "SKILL.md")
    scan_files.extend(sorted((ROOT / "references").rglob("*.md")))
    seen: set[tuple[str, str]] = set()
    for path in scan_files:
        if not path.exists():
            continue
        label = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _RE_FORWARD.finditer(text):
            pair = (match.group("file"), match.group("head").strip())
            if not _is_placeholder(pair[0]) and not _is_placeholder(pair[1]):
                if pair not in seen:
                    seen.add(pair)
                    yield pair[0], pair[1], label
        for match in _RE_BACKWARD.finditer(text):
            pair = (match.group("file"), match.group("head").strip())
            if not _is_placeholder(pair[0]) and not _is_placeholder(pair[1]):
                if pair not in seen:
                    seen.add(pair)
                    yield pair[0], pair[1], label


def _map_coordinates():
    """Yield (file, heading, source_label) from every map section value."""
    stages = read_reference.load_map()["stages"]
    for stage_name, spec in stages.items():
        for file_path, headings in spec.get("sections", {}).items():
            for heading in headings:
                yield file_path, heading, f"map:{stage_name}:sections"
        for condition, group in spec.get("conditional", {}).items():
            for file_path, headings in group.items():
                for heading in headings:
                    yield file_path, heading, f"map:{stage_name}:{condition}"


class ReferenceCoordinateTests(unittest.TestCase):
    def test_text_coordinates_resolve_uniquely(self):
        failures = []
        count = 0
        for file_path, heading, source in _text_coordinates():
            count += 1
            with self.subTest(source=source, file=file_path, heading=heading):
                try:
                    result = read_reference.extract_section(file_path, heading)
                except read_reference.ReferenceError as exc:
                    failures.append(f"{source} -> {file_path} {heading}: {exc}")
                else:
                    self.assertEqual(result["section"], heading)
        self.assertGreater(count, 20, "坐标扫描正则应覆盖大量生产坐标")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_reference_map_section_values_resolve_uniquely(self):
        failures = []
        count = 0
        for file_path, heading, source in _map_coordinates():
            count += 1
            with self.subTest(source=source, file=file_path, heading=heading):
                try:
                    result = read_reference.extract_section(file_path, heading)
                except read_reference.ReferenceError as exc:
                    failures.append(f"{source} -> {file_path} {heading}: {exc}")
                else:
                    self.assertEqual(result["section"], heading)
        self.assertGreater(count, 100, "reference_map 应含上百个章节锚点")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_reference_map_full_entries_exist(self):
        stages = read_reference.load_map()["stages"]
        missing = []
        for stage_name, spec in stages.items():
            for file_path in spec.get("full", []):
                if not (ROOT / file_path).is_file():
                    missing.append(f"map:{stage_name}:full -> {file_path}")
        self.assertEqual(missing, [], "\n".join(missing))


if __name__ == "__main__":
    unittest.main()
