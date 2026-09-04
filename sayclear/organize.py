from __future__ import annotations

import re
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


# 整段都是垫话时不当成正文。短句是否确认语由模型判断；这里只在模型空返回时兜底。
_FILLER_ONLY = re.compile(
    r"^(嗯+|啊+|呃+|额+|唔+|哦+|喔+|哈+|那个+|就是+|你知道吧)+$",
    re.IGNORECASE,
)


def short_reply_passthrough(transcript: str) -> str | None:
    raw = transcript.strip().strip("。.!！，,、 ")
    if not raw:
        return None
    compact = re.sub(r"[\s，,。.!！、？?]+", "", raw)
    if not compact or _FILLER_ONLY.match(compact):
        return None
    if len(compact) <= 12:
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
        # V4 默认开思考；整理只要快速出正文。
        "thinking": {"type": "disabled"},
        "reasoning_effort": "none",
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
