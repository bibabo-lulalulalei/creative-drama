"""预检已形成的完整 SEG 或轻量单任务；不要求生成授权/结果，不进行 HTTP。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/video"))
from content_first import (check_lightweight, load_source, parse_lightweight, project_file, read_json, reconcile_storyboard)
from timeline_core import canonical_sha, to_ms
from rhythm_engine import atomic_write_many, json_text, load_h3
from h3_contract import ContractError, prepare_request, preflight_receipt, scoped_design, scoped_timing


def validate_manifest_inputs(segment, gen):
    for field, kind in (("reference_inputs", "image"), ("video_inputs", "video"), ("audio_inputs", "audio")):
        rows = segment.get(field, [])
        actual = [row for row in gen.get("inputs", []) if row.get("kind") == kind]
        if (not isinstance(rows, list) or len(rows) != len(actual)
                or any(not isinstance(row, dict) or row.get("order") != i
                       or row.get("file") != submitted.get("path") or row.get("role") != submitted.get("role")
                       for i, (row, submitted) in enumerate(zip(rows, actual), 1))):
            raise ContractError("h3_input_invalid", "manifest 的实际输入顺序/文件或原样 URL/职责与 gen 不同")
        for row, submitted in zip(rows, actual):
            if kind in {"video", "audio"} and "duration_s" in row:
                try:
                    same = to_ms(row["duration_s"], positive=True) == to_ms(submitted.get("duration_s"), positive=True)
                except ValueError:
                    same = False
                if not same:
                    raise ContractError("h3_input_invalid", "manifest 的参考媒体时长与实际请求不同")


def validate_segment_timing(segment, expected, gen):
    try:
        if (segment.get("shot_ids") != expected["shot_ids"]
                or to_ms(gen.get("duration_s"), positive=True) != to_ms(expected["request_duration_s"], positive=True)
                or to_ms(segment.get("duration_s"), positive=True) != to_ms(gen["duration_s"], positive=True)
                or to_ms(segment.get("content_duration_s"), positive=True) != to_ms(expected["duration_s"], positive=True)
                or to_ms(segment.get("tail_handle_s")) != to_ms(expected["tail_handle_s"])):
            raise ValueError("SEG 镜头、内容时间、请求时间或技术尾余量不符同源核算")
        for field in ("content_duration_s", "tail_handle_s"):
            if field in gen and to_ms(gen[field]) != to_ms(segment[field]):
                raise ValueError("gen 的内容时间/尾余量与当前 SEG 不同")
    except (ValueError, KeyError, TypeError) as exc:
        raise ContractError("pack_drift", str(exc)) from None


def validate_compilation_map(mapping, result, segment, inp, index, speech_bridge=None):
    if (not isinstance(mapping, list) or any(not isinstance(row, dict) for row in mapping)
            or [row.get("shot_id") for row in mapping] != segment["shot_ids"]):
        raise ContractError("h3_compilation_mismatch", "编译映射须按当前 SEG 镜头顺序完整覆盖")
    offset = to_ms(segment["time_range_s"][0])
    by_shot = {shot["shot_id"]: shot for shot in result["shots"]}
    utterances = {row["utterance_id"]: row for row in inp["utterances"]}
    speech_events = {part["event_id"]: part for part in result["events"] if part.get("kind") == "speech"}
    declared_spans = {}
    for row in mapping:
        spans = row.get("speech_spans", [])
        if not isinstance(spans, list):
            raise ContractError("speech_span_incomplete", "发声分片须为对象数组")
        for span in spans:
            if not isinstance(span, dict) or not isinstance(span.get("event_id"), str):
                raise ContractError("speech_span_incomplete", "发声分片须引用实际人声事件")
            part = speech_events.get(span["event_id"])
            if (not part or part["shot_id"] != row["shot_id"] or span["event_id"] in declared_spans
                    or span.get("utterance_id", part["utterance_id"]) != part["utterance_id"]
                    or not isinstance(span.get("spoken_text"), str) or not span["spoken_text"]):
                raise ContractError("speech_span_incomplete", "发声分片须唯一对应实际镜头及 utterance，不得漏文、错绑或重复")
            declared_spans[span["event_id"]] = dict(span, utterance_id=part["utterance_id"])
    for row in mapping:
        shot = by_shot[row["shot_id"]]
        expected = [(to_ms(value) - offset) / 1000 for value in shot["time_range_s"]]
        if row.get("content_range_s") != expected:
            raise ContractError("h3_compilation_mismatch", "镜头编译的 SEG 局部时间与核算不符")
        required = []
        for event in shot["timing_events"]:
            if event["kind"] != "speech":
                continue
            utterance = utterances[event["utterance_id"]]
            all_parts = [e for e in result["events"] if e.get("utterance_id") == event["utterance_id"]]
            if len(all_parts) > 1:
                # Words come from explicit spans, never inferred from elapsed seconds.
                crosses_segment = any(part["shot_id"] not in segment["shot_ids"] for part in all_parts)
                if crosses_segment and (not isinstance(speech_bridge, dict) or not speech_bridge.get("implementation")
                        or not speech_bridge.get("review_ref")):
                    raise ContractError("speech_span_discontinuous", "跨 SEG 发声须有真实实施方式和声音承接审校引用")
                match = declared_spans.get(event["event_id"])
                source_text = index["line:" + utterance["line_id"]]["spoken_text"]
                if crosses_segment:
                    bridge_spans = speech_bridge.get("utterance_spans", [])
                else:
                    bridge_spans = [declared_spans[part["event_id"]] for part in all_parts
                                    if part["event_id"] in declared_spans]
                known_spans = {(part.get("utterance_id"), part["event_id"])
                               for part in result["events"] if part.get("kind") == "speech"}
                if (not isinstance(bridge_spans, list)
                        or any(not isinstance(span, dict)
                               or not isinstance(span.get("utterance_id"), str)
                               or not isinstance(span.get("event_id"), str)
                               or (span["utterance_id"], span["event_id"]) not in known_spans
                               for span in bridge_spans)):
                    raise ContractError("speech_span_incomplete", "声音承接须明确完整逐字分片")
                ordered = sorted(all_parts, key=lambda part: to_ms(part['utterance_offset_s']))
                pieces = [[span for span in bridge_spans if isinstance(span, dict)
                           and span.get('utterance_id') == event['utterance_id'] and span.get('event_id') == part['event_id']]
                          for part in ordered]
                if (any(len(piece) != 1 or not isinstance(piece[0].get('spoken_text'), str) or not piece[0]['spoken_text'] for piece in pieces)
                        or ''.join(piece[0]['spoken_text'] for piece in pieces) != source_text):
                    raise ContractError("speech_span_incomplete", "跨镜/跨 SEG 发声分片必须按 utterance 顺序逐字覆盖源台词，无遗漏或重复")
                planned_piece = next(piece[0]['spoken_text'] for part, piece in zip(ordered, pieces) if part['event_id'] == event['event_id'])
                if not match or match["spoken_text"] != planned_piece:
                    raise ContractError("source_line_uncovered", "跨镜/跨 SEG 需明确逐字发声分片，不由秒数猜词")
                required.append(match["spoken_text"])
            else:
                source_text = index["line:" + utterance["line_id"]]["spoken_text"]
                if event["event_id"] in declared_spans and declared_spans[event["event_id"]]["spoken_text"] != source_text:
                    raise ContractError("source_line_uncovered", "单镜发声分片须保留完整源台词")
                required.append(source_text)
        if row.get("spoken_texts", []) != list(dict.fromkeys(required)):
            raise ContractError("source_line_uncovered", "编译映射的逐字人声须来自当前源台词，不能省略或换文")


def prepare_full(root, episode, segment_id):
    root = Path(root).resolve()
    base = root / "episodes" / episode
    sb_path = base / f"02_分镜/storyboard_{episode}.json"
    timing_path = base / f"02_分镜/rhythm_input_{episode}.json"
    sb, inp = read_json(sb_path), read_json(timing_path)
    result, pack, issues = reconcile_storyboard(root, sb, inp, timing_path, load_h3())
    if issues:
        raise ContractError(issues[0]["code"], issues[0]["message"])
    video_path = base / f"04_视频片段/video_manifest_{episode}.json"
    video = read_json(video_path)
    if video.get("schema_version") != "1.2":
        raise ContractError("h3_request_invalid", "新 video manifest 需 schema 1.2")
    matches = [seg for seg in video.get("segments", []) if seg.get("segment_id") == segment_id]
    if len(matches) != 1:
        raise ContractError("h3_request_invalid", "SEG 不存在或重复")
    seg = matches[0]
    storyboard_segment = next((row for row in sb["segments"] if row["segment_id"] == segment_id), None)
    if not storyboard_segment:
        raise ContractError("pack_drift", "视频 SEG 不在当前分镜")
    gen_path = project_file(root, seg.get("gen_file"))
    gen = read_json(gen_path)
    validate_manifest_inputs(seg, gen)
    validate_segment_timing(seg, storyboard_segment, gen)
    source = inp["source_script"]
    contract = read_json(project_file(root, source["file"]))
    records_file = "00_制作控制/用户确认记录.jsonl"
    records = [json.loads(line) for line in (root / records_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    confirmation = [row for row in records if isinstance(row, dict) and row.get("stage") == "script"
                    and row.get("episode_id") == episode and row.get("decision") == "confirmed" and row.get("valid", True) is not False][-1]
    specs = [{"role": "director_package", "file": seg.get("compiled_prompt_file")},
             {"role": "storyboard_design", "file": str(sb_path.relative_to(root)).replace("\\", "/"), "shot_ids": storyboard_segment["shot_ids"]},
             {"role": "timing_input", "file": str(timing_path.relative_to(root)).replace("\\", "/"), "shot_ids": storyboard_segment["shot_ids"]},
             {"role": "source_script", "file": source["file"]},
             {"role": "script_markdown", "file": contract["source_markdown"]},
             {"role": "source_confirmation", "file": records_file, "confirmation_id": confirmation["confirmation_id"]}]
    inbound = seg.get("inbound")
    if seg.get("seam_type") == "continuous" and not inbound:
        raise ContractError("adopted_cut_out_invalid", "continuous 后段需先锁采用出点和真实入站帧，再编译")
    if inbound:
        specs.append({"role": "adopted_cut_out", "file": inbound["cut_file"]})
    if (root / "00_制作控制/project_data_card.json").is_file():
        specs.append({"role": "asset_facts", "file": "00_制作控制/project_data_card.json"})
    mapping = seg.get("compilation_map")
    index, _ = load_source(root, inp, sb)
    validate_compilation_map(mapping, result, storyboard_segment, inp, index, seg.get("speech_bridge"))
    prepared = prepare_request(gen=gen, root=root, prompt_file=seg.get("h3_prompt_file"), verify=False,
                               dependency_specs=specs, content_review_ref=canonical_sha({"design": scoped_design(sb, storyboard_segment["shot_ids"]),
                                   "timing": scoped_timing(inp, storyboard_segment["shot_ids"]), "open_issues": sb["content_review"]["open_issues"]}),
                               compilation_map=mapping, inbound=inbound)
    return gen_path, gen, prepared, video_path, video, seg


def prepare_lightweight(root, design, package, gen_path, prompt, *, segment=None):
    root = Path(root).resolve()
    text = project_file(root, design).read_text(encoding="utf-8")
    inp, metadata, result, pack, issues = check_lightweight(text, load_h3())
    if issues:
        raise ContractError(issues[0]["code"], issues[0]["message"])
    path = project_file(root, gen_path)
    gen = read_json(path)
    if not pack or gen.get("duration_s") != pack["segments"][0]["request_duration_s"]:
        raise ContractError("pack_drift", "轻量请求时长不符实际单条设计")
    expected = pack["segments"][0]
    if segment is not None:
        validate_segment_timing(segment, expected, gen)
    if ("content_duration_s" in gen and gen["content_duration_s"] != expected["duration_s"]
            or "tail_handle_s" in gen and gen["tail_handle_s"] != expected["tail_handle_s"]):
        raise ContractError("pack_drift", "轻量 gen 的内容时间/尾余量与设计不同")
    # Current authored mapping is authority; an old receipt cannot mask a revised design.
    mapping = metadata.get("source_metadata", {}).get("compilation_map")
    _, _, _, index = parse_lightweight(text)
    validate_compilation_map(mapping, result, pack["segments"][0], inp, index)
    prepared = prepare_request(gen=gen, root=root, prompt_file=prompt, verify=False,
                               dependency_specs=[{"role": "lightweight_design", "file": design},
                                                 {"role": "director_package", "file": package}],
                               content_review_ref=canonical_sha(metadata["content_review"]), compilation_map=mapping)
    return path, gen, prepared


def main():
    parser = argparse.ArgumentParser(description="H3 本地预检，无 HTTP、凭证或生成授权副作用")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", choices=("full", "lightweight"), default="full")
    parser.add_argument("--episode")
    parser.add_argument("--segment")
    parser.add_argument("--design")
    parser.add_argument("--director-package")
    parser.add_argument("--gen")
    parser.add_argument("--prompt")
    parser.add_argument("--video-manifest", help="轻量可在同次原子写回已有清单；与 --segment 一起使用")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        if args.mode == "lightweight":
            if not all((args.design, args.director_package, args.gen, args.prompt)):
                parser.error("轻量需 --design --director-package --gen --prompt")
            video_path = None
            segment = None
            if args.video_manifest or args.segment:
                if not args.video_manifest or not args.segment:
                    parser.error("轻量登记需同时提供 --video-manifest 和 --segment")
                video_path = project_file(args.project_root, args.video_manifest)
                video = read_json(video_path)
                segments = video.get("segments")
                if video.get("schema_version") != "1.2" or not isinstance(segments, list) or len(segments) != 1:
                    raise ContractError("h3_request_invalid", "轻量清单需 schema 1.2 且恰有一个 SEG")
                segment = segments[0]
                if (segment.get("segment_id") != args.segment or segment.get("gen_file") != args.gen
                        or segment.get("h3_prompt_file") != args.prompt or segment.get("compiled_prompt_file") != args.director_package):
                    raise ContractError("pack_drift", "轻量清单须登记同一设计、包、成稿及请求")
            path, gen, prepared = prepare_lightweight(args.project_root, args.design, args.director_package, args.gen, args.prompt, segment=segment)
            if segment is not None:
                validate_manifest_inputs(segment, gen)
        else:
            if not args.episode or not args.segment:
                parser.error("完整模式需 --episode --segment")
            path, gen, prepared, video_path, video, segment = prepare_full(args.project_root, args.episode, args.segment)
        if args.write:
            gen["preflight"] = preflight_receipt(prepared)
            entries = [(path, json_text(gen))]
            if video_path is not None:
                segment["binding_id"] = prepared.contract["binding_id"]
                segment["request_snapshot"] = prepared.contract["request_snapshot"]
                segment["h3_prompt_sha256"] = prepared.contract["h3_prompt_sha256"]
                from content_first import file_sha
                segment["prompt_sha256"] = file_sha(project_file(args.project_root, segment["compiled_prompt_file"]))
                entries.append((video_path, json_text(video)))
            atomic_write_many(entries)
        print(json.dumps(prepared.summary(), ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, StopIteration, IndexError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
