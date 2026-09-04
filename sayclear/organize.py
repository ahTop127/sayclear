from __future__ import annotations

import socket
import ssl
from urllib.parse import urlparse

import requests

from .env import ORGANIZE_BASE, ORGANIZE_KEY, ORGANIZE_MODEL
from .prompt import ORGANIZE_SYSTEM


class OrganizeError(Exception):
    pass


_http = requests.Session()
_http.headers.update({"User-Agent": "curl/8.0"})


def warmup_organize() -> None:
    try:
        parsed = urlparse(ORGANIZE_BASE)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            return
        sock = socket.create_connection((host, port), timeout=3)
        if parsed.scheme == "https":
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(sock, server_hostname=host)
        sock.close()
    except Exception as exc:
        print("organize warmup:", exc, flush=True)


_SHORT_REPLIES = {
    "好的",
    "好",
    "是的",
    "是",
    "对",
    "对的",
    "对对",
    "对对对",
    "行",
    "可以",
    "没问题",
    "嗯",
    "嗯嗯",
    "ok",
    "okay",
    "yes",
    "yeah",
}


def short_reply_passthrough(transcript: str) -> str | None:
    raw = transcript.strip().strip("。.!！，,、 ")
    if not raw:
        return None
    if raw.lower() in _SHORT_REPLIES or raw in _SHORT_REPLIES:
        return raw
    return None


def organize(transcript: str) -> str:
    if not ORGANIZE_KEY:
        raise OrganizeError("未配置整理密钥（.env 里的 CUN_AI_API_KEY）")
    passthrough = short_reply_passthrough(transcript)
    body = {
        "model": ORGANIZE_MODEL,
        "temperature": 0.3,
        "max_tokens": 1024,
        "thinking": {"type": "disabled"},
        "messages": [
            {"role": "system", "content": ORGANIZE_SYSTEM},
            {"role": "user", "content": transcript},
        ],
    }
    try:
        resp = _http.post(
            ORGANIZE_BASE + "/chat/completions",
            json=body,
            headers={
                "Authorization": "Bearer " + ORGANIZE_KEY,
                "Content-Type": "application/json",
            },
            timeout=60,
        )
    except requests.RequestException as exc:
        raise OrganizeError(str(exc)) from exc
    if resp.status_code >= 400:
        raise OrganizeError(resp.text[:400])
    payload = resp.json()
    choices = payload.get("choices") or []
    if not choices:
        if passthrough:
            return passthrough
        raise OrganizeError("整理没有返回内容")
    text = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not text:
        if passthrough:
            return passthrough
        raise OrganizeError("整理没有返回内容")
    return text


def looks_usable(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    prefixes = ("我理解你的需求是", "以下是给你的 Prompt", "以下是 Prompt")
    for prefix in prefixes:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix) :].lstrip("：: \n")
    return bool(stripped.strip())
