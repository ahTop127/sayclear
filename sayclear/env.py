from __future__ import annotations

from pathlib import Path


def load_env() -> dict[str, str]:
    root = Path(__file__).resolve().parent.parent
    path = root / ".env"
    data: dict[str, str] = {}
    if not path.is_file():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


ENV = load_env()
PROJECT_ID = ENV.get("GOOGLE_CLOUD_PROJECT", "sayclear")
ORGANIZE_KEY = ENV.get("CUN_AI_API_KEY", "")
ORGANIZE_BASE = ENV.get("CUN_AI_BASE_URL", "https://wintoken.dev/v1").rstrip("/")
ORGANIZE_MODEL = ENV.get("CUN_AI_MODEL", "deepseek-v4-flash-0731")
