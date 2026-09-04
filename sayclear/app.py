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
from .organize import OrganizeError, looks_usable, organize, warmup_organize
from .paste import paste_text
from .recorder import RecordError, Recorder, warmup_mic
from .stt import LiveRecognizer, SpeechError, prefetch_token
from .sounds import play_cue
from .timing import log_timing, now


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
        self.stt = LiveRecognizer()
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
        threading.Thread(target=self._warmup, name="sayclear-warmup", daemon=True).start()

    @python_method
    def _warmup(self) -> None:
        warmup_mic()
        prefetch_token()
        warmup_organize()
        print("warmup done", flush=True)

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
        self.stt.cancel()
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
            self.stt.start()
            self.recorder.start(on_chunk=self.stt.push)
        except RecordError as exc:
            self.stt.cancel()
            self._fail("无法录音。打开麦克风权限后重试。")
            print("record start:", exc)
            return
        self.state = RECORDING
        play_cue()
        self.hud.show_record()

    @python_method
    def _finish_record(self) -> None:
        self.state = THINKING
        play_cue()
        self.hud.show_thinking()
        self._gen += 1
        gen = self._gen
        threading.Thread(target=self._pipeline, args=(gen,), daemon=True).start()

    @python_method
    def _pipeline(self, gen: int) -> None:
        t0 = now()
        try:
            pcm = self.recorder.stop()
            t1 = now()
            if pcm is None:
                raise RecordError("没有录到声音")
            transcript = self.stt.finish()
            t2 = now()
            text = organize(transcript)
            if not looks_usable(text):
                raise OrganizeError("整理结果不可用")
            t3 = now()
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
        log_timing(
            {
                "stop": t1 - t0,
                "stt": t2 - t1,
                "organize": t3 - t2,
                "ok_to_text": t3 - t0,
            },
            extra=f"chars={len(text)} stt={self.stt.mode}",
        )
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
        t0 = now()
        self.state = IDLE
        self.hud.hide()
        try:
            paste_text(text)
        except Exception:
            traceback.print_exc()
            self._fail("这次没能把文字放进去。")
            return
        log_timing({"paste": now() - t0})

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
