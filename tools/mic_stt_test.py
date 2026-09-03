#!/usr/bin/env python3
"""最小麦克风识别测试：浏览器录音 → Google Speech-to-Text V2。"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "sayclear")
HOST = "127.0.0.1"
PORT = 8766
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SayClear 识别测试</title>
  <style>
    body { font-family: -apple-system, sans-serif; max-width: 40rem; margin: 3rem auto; padding: 0 1.5rem; color: #111; }
    h1 { font-size: 1.25rem; }
    p { color: #444; line-height: 1.5; }
    button { font-size: 1rem; padding: .6rem 1.2rem; border-radius: 999px; border: 0; cursor: pointer; }
    #rec { background: #111; color: #fff; }
    #rec.live { background: #c0392b; }
    #out { white-space: pre-wrap; background: #f4f4f4; padding: 1rem; border-radius: 12px; min-height: 4rem; }
    .hint { font-size: .875rem; color: #888; }
  </style>
</head>
<body>
  <h1>说一段话，看识别结果</h1>
  <p>这是最小测试：只做语音转文字，不做整理。</p>
  <p>
    <button id="rec">开始录音</button>
  </p>
  <p class="hint" id="status">点开始后对着麦克风说话，再点停止。</p>
  <pre id="out">（还没有结果）</pre>
  <script>
    const rec = document.getElementById("rec");
    const status = document.getElementById("status");
    const out = document.getElementById("out");
    let recorder = null;
    let chunks = [];
    let stream = null;

    rec.onclick = async () => {
      if (recorder && recorder.state === "recording") {
        recorder.stop();
        rec.textContent = "开始录音";
        rec.classList.remove("live");
        return;
      }
      out.textContent = "（录音中…）";
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks = [];
      recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        status.textContent = "正在识别…";
        rec.disabled = true;
        try {
          const res = await fetch("/recognize", { method: "POST", body: blob });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || res.statusText);
          out.textContent = data.transcript || "（没有听出内容，请再试一次）";
          status.textContent = data.note || "识别完成。可以再录一段。";
        } catch (err) {
          out.textContent = "失败：" + err.message;
          status.textContent = "请检查麦克风权限，或看终端报错。";
        }
        rec.disabled = false;
      };
      recorder.start();
      rec.textContent = "停止并识别";
      rec.classList.add("live");
      status.textContent = "正在录音，说完后点停止。";
    };
  </script>
</body>
</html>
"""


def access_token() -> str:
    import google.auth
    from google.auth.transport.requests import Request

    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(Request())
    return creds.token


def to_wav_16k(raw: bytes) -> Path:
    src = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
    src.write(raw)
    src.close()
    dst = Path(src.name).with_suffix(".wav")
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-i",
            src.name,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(dst),
        ],
        check=True,
        capture_output=True,
    )
    Path(src.name).unlink(missing_ok=True)
    return dst


def recognize_wav(wav_path: Path) -> tuple[str, str]:
    content = wav_path.read_bytes()
    import base64

    b64 = base64.b64encode(content).decode("ascii")
    attempts = [
        {
            "url": f"https://us-speech.googleapis.com/v2/projects/{PROJECT_ID}/locations/us/recognizers/_:recognize",
            "body": {
                "config": {
                    "autoDecodingConfig": {},
                    "languageCodes": ["cmn-Hans-CN", "en-US"],
                    "model": "chirp_3",
                },
                "content": b64,
            },
            "note": "Chirp 3 / 中英",
        },
        {
            "url": f"https://speech.googleapis.com/v2/projects/{PROJECT_ID}/locations/global/recognizers/_:recognize",
            "body": {
                "config": {
                    "autoDecodingConfig": {},
                    "languageCodes": ["cmn-Hans-CN", "en-US"],
                    "model": "long",
                },
                "content": b64,
            },
            "note": "global / long 回退",
        },
    ]
    token = access_token()
    last_error = "未知错误"
    for attempt in attempts:
        req = urllib.request.Request(
            attempt["url"],
            data=json.dumps(attempt["body"]).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
                "x-goog-user-project": PROJECT_ID,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc.read().decode("utf-8", errors="replace")[:800]
            continue
        texts = []
        for result in payload.get("results") or []:
            alts = result.get("alternatives") or []
            if alts and alts[0].get("transcript"):
                texts.append(alts[0]["transcript"])
        return " ".join(texts).strip(), attempt["note"]
    raise RuntimeError(last_error)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print("[mic-stt]", fmt % args)

    def do_GET(self) -> None:
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        data = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if self.path != "/recognize":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        wav = None
        try:
            wav = to_wav_16k(raw)
            transcript, note = recognize_wav(wav)
            body = json.dumps(
                {"transcript": transcript, "note": f"识别完成（{note}）"},
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(200)
        except Exception as exc:
            body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
        finally:
            if wav:
                wav.unlink(missing_ok=True)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", PROJECT_ID)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"打开 http://{HOST}:{PORT}/ 后点「开始录音」说话。")
    print("Ctrl+C 结束。")
    server.serve_forever()


if __name__ == "__main__":
    main()
