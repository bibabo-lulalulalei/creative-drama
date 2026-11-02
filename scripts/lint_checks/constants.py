"""Shared stage names, exact enums and package-relative resource paths."""
from __future__ import annotations

import re
from pathlib import Path


STAGES = ("planning", "script", "assets", "storyboard", "keyframes", "video", "final")

EPISODE_STAGES = set(STAGES[1:])

STATUS_VALUES = {"pending", "in_progress", "awaiting_confirmation", "confirmed", "invalidated", "blocked"}

ASSET_STATUS_VALUES = {"draft", "reviewed", "approved", "rejected", "superseded"}

VISUAL_REFERENCE_DECISIONS = {"used", "none_available", "explicit_user_override"}

PROJECT_VISUAL_MODES = {"live_action", "photoreal", "2d_comic", "anime", "ink_animation", "illustration", "stylized_3d", "mixed_with_explicit_scope"}

VIDEO_STATUS_VALUES = {"candidate", "accepted", "rejected", "blocked"}

VIDEO_TOOL_MODES = {"text_to_video", "media_to_video", "image_to_video", "video_edit"}

IMAGE_GENERATION_TOOLS = {"image_gen", "image_edit"}

FORBIDDEN_TOOL_TERMS = ("text_to_image",)

SKILL_SCRIPTS_DIR = Path(__file__).resolve().parents[1]

BEAT_LIBRARY_JSON_PATH = SKILL_SCRIPTS_DIR / "beat_types.json"

BEAT_LIBRARY_MD_PATH = SKILL_SCRIPTS_DIR.parent / "references" / "节拍类型库.md"

H3_CAPABILITY_PATH = SKILL_SCRIPTS_DIR.parent / "tools" / "video" / "h3.json"

CUT_MOTIVATIONS = {"match_on_action", "eyeline", "sound_bridge", "occlusion", "reaction", "spatial", "information", "motivated_hard_cut"}

REFERENCE_ROLES = {
    "previous_tail_as_start_frame",
    "previous_scene_anchor_reference",
    "previous_character_state_reference",
    "previous_prop_state_reference",
    "segment_highlight_reference",
    "identity_reference",
    "character_state_reference",
    "scene_layout",
    "prop_structure",
    "prop_state_reference",
    "style_reference",
}

VIDEO_INPUT_ROLES = {
    "previous_segment_video_reference",
    "style_video_reference",
    "character_video_reference",
    "scene_video_reference",
    "source_video_for_edit",
}

AUDIO_INPUT_ROLES = {
    "voice_audio_reference",
    "music_reference",
    "sound_effect_reference",
    "ambient_reference",
}

STATE_REFERENCE_ROLES = {"character_state_reference", "prop_state_reference"}

ASSET_PREFIX_BY_CATEGORY = {
    "character": "CHR",
    "scene": "SCN",
    "prop": "PROP",
    "voice": "VOICE",
    "style": "STYLE",
}

CURRENT_STAGE_ACTIVE_VALUES = {"in_progress", "awaiting_confirmation", "invalidated", "blocked"}

CONFIRMATION_MODES = {"full", "incremental"}

IMAGE_INPUT_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}

ISO_TIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})")

ASSET_ID_PATTERN = re.compile(r"^((?:CHR|SCN|PROP|STYLE)\d+)(?:[_:]v?(\d+))?")

ASSET_ROLE_COMPATIBILITY = {
    "CHR": {"identity_reference", "character_state_reference", "previous_character_state_reference"},
    "SCN": {"scene_layout", "previous_scene_anchor_reference"},
    "PROP": {"prop_structure", "prop_state_reference", "previous_prop_state_reference"},
    "STYLE": {"style_reference"},
}

WORLD_FACT_CATEGORIES = {"season", "festival", "date", "time_of_day", "weather", "location_fact", "other"}

BEAT_DISPOSITIONS = {"kept", "compressed", "moved", "dropped"}

CAUSAL_ROLES = {"establish", "evidence", "reaction", "result", "transition"}

CAUSAL_REF_TYPES = {"beat", "shot", "asset_state", "world_fact"}

EVIDENCE_VISIBILITIES = {"in_frame", "partial", "occluded", "audio_only"}

BREAKPOINT_RISKS = {"C1", "C2", "C3", "C4", "C5"}
