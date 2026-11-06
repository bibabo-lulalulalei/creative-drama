#!/usr/bin/env python3
"""Track reference files already returned to the model across CLI calls."""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 2
PROJECT_LEDGER = "00_制作控制/上下文账本.json"
PROJECT_EVENTS = "00_制作控制/上下文事件.jsonl"


def project_paths(root: Path) -> tuple[Path, Path]:
    return root.resolve() / PROJECT_LEDGER, root.resolve() / PROJECT_EVENTS


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def empty_ledger() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "reference_map_sha256": None, "loaded": []}


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_ledger()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return empty_ledger()
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        return empty_ledger()
    loaded = value.get("loaded")
    if not isinstance(loaded, list):
        return empty_ledger()
    value["loaded"] = [item for item in loaded if isinstance(item, dict)]
    return value


def write_ledger(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def reset_ledger(path: Path) -> None:
    write_ledger(path, empty_ledger())


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def _entry_key(entry: dict[str, Any]) -> tuple[str, str | None]:
    return (str(entry.get("file", "")), entry.get("section"))


def _loaded_index(ledger: dict[str, Any]) -> dict[tuple[str, str | None], dict[str, Any]]:
    result: dict[tuple[str, str | None], dict[str, Any]] = {}
    for item in ledger.get("loaded", []):
        if isinstance(item, dict) and item.get("file"):
            result[_entry_key(item)] = item
    return result


def record_tool_result(path: Path | None, tool: str, output: str) -> None:
    if path is not None:
        append_event(path, {"kind": "tool_result", "tool": tool, "chars": len(output)})


@dataclass
class ReferenceRead:
    entries: list[dict[str, Any]]
    info: dict[str, Any]
    prior: dict[tuple[str, str | None], dict[str, Any]]
    records: dict[tuple[str, str | None], dict[str, Any]]
    events: list[dict[str, Any]]
    ledger_path: Path
    events_path: Path | None
    map_hash: str

    def summary(self, delivered: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        keys = {_entry_key(entry) for entry in (self.entries if delivered is None else delivered)}
        changed = [entry for entry in self.info["changed"] if _entry_key(entry) in keys]
        return {**self.info, "new_count": len(keys) - len(changed),
                "changed_count": len(changed), "changed": changed}

    def commit(self, delivered: list[dict[str, Any]] | None = None) -> None:
        """Commit only bodies successfully emitted, never a budget locator."""
        keys = {_entry_key(entry) for entry in (self.entries if delivered is None else delivered)}
        merged = {} if self.info["map_changed"] else dict(self.prior)
        merged.update({key: record for key, record in self.records.items() if key in keys})
        write_ledger(self.ledger_path, {
            "schema_version": SCHEMA_VERSION,
            "reference_map_sha256": self.map_hash,
            "loaded": sorted(merged.values(), key=lambda item: (item["file"], str(item.get("section")))),
        })
        if self.events_path is not None:
            for event in self.events:
                if event["status"] == "skipped" or _entry_key(event) in keys:
                    append_event(self.events_path, event)


def prepare_entries(
    entries: list[dict[str, Any]],
    *,
    root: Path,
    ledger_path: Path,
    reference_map: Path,
    force: bool = False,
    events_path: Path | None = None,
) -> ReferenceRead:
    """Select unread bodies without mutating the ledger or the event log.

    The ledger is only a transport optimization. It never asserts that a skipped
    file is valid for the project; callers still use project state and lint as
    authority.
    """
    ledger = load_ledger(ledger_path)
    map_hash = sha256_file(reference_map)
    map_changed = ledger.get("reference_map_sha256") not in (None, map_hash)
    prior = _loaded_index(ledger)
    now = datetime.now(timezone.utc).isoformat()
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    current_records: dict[tuple[str, str | None], dict[str, Any]] = {}
    events: list[dict[str, Any]] = []

    for entry in entries:
        file_name = str(entry["file"])
        source = (root / file_name).resolve()
        source_hash = sha256_file(source)
        key = _entry_key(entry)
        previous = prior.get(key)
        record = {
            "file": file_name,
            "section": entry.get("section"),
            "sha256": source_hash,
            "loaded_at": now,
        }
        current_records[key] = record
        is_same = (
            not force
            and not map_changed
            and previous is not None
            and previous.get("sha256") == source_hash
        )
        if is_same:
            skipped.append({"file": file_name, "section": entry.get("section"), "reason": "unchanged"})
            if events_path is not None:
                events.append({
                    "kind": "reference",
                    "status": "skipped",
                    "file": file_name,
                    "section": entry.get("section"),
                    "sha256": source_hash,
                    "chars": 0,
                })
        else:
            selected.append(entry)
            if previous is not None:
                changed.append({"file": file_name, "section": entry.get("section"), "reason": "source_changed" if previous.get("sha256") != source_hash else "route_changed"})
            if events_path is not None:
                events.append({
                    "kind": "reference",
                    "status": "returned",
                    "file": file_name,
                    "section": entry.get("section"),
                    "sha256": source_hash,
                    "chars": len(str(entry.get("content", ""))),
                    "full": entry.get("section") is None,
                })

    info = {
        "path": str(ledger_path),
        "map_changed": map_changed,
        "forced": force,
        "new_count": len(selected) - len(changed),
        "changed_count": len(changed),
        "skipped_count": len(skipped),
        "skipped": skipped,
        "changed": changed,
    }
    return ReferenceRead(selected, info, prior, current_records, events,
                         ledger_path, events_path, map_hash)
