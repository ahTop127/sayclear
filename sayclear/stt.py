from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from .env import PROJECT_ID


class SpeechError(Exception):
    pass


def _token() -> str:
    import google.auth
    from google.auth.transport.requests import Request

    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(Request())
    if not creds.token:
        raise SpeechError("无法取得 Google 登录凭证")
    return creds.token


def transcribe(wav_bytes: bytes) -> str:
    b64 = base64.b64encode(wav_bytes).decode("ascii")
    attempts = [
        {
            "url": (
                f"https://us-speech.googleapis.com/v2/projects/{PROJECT_ID}"
                "/locations/us/recognizers/_:recognize"
            ),
            "body": {
                "config": {
                    "autoDecodingConfig": {},
                    "languageCodes": ["cmn-Hans-CN", "en-US"],
                    "model": "chirp_3",
                },
                "content": b64,
            },
        },
        {
            "url": (
                f"https://speech.googleapis.com/v2/projects/{PROJECT_ID}"
                "/locations/global/recognizers/_:recognize"
            ),
            "body": {
                "config": {
                    "autoDecodingConfig": {},
                    "languageCodes": ["cmn-Hans-CN", "en-US"],
                    "model": "long",
                },
                "content": b64,
            },
        },
    ]
    token = _token()
    last = "识别失败"
    for attempt in attempts:
        req = urllib.request.Request(
            attempt["url"],
            data=json.dumps(attempt["body"]).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
                "x-goog-user-project": PROJECT_ID,
                "User-Agent": "curl/8.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last = exc.read().decode("utf-8", errors="replace")[:400]
            continue
        except OSError as exc:
            last = str(exc)
            continue
        texts = []
        for result in payload.get("results") or []:
            alts = result.get("alternatives") or []
            if alts and alts[0].get("transcript"):
                texts.append(alts[0]["transcript"].strip())
        text = " ".join(texts).strip()
        if text:
            return text
        last = "没有听出内容"
    raise SpeechError(last)
