from __future__ import annotations

import time

from AppKit import NSPasteboard, NSPasteboardTypeString
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGEventFlagMaskCommand,
    kCGHIDEventTap,
)


KEYCODE_V = 9


def paste_text(text: str) -> None:
    board = NSPasteboard.generalPasteboard()
    previous = board.stringForType_(NSPasteboardTypeString)
    board.clearContents()
    board.setString_forType_(text, NSPasteboardTypeString)
    time.sleep(0.05)
    down = CGEventCreateKeyboardEvent(None, KEYCODE_V, True)
    up = CGEventCreateKeyboardEvent(None, KEYCODE_V, False)
    CGEventSetFlags(down, kCGEventFlagMaskCommand)
    CGEventSetFlags(up, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)
    time.sleep(0.12)
    board.clearContents()
    if previous:
        board.setString_forType_(previous, NSPasteboardTypeString)
