from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayclear.organize import (
    OrganizeError,
    looks_usable,
    organize,
    short_reply_passthrough,
)


@dataclass
class Case:
    id: str
    transcript: str
    checks: list
    note: str = ""


@dataclass
class Result:
    id: str
    ok: bool
    ms: float
    output: str
    failed: list[str] = field(default_factory=list)


def has_numbered(text: str) -> bool:
    return bool(re.search(r"(?m)^\s*1[\.、\)]\s+", text)) and bool(
        re.search(r"(?m)^\s*2[\.、\)]\s+", text)
    )


def no_numbered(text: str) -> bool:
    return not has_numbered(text)


def contains_all(*needles: str):
    def _check(text: str) -> str | None:
        missing = [n for n in needles if n.lower() not in text.lower()]
        if missing:
            return "缺少：" + "、".join(missing)
        return None

    return _check


def contains_none(*needles: str):
    def _check(text: str) -> str | None:
        found = [n for n in needles if n.lower() in text.lower()]
        if found:
            return "不应出现：" + "、".join(found)
        return None

    return _check


def numbered():
    def _check(text: str) -> str | None:
        return None if has_numbered(text) else "应为 1. 2. 分点"

    return _check


def paragraph():
    def _check(text: str) -> str | None:
        return None if no_numbered(text) else "应是段落，不要 1. 2. 3."

    return _check


def title_then_numbered():
    def _check(text: str) -> str | None:
        lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        if not lines:
            return "空输出"
        if re.match(r"^1[\.、\)]\s+", lines[0]):
            return "分点前应有一句归纳标题"
        if len(lines[0]) > 24:
            return "标题过长：" + lines[0]
        if not has_numbered(text):
            return "应为标题 + 1. 2. 分点"
        return None

    return _check


def empty_or_fail():
    return "__empty_or_fail__"


CASES = [
    Case(
        "O1",
        "帮我写一个 Python 脚本，不对，用 TypeScript，读取 CSV 然后，呃，输出 JSON。",
        [
            contains_all("TypeScript", "CSV", "JSON"),
            contains_none("Python", "不对", "呃"),
            paragraph(),
        ],
        "场景 A：改口后只留 TypeScript",
    ),
    Case(
        "O2",
        "这个页面有几个地方需要改，按钮太大了，颜色也需要调整一下，然后整体再简洁一点。",
        [
            title_then_numbered(),
            contains_all("按钮", "颜色"),
            contains_none("有几个地方需要改", "我理解你的需求是"),
        ],
        "场景 B：归纳标题 + 并列改点",
    ),
    Case(
        "O3",
        "把这个 button 改小一点，再把 padding 调一下，那个 hover 状态的颜色太暗了。",
        [
            title_then_numbered(),
            contains_all("button", "padding", "hover"),
            contains_none("内边距"),
        ],
        "场景 C：中英专有词原样",
    ),
    Case(
        "O4",
        "明天上午先去超市，然后下午去图书馆，晚上回来把报告写完。",
        [
            title_then_numbered(),
            contains_all("明天", "超市", "图书馆", "报告"),
        ],
        "场景 D：贴近原话归纳 + 分点",
    ),
    Case(
        "O5",
        "嗯那个，帮我查一下 2024 年 WWDC 发布了哪些 AI 功能。",
        [
            contains_all("2024", "WWDC", "AI"),
            contains_none("嗯", "那个"),
            paragraph(),
        ],
        "场景 E：一句完整问题",
    ),
    Case(
        "O6",
        "用 fetch，不对，用 axios",
        [contains_all("axios"), contains_none("fetch")],
        "中英改口",
    ),
    Case(
        "O7",
        "用红色，不对蓝色，还是黑色吧",
        [contains_all("黑"), contains_none("红", "蓝")],
        "多次改口只留最终色",
    ),
    Case(
        "O8",
        "把按钮改小，对了，标题也改成 About",
        [
            title_then_numbered(),
            contains_all("按钮", "About"),
            contains_none("关于"),
        ],
        "补充不是覆盖",
    ),
    Case(
        "O9",
        "好的",
        [contains_all("好的")],
        "短确认语要填入",
    ),
    Case(
        "O9b",
        "是的",
        [contains_all("是的")],
        "短确认语要填入",
    ),
    Case(
        "O9c",
        "可以",
        [contains_all("可以")],
        "确认语不限于好的/是的",
    ),
    Case(
        "O9d",
        "收到",
        [contains_all("收到")],
        "确认语不限于好的/是的",
    ),
    Case(
        "O9e",
        "那个那个",
        [empty_or_fail()],
        "无意义垫话不应填入",
    ),
    Case(
        "S2",
        "不对",
        [contains_all("不对"), paragraph()],
        "单独纠正有含义，要写入",
    ),
    Case(
        "S4",
        "好的，用 TypeScript",
        [contains_all("TypeScript"), contains_none("好的"), paragraph()],
        "句首确认只是起头，留后面",
    ),
    Case(
        "S6",
        "把按钮改小，不对，改成图标",
        [contains_all("图标"), contains_none("不对"), paragraph()],
        "改口信号不要当正文",
    ),
    Case(
        "T1",
        "今天要把饭吃了，然后去锻炼",
        [
            title_then_numbered(),
            contains_all("今天", "饭", "锻炼"),
        ],
        "日程也可归纳，标题贴原话",
    ),
    Case(
        "T2",
        "记得把周报交了，顺便约一下设计评审",
        [
            title_then_numbered(),
            contains_all("周报", "设计评审"),
        ],
        "待办也可归纳，不限这一类",
    ),
    Case(
        "T5",
        "先把 timeout 改成 30，再把 hover 颜色调亮",
        [
            title_then_numbered(),
            contains_all("timeout", "30", "hover"),
        ],
        "标题带原词，英文不翻译",
    ),
    Case(
        "T7",
        "帮我查一下 2024 年 WWDC 的 AI 功能，再看看 Vision 相关的 session",
        [
            title_then_numbered(),
            contains_all("WWDC", "AI", "Vision", "session"),
        ],
        "调研问题也可归纳",
    ),
    Case(
        "T8",
        "今天要把饭吃了",
        [contains_all("今天", "饭"), paragraph()],
        "一件事：无标题、不分点",
    ),
    Case(
        "T10",
        "今日安排就是吃饭然后锻炼",
        [
            title_then_numbered(),
            contains_all("今日安排", "吃饭", "锻炼"),
        ],
        "用户已起标题则沿用",
    ),
]


