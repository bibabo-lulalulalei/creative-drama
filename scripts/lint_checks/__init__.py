"""Focused checks behind the drama_lint command; use the generated source index to navigate."""
from pathlib import Path
import sys

_VIDEO_TOOLS = str(Path(__file__).resolve().parents[2] / "tools/video")
if _VIDEO_TOOLS not in sys.path:
    sys.path.insert(0, _VIDEO_TOOLS)
