"""离线覆盖上游派生、真实素材门、事务失败和已有结果保护。"""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_video import PreparationError, combine_evidence, load_segment_context, prepare_segment
from video_confirmations import authorization_binding, request_segment_snapshot
from rhythm_engine import canonical_sha


class PrepareVideoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="prepare_video_test_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = "episodes/ep_1"
        self.manifest_rel = f"{self.base}/04_视频片段/video_manifest_ep_1.json"
        self.storyboard_rel = f"{self.base}/02_分镜/storyboard_ep_1.json"
        self.prompt_rel = f"{self.base}/04_视频片段/prompt.h3.md"
        self.request_rel = f"{self.base}/04_视频片段/request.json"
        self.write("00_制作控制/制作状态.json", {"phases": {stage: "confirmed" for stage in ("script", "assets", "storyboard", "keyframes")}})
        self.write("00_制作控制/drama_plan.json", {"revision": 2, "scale_plan": {"aspect_ratio": "16:9", "resolution_plan": "768p横"}, "model_plan": {"video": {"model": "MiniMax H3"}}, "delivery_settings": {"subtitle_enabled": False}})
        self.write("00_制作控制/project_data_card.json", {"revision": 3, "global_settings": {"ratio": "16:9"}, "voices": [{"voice_id": "VOICE001", "voice_anchor": "沉稳青年男声"}]})
        self.write("shared/03_资产/asset_registry.json", {"assets": []})
        self.write(f"{self.base}/03_资产/asset_usage_ep_1.json", {"revision": 1, "shared_assets": [], "episode_assets": []})
        self.write(f"{self.base}/03_资产/keyframe_manifest_ep_1.json", {"revision": 1, "keyframes": []})
        self.write(f"{self.base}/01_剧本/script_contract_ep_1.json", {"revision": 1, "scenes": [{"scene_id": "E01S01", "speech_lines": [{"line_id": "LINE001", "speaker": "CHR001", "voice_id": "VOICE001", "type": "on_screen_dialogue", "source_text": "门开了。"}]}]})
        self.write(f"{self.base}/02_分镜/director.md", "| SEG | 导演执行 |\n|---|---|\n| SEG001 | 抬手开门，窗光照亮脸部 |\n| SEG002 | 不应加载的第二段 |\n")
        headers = ["场次", "视频片段", "镜号", "镜头职责", "时长", "画面描述", "景别", "机位", "光影", "对白", "音效", "摄影过程", "切入切出", "连续性", "承接"]
        cells = ["E01S01", "SEG001", "E01S01-SHOT001", "门内发现", "4秒", "人物抬手推门，窗光照脸", "近景", "眼平", "暖光", "LINE001 门开了。", "门轴响", "缓推后停稳", "动作切", "人物身份一致", "门打开"]
        self.write(f"{self.base}/02_分镜/shots.md", "| " + " | ".join(headers) + " |\n|" + "---|" * 15 + "\n| " + " | ".join(cells) + " |\n")
        self.storyboard = {"revision": 4, "source_markdown": f"{self.base}/02_分镜/shots.md", "director_control_card": f"{self.base}/02_分镜/director.md", "segments": [{"segment_id": "SEG001", "duration_s": 3.5, "request_duration_s": 4, "tail_handle_s": 0.5, "shot_ids": ["E01S01-SHOT001"], "reference_input_plan": []}, {"segment_id": "SEG002", "duration_s": 4, "request_duration_s": 4, "shot_ids": []}], "shots": [{"shot_id": "E01S01-SHOT001", "segment_id": "SEG001", "duration_s": 3.5, "timing_events": [{"kind": "visual", "process": "人物推门，光线照亮脸部"}, {"kind": "camera", "process": "缓推后停稳"}]}], "seams": [], "asset_usage_plan": []}
        self.write(self.storyboard_rel, self.storyboard)
        self.write(self.request_rel, {"mode": "T2VA", "inputs": []})
        self.write(self.prompt_rel, "integrated_multimodal_description: A person pushes the door. <d>门开了。</d>\noverall_soundscape: A door creaks.\nnon_diegetic_music: None.\n")

    def write(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data, encoding="utf-8")

    def read(self, rel):
        return json.loads((self.root / rel).read_text(encoding="utf-8"))

    def prepare(self, **kwargs):
        return prepare_segment(self.root, "ep_1", "SEG001", self.request_rel, self.prompt_rel, **kwargs)

    def test_derives_and_freezes_preserving_other_segment(self):
        old = {"segment_id": "SEG002", "episode_segment_index": 2, "duration_s": 4, "output_file": "old.mp4", "status": "accepted", "render_notes": {"keep": True}}
        self.write(self.manifest_rel, {"episode_id": "ep_1", "segments": [old]})
        result = self.prepare()
        manifest = self.read(self.manifest_rel)
        segment = manifest["segments"][0]
        self.assertEqual(manifest["segments"][1], old)
        self.assertEqual(manifest["duration_s"], 8)
        self.assertEqual(segment["shot_plan"], self.storyboard["shots"])
        self.assertEqual(segment["speech_lines"][0]["source_text"], "门开了。")
        self.assertEqual(segment["request_snapshot"]["duration_s"], 4)
        self.assertTrue(segment["request_snapshot"]["workflow"])
        self.assertEqual(segment["compiled_prompt_file"], f"{self.base}/02_分镜/director.md")
        evidence = self.read(result["evidence_file"])
        self.assertEqual(evidence["authorization_bindings"], [authorization_binding(self.root, segment)])
        self.assertEqual(evidence["request_snapshot_sha256"], canonical_sha({"segments": [request_segment_snapshot(segment)]}))
        self.assertEqual(evidence["displayed_parameter_table"]["quantity"], 1)
        for field in ("visual_content", "subject_action", "audio", "camera_and_materials"):
            self.assertIn(evidence["displayed_storyboard_rows"][0][field], evidence["final_parameters_text"])

    def test_context_and_check_only_do_not_create_files(self):
        context = load_segment_context(self.root, "ep_1", "SEG001")
        self.assertNotIn("不应加载的第二段", context["director_segment"])
        self.assertEqual(context["source_files"][0]["revision"], 4)
        result = self.prepare(check_only=True)
        self.assertFalse(result["written"])
        self.assertFalse((self.root / self.manifest_rel).exists())
        self.assertFalse((self.root / result["evidence_file"]).exists())

    def test_context_preserves_global_direction_and_current_episode(self):
        self.write(f"{self.base}/02_分镜/director.md", "## 视觉风格系统\n保持冷蓝光与暖色门缝。\n## 声音设计\n脚步停止后再开口。\n## 场面调度总纲\n门框隔开两人。\n## 节奏设计\n先停顿再揭示。\n转折落在 SEG002，由静到动。\n## 逐段执行区\n| SEG | 导演执行 |\n|---|---|\n| SEG001 | 抬手开门 |\n| SEG002 | 不应加载的第二段 |\n## 核心意象\n门缝逐渐扩大。\n")
        context = load_segment_context(self.root, "ep_1", "SEG001")
        self.assertIn("脚步停止后再开口", context["director_global_contracts"])
        self.assertIn("冷蓝光", context["director_global_contracts"])
        for value in ("门框隔开两人", "先停顿再揭示", "门缝逐渐扩大", "转折落在 SEG002"):
            self.assertIn(value, context["director_global_contracts"])
        self.assertNotIn("第二段", context["director_global_contracts"])
        state = self.read("00_制作控制/制作状态.json")
        state["current_episode"] = "ep_2"
        self.write("00_制作控制/制作状态.json", state)
        with self.assertRaisesRegex(PreparationError, "当前制作集"):
            self.prepare()

    def test_prepared_evidence_authorizes_real_runner_and_shared_lint(self):
        import stamp_confirmation
        from h3_contract import check_authorization
        from video_confirmations import validate_project_confirmations

        result = self.prepare()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(stamp_confirmation.main([
                "--project-root", str(self.root), "--stage", "video", "--video",
                "--episode", "ep_1", "--revision", "2", "--segments", "SEG001",
                "--confirmation-id", "CONF-INTEGRATION", "--evidence-file", result["evidence_file"],
                "--user-message", "按要求生成", "--confirmed-at", "2020-01-01T00:00:00+08:00", "--append"]), 0)
        self.assertEqual(check_authorization(self.root, "SEG001", episode="ep_1")["confirmation_id"], "CONF-INTEGRATION")
        runner_path = Path(__file__).resolve().parents[1] / "tools/video/h3.py"
        spec = importlib.util.spec_from_file_location("h3_integration", runner_path)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        posts = []

        def backend(method, url, token, payload=None, raw=False, **kwargs):
            if method == "POST":
                posts.append(payload)
                return {"code": "Success", "data": {"task_id": "TASK-INTEGRATION"}}
            if raw:
                return b"mock video bytes"
            return {"data": {"status": "SUCCESS", "results": [{"type": "video", "url": "https://example.invalid/take.mp4"}]}}

        def media(command, **kwargs):
            body = json.dumps({"streams": [{"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720}, {"codec_type": "audio", "codec_name": "aac"}], "format": {"duration": "4.0"}})
            return subprocess.CompletedProcess(command, 0, body if command[0] == "ffprobe" else "", "")

        args = ["--project-root", str(self.root), "--episode", "ep_1", "--segment", "SEG001", "--out", "take.mp4"]
        with mock.patch.object(runner, "_http", side_effect=backend), mock.patch.object(runner, "local_settings", return_value={"AUTODL_API_KEY": "test"}), mock.patch.object(runner.subprocess, "run", side_effect=media), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(runner.main(args), 0)
            self.assertEqual(runner.main(args + ["--resume"]), 0)
        self.assertEqual(len(posts), 1)
        self.assertIn("门开了。", posts[0]["prompt"])
        self.assertEqual(self.read(self.manifest_rel)["segments"][0]["status"], "candidate")
        self.assertEqual(validate_project_confirmations(self.root, "ep_1"), [])

    def test_locked_parameter_mismatch_leaves_existing_manifest_unchanged(self):
        self.write(self.manifest_rel, {"segments": []})
        before = (self.root / self.manifest_rel).read_bytes()
        self.write(self.request_rel, {"mode": "T2VA", "duration_s": 5, "inputs": []})
        with self.assertRaisesRegex(PreparationError, "duration_s"):
            self.prepare()
        self.assertEqual((self.root / self.manifest_rel).read_bytes(), before)
        self.assertFalse(list((self.root / self.base / "04_视频片段").glob("生成确认*")))

    def test_required_real_input_missing_is_blocked_before_write(self):
        self.storyboard["segments"][0]["reference_input_plan"] = [{"role": "scene_layout", "planned_source": "SCN001_v01（房间）", "adopt": "房间布局", "exclude": "图中文字"}]
        self.write(self.storyboard_rel, self.storyboard)
        with self.assertRaisesRegex(PreparationError, "缺必需输入"):
            self.prepare()
        self.assertFalse((self.root / self.manifest_rel).exists())

    def test_approved_source_cannot_be_bound_to_a_different_file(self):
        self.write("shared/scene.png", "a real fixture byte sequence")
        self.write("shared/wrong.png", "another byte sequence")
        self.write("shared/03_资产/asset_registry.json", {"assets": [{"asset_id": "SCN001", "version": "v01", "status": "approved", "files": ["shared/scene.png"]}]})
        self.write(self.request_rel, {"mode": "I2VA", "inputs": [{"kind": "image", "path": "shared/wrong.png", "source_ref": "SCN001_v01", "role": "scene_layout"}]})
        self.write(self.prompt_rel, "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\nintegrated_multimodal_description: The door opens. <d>门开了。</d>\noverall_soundscape: Quiet.\nnon_diegetic_music: None.")
        with self.assertRaisesRegex(PreparationError, "不是该 approved 资产"):
            self.prepare()
        self.assertFalse((self.root / self.manifest_rel).exists())

    def test_approved_image_mapping_is_derived_from_actual_input(self):
        self.write("shared/scene.png", "fixture image bytes")
        self.write("shared/03_资产/asset_registry.json", {"assets": [{"asset_id": "SCN001", "version": "v01", "status": "approved", "files": ["shared/scene.png"]}]})
        self.storyboard["segments"][0]["reference_input_plan"] = [{"role": "scene_layout", "planned_source": "SCN001_v01（房间）", "adopt": "房间布局", "exclude": "图中文字"}]
        self.write(self.storyboard_rel, self.storyboard)
        self.write(self.request_rel, {"mode": "I2VA", "inputs": [{"kind": "image", "path": "shared/scene.png", "source_ref": "SCN001_v01", "role": "scene_layout"}]})
        self.write(self.prompt_rel, "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\nintegrated_multimodal_description: The door opens. <d>门开了。</d>\noverall_soundscape: Quiet.\nnon_diegetic_music: None.")
        result = self.prepare()
        reference = result["segment"]["reference_inputs"][0]
        self.assertEqual(reference["source_id"], "SCN001_v01")
        self.assertEqual(reference["adopt"], "房间布局")
        self.assertEqual(result["segment"]["required_reference_roles"], ["scene_layout"])

    def test_existing_generated_segment_needs_explicit_replacement(self):
        initial = self.prepare()
        manifest = self.read(self.manifest_rel)
        old = manifest["segments"][0]
        old.update(output_file="original.mp4", status="accepted", tool_call_id="actual-tool", tool_called_at="2026-11-11T10:00:00+08:00", generation_confirmation_id="confirmed")
        self.write("original.mp4", "original media bytes")
        self.write(self.manifest_rel, manifest)
        old_bytes = (self.root / self.manifest_rel).read_bytes()
        prompt = (self.root / self.prompt_rel).read_text(encoding="utf-8")
        self.write(self.prompt_rel, prompt.replace("A person", "The person"))
        with self.assertRaisesRegex(PreparationError, "已有生成结果"):
            self.prepare()
        self.assertEqual((self.root / self.manifest_rel).read_bytes(), old_bytes)
        self.prepare(replace_generated=True)
        current = self.read(self.manifest_rel)["segments"][0]
        self.assertNotIn("output_file", current)
        self.assertNotIn("status", current)
        self.assertEqual(current["previous_results"][0]["output_file"], "original.mp4")
        self.assertEqual((self.root / "original.mp4").read_text(encoding="utf-8"), "original media bytes")

    def test_reprepare_preserves_snapshot_and_result_versions(self):
        initial = self.prepare()
        manifest = self.read(self.manifest_rel)
        old = manifest["segments"][0]
        old.update(previous_results=[{"output_file": "earlier.mp4"}],
                   output_file="current.mp4", status="accepted", tool_call_id="actual-tool",
                   tool_called_at="2026-11-11T10:00:00+08:00", generation_confirmation_id="confirmed")
        frozen = request_segment_snapshot(old)
        self.write(self.manifest_rel, manifest)
        current = self.prepare()["segment"]
        self.assertEqual(request_segment_snapshot(current), frozen)
        self.assertEqual(current["status"], "accepted")
        self.assertEqual(current["previous_results"], old["previous_results"])
        prompt = (self.root / self.prompt_rel).read_text(encoding="utf-8")
        self.write(self.prompt_rel, prompt.replace("A person", "The person"))
        replaced = self.prepare(replace_generated=True)["segment"]
        self.assertEqual([row["output_file"] for row in replaced["previous_results"]],
                         ["earlier.mp4", "current.mp4"])
        self.assertEqual(self.prepare()["segment"]["previous_results"], replaced["previous_results"])

    def video_input(self, ref, role, path):
        self.write(self.request_rel, {"mode": "Ref2VA", "inputs": [
            {"kind": "video", "path": path, "source_ref": ref, "role": role, "duration_s": 4}]})
        self.write(self.prompt_rel, "subject_definitions: A person from <Video 1>.\nsummary: A door opens.\n"
                   "retention_analysis: Retain the person's identity.\ndetailed_description: The person opens the door. <d>门开了。</d>\n"
                   "overall_soundscape: A door creaks.\nnon_diegetic_music: None.\n")

    def test_existing_segment_video_can_be_edit_source_across_repreparation(self):
        self.prepare()
        manifest = self.read(self.manifest_rel)
        manifest["segments"][0].update(output_file="original.mp4", status="rejected")
        self.write(self.manifest_rel, manifest)
        self.write("original.mp4", "source video bytes")
        self.video_input("SEG001", "source_video_for_edit", "original.mp4")
        result = self.prepare(replace_generated=True)
        self.assertEqual(result["segment"]["tool_mode"], "video_edit")
        self.assertEqual(result["segment"]["video_inputs"][0]["resource_id"], "SEG001")
        self.assertEqual(self.prepare()["segment"]["video_inputs"][0]["file"], "original.mp4")
        self.video_input("SEG001", "source_video_for_edit", "unregistered.mp4")
        self.write("unregistered.mp4", "different bytes")
        with self.assertRaisesRegex(PreparationError, "缺可用的同集既有视频"):
            self.prepare()

    def test_previous_video_reference_requires_real_accepted_earlier_segment(self):
        original = self.storyboard["segments"][0]
        original["segment_id"] = "SEG002"
        self.storyboard["segments"] = [{"segment_id": "SEG001", "duration_s": 4,
                                         "request_duration_s": 4, "shot_ids": []}, original]
        self.storyboard["shots"][0]["segment_id"] = "SEG002"
        self.write(self.storyboard_rel, self.storyboard)
        shot_path = self.root / self.base / "02_分镜/shots.md"
        self.write(f"{self.base}/02_分镜/shots.md", shot_path.read_text(encoding="utf-8").replace("SEG001", "SEG002"))
        self.write("previous.mp4", "accepted video bytes")
        manifest = {"episode_id": "ep_1", "segments": [{"segment_id": "SEG001", "episode_segment_index": 1,
                    "duration_s": 4, "output_file": "previous.mp4", "status": "accepted"}]}
        self.write(self.manifest_rel, manifest)
        self.video_input("SEG001", "previous_segment_video_reference", "previous.mp4")
        def prepare():
            return prepare_segment(self.root, "ep_1", "SEG002", self.request_rel, self.prompt_rel, check_only=True)
        self.assertEqual(prepare()["segment"]["video_inputs"][0]["resource_id"], "SEG001")
        manifest["segments"][0]["status"] = "candidate"
        self.write(self.manifest_rel, manifest)
        with self.assertRaisesRegex(PreparationError, "前段参考需 accepted"):
            prepare()
        manifest["segments"][0].update(segment_id="SEG002", status="accepted")
        self.write(self.manifest_rel, manifest)
        self.video_input("SEG002", "previous_segment_video_reference", "previous.mp4")
        with self.assertRaisesRegex(PreparationError, "缺可用的同集既有视频"):
            prepare()

    def prepare_two_segments(self):
        self.storyboard["segments"][1].update(duration_s=3.5, tail_handle_s=0.5,
                                             shot_ids=["E01S01-SHOT002"])
        second_shot = dict(self.storyboard["shots"][0], shot_id="E01S01-SHOT002", segment_id="SEG002")
        self.storyboard["shots"].append(second_shot)
        self.write(self.storyboard_rel, self.storyboard)
        shot_path = self.root / self.base / "02_分镜/shots.md"
        text = shot_path.read_text(encoding="utf-8")
        last = text.splitlines()[-1].replace("SEG001", "SEG002").replace("SHOT001", "SHOT002")
        self.write(f"{self.base}/02_分镜/shots.md", text + last + "\n")
        self.prepare()
        prepare_segment(self.root, "ep_1", "SEG002", self.request_rel, self.prompt_rel)

    def test_combined_evidence_authorizes_two_ready_segments_and_detects_staleness(self):
        import stamp_confirmation
        from h3_contract import check_authorization
        self.prepare_two_segments()
        result = combine_evidence(self.root, "ep_1", ["SEG001", "SEG002"])
        evidence = self.read(result["evidence_file"])
        self.assertEqual(evidence["displayed_parameter_table"]["quantity"], 2)
        self.assertEqual(evidence["displayed_parameter_table"]["total_duration"], "8秒")
        self.assertEqual([row["segment_id"] for row in evidence["displayed_storyboard_rows"]], ["SEG001", "SEG002"])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(stamp_confirmation.main([
                "--project-root", str(self.root), "--stage", "video", "--video", "--episode", "ep_1",
                "--revision", "2", "--segments", "SEG001,SEG002", "--confirmation-id", "CONF-BATCH",
                "--evidence-file", result["evidence_file"], "--user-message", "两段一起生成", "--append"]), 0)
        for sid in ("SEG001", "SEG002"):
            self.assertEqual(check_authorization(self.root, sid, episode="ep_1")["confirmation_id"], "CONF-BATCH")
        with self.assertRaisesRegex(PreparationError, "顺序连续"):
            combine_evidence(self.root, "ep_1", ["SEG002", "SEG001"])
        self.write(self.prompt_rel, (self.root / self.prompt_rel).read_text(encoding="utf-8") + "Changed.")
        with self.assertRaisesRegex(PreparationError, "素材已变"):
            combine_evidence(self.root, "ep_1", ["SEG001", "SEG002"])

    def test_combined_evidence_blocks_dependency_on_same_batch_new_result(self):
        self.prepare_two_segments()
        manifest = self.read(self.manifest_rel)
        manifest["segments"][1]["incoming_seam"] = {"seam_mode": "continuous", "from_segment": "SEG001", "to_segment": "SEG002"}
        self.write(self.manifest_rel, manifest)
        with self.assertRaisesRegex(PreparationError, "不能合批授权"):
            combine_evidence(self.root, "ep_1", ["SEG001", "SEG002"])
        self.assertFalse(list((self.root / self.base / "04_视频片段").glob("*_batch.json")))


if __name__ == "__main__":
    unittest.main()
