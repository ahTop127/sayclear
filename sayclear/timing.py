from __future__ import annotations

import time
from typing import Optional


def now() -> float:
    return time.perf_counter()


def log_timing(parts: dict[str, float], extra: Optional[str] = None) -> None:
    bits = [f"{name}={secs:.2f}s" for name, secs in parts.items()]
    line = "[timing] " + " ".join(bits)
    if extra:
        line += " | " + extra
    print(line, flush=True)
