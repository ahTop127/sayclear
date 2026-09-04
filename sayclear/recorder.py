from __future__ import annotations

import os
import shutil
import subprocess
import threading
from typing import Callable, Optional


SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_BYTES = 3200  # 100ms of 16-bit mono PCM


class RecordError(Exception):
    pass


_mic_index: Optional[int] = None


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
    global _mic_index
    if _mic_index is not None:
        return _mic_index
    proc = subprocess.run(
        [_ffmpeg(), "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True,
        text=True,
    )
    text = (proc.stderr or "") + (proc.stdout or "")
    in_audio = False
    fallback: Optional[int] = None
    chosen: Optional[int] = None
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
        if "麦克风" in name or "MacBook" in name:
            chosen = idx
            break
        if fallback is None:
            fallback = idx
    _mic_index = chosen if chosen is not None else (fallback if fallback is not None else 1)
    return _mic_index


def warmup_mic() -> None:
    try:
        pick_mic_index()
    except RecordError:
        pass


class Recorder:
    """把麦克风写成内存里的 16k PCM，边录边回调，结束时不等待写文件。"""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._reader: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._on_chunk: Optional[Callable[[bytes], None]] = None
        self._pcm = bytearray()
        self._err = b""
        self._lock = threading.Lock()

    def start(self, on_chunk: Optional[Callable[[bytes], None]] = None) -> None:
        self.stop()
        self._on_chunk = on_chunk
        self._pcm = bytearray()
        self._err = b""
        mic = pick_mic_index()
        cmd = [
            _ffmpeg(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-fflags",
            "nobuffer",
            "-flags",
            "low_delay",
            "-f",
            "avfoundation",
            "-i",
            f":{mic}",
            "-ac",
            str(CHANNELS),
            "-ar",
            str(SAMPLE_RATE),
            "-f",
            "s16le",
            "pipe:1",
        ]
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        self._reader = threading.Thread(target=self._read_stdout, name="sayclear-pcm", daemon=True)
        self._stderr_thread = threading.Thread(
            target=self._read_stderr, name="sayclear-ffmpeg-err", daemon=True
        )
        self._reader.start()
        self._stderr_thread.start()

    def _read_stdout(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        while True:
            chunk = proc.stdout.read(CHUNK_BYTES)
            if not chunk:
                break
            with self._lock:
                self._pcm.extend(chunk)
            cb = self._on_chunk
            if cb:
                try:
                    cb(chunk)
                except Exception:
                    pass

    def _read_stderr(self) -> None:
        proc = self._proc
        if proc is None or proc.stderr is None:
            return
        self._err = proc.stderr.read() or b""

    def stop(self) -> Optional[bytes]:
        proc = self._proc
        self._proc = None
        if proc is None:
            self._on_chunk = None
            return None
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=0.4)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=0.4)
                except subprocess.TimeoutExpired:
                    pass
        if self._reader:
            self._reader.join(timeout=0.6)
        if self._stderr_thread:
            self._stderr_thread.join(timeout=0.2)
        self._reader = None
        self._stderr_thread = None
        self._on_chunk = None
        with self._lock:
            data = bytes(self._pcm)
        if len(data) < SAMPLE_RATE:  # 少于约 0.5 秒
            msg = self._err.decode("utf-8", errors="replace").strip() or "没有录到声音"
            raise RecordError(msg)
        return data
