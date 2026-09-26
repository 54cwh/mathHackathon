"""论文引用守护：正文里的每个 cite key 必须存在于 refs.bib。

为什么需要它：BibTeX 对**不存在的 key** 只在日志里给一条 warning，正文渲染成 ?，
不会中止编译 —— 属于典型的静默失败。这类错误必须变成红灯。
同时也守住「正文只引已登记文献」这条仓库硬约束。
"""

import re
from pathlib import Path

import pytest

# 正则里表示「一个字面反斜杠」需要两个字符。用 BS2 拼接，避免手写出错。
# 两种常量，别混：BS1 用于**正则转义**（正则里的单个反斜杠），
# BS2 用于匹配**正文里字面出现的反斜杠**（LaTeX 命令前缀），正则里要写成两个反斜杠。
BS1 = chr(92)
BS2 = chr(92) + chr(92)

ROOT = Path(__file__).resolve().parents[1]
BIB = ROOT / "paper" / "latex" / "refs.bib"
SECTIONS = ROOT / "paper" / "latex" / "sections"

# 匹配 cite / citep / citet 等命令的 key 列表
CITE_RE = re.compile(BS2 + "cite[a-z]*" + BS2 + "?{([^}]*)}")
# 匹配 refs.bib 里的条目名（@article{key,）
KEY_RE = re.compile("@" + BS1 + "w+" + BS1 + "{([^,]+),")


def _bib_keys() -> set:
    return set(KEY_RE.findall(BIB.read_text(encoding="utf-8")))


def test_bib_has_entries():
    assert _bib_keys(), "refs.bib 里没有任何条目"


def test_all_citation_keys_exist():
    """逐 section 扫描 cite 命令，每个 key 都必须在 refs.bib 里。"""
    keys = _bib_keys()
    missing = []
    scanned = 0
    for tex in sorted(SECTIONS.glob("*.tex")):
        text = tex.read_text(encoding="utf-8")
        for group in CITE_RE.findall(text):
            for key in (k.strip() for k in group.split(",") if k.strip()):
                scanned += 1
                if key not in keys:
                    missing.append(tex.name + ": " + key)
    if scanned == 0:
        pytest.skip("正文尚未引用任何文献")
    assert not missing, (
        "以下引用 key 不在 refs.bib 中（会渲染成 ?）：" + chr(10) + chr(10).join(missing)
    )
