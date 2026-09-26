"""LaTeX 产物安全检查：把两类**实测崩过**的缺陷钉成测试。

两次真实事故（2026-09-26）：

1. `.bbl` 里出现**嵌套的 url 宏**：refs.bib 的 url 字段被写成「字段值本身再包一层
   url 宏」，而 plainnat 生成 .bbl 时**自己也会包一层** ⇒ 变成嵌套调用 ⇒
   hyperref 的 hyper@normalise 无限递归 ⇒ TeX capacity exceeded [input stack size]。
2. 正文出现 emoji（警示符 U+26A0）：matplotlib 无 CJK 是已知坑，但 **LaTeX** 同样会
   报 Missing character ⇒ 静默丢字 / 渲染成方框。
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
LATEX = ROOT / "paper" / "latex"
BIB = LATEX / "refs.bib"
URL_CMD = "url{"


def test_url_fields_are_bare_and_not_double_wrapped():
    """refs.bib 的 url 字段必须是**裸 URL**：包 url 宏会与 plainnat 撞车成嵌套调用。"""
    if not BIB.is_file():
        return
    offenders = []
    for i, line in enumerate(BIB.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s.startswith("url") or "=" not in s:
            continue
        value = s.split("=", 1)[1].strip()
        if URL_CMD in value:
            offenders.append(str(i) + ": " + s[:120])
    assert not offenders, (
        "url 字段里又出现了 url 宏（会与 plainnat 叠加成嵌套调用）："
        + chr(10)
        + chr(10).join(offenders)
    )


def test_no_emoji_or_unrenderable_symbols_in_latex_sources():
    """tex / bib 源不得含 LaTeX 字体渲染不了的符号（emoji、变体选择符等）。"""

    def suspicious(ch: str) -> bool:
        o = ord(ch)
        if o < 0x2000:
            return False
        if 0x3000 <= o <= 0x9FFF:
            return False  # CJK
        if 0xFF00 <= o <= 0xFFEF:
            return False  # 全角形式
        if 0x2010 <= o <= 0x203A:
            return False  # 连字、引号
        if 0x2160 <= o <= 0x217F:
            return False  # 罗马数字
        return o not in (0x2260, 0x2248, 0x00D7, 0x2192, 0x2264, 0x2265, 0xFE0F)

    files = sorted(LATEX.rglob("*.tex")) + ([BIB] if BIB.is_file() else [])
    offenders = []
    for p in files:
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("%"):
                continue
            for ch in line:
                if suspicious(ch):
                    offenders.append(
                        p.name + ":" + str(i) + ": " + hex(ord(ch)) + " in " + line.strip()[:90]
                    )
                    break
    assert not offenders, "LaTeX 源里有字体渲染不了的符号：" + chr(10) + chr(10).join(offenders)
