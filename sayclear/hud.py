from __future__ import annotations

import math

from AppKit import (
    NSBezierPath,
    NSButton,
    NSColor,
    NSFont,
    NSMakeRect,
    NSPanel,
    NSScreen,
    NSTextField,
    NSView,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSFloatingWindowLevel,
    NSTimer,
)
from Foundation import NSObject
from objc import python_method
from objc import super as objc_super


class CircleButton(NSButton):
    def acceptsFirstMouse_(self, event) -> bool:
        return True


class BarsView(NSView):
    def initWithFrame_(self, frame):
        self = objc_super(BarsView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.phase = 0.0
        return self

    def drawRect_(self, rect) -> None:
        NSColor.colorWithWhite_alpha_(0.92, 1.0).set()
        bounds = self.bounds()
        n = 7
        gap = 2.0
        width = 2.0
        total = n * width + (n - 1) * gap
        x0 = (bounds.size.width - total) / 2
        mid = bounds.size.height / 2
        for i in range(n):
            wave = 0.35 + 0.65 * abs(math.sin(self.phase + i * 0.55))
            h = 6.0 + 10.0 * wave
            x = x0 + i * (width + gap)
            path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x, mid - h / 2, width, h), 1.0, 1.0
            )
            path.fill()


class Hud(NSObject):
    def init(self):
        self = objc_super(Hud, self).init()
        if self is None:
            return None
        self._cancel_cb = None
        self._ok_cb = None
        self.window = None
        self.bars = None
        self.timer = None
        self.cancel_btn = None
        self.ok_btn = None
        self.think_label = None
        self.fail_label = None
        return self

    @python_method
    def setup(self, cancel_cb, ok_cb):
        self._cancel_cb = cancel_cb
        self._ok_cb = ok_cb
        self._build()
        return self

    @python_method
    def _build(self) -> None:
        screen = NSScreen.mainScreen().visibleFrame()
        width, height = 132.0, 38.0
        x = screen.origin.x + (screen.size.width - width) / 2
        y = screen.origin.y + 28.0
        window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, width, height),
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )
        window.setLevel_(NSFloatingWindowLevel)
        window.setOpaque_(False)
        window.setBackgroundColor_(NSColor.clearColor())
        window.setHasShadow_(True)
        window.setIgnoresMouseEvents_(False)
        window.setHidesOnDeactivate_(False)
        # canJoinAllSpaces | stationary，避免进全屏主窗口行为
        window.setCollectionBehavior_(1 << 0 | 1 << 4)
        window.setFloatingPanel_(True)
        window.setBecomesKeyOnlyIfNeeded_(True)

        content = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
        content.setWantsLayer_(True)
        content.layer().setBackgroundColor_(
            NSColor.colorWithWhite_alpha_(0.086, 0.96).CGColor()
        )
        content.layer().setCornerRadius_(19.0)
        window.setContentView_(content)

        cancel = CircleButton.alloc().initWithFrame_(NSMakeRect(6, 8, 22, 22))
        cancel.setTitle_("X")
        cancel.setBordered_(False)
        cancel.setFont_(NSFont.systemFontOfSize_(13))
        cancel.setWantsLayer_(True)
        cancel.layer().setBackgroundColor_(NSColor.colorWithWhite_alpha_(0.18, 1).CGColor())
        cancel.layer().setCornerRadius_(11.0)
        cancel.setContentTintColor_(NSColor.whiteColor())
        cancel.setTarget_(self)
        cancel.setAction_("cancel:")
        self.cancel_btn = cancel

        ok = CircleButton.alloc().initWithFrame_(NSMakeRect(104, 8, 22, 22))
        ok.setTitle_("OK")
        ok.setBordered_(False)
        ok.setFont_(NSFont.boldSystemFontOfSize_(8))
        ok.setWantsLayer_(True)
        ok.layer().setBackgroundColor_(NSColor.colorWithWhite_alpha_(0.93, 1).CGColor())
        ok.layer().setCornerRadius_(11.0)
        ok.setTarget_(self)
        ok.setAction_("ok:")
        self.ok_btn = ok

        bars = BarsView.alloc().initWithFrame_(NSMakeRect(32, 11, 68, 16))
        self.bars = bars

        think = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 8, width, 22))
        think.setBezeled_(False)
        think.setDrawsBackground_(False)
        think.setEditable_(False)
        think.setSelectable_(False)
        think.setAlignment_(2)
        think.setStringValue_("Thinking")
        think.setTextColor_(NSColor.colorWithWhite_alpha_(0.95, 1))
        think.setFont_(NSFont.systemFontOfSize_weight_(13, 0.4))
        think.setHidden_(True)
        self.think_label = think

        fail = NSTextField.alloc().initWithFrame_(NSMakeRect(12, 6, 108, 26))
        fail.setBezeled_(False)
        fail.setDrawsBackground_(False)
        fail.setEditable_(False)
        fail.setSelectable_(False)
        fail.setStringValue_("")
        fail.setTextColor_(NSColor.colorWithWhite_alpha_(0.95, 1))
        fail.setFont_(NSFont.systemFontOfSize_(10))
        fail.setHidden_(True)
        self.fail_label = fail

        content.addSubview_(cancel)
        content.addSubview_(ok)
        content.addSubview_(bars)
        content.addSubview_(think)
        content.addSubview_(fail)
        self.window = window

    def cancel_(self, sender) -> None:
        if self._cancel_cb:
            self._cancel_cb()

    def ok_(self, sender) -> None:
        if self._ok_cb:
            self._ok_cb()

    def _tick_(self, timer) -> None:
        if self.bars and not self.bars.isHidden():
            self.bars.phase += 0.28
            self.bars.setNeedsDisplay_(True)

    @python_method
    def show_record(self) -> None:
        self.cancel_btn.setHidden_(False)
        self.ok_btn.setHidden_(False)
        self.bars.setHidden_(False)
        self.think_label.setHidden_(True)
        self.fail_label.setHidden_(True)
        self._resize(132, 38)
        self.window.orderFront_(None)
        self._start_timer()

    @python_method
    def show_thinking(self) -> None:
        self.cancel_btn.setHidden_(True)
        self.ok_btn.setHidden_(True)
        self.bars.setHidden_(True)
        self.think_label.setHidden_(False)
        self.fail_label.setHidden_(True)
        self._resize(132, 38)
        self.window.orderFront_(None)
        self._stop_timer()

    @python_method
    def show_error(self, title: str) -> None:
        self.cancel_btn.setHidden_(True)
        self.ok_btn.setHidden_(True)
        self.bars.setHidden_(True)
        self.think_label.setHidden_(True)
        self.fail_label.setHidden_(False)
        self.fail_label.setStringValue_(title)
        self._resize(220, 44)
        self.window.orderFront_(None)
        self._stop_timer()

    @python_method
    def hide(self) -> None:
        self._stop_timer()
        self.window.orderOut_(None)

    @python_method
    def _resize(self, width: float, height: float) -> None:
        screen = NSScreen.mainScreen().visibleFrame()
        x = screen.origin.x + (screen.size.width - width) / 2
        y = screen.origin.y + 28.0
        self.window.setFrame_display_(NSMakeRect(x, y, width, height), True)
        content = self.window.contentView()
        content.setFrame_(NSMakeRect(0, 0, width, height))
        self.think_label.setFrame_(NSMakeRect(0, 8, width, 22))
        self.fail_label.setFrame_(NSMakeRect(12, 8, width - 24, 28))

    @python_method
    def _start_timer(self) -> None:
        self._stop_timer()
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.06, self, "_tick:", None, True
        )

    @python_method
    def _stop_timer(self) -> None:
        if self.timer:
            self.timer.invalidate()
            self.timer = None
