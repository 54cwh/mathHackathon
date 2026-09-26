"""refs.bib 的 LaTeX 安全守护：字段值里不许出现未转义的 # 或 &。

为什么需要它：生成器曾把 `bibliography.md #23` 原样写进 note 字段，
BibTeX 把它带进 .bbl 后 LaTeX 直接报
「You can not use macro parameter character #」并中止编译 ——
而且是在编译**末尾**才炸，前面所有 warning 都像是无关的。这类静默/延迟失败必须变红灯。
"""

from pathlib import Path

import pytest

BS = chr(92)
ROOT = Path(__file__).resolve().parents[1]
BIB = ROOT / "paper" / "latex" / "refs.bib"
# 这些字符在 LaTeX 正文里必须转义（% 在 .bib 里是注释符，字段值里同样危险）
HOSTILE = ("#", "&", "%", "$")


def _body() -> str:
    """只看真正会进 .bbl 的字段值：去掉注释行，并剔掉 url 字段。

    url 里的 % 是**百分号编码**（如 12%3A），在 url 宏包内合法，不算危险字符。
    """
    text = BIB.read_text(encoding="utf-8")
    keep = [
        ln
        for ln in text.split(chr(10))
        if not ln.lstrip().startswith("%") and not ln.strip().startswith("url")
    ]
    return chr(10).join(keep)


def test_bib_exists():
    assert BIB.is_file(), "refs.bib 未生成；先跑 scripts/make_bib.py"


def _unescaped(text: str, ch: str) -> list:
    hits = []
    for i, c in enumerate(text):
        if c == ch and (i == 0 or text[i - 1] != BS):
            hits.append(i)
    return hits


def test_no_hostile_characters_in_bib_values():
    if not BIB.is_file():
        pytest.skip("refs.bib 未生成")
    body = _body()
    problems = []
    for ch in HOSTILE:
        hits = _unescaped(body, ch)
        if hits:
            for pos in hits[:2]:
                problems.append(
                    ch + " -> " + body[max(0, pos - 60) : pos + 20].replace(chr(10), " | ")
                )
    assert not problems, "refs.bib 里有未转义的 LaTeX 危险字符：" + chr(10) + chr(10).join(problems)
