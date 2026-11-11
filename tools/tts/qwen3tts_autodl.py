# -*- coding: utf-8 -*-
"""qwen3tts_autodl.py — 经 SSH 在 AutoDL 实例上用 N06-Qwen3TTS「音频创造」工作流
批量生成角色 TTS 参考音（无需参考音频，音色由自然语言描述）。

流水线环节：S7 资产生产——07-assets/tts/<CHAR>_tts.wav 声音参考。

原理（实测，Zealman 镜像 v9.33）：
  1. paramiko SSH 连实例（ComfyUI 跑在 127.0.0.1:6006，面板 6008）；
  2. 上传内嵌 runner：手搭 N06 API 格式 prompt（TDQwen3TTSModelLoader →
     TDQwen3TTSVoiceDesign ← CR Prompt Text×2（台词/音色描述）→ SaveAudio），
     POST /prompt 入队，轮询 /history/{prompt_id}；
  3. SFTP 拉回 flac，本机 ffmpeg 转 wav（44.1kHz 单声道 pcm_s16le）。

依赖：paramiko（pip install paramiko）＋系统 PATH 有 ffmpeg。

用法：
  # 单角色
  python tools/tts/qwen3tts_autodl.py --role SHENYAN \
      --instruct "28岁成年男性，低男中音，语速缓慢沉稳……" \
      --text "台词一。\n台词二。" --out 07-assets/tts/SHENYAN_tts.wav

  # 多角色（JSON：role/instruct/text/out；每项可选 language 覆盖 --language，缺省 Auto）
  python tools/tts/qwen3tts_autodl.py --roles-file roles.json

连接配置（密码不落盘、不写进 skill）：环境变量或 --config <KEY=VALUE 文件>
  AUTODL_SSH_HOST / AUTODL_SSH_PORT(默认22) / AUTODL_SSH_USER(默认root)
  / AUTODL_SSH_PASSWORD
  AutoDL 实例重装后 host/port 会变，以控制台「SSH 登录」为准。
"""
import argparse, json, os, sys, subprocess, tempfile
import posixpath
import re
import shlex
import uuid

LANGUAGES = ("Auto", "Chinese", "English", "Japanese", "Korean", "German",
             "French", "Russian", "Portuguese", "Spanish", "Italian")

REMOTE_RUNNER = r'''
import json, sys, time, urllib.request, uuid

COMFY = "http://127.0.0.1:6006"

def build_prompt(text, instruct, prefix, language="Auto"):
    return {
        "15": {"class_type": "TDQwen3TTSModelLoader", "inputs": {
            "model_path": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            "precision": "bf16", "device": "cuda",
            "attn_implementation": "flash_attention_2",
            "auto_download": False, "download_source": "ModelScope"}},
        "23": {"class_type": "CR Prompt Text", "inputs": {"prompt": text}},
        "25": {"class_type": "CR Prompt Text", "inputs": {"prompt": instruct}},
        "24": {"class_type": "TDQwen3TTSVoiceDesign", "inputs": {
            "model": ["15", 0], "text": ["23", 0], "instruct": ["25", 0],
            "language": language}},
        "21": {"class_type": "SaveAudio", "inputs": {
            "audio": ["24", 0], "filename_prefix": "audio/" + prefix}},
    }

def post(url, payload):
    req = urllib.request.Request(url, method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8"))
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def run(text, instruct, prefix, language="Auto"):
    resp = post(COMFY + "/prompt",
                {"prompt": build_prompt(text, instruct, prefix, language),
                 "client_id": str(uuid.uuid4())})
    pid = resp.get("prompt_id")
    if not pid:
        print("SUBMIT FAIL " + json.dumps(resp, ensure_ascii=False)[:500])
        return 1
    print("[queued] " + pid, flush=True)
    for _ in range(180):
        time.sleep(5)
        item = get(COMFY + "/history/" + pid).get(pid)
        if not item:
            continue
        status = item.get("status") or {}
        if status.get("completed"):
            outs = item.get("outputs", {})
            audio = outs.get("21", {}).get("audio", [])
            if not audio:
                print("[error] 本次任务未返回音频文件")
                return 1
            print("[result] " + json.dumps(audio[0], ensure_ascii=False), flush=True)
            return 0
        if status.get("status_str") == "error":
            print("[error] " + json.dumps(item, ensure_ascii=False)[:800])
            return 1
    print("[timeout]")
    return 1

if __name__ == "__main__":
    job = json.load(open(sys.argv[1], encoding="utf-8"))
    sys.exit(run(job["text"], job["instruct"], job["prefix"], job["language"]))
'''


def load_config(path):
    cfg = {}
    if path:
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    for k in ("AUTODL_SSH_HOST", "AUTODL_SSH_PORT", "AUTODL_SSH_USER",
              "AUTODL_SSH_PASSWORD"):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    missing = [k for k in ("AUTODL_SSH_HOST", "AUTODL_SSH_PASSWORD")
               if not cfg.get(k)]
    if missing:
        sys.exit("缺连接配置 %s（环境变量或 --config 文件）" % ",".join(missing))
    cfg["AUTODL_SSH_PORT"] = cfg.get("AUTODL_SSH_PORT") or "22"
    cfg["AUTODL_SSH_USER"] = cfg.get("AUTODL_SSH_USER") or "root"
    return cfg