def run_organize_case(case: Case) -> Result:
    t0 = time.perf_counter()
    failed: list[str] = []
    output = ""
    try:
        output = organize(case.transcript)
    except OrganizeError:
        output = ""
        if empty_or_fail() not in case.checks:
            failed.append("整理接口失败")
    ms = (time.perf_counter() - t0) * 1000
    if empty_or_fail() in case.checks:
        if output.strip():
            failed.append("空洞输入不应产出正文：" + output[:40])
        return Result(case.id, not failed, ms, output, failed)
    if not output.strip():
        failed.append("没有输出")
        return Result(case.id, False, ms, output, failed)
    if output.startswith("我理解你的需求是") or output.startswith("以下是"):
        failed.append("出现禁止前缀")
    for check in case.checks:
        if check == empty_or_fail():
            continue
        msg = check(output)
        if msg:
            failed.append(msg)
    if ms > 8000:
        failed.append(f"整理过慢：{ms:.0f}ms")
    return Result(case.id, not failed, ms, output, failed)


def run_client_cases() -> list[Result]:
    rows = []
    t0 = time.perf_counter()
    ok = looks_usable("") is False
    rows.append(Result("C1", ok, 0, "", [] if ok else ["空串应不可用"]))
    ok = looks_usable("把按钮改小") is True
    rows.append(Result("C2", ok, 0, "把按钮改小", [] if ok else ["正常短句应可用"]))
    ok = looks_usable("我理解你的需求是：把按钮改小") is True
    rows.append(
        Result(
            "C3",
            ok,
            (time.perf_counter() - t0) * 1000,
            "我理解你的需求是：把按钮改小",
            [] if ok else ["去掉前缀后应仍可用"],
        )
    )
    ok = looks_usable("好的") is True
    rows.append(Result("C4", ok, 0, "好的", [] if ok else ["「好的」应可作为正文"]))
    ok = short_reply_passthrough("收到") == "收到"
    rows.append(Result("C5", ok, 0, "收到", [] if ok else ["短确认应可兜底填入"]))
    ok = short_reply_passthrough("那个那个") is None
    rows.append(Result("C6", ok, 0, "那个那个", [] if ok else ["垫话不应兜底填入"]))
    ok = short_reply_passthrough("不对") == "不对"
    rows.append(Result("C7", ok, 0, "不对", [] if ok else ["单独「不对」应可兜底填入"]))
    return rows


def main() -> int:
    print("SayClear 自动测试  整理走当前 .env 通道")
    print("-" * 60)
    results: list[Result] = []
    for case in CASES:
        print(f"跑 {case.id}  {case.note} ...", flush=True)
        result = run_organize_case(case)
        results.append(result)
        mark = "PASS" if result.ok else "FAIL"
        print(f"  {mark}  {result.ms:.0f}ms")
        if result.output:
            for line in result.output.splitlines()[:8]:
                print("   ", line)
        for msg in result.failed:
            print("   !", msg)
        print(flush=True)
    client_rows = run_client_cases()
    results.extend(client_rows)
    for row in client_rows:
        print(f"{row.id}  {'PASS' if row.ok else 'FAIL'}  {'; '.join(row.failed)}")
    passed = sum(1 for r in results if r.ok)
    print("-" * 60)
    print(f"合计 {passed}/{len(results)} 通过")
    print("手工项 M1–M4 见 docs/SayClear-测试用例.md，本次未跑。")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
