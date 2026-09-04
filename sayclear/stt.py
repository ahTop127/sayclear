from __future__ import annotations

import base64
import io
import threading
import time
import wave
from typing import Optional

import requests

from .env import PROJECT_ID
from .recorder import SAMPLE_RATE


class SpeechError(Exception):
    pass


_token: Optional[str] = None
_token_exp = 0.0
_http = requests.Session()
_http.headers.update({"User-Agent": "curl/8.0"})


def _token_value() -> str:
    global _token, _token_exp
    now = time.time()
    if _token and now < _token_exp - 60:
        return _token
    import google.auth
    from google.auth.transport.requests import Request

    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(Request())
    if not creds.token:
        raise SpeechError("无法取得 Google 登录凭证")
    _token = creds.token
    expiry = getattr(creds, "expiry", None)
    _token_exp = expiry.timestamp() if expiry else now + 3000
    return _token


def prefetch_token() -> None:
    try:
        _token_value()
    except Exception as exc:
        print("stt warmup:", exc, flush=True)


def pcm_to_wav(pcm: bytes, rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm)
    return buf.getvalue()


def _parse_results(payload: dict) -> str:
    texts = []
    for result in payload.get("results") or []:
        alts = result.get("alternatives") or []
        if alts and alts[0].get("transcript"):
            texts.append(alts[0]["transcript"].strip())
    return " ".join(texts).strip()


def transcribe_pcm(pcm: bytes) -> str:
    return transcribe(pcm_to_wav(pcm))


def transcribe(wav_bytes: bytes) -> str:
    b64 = base64.b64encode(wav_bytes).decode("ascii")
    url = (
        f"https://us-speech.googleapis.com/v2/projects/{PROJECT_ID}"
        "/locations/us/recognizers/_:recognize"
    )
    body = {
        "config": {
            "autoDecodingConfig": {},
            "languageCodes": ["cmn-Hans-CN", "en-US"],
            "model": "chirp_3",
        },
        "content": b64,
    }
    token = _token_value()
    try:
        resp = _http.post(
            url,
            json=body,
            headers={
                "Authorization": "Bearer " + token,
                "x-goog-user-project": PROJECT_ID,
            },
            timeout=60,
        )
    except requests.RequestException as exc:
        raise SpeechError(str(exc)) from exc
    if resp.status_code >= 400:
        raise SpeechError(resp.text[:400])
    text = _parse_results(resp.json())
    if not text:
        raise SpeechError("没有听出内容")
    return text


class LiveRecognizer:
    """本机 gRPC 流式连不上（握手失败）。录音中只缓存 PCM，结束立刻走 REST。"""

    def __init__(self) -> None:
        self._pcm = bytearray()
        self._lock = threading.Lock()
        self._active = False
        self._mode = "idle"

    @property
    def mode(self) -> str:
        return self._mode

    def start(self) -> None:
        with self._lock:
            self._pcm = bytearray()
        self._active = True
        self._mode = "buffer"

    def push(self, pcm: bytes) -> None:
        if not self._active or not pcm:
            return
        with self._lock:
            self._pcm.extend(pcm)

    def cancel(self) -> None:
        self._active = False
        with self._lock:
            self._pcm = bytearray()
        self._mode = "idle"

    def finish(self) -> str:
        self._active = False
        with self._lock:
            pcm = bytes(self._pcm)
        self._mode = "rest"
        if len(pcm) < SAMPLE_RATE:
            raise SpeechError("没有听出内容")
        text = transcribe_pcm(pcm)
        self._mode = "done"
        return text
