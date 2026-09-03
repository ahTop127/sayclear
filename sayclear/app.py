from __future__ import annotations

import queue
import threading
import traceback

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
)
from Foundation import NSObject, NSTimer
from objc import python_method
from objc import super as objc_super

from .hotkey import CommandTap
from .hud import Hud
from .organize import OrganizeError, looks_usable, organize
from .paste import paste_text
from .recorder import RecordError, Recorder
from .stt import SpeechError, transcribe


IDLE = "idle"
RECORDING = "recording"
THINKING = "thinking"


class SayClearApp(NSObject):
    def init(self):
        self = objc_super(SayClearApp, self).init()
        if self is None:
            return None
        self.state = IDLE
        self.recorder = Recorder()
        self.hud = None
        self._gen = 0
        self._status = None
        self._main_q: queue.Queue = queue.Queue()
        return self

    @python_method
    def start(self) -> None:
        hud = Hud.alloc().init()
        hud.setup(self._on_cancel, self._on_ok)
        self.hud = hud
        self._status = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
        self._status.button().setTitle_("SC")
        menu = NSMenu.alloc().init()
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "退出 SayClear", "terminate:", ""
        )
        quit_item.setTarget_(NSApplication.sharedApplication())
        menu.addItem_(quit_item)
        self._status.setMenu_(menu)
        CommandTap(self._on_command).start()

    @python_method
    def _on_command(self) -> None:
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "_commandMain:", None, False
        )

    def _commandMain_(self, _obj) -> None:
        if self.state == IDLE:
            self._begin_record()
        elif self.state == RECORDING:
            self._finish_record()

    @python_method
    def _on_cancel(self) -> None:
        if self.state != RECORDING:
            return
        try:
            self.recorder.stop()
        except RecordError:
            pass
        self.state = IDLE
        self._gen += 1
        self.hud.hide()

    @python_method
    def _on_ok(self) -> None:
        if self.state == RECORDING:
            self._finish_record()

    @python_method
    def _begin_record(self) -> None:
        try:
            self.recorder.start()
        except RecordError as exc:
            self._fail("无法录音。打开麦克风权限后重试。")
            print("record start:", exc)
            return
        self.state = RECORDING
        self.hud.show_record()

    @python_method
    def _finish_record(self) -> None:
        self.state = THINKING
        self.hud.show_thinking()
        self._gen += 1
        gen = self._gen
        threading.Thread(target=self._pipeline, args=(gen,), daemon=True).start()

    @python_method
    def _pipeline(self, gen: int) -> None:
        try:
            audio = self.recorder.stop()
            if audio is None:
                raise RecordError("没有录到声音")
            transcript = transcribe(audio)
            text = organize(transcript)
            if not looks_usable(text):
                raise OrganizeError("整理结果不可用")
        except RecordError:
            self._later(gen, lambda: self._fail("没有录到声音，靠近再试一次。"))
            return
        except SpeechError:
            self._later(gen, lambda: self._fail("识别没成功，稍后重试。"))
            traceback.print_exc()
            return
        except OrganizeError:
            self._later(gen, lambda: self._fail("整理没成功，稍后重试。"))
            traceback.print_exc()
            return
        except Exception:
            self._later(gen, lambda: self._fail("这次没完成，稍后重试。"))
            traceback.print_exc()
            return
        self._later(gen, lambda: self._succeed(text))

    @python_method
    def _later(self, gen: int, fn) -> None:
        self._main_q.put((gen, fn))
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "_drain:", None, False
        )

    def _drain_(self, _obj) -> None:
        while True:
            try:
                gen, fn = self._main_q.get_nowait()
            except queue.Empty:
                break
            if gen == self._gen:
                fn()

    @python_method
    def _succeed(self, text: str) -> None:
        self.state = IDLE
        self.hud.hide()
        try:
            paste_text(text)
        except Exception:
            traceback.print_exc()
            self._fail("这次没能把文字放进去。")

    @python_method
    def _fail(self, message: str) -> None:
        self.state = IDLE
        self.hud.show_error(message)
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            3.2, self, "_hideError:", None, False
        )

    def _hideError_(self, timer) -> None:
        if self.state == IDLE:
            self.hud.hide()


def main() -> None:
    import sys

    nsapp = NSApplication.sharedApplication()
    nsapp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    app = SayClearApp.alloc().init()
    app.start()
    print("SayClear 已运行。把光标放进输入框，点一下 ⌘ 开始说话，再点 ⌘ 或 OK 结束。", flush=True)
    print("菜单栏图标是 SC。需要麦克风和辅助功能权限。", flush=True)
    print("当前 Python：", sys.executable, flush=True)
    nsapp.run()
