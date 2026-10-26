#!/usr/bin/env python3
"""Validate and deterministically merge scene-level storyboard JSON shards."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def force_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", required=True, help="JSON containing scene_order and shard entries")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    index_path = Path(args.index).resolve()
    output = Path(args.output).resolve()
    try:
        index = load(index_path)
        order = index.get("scene_order")
        shards = index.get("shards")
        if not isinstance(order, list) or not isinstance(shards, list):
            raise ValueError("index 必须包含 scene_order[] 和 shards[]")
        if not order or any(not isinstance(sid, str) or not sid for sid in order):
            raise ValueError("scene_order 必须是非空且只含有效场次 ID 的数组")
        base = index.get("storyboard_base")
        if not isinstance(base, dict):
            raise ValueError("index.storyboard_base 必须包含正式 storyboard 的非 shots 字段")
        base_scenes = base.get("scenes")
        if not isinstance(base_scenes, list) or not base_scenes:
            raise ValueError("storyboard_base.scenes 必须是非空场次数组，用于证明场次覆盖完整")
        base_order = [scene.get("scene_id") for scene in base_scenes if isinstance(scene, dict)]
        if len(base_order) != len(base_scenes) or base_order != order:
            raise ValueError(f"scene_order 必须与 storyboard_base.scenes[].scene_id 顺序完全一致；order={order}, base={base_order}")
        by_scene: dict[str, dict[str, Any]] = {}
        for item in shards:
            if not isinstance(item, dict) or not isinstance(item.get("scene_id"), str) or not isinstance(item.get("path"), str):
                raise ValueError("shards 每项必须有 scene_id 和 path")
            sid = item["scene_id"]
            if sid in by_scene:
                raise ValueError(f"重复 scene_id: {sid}")
            path = (index_path.parent / item["path"]).resolve()
            if index_path.parent.resolve() not in path.parents or not path.is_file():
                raise ValueError(f"shard 不存在或越出工作目录: {item['path']}")
            raw = path.read_bytes()
            data = json.loads(raw.decode("utf-8"))
            if data.get("scene_id") != sid or not isinstance(data.get("shots"), list) or not data["shots"]:
                raise ValueError(f"{item['path']}: scene_id 不匹配或缺少 shots[]")
            by_scene[sid] = {"path": path, "source_path": item["path"], "data": data, "sha256": digest(raw)}
        if len(order) != len(set(order)) or set(order) != set(by_scene):
            raise ValueError(f"scene_order 必须与 shard scene_id 一一对应；order={order}, shards={sorted(by_scene)}")
        shot_ids: set[str] = set()
        merged_shots: list[dict[str, Any]] = []
        for sid in order:
            for shot in by_scene[sid]["data"]["shots"]:
                if not isinstance(shot, dict) or not isinstance(shot.get("shot_id"), str) or shot.get("scene_id") != sid:
                    raise ValueError(f"{sid}: 每个镜头必须有全局唯一 shot_id，且 scene_id 必须与所属分场一致")
                shot_id = shot["shot_id"]
                if shot_id in shot_ids:
                    raise ValueError(f"重复 shot_id: {shot_id}")
                shot_ids.add(shot_id)
                merged_shots.append(shot)
        out = dict(base)
        out["shots"] = merged_shots
        out["merge_provenance"] = {
            "scene_order": order,
            "shards": [{"scene_id": sid, "path": by_scene[sid]["source_path"], "sha256": by_scene[sid]["sha256"]} for sid in order],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(out, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, output)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        print(json.dumps({"ok": True, "output": str(output), "scenes": len(order), "shots": len(merged_shots)}, ensure_ascii=False))
        return 0
    except (OSError, UnicodeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "output_written": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    force_utf8_stdio()
    raise SystemExit(main())
