"""媒体工具离线回归；真实 ffmpeg 只处理临时合成素材。"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tts = load("tts_tool", "tools/tts/qwen3tts_autodl.py")
ffmpeg = load("ffmpeg_tool", "tools/video/ffmpeg_tool.py")


class TtsTests(unittest.TestCase):
    def job(self):
        return {"role": "VOICE001", "text": "Hello.", "instruct": "A calm voice.", "out": "voice.wav"}

    def test_requested_language_reaches_actual_remote_graph(self):
        remote = {"__name__": "test_runner"}
        exec(tts.REMOTE_RUNNER, remote)
        for language in ("Auto", "English", "Japanese"):
            job = tts.validate_jobs([self.job()], language)[0]
            graph = remote["build_prompt"](job["text"], job["instruct"], "unique", job["language"])
            self.assertEqual(graph["24"]["inputs"]["language"], language)
        job = dict(self.job(), language="Korean")
        self.assertEqual(tts.validate_jobs([job], "English")[0]["language"], "Korean")

    def test_audio_path_uses_exact_returned_file_and_rejects_invalid_results(self):
        output = '[queued] task-id\n[result] ' + json.dumps(
            {"filename": "VOICE001_unique_0001.flac", "subfolder": "audio", "type": "output"})
        self.assertEqual(tts.result_audio_path(output), "/root/ComfyUI/output/audio/VOICE001_unique_0001.flac")
        for output in ("[done] {}", '[result] {"filename":"../../outside.flac","type":"output"}',
                       '[result] {"filename":"x.flac","type":"temp"}'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                tts.result_audio_path(output)

    def test_role_cannot_be_remote_shell_or_path(self):
        for role in ("../VOICE", "VOICE; ls", "VOICE$(id)"):
            with self.subTest(role=role), self.assertRaises(ValueError):
                tts.validate_jobs([dict(self.job(), role=role)])

    def test_failed_generation_returns_nonzero_and_never_downloads_stale_audio(self):
        client = mock.MagicMock()
        output = mock.Mock()
        output.read.return_value = b"[error] generation failed\n"
        errors = mock.Mock()
        errors.read.return_value = b""
        client.exec_command.return_value = (None, output, errors)
        with mock.patch.object(tts, "load_config", return_value={}), mock.patch.object(
                tts, "ssh_client", return_value=client), contextlib.redirect_stdout(io.StringIO()):
            code = tts.main(["--role", "VOICE001", "--instruct", "Calm", "--text", "Hello", "--out", "voice.wav"])
        self.assertEqual(code, 1)
        client.open_sftp.return_value.get.assert_not_called()
        self.assertEqual(client.exec_command.call_count, 1)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires ffmpeg/ffprobe")
class ConcatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def clip(self, name, stereo=False):
        path = self.root / name
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=blue:s=64x64:r=24:d=0.5"]
        if stereo:
            cmd += ["-f", "lavfi", "-i", "aevalsrc=0|0.5*sin(2*PI*440*t):s=48000:d=0.5:c=stereo"]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
        if stereo:
            cmd += ["-c:a", "aac"]
        subprocess.run(cmd + [str(path)], check=True, capture_output=True)
        return str(path)

    def test_single_silent_clip_and_mixed_audio_sequence(self):
        silent, stereo = self.clip("silent.mp4"), self.clip("stereo.mp4", stereo=True)
        single = str(self.root / "single.mp4")
        ffmpeg.concat(single, [silent])
        single_info = ffmpeg._concat_info(single)
        self.assertTrue(single_info["has_audio"])
        self.assertAlmostEqual(single_info["duration_s"], 0.5, delta=0.06)
        joined = str(self.root / "joined.mp4")
        ffmpeg.concat(joined, [silent, stereo])
        info = ffmpeg._concat_info(joined)
        self.assertAlmostEqual(info["duration_s"], 1.0, delta=0.06)
        # 左路原本静音、右路有声；若把左右都复制成 c0，此处将测不到右路能量。
        decoded = subprocess.run(["ffmpeg", "-v", "error", "-i", joined, "-ss", "0.6", "-t", "0.2",
                                  "-map", "0:a:0", "-f", "f32le", "-acodec", "pcm_f32le", "-"],
                                 check=True, capture_output=True).stdout
        import array
        samples = array.array("f", decoded)
        self.assertGreater(sum(abs(value) for value in samples[1::2]), 10)
        self.assertLess(sum(abs(value) for value in samples[::2]), 1)

    def test_probe_json_is_one_parseable_document(self):
        clip = self.clip("probe.mp4")
        result = subprocess.run([__import__("sys").executable, str(ROOT / "tools/video/ffmpeg_tool.py"),
                                 "probe", clip, "--json"], check=True, capture_output=True,
                                text=True, encoding="utf-8")
        self.assertIn("streams", json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
