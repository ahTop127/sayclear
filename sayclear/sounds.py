from __future__ import annotations

from AppKit import NSBeep, NSSound

_held = None


def play_cue() -> None:
    """开始 / 结束录音的短提示音。"""
    global _held
    for name in ("Tink", "Ping", "Pop"):
        snd = NSSound.soundNamed_(name)
        if snd is None:
            continue
        copy = snd.copy()
        if copy is None:
            copy = snd
        copy.play()
        _held = copy
        return
    NSBeep()