def ssh_client(cfg):
    try:
        import paramiko
    except ImportError:
        sys.exit("缺少依赖 paramiko，请先运行: pip install paramiko")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(cfg["AUTODL_SSH_HOST"], port=int(cfg["AUTODL_SSH_PORT"]),
              username=cfg["AUTODL_SSH_USER"],
              password=cfg["AUTODL_SSH_PASSWORD"], timeout=30)
    return c


def to_wav(ffmpeg, src, dst):
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", src,
                    "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", dst],
                   check=True)


def validate_jobs(jobs, language="Auto"):
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("roles-file 必须是非空数组")
    for job in jobs:
        if not isinstance(job, dict) or any(not isinstance(job.get(key), str) or not job[key].strip()
                                            for key in ("role", "instruct", "text", "out")):
            raise ValueError("每个角色需非空 role/instruct/text/out")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", job["role"]):
            raise ValueError("role 只允许英文字母、数字、下划线和连字符")
        job.setdefault("language", language)
        if job["language"] not in LANGUAGES:
            raise ValueError("language 不在 Qwen3TTS 支持范围；请使用 Auto 或受支持语言")
    return jobs


def result_audio_path(output):
    """只采用本次 prompt_id 返回的 SaveAudio 文件，不猜测最新文件。"""
    results = [json.loads(line[len("[result] "):]) for line in output.splitlines()
               if line.startswith("[result] ")]
    if len(results) != 1 or not isinstance(results[0], dict):
        raise ValueError("本次任务未返回唯一音频结果")
    result = results[0]
    filename, subfolder = result.get("filename"), result.get("subfolder", "")
    if result.get("type") != "output" or not isinstance(filename, str) or not isinstance(subfolder, str):
        raise ValueError("本次音频结果路径无效")
    root = "/root/ComfyUI/output"
    path = posixpath.normpath(posixpath.join(root, subfolder, filename))
    if not path.startswith(root + "/") or not filename:
        raise ValueError("本次音频结果越出 ComfyUI 输出目录")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="AutoDL N06-Qwen3TTS 角色参考音生成")
    ap.add_argument("--config", help="KEY=VALUE 连接配置文件")
    ap.add_argument("--role"); ap.add_argument("--instruct"); ap.add_argument("--text")
    ap.add_argument("--out")
    ap.add_argument("--language", choices=LANGUAGES, default="Auto",
                    help="样音语言；默认 Auto 按台词识别，按项目 video_language 选择受支持语言")
    ap.add_argument("--roles-file", help='[{"role","instruct","text","out","language"(可选)},...]')
    ap.add_argument("--ffmpeg", default="ffmpeg")
    args = ap.parse_args(argv)

    jobs = []
    if args.roles_file:
        jobs = json.load(open(args.roles_file, encoding="utf-8-sig"))
    elif args.role and args.instruct and args.text and args.out:
        jobs = [{"role": args.role, "instruct": args.instruct,
                 "text": args.text, "out": args.out}]
    else:
        sys.exit("给 --role/--instruct/--text/--out 或 --roles-file")
    jobs = validate_jobs(jobs, args.language)

    cfg = load_config(args.config)
    c = ssh_client(cfg)
    failed = 0
    remote_files = []
    sftp = None
    try:
        sftp = c.open_sftp()
        run_id = uuid.uuid4().hex
        runner_path = "/tmp/qwen3tts_runner_%s.py" % run_id
        remote_files.append(runner_path)
        with sftp.open(runner_path, "w") as f:
            f.write(REMOTE_RUNNER)
        for index, job in enumerate(jobs):
            role = job["role"]
            print("[gen] %s ..." % role, flush=True)
            job_path = "/tmp/qwen3tts_job_%s_%s.json" % (run_id, index)
            remote_files.append(job_path)
            with sftp.open(job_path, "w") as f:
                json.dump({"text": job["text"], "instruct": job["instruct"],
                           "prefix": role + "_tts_" + run_id,
                           "language": job["language"]}, f, ensure_ascii=False)
            stdin, stdout, stderr = c.exec_command(
                "/root/miniconda3/bin/python " + shlex.quote(runner_path) + " " + shlex.quote(job_path),
                timeout=1200)
            out = stdout.read().decode("utf-8", "replace")
            err = stderr.read().decode("utf-8", "replace")
            print(out, end="")
            if err.strip():
                print("ERR:", err[:500])
            try:
                remote_flac = result_audio_path(out)
            except ValueError as exc:
                print("[fail] %s: %s" % (role, exc))
                failed += 1
                continue
            os.makedirs(os.path.dirname(os.path.abspath(job["out"])),
                        exist_ok=True)
            with tempfile.NamedTemporaryFile(suffix=".flac",
                                             delete=False) as tf:
                tmp = tf.name
            try:
                sftp.get(remote_flac, tmp)
                to_wav(args.ffmpeg, tmp, job["out"])
            except (OSError, subprocess.CalledProcessError) as exc:
                print("[fail] %s 下载或转码失败: %s" % (role, exc))
                failed += 1
                continue
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            print("[ok] %s -> %s" % (role, job["out"]), flush=True)
    finally:
        if sftp is not None:
            for remote_file in remote_files:
                try:
                    sftp.remove(remote_file)
                except OSError:
                    pass
            sftp.close()
        c.close()
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print("qwen3tts: %s" % exc, file=sys.stderr)
        sys.exit(1)
