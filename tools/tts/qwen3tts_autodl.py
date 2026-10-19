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

  # 多角色（JSON 文件：[{"role":..,"instruct":..,"text":..,"out":..}, ...]）
  python tools/tts/qwen3tts_autodl.py --roles-file roles.json

连接配置（密码不落盘、不写进 skill）：环境变量或 --config <KEY=VALUE 文件>
  AUTODL_SSH_HOST / AUTODL_SSH_PORT(默认22) / AUTODL_SSH_USER(默认root)
  / AUTODL_SSH_PASSWORD
  AutoDL 实例重装后 host/port 会变，以控制台「SSH 登录」为准。
"""
import argparse, json, os, sys, subprocess, tempfile, time

REMOTE_RUNNER = r'''
import json, sys, time, urllib.request, uuid

COMFY = "http://127.0.0.1:6006"

def build_prompt(text, instruct, prefix):
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
            "language": "Chinese"}},
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

def run(text, instruct, prefix):
    resp = post(COMFY + "/prompt",
                {"prompt": build_prompt(text, instruct, prefix),
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
            print("[done] " + json.dumps(outs, ensure_ascii=False)[:400])
            return 0
        if status.get("status_str") == "error":
            print("[error] " + json.dumps(item, ensure_ascii=False)[:800])
            return 1
    print("[timeout]")
    return 1

if __name__ == "__main__":
    job = json.load(open(sys.argv[1], encoding="utf-8"))
    sys.exit(run(job["text"], job["instruct"], job["prefix"]))
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
    cfg.setdefault("AUTODL_SSH_PORT", "22")
    cfg.setdefault("AUTODL_SSH_USER", "root")
    return cfg


def ssh_client(cfg):
    import paramiko
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


def main():
    ap = argparse.ArgumentParser(description="AutoDL N06-Qwen3TTS 角色参考音生成")
    ap.add_argument("--config", help="KEY=VALUE 连接配置文件")
    ap.add_argument("--role"); ap.add_argument("--instruct"); ap.add_argument("--text")
    ap.add_argument("--out")
    ap.add_argument("--roles-file", help='[{"role","instruct","text","out"},...]')
    ap.add_argument("--ffmpeg", default="ffmpeg")
    args = ap.parse_args()

    jobs = []
    if args.roles_file:
        jobs = json.load(open(args.roles_file, encoding="utf-8"))
    elif args.role and args.instruct and args.text and args.out:
        jobs = [{"role": args.role, "instruct": args.instruct,
                 "text": args.text, "out": args.out}]
    else:
        sys.exit("给 --role/--instruct/--text/--out 或 --roles-file")

    cfg = load_config(args.config)
    c = ssh_client(cfg)
    try:
        sftp = c.open_sftp()
        with sftp.open("/tmp/qwen3tts_runner.py", "w") as f:
            f.write(REMOTE_RUNNER)
        for job in jobs:
            role = job["role"]
            print("[gen] %s ..." % role, flush=True)
            job_path = "/tmp/qwen3tts_job_%s.json" % role
            with sftp.open(job_path, "w") as f:
                json.dump({"text": job["text"], "instruct": job["instruct"],
                           "prefix": role + "_tts"}, f, ensure_ascii=False)
            stdin, stdout, stderr = c.exec_command(
                "/root/miniconda3/bin/python /tmp/qwen3tts_runner.py " + job_path,
                timeout=1200)
            out = stdout.read().decode("utf-8", "replace")
            err = stderr.read().decode("utf-8", "replace")
            print(out, end="")
            if err.strip():
                print("ERR:", err[:500])
            if "[done]" not in out:
                print("[fail] %s 未成功，跳过下载" % role)
                continue
            ls_in, ls_out, ls_err = c.exec_command(
                "ls -t /root/ComfyUI/output/audio/%s_tts_*.flac | head -1" % role,
                timeout=30)
            remote_flac = ls_out.read().decode("utf-8", "replace").strip()
            if not remote_flac:
                print("[fail] %s 远端未找到产物 flac，跳过下载" % role)
                continue
            os.makedirs(os.path.dirname(os.path.abspath(job["out"])),
                        exist_ok=True)
            with tempfile.NamedTemporaryFile(suffix=".flac",
                                             delete=False) as tf:
                tmp = tf.name
            sftp.get(remote_flac, tmp)
            to_wav(args.ffmpeg, tmp, job["out"])
            os.unlink(tmp)
            print("[ok] %s -> %s" % (role, job["out"]), flush=True)
        sftp.close()
    finally:
        c.close()


if __name__ == "__main__":
    main()
