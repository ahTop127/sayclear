from __future__ import annotations

import threading
from typing import Callable, Optional

from Quartz import (
    CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    CFRunLoopRun,
    CGEventGetFlags,
    CGEventTapCreate,
    CGEventTapEnable,
    kCFRunLoopCommonModes,
    kCGEventFlagsChanged,
    kCGEventKeyDown,
    kCGEventTapOptionDefault,
    kCGHeadInsertEventTap,
    kCGSessionEventTap,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskShift,
)


MODS = (
    kCGEventFlagMaskShift
    | kCGEventFlagMaskControl
    | kCGEventFlagMaskAlternate
)


class CommandTap:
    """把「单独点一下 ⌘、没有配其它键」当成开始/结束。"""

    def __init__(self, on_tap: Callable[[], None]) -> None:
        self._on_tap = on_tap
        self._cmd_down = False
        self._combo = False
        self._tap = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="sayclear-hotkey", daemon=True)
        self._thread.start()

    def _callback(self, proxy, event_type, event, refcon):
        flags = CGEventGetFlags(event)
        cmd = bool(flags & kCGEventFlagMaskCommand)
        if event_type == kCGEventKeyDown and cmd:
            self._combo = True
        elif event_type == kCGEventFlagsChanged:
            if cmd and not self._cmd_down:
                self._cmd_down = True
                self._combo = False
            elif not cmd and self._cmd_down:
                self._cmd_down = False
                extra = bool(flags & MODS)
                if not self._combo and not extra:
                    threading.Thread(target=self._on_tap, daemon=True).start()
        return event

    def _run(self) -> None:
        mask = (1 << kCGEventFlagsChanged) | (1 << kCGEventKeyDown)
        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            mask,
            self._callback,
            None,
        )
        if not tap:
            import sys

            print(
                "无法监听 ⌘：请在系统设置 → 隐私与安全性 → 辅助功能 中允许这个 Python：",
                flush=True,
            )
            print(" ", sys.executable, flush=True)
            return
        self._tap = tap
        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)
        CGEventTapEnable(tap, True)
        CFRunLoopRun()
