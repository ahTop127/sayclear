from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
from typing import Optional


class RecordError(Exception):
    pass


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    for candidate in (
        "/opt/anaconda3/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ):
        if os.path.isfile(candidate):
            return candidate
    raise RecordError("找不到 ffmpeg，无法录音")


def pick_mic_index() -> int:
    proc = subprocess.run(
        [_ffmpeg(), "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True,
        text=True,
    )
    text = (proc.stderr or "") + (proc.stdout or "")
    in_audio = False
    fallback: Optional[int] = None
    for line in text.splitlines():
        if "AVFoundation audio devices" in line:
            in_audio = True
            continue
        if "AVFoundation video devices" in line:
            in_audio = False
            continue
        if not in_audio:
            continue
        if "] [" not in line:
            continue
        try:
            idx = int(line.split("[")[-1].split("]")[0])
        except ValueError:
            continue
        name = line.split("]", 2)[-1].strip()
        if "iPhone" in name:
            if fallback is None:
                fallback = idx
            continue
        if "麦克风" in name:
            return idx
        if fallback is None:
            fallback = idx
        if "MacBook" in name:
            return idx
    if fallback is not None:
        return fallback
    return 1


class Recorder:
    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._path: Optional[str] = None

    def start(self) -> None:
        self.stop()
        fd, path = tempfile.mkstemp(prefix="sayclear-", suffix=".wav")
        os.close(fd)
        os.remove(path)
        self._path = path
        mic = pick_mic_index()
        cmd = [
            _ffmpeg(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "avfoundation",
            "-i",
            f":{mic}",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            path,
        ]
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    def stop(self) -> Optional[bytes]:
        proc = self._proc
        path = self._path
        self._proc = None
        self._path = None
        if proc is None:
            return None
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        err = b""
        if proc.stderr:
            err = proc.stderr.read() or b""
        data = b""
        if path and os.path.isfile(path):
            with open(path, "rb") as fh:
                data = fh.read()
            os.remove(path)
        if len(data) < 800:
            msg = err.decode("utf-8", errors="replace").strip() or "没有录到声音"
            raise RecordError(msg)
        return data
