from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayclear.organize import OrganizeError, looks_usable, organize


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
            numbered(),
            contains_all("按钮", "颜色"),
            contains_none("有几个地方需要改"),
        ],
        "场景 B：并列改点分点",
    ),
    Case(
        "O3",
        "把这个 button 改小一点，再把 padding 调一下，那个 hover 状态的颜色太暗了。",
        [
            numbered(),
            contains_all("button", "padding", "hover"),
            contains_none("内边距"),
        ],
        "场景 C：中英专有词原样",
    ),
    Case(
        "O4",
        "明天上午先去超市，然后下午去图书馆，晚上回来把报告写完。",
        [
            numbered(),
            contains_all("超市", "图书馆", "报告"),
        ],
        "场景 D：有顺序的多步",
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
        [contains_all("按钮", "About"), contains_none("关于")],
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
    results.extend(run_client_cases())
    for row in results[-3:]:
        print(f"{row.id}  {'PASS' if row.ok else 'FAIL'}  {'; '.join(row.failed)}")
    passed = sum(1 for r in results if r.ok)
    print("-" * 60)
    print(f"合计 {passed}/{len(results)} 通过")
    print("手工项 M1–M4 见 docs/SayClear-测试用例.md，本次未跑。")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
