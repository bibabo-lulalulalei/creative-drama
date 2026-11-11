"""H3 执行闭环：mock 服务端，真实临时项目与任务状态，不使用凭证或付费生成。"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("h3_runner", SKILL_ROOT / "tools/video/h3.py")
h3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h3)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.folder = self.root / "episodes/ep_1/04_视频片段"
        self.folder.mkdir(parents=True)
        self.manifest = self.folder / "video_manifest_ep_1.json"
        self.task_file = self.folder / "h3_task_SEG001.json"
        self.prompt = self.folder / "prompt.h3.md"
        self.prompt.write_text("integrated_multimodal_description:\nA boat crosses the sea.\n"
                               "overall_soundscape:\nWaves.\nnon_diegetic_music:\nNone.\n", encoding="utf-8")
        self.relative_prompt = self.prompt.relative_to(self.root).as_posix()
        self.out = self.folder / "take.mp4"
        self.output_file = self.out.relative_to(self.root).as_posix()
        self.write_manifest({"segments": [{"segment_id": "SEG001", "episode_segment_index": 1,
                             "duration_s": 4, "status": "planned", "h3_prompt_file": self.relative_prompt,
                             "request_snapshot": {"model": "H3", "mode": "T2VA", "duration_s": 4,
                                                  "workflow": "test-workflow", "base_url": "https://example.test",
                                                  "inputs": []}}]})
        self.authorization = mock.patch.object(h3, "check_authorization",
                                                return_value={"confirmation_id": "CONF001"}).start()
        self.settings = mock.patch.object(h3, "local_settings", return_value={"AUTODL_API_KEY": "test"}).start()
        self.http = mock.patch.object(h3, "_http", side_effect=self.backend).start()
        self.process = mock.patch.object(h3.subprocess, "run", side_effect=self.media_tool).start()
        self.addCleanup(mock.patch.stopall)
        self.posts = 0
        self.polls = 0
        self.downloads = 0
        self.server_status = "SUCCESS"
        self.fail_poll = False

    def write_manifest(self, value):
        self.manifest.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def read_manifest(self):
        return json.loads(self.manifest.read_text(encoding="utf-8"))

    def task(self):
        return json.loads(self.task_file.read_text(encoding="utf-8"))

    def backend(self, method, url, token, payload=None, raw=False, **kwargs):
        if method == "POST":
            self.posts += 1
            self.assertEqual(self.task()["phase"], "submission_pending")
            return {"code": "Success", "data": {"task_id": "TASK001"}}
        if raw:
            self.downloads += 1
            return b"mock mp4 bytes"
        self.polls += 1
        self.assertEqual(self.task()["task_id"], "TASK001")
        if self.fail_poll:
            raise h3.BackendError("connection interrupted")
        return {"code": "Success", "data": {"status": self.server_status, "seed": 42,
                "results": [{"type": "video", "url": "https://example.test/result.mp4"}]}}

    def media_tool(self, command, **kwargs):
        self.assertIsInstance(command, list)
        if command[0] == "ffprobe":
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "streams": [{"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720}],
                "format": {"duration": "4.0"}}), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    def run_cli(self, *extra, output=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = h3.main(["--project-root", str(self.root), "--episode", "ep_1", "--segment", "SEG001",
                            "--out", output or self.output_file, *extra])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_submit_only_then_resume_submits_once_and_registers_candidate(self):
        self.assertEqual(self.run_cli("--submit-only")[0], 0)
        self.assertEqual((self.posts, self.polls), (1, 0))
        task = self.task()
        self.assertEqual(task["binding"]["confirmation_id"], "CONF001")
        self.assertEqual(len(task["binding"]["request_sha256"]), 64)
        self.assertEqual(self.read_manifest()["segments"][0]["status"], "planned")
        code, output, error = self.run_cli("--resume")
        self.assertEqual(code, 0, error)
        self.assertTrue(self.out.is_file())
        self.assertEqual(self.posts, 1)
        segment = self.read_manifest()["segments"][0]
        self.assertEqual(segment["status"], "candidate")
        self.assertEqual(segment["tool_call_id"], "TASK001")
        self.assertEqual(segment["generation_confirmation_id"], "CONF001")
        self.assertEqual(segment["output_file"], self.output_file)
        self.assertTrue(segment["tool_called_at"])
        self.assertTrue(json.loads(output)["media"]["decode_ok"])
        self.assertEqual(self.task()["phase"], "complete")
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual((self.posts, self.downloads), (1, 1))
        self.authorization.assert_called_with(self.root, "SEG001", episode="ep_1")

    def test_default_reentry_resumes_network_interruption_without_post(self):
        self.fail_poll = True
        self.assertEqual(self.run_cli()[0], 1)
        self.assertEqual(self.task()["task_id"], "TASK001")
        self.assertFalse(self.out.exists())
        self.fail_poll = False
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(self.posts, 1)

    def test_failed_backend_keeps_task_without_candidate_or_resubmission(self):
        self.server_status = "FAILED"
        self.assertEqual(self.run_cli()[0], 1)
        self.assertEqual(self.task()["phase"], "failed")
        self.assertEqual(self.read_manifest()["segments"][0]["status"], "planned")
        self.assertFalse(self.out.exists())
        calls = self.http.call_count
        self.assertEqual(self.run_cli("--resume")[0], 1)
        self.assertEqual(self.http.call_count, calls)
        self.assertEqual(self.posts, 1)

    def test_changed_prompt_confirmation_or_output_cannot_rebind_task(self):
        self.assertEqual(self.run_cli("--submit-only")[0], 0)
        original = self.prompt.read_text(encoding="utf-8")
        self.prompt.write_text(original.replace("boat", "ship"), encoding="utf-8")
        self.assertEqual(self.run_cli("--resume")[0], 1)
        self.prompt.write_text(original, encoding="utf-8")
        self.authorization.return_value = {"confirmation_id": "CONF002"}
        self.assertEqual(self.run_cli("--resume")[0], 1)
        self.authorization.return_value = {"confirmation_id": "CONF001"}
        self.assertEqual(self.run_cli("--resume", output="elsewhere.mp4")[0], 1)
        self.assertEqual(self.posts, 1)
        self.assertEqual(self.polls, 0)

    def test_check_only_has_no_authorization_network_or_write_side_effects(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        code, output, error = self.run_cli("--check-only")
        self.assertEqual(code, 0, error)
        self.assertTrue(json.loads(output)["ok"])
        self.authorization.assert_not_called()
        self.settings.assert_not_called()
        self.http.assert_not_called()
        self.process.assert_not_called()
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_local_media_bytes_are_bound_across_resume(self):
        media = self.folder / "input.png"
        media.write_bytes(b"first image")
        manifest = self.read_manifest()
        snapshot = manifest["segments"][0]["request_snapshot"]
        snapshot.update(mode="I2VA", inputs=[{"kind": "image", "path": media.relative_to(self.root).as_posix()}])
        self.write_manifest(manifest)
        original = self.prompt.read_text(encoding="utf-8")
        self.prompt.write_text("For the target video, at 0.00 seconds into the target video, <Picture 1> "
                               "(from [Shot 1]) is fully referenced.\n\n" + original, encoding="utf-8")
        code, _, error = self.run_cli("--submit-only")
        self.assertEqual(code, 0, error)
        media.write_bytes(b"different image")
        self.assertEqual(self.run_cli("--resume")[0], 1)
        self.assertEqual((self.posts, self.polls), (1, 0))

    def test_request_changes_during_polling_do_not_register_candidate(self):
        def changing_backend(method, url, token, **kwargs):
            response = self.backend(method, url, token, **kwargs)
            if method == "GET" and not kwargs.get("raw"):
                manifest = self.read_manifest()
                manifest["segments"][0]["request_snapshot"]["seed"] = 99
                self.write_manifest(manifest)
            return response
        self.http.side_effect = changing_backend
        self.assertEqual(self.run_cli()[0], 1)
        self.assertFalse(self.out.exists())
        self.assertTrue(self.out.with_name(self.out.name + ".h3-download.part").is_file())
        self.assertEqual(self.read_manifest()["segments"][0]["status"], "planned")
        self.assertEqual(self.task()["phase"], "downloaded")

    def test_missing_planned_audio_or_wrong_duration_does_not_publish(self):
        manifest = self.read_manifest()
        manifest["segments"][0]["speech_lines"] = [{"source_text": "Hello"}]
        self.write_manifest(manifest)
        self.assertEqual(self.run_cli()[0], 1)
        self.assertFalse(self.out.exists())
        self.assertEqual(self.task()["phase"], "downloaded")
        self.assertEqual(self.read_manifest()["segments"][0]["status"], "planned")
        manifest["segments"][0].pop("speech_lines")
        self.write_manifest(manifest)

        def wrong_duration(command, **kwargs):
            result = self.media_tool(command, **kwargs)
            if command[0] == "ffprobe":
                data = json.loads(result.stdout)
                data["format"]["duration"] = "1.0"
                result.stdout = json.dumps(data)
            return result

        self.process.side_effect = wrong_duration
        self.assertEqual(self.run_cli("--resume")[0], 1)
        self.assertFalse(self.out.exists())
        self.assertEqual(self.posts, 1)

    def test_racing_output_is_not_overwritten(self):
        def racing_backend(method, url, token, **kwargs):
            response = self.backend(method, url, token, **kwargs)
            if kwargs.get("raw"):
                self.out.write_bytes(b"another producer")
            return response
        self.http.side_effect = racing_backend
        self.assertEqual(self.run_cli()[0], 1)
        self.assertEqual(self.out.read_bytes(), b"another producer")
        self.assertEqual(self.read_manifest()["segments"][0]["status"], "planned")

    def test_missing_media_tools_keeps_download_and_resumes_without_network(self):
        self.process.side_effect = FileNotFoundError("ffprobe")
        code, _, error = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn("ffprobe", error)
        self.assertEqual(self.task()["phase"], "downloaded")
        part = self.out.with_name(self.out.name + ".h3-download.part")
        self.assertTrue(part.is_file())
        self.assertFalse(self.out.exists())
        self.assertEqual(self.read_manifest()["segments"][0]["status"], "planned")
        calls = self.http.call_count
        self.process.side_effect = self.media_tool
        self.assertEqual(self.run_cli("--resume")[0], 0)
        self.assertEqual(self.http.call_count, calls)

    def test_decode_error_never_publishes_or_registers(self):
        def invalid_decode(command, **kwargs):
            if command[0] == "ffmpeg":
                return subprocess.CompletedProcess(command, 1, "", "invalid data")
            return self.media_tool(command, **kwargs)
        self.process.side_effect = invalid_decode
        self.assertEqual(self.run_cli()[0], 1)
        self.assertFalse(self.out.exists())
        self.assertEqual(self.read_manifest()["segments"][0]["status"], "planned")
        self.assertEqual(self.task()["phase"], "downloaded")

    def test_existing_output_is_never_overwritten_or_submitted(self):
        self.out.write_bytes(b"keep me")
        self.assertEqual(self.run_cli()[0], 1)
        self.assertEqual(self.out.read_bytes(), b"keep me")
        self.http.assert_not_called()
        self.assertFalse(self.task_file.exists())

    def test_lost_post_response_is_not_automatically_retried(self):
        self.http.side_effect = h3.BackendError("connection lost during POST")
        self.assertEqual(self.run_cli()[0], 1)
        self.assertEqual(self.task()["phase"], "submission_pending")
        calls = self.http.call_count
        self.assertEqual(self.run_cli()[0], 1)
        self.assertEqual(self.http.call_count, calls)

    def test_resume_requires_an_existing_task(self):
        self.assertEqual(self.run_cli("--resume")[0], 1)
        self.http.assert_not_called()

    def test_completed_resume_preserves_human_acceptance(self):
        self.assertEqual(self.run_cli()[0], 0)
        manifest = self.read_manifest()
        manifest["segments"][0]["status"] = "accepted"
        self.write_manifest(manifest)
        self.assertEqual(self.run_cli("--resume")[0], 0)
        self.assertEqual(self.read_manifest()["segments"][0]["status"], "accepted")
        self.assertEqual(self.posts, 1)

    def test_new_task_requires_new_confirmation_and_new_output_then_archives(self):
        self.assertEqual(self.run_cli()[0], 0)
        old_output = self.out.read_bytes()
        new_output = self.out.with_name("take_v02.mp4").relative_to(self.root).as_posix()
        self.assertEqual(self.run_cli("--new-task", output=new_output)[0], 1)
        self.assertEqual(self.posts, 1)
        self.authorization.return_value = {"confirmation_id": "CONF002"}
        self.assertEqual(self.run_cli("--new-task")[0], 1)
        self.assertEqual(self.posts, 1)
        code, _, error = self.run_cli("--new-task", output=new_output)
        self.assertEqual(code, 0, error)
        self.assertEqual(self.posts, 2)
        self.assertEqual(self.out.read_bytes(), old_output)
        self.assertTrue((self.root / new_output).is_file())
        archives = list(self.folder.glob("h3_task_SEG001.history_*.json"))
        self.assertEqual(len(archives), 1)
        self.assertIn("TASK001_CONF001", archives[0].name)
        self.assertEqual(json.loads(archives[0].read_text(encoding="utf-8"))["binding"]["confirmation_id"], "CONF001")
        self.assertEqual(self.task()["binding"]["confirmation_id"], "CONF002")
        self.authorization.return_value = {"confirmation_id": "CONF001"}
        self.assertEqual(self.run_cli("--new-task", output="take_v03.mp4")[0], 1)
        self.assertEqual(self.posts, 2)

    def test_prompt_change_before_post_does_not_submit_stale_prepared_payload(self):
        original = self.authorization.side_effect
        def change_after_preparation(*args, **kwargs):
            self.prompt.write_text(self.prompt.read_text(encoding="utf-8").replace("boat", "ship"), encoding="utf-8")
            return {"confirmation_id": "CONF001"}
        self.authorization.side_effect = change_after_preparation
        self.assertEqual(self.run_cli()[0], 1)
        self.http.assert_not_called()
        self.authorization.side_effect = original


if __name__ == "__main__":
    unittest.main()
