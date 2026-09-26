"""论文文献同步守护：`refs.bib` 必须与 `bibliography.md` 一致。

仓库硬约束：`research/notes/bibliography.md` 是文献事实的**唯一来源**。
`paper/latex/refs.bib` 是派生产物；一旦有人手改 .bib、或改了 md 忘了重生成，
两边就会漂移，后果是「正文引了一条不一致的文献」。本测试把这种漂移变成红灯。
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "make_bib.py"
BIB = ROOT / "paper" / "latex" / "refs.bib"


def test_bib_generator_exists():
    assert SCRIPT.is_file()


def test_refs_bib_in_sync_with_bibliography():
    """重跑生成器与磁盘上的 refs.bib 比较（与 --check 同一逻辑）。"""
    if not BIB.is_file():
        pytest.skip("refs.bib 尚未生成；先跑 scripts/make_bib.py")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    detail = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode == 0, (
        "refs.bib 与 bibliography.md 不同步 —— 请重跑 scripts/make_bib.py" + chr(10) + detail
    )


def test_every_bib_entry_has_stable_identifier():
    """规则 1：每条必须有 DOI 或稳定链接 —— 生成的 .bib 里必须能看到其一。"""
    if not BIB.is_file():
        pytest.skip("refs.bib 尚未生成")
    text = BIB.read_text(encoding="utf-8")
    entries = text.split("@")[1:]
    assert entries, "refs.bib 里没有任何条目"
    for block in entries:
        assert "doi" in block or "url" in block, f"条目缺 DOI/url：{block[:200]}"


def test_all_registered_entries_reach_the_bib():
    """**不许静默丢条目**：md 的编号条目数必须等于 .bib 的条目数。"""
    import re

    if not BIB.is_file():
        pytest.skip("refs.bib 尚未生成")
    md = (ROOT / "research" / "notes" / "bibliography.md").read_text(encoding="utf-8")
    numbered = len(re.findall(r"(?m)^\d+\.\s+\S", md))
    in_bib = len(re.findall(r"(?m)^@", BIB.read_text(encoding="utf-8")))
    assert in_bib == numbered, (
        f"bibliography.md 有 {numbered} 条编号条目，但 refs.bib 只有 {in_bib} 条 "
        "—— 有条目被解析器静默丢弃，请检查 scripts/make_bib.py"
    )
