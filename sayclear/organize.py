from __future__ import annotations

import json
import urllib.error
import urllib.request

from .env import ORGANIZE_BASE, ORGANIZE_KEY, ORGANIZE_MODEL
from .prompt import ORGANIZE_SYSTEM


class OrganizeError(Exception):
    pass


def organize(transcript: str) -> str:
    if not ORGANIZE_KEY:
        raise OrganizeError("未配置整理密钥（.env 里的 CUN_AI_API_KEY）")
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
    req = urllib.request.Request(
        ORGANIZE_BASE + "/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + ORGANIZE_KEY,
            "Content-Type": "application/json",
            "User-Agent": "curl/8.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise OrganizeError(exc.read().decode("utf-8", errors="replace")[:400]) from exc
    except OSError as exc:
        raise OrganizeError(str(exc)) from exc
    choices = payload.get("choices") or []
    if not choices:
        raise OrganizeError("整理没有返回内容")
    text = (choices[0].get("message") or {}).get("content") or ""
    return text.strip()


def looks_usable(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    prefixes = ("我理解你的需求是", "以下是给你的 Prompt", "以下是 Prompt")
    for prefix in prefixes:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix) :].lstrip("：: \n")
    return bool(stripped.strip())
