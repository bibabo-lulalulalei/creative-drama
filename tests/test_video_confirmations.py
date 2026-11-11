"""离线确认链回归：真实 stamp 写入、同一 lint/执行门、变更和重试范围。"""
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import drama_lint
import h3_contract
import stamp_confirmation as stamp
from rhythm_engine import canonical_sha
from video_confirmations import (authorization_binding, load_confirmation_history, request_segment_snapshot,
                                 validate_project_confirmations)


class ConfirmationFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "00_制作控制").mkdir()
        (self.root / "reference.png").write_bytes(b"image-version-one")
        self.make_episode("ep_1")

    def path(self, episode="ep_1"):
        return self.root / f"episodes/{episode}/04_视频片段/video_manifest_{episode}.json"

    def read(self, episode="ep_1"):
        return json.loads(self.path(episode).read_text(encoding="utf-8"))

    def write(self, data, episode="ep_1"):
        self.path(episode).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def make_episode(self, episode, count=1):
        directory = self.path(episode).parent
        directory.mkdir(parents=True, exist_ok=True)
        segments = []
        for index in range(1, count + 1):
            sid = f"SEG{index:03d}"
            prompt = directory / f"{sid}.h3.md"
            prompt.write_text(
                "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
                "integrated_multimodal_description: From <Picture 1>, a person opens a door over four seconds.\n"
                "overall_soundscape: Quiet room and footsteps.\nnon_diegetic_music: None.\n", encoding="utf-8")
            segments.append({"segment_id": sid, "episode_segment_index": index, "duration_s": 4,
                             "h3_prompt_file": prompt.relative_to(self.root).as_posix(),
                             "request_snapshot": {"model": "MiniMax H3", "mode": "I2VA", "duration_s": 4,
                                                  "inputs": [{"kind": "image", "path": "reference.png"}],
                                                  "workflow": "frozen-workflow", "base_url": "https://example.invalid"}})
        self.write({"episode_id": episode, "revision": 1, "duration_s": 4 * count, "segments": segments}, episode)

    def evidence(self, segments):
        rows = [{"segment_id": seg["segment_id"], "duration_s": seg["duration_s"],
                 "visual_content": "A person in a room", "subject_action": "Opening the door",
                 "audio": "Footsteps", "camera_and_materials": "A fixed camera and reference image"} for seg in segments]
        table = {"task_type": "video", "delivery_format": "MP4", "quantity": len(rows),
                 "total_duration": f"{4 * len(rows)}秒", "aspect_ratio_and_resolution": "16:9",
                 "model": "MiniMax H3", "visual_and_continuity": "Same person",
                 "audio_and_subtitles": "Footsteps; no subtitles", "reference_materials": "reference.png"}
        text = "\n".join(f"{row['segment_id']} {row['duration_s']}秒 " + " ".join(
            row[key] for key in ("visual_content", "subject_action", "audio", "camera_and_materials")) for row in rows)
        path = self.root / "evidence.json"
        path.write_text(json.dumps({"displayed_parameter_table": table, "displayed_storyboard_rows": rows,
                                    "final_parameters_text": text,
                                    "request_snapshot_sha256": canonical_sha({"segments": [request_segment_snapshot(seg) for seg in segments]}),
                                    "authorization_bindings": [authorization_binding(self.root, seg) for seg in segments]},
                                   ensure_ascii=False), encoding="utf-8")
        return path

    def confirm(self, cid="CONF-1", episode="ep_1", ids=None, time="2026-11-11T13:00:00+08:00"):
        segments = self.read(episode)["segments"]
        selected = [seg for seg in segments if ids is None or seg["segment_id"] in ids]
        evidence = self.evidence(selected)
        with redirect_stdout(io.StringIO()):
            result = stamp.main(["--project-root", str(self.root), "--stage", "video", "--video",
                                 "--episode", episode, "--revision", "1", "--confirmation-id", cid,
                                 "--segments", ",".join(seg["segment_id"] for seg in selected),
                                 "--evidence-file", str(evidence), "--ask-call-id", f"ask-{cid}",
                                 "--user-message", "按要求生成", "--confirmed-at", time, "--append"])
        self.assertEqual(result, 0)
        return load_confirmation_history(self.root, episode)[-1]

    def test_real_stamp_writes_one_authority_and_both_readers_accept(self):
        original = self.path().read_bytes()
        record = self.confirm()
        self.assertEqual(self.path().read_bytes(), original)
        self.assertEqual(record["request_snapshot_sha256"], canonical_sha(record["request_snapshot"]))
        self.assertEqual(record["attempt"], 1)
        data = self.read()
        data["segments"][0].update(status="candidate", output_file="generated.mp4", tool_call_id="actual-tool-call",
                                   tool_called_at="2026-11-11T13:00:01+08:00", generation_confirmation_id="CONF-1")
        self.write(data)
        self.assertEqual(validate_project_confirmations(self.root, "ep_1"), [])
        self.assertEqual(h3_contract.check_authorization(self.root, "SEG001", "ep_1")["confirmation_id"], "CONF-1")
        issues = []
        drama_lint.check_video_generation_confirmations(self.read(), self.read()["segments"], self.path(), issues,
                                                       self.root, "ep_1")
        self.assertEqual(issues, [])

    def test_missing_confirmation_and_stale_prepare_evidence_are_rejected(self):
        with self.assertRaises(h3_contract.ContractError):
            h3_contract.check_authorization(self.root, "SEG001", "ep_1")
        segments = self.read()["segments"]
        evidence_path = self.evidence(segments)
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        parts = stamp.build_video_parts(self.root, "ep_1", ["SEG001"])
        evidence.update({key: parts[key] for key in ("request_snapshot_sha256", "authorization_bindings")})
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        (self.root / "reference.png").write_bytes(b"changed-after-display")
        with redirect_stdout(io.StringIO()):
            result = stamp.main(["--project-root", str(self.root), "--stage", "video", "--video", "--episode", "ep_1",
                                 "--revision", "1", "--confirmation-id", "STALE", "--segments", "SEG001",
                                 "--user-message", "按要求生成", "--evidence-file", str(evidence_path), "--append"])
        self.assertEqual(result, 2)
        self.assertFalse((self.root / stamp.LEDGER_REL).exists())

    def test_authorization_requires_explicit_canonical_record_fields(self):
        record = self.confirm()
        ledger = self.root / stamp.LEDGER_REL
        for field in ("stage", "decision", "confirmation_purpose", "authorization_version"):
            with self.subTest(missing=field):
                incomplete = copy.deepcopy(record)
                incomplete.pop(field)
                ledger.write_text(json.dumps(incomplete) + "\n", encoding="utf-8")
                with self.assertRaises(h3_contract.ContractError):
                    h3_contract.check_authorization(self.root, "SEG001", "ep_1")

    def test_invalid_prompt_or_incomplete_evidence_cannot_create_authorization(self):
        segments = self.read()["segments"]
        evidence_path = self.evidence(segments)
        evidence_original = evidence_path.read_text(encoding="utf-8")
        prompt = self.root / segments[0]["h3_prompt_file"]
        prompt_original = prompt.read_bytes()
        for mutation in ("evidence", "prompt", "prompt_path"):
            with self.subTest(mutation=mutation):
                evidence_path.write_text(evidence_original, encoding="utf-8")
                prompt.write_bytes(prompt_original)
                data = self.read()
                data["segments"][0]["h3_prompt_file"] = segments[0]["h3_prompt_file"]
                if mutation == "evidence":
                    evidence = json.loads(evidence_original)
                    evidence.pop("authorization_bindings")
                    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
                elif mutation == "prompt":
                    prompt.write_text("arbitrary non-H3 instructions", encoding="utf-8")
                else:
                    data["segments"][0]["h3_prompt_file"] = "../outside.md"
                self.write(data)
                with redirect_stdout(io.StringIO()):
                    result = stamp.main(["--project-root", str(self.root), "--stage", "video", "--video", "--episode", "ep_1",
                                         "--revision", "1", "--confirmation-id", "INVALID", "--segments", "SEG001",
                                         "--user-message", "按要求生成", "--evidence-file", str(evidence_path), "--append"])
                self.assertEqual(result, 2)
                self.assertFalse((self.root / stamp.LEDGER_REL).exists())

    def test_request_prompt_and_local_input_changes_invalidate_authorization(self):
        self.confirm()
        original = self.read()
        prompt = self.root / original["segments"][0]["h3_prompt_file"]
        prompt_original = prompt.read_bytes()
        for mutation in ("request", "prompt", "input"):
            with self.subTest(mutation=mutation):
                self.write(copy.deepcopy(original))
                prompt.write_bytes(prompt_original)
                (self.root / "reference.png").write_bytes(b"image-version-one")
                if mutation == "request":
                    data = self.read()
                    data["segments"][0]["request_snapshot"]["workflow"] = "changed-workflow"
                    self.write(data)
                elif mutation == "prompt":
                    prompt.write_bytes(prompt_original + b"changed")
                else:
                    (self.root / "reference.png").write_bytes(b"image-version-two")
                with self.assertRaises(h3_contract.ContractError):
                    h3_contract.check_authorization(self.root, "SEG001", "ep_1")
                self.assertTrue(validate_project_confirmations(self.root, "ep_1"))

    def test_retry_replaces_only_covered_segment_and_retains_history(self):
        self.make_episode("ep_1", count=2)
        self.confirm()
        second = self.confirm("CONF-2", ids=["SEG001"], time="2026-11-11T13:01:00+08:00")
        self.assertEqual(second["attempt"], 2)
        self.assertEqual(second["supersedes_confirmation_ids"], ["CONF-1"])
        self.assertEqual(len(load_confirmation_history(self.root, "ep_1")), 2)
        self.assertEqual(h3_contract.check_authorization(self.root, "SEG001", "ep_1")["confirmation_id"], "CONF-2")
        self.assertEqual(h3_contract.check_authorization(self.root, "SEG002", "ep_1")["confirmation_id"], "CONF-1")

    def test_same_segment_name_in_two_episodes_does_not_share_authorization(self):
        self.make_episode("ep_2")
        self.confirm()
        with self.assertRaises(h3_contract.ContractError):
            h3_contract.check_authorization(self.root, "SEG001", "ep_2")
        with self.assertRaises(h3_contract.ContractError):
            h3_contract.check_authorization(self.root, "SEG001")
        self.confirm("CONF-EP2", episode="ep_2")
        self.assertEqual(h3_contract.check_authorization(self.root, "SEG001", "ep_2")["confirmation_id"], "CONF-EP2")

    def test_freeze_persists_resolved_deployment(self):
        snapshot = self.read()["segments"][0]["request_snapshot"]
        snapshot.pop("workflow")
        snapshot.pop("base_url")
        request_file = self.root / "request.json"
        request_file.write_text(json.dumps(snapshot), encoding="utf-8")
        with patch.object(h3_contract, "local_settings", return_value={"H3_WORKFLOW": "resolved-workflow",
                                                                        "H3_BASE_URL": "https://resolved.invalid"}):
            with redirect_stdout(io.StringIO()):
                result = stamp.main(["--project-root", str(self.root), "--episode", "ep_1", "--segment-id", "SEG001",
                                     "--freeze-request", "--request-file", str(request_file), "--append"])
        self.assertEqual(result, 0)
        frozen = self.read()["segments"][0]["request_snapshot"]
        self.assertEqual(frozen["workflow"], "resolved-workflow")
        self.assertEqual(frozen["base_url"], "https://resolved.invalid")

    def ready_for_acceptance(self, target="final"):
        self.confirm()
        data = self.read()
        data["segments"][0].update(status="candidate", output_file="generated.mp4", tool_call_id="actual-call",
                                   tool_called_at="2026-11-11T13:00:01+08:00", generation_confirmation_id="CONF-1")
        self.write(data)
        (self.root / "generated.mp4").write_bytes(b"generated media")
        storyboard = self.root / "episodes/ep_1/02_分镜/storyboard_ep_1.json"
        storyboard.parent.mkdir(parents=True)
        storyboard.write_text(json.dumps({"segments": [{"segment_id": "SEG001"}]}), encoding="utf-8")
        (self.root / "00_制作控制/drama_plan.json").write_text(
            json.dumps({"objective": {"target_stage": target}}), encoding="utf-8")

    def acceptance(self, target="final"):
        args = ["--project-root", str(self.root), "--stage", "video", "--episode", "ep_1", "--revision", "1",
                "--user-message", "接受当前视频", "--confirmed-at", "2026-11-11T13:01:00+08:00", "--append"]
        if target == "final":
            args += ["--confirmation-purpose", "video_acceptance_and_final_assembly", "--ask-call-id", "ask-assembly",
                     "--interaction-ask-result", "proceed_assembly"]
        with redirect_stdout(io.StringIO()):
            return stamp.main(args)

    def accept_segment(self):
        with redirect_stdout(io.StringIO()):
            return stamp.main(["--project-root", str(self.root), "--episode", "ep_1", "--video-status",
                               "--segment-id", "SEG001", "--status", "accepted", "--output-file", "generated.mp4",
                               "--tool-call-id", "actual-call", "--tool-called-at", "2026-11-11T13:00:01+08:00",
                               "--confirmation-id", "CONF-1", "--append"])

    def test_generation_permission_cannot_accept_video_but_real_output_confirmation_can(self):
        self.ready_for_acceptance()
        self.assertEqual(self.accept_segment(), 2)
        self.assertEqual(self.read()["segments"][0]["status"], "candidate")
        self.assertEqual(self.acceptance(), 0)
        self.assertEqual(self.accept_segment(), 0)
        self.assertEqual(self.read()["segments"][0]["status"], "accepted")

    def test_target_video_acceptance_does_not_require_or_create_assembly_authorization(self):
        self.ready_for_acceptance(target="video")
        self.assertEqual(self.acceptance(target="video"), 0)
        self.assertEqual(self.accept_segment(), 0)
        records = drama_lint.load_confirmation_records(self.root, [], required=True)
        self.assertEqual(records[-1]["confirmation_purpose"], "")
        self.assertEqual(records[-1]["interaction_ask_result"], "")

    def test_assembly_confirmation_cannot_accept_incomplete_episode(self):
        self.ready_for_acceptance()
        path = self.root / "episodes/ep_1/02_分镜/storyboard_ep_1.json"
        path.write_text(json.dumps({"segments": [{"segment_id": "SEG001"}, {"segment_id": "SEG002"}]}), encoding="utf-8")
        before = (self.root / stamp.LEDGER_REL).read_bytes()
        self.assertEqual(self.acceptance(), 2)
        self.assertEqual((self.root / stamp.LEDGER_REL).read_bytes(), before)

    def test_old_output_acceptance_does_not_accept_new_generated_result(self):
        self.ready_for_acceptance()
        self.assertEqual(self.acceptance(), 0)
        data = self.read()
        data["segments"][0]["tool_called_at"] = "2026-11-11T13:02:00+08:00"
        self.write(data)
        with self.assertRaises(stamp.StampError):
            rows = drama_lint.load_confirmation_records(self.root, [], required=True)
            stamp.verify_video_acceptance(self.root, rows[-1], drama_lint)


if __name__ == "__main__":
    unittest.main()
