"""控制台编码守护：脚本被**管道/重定向**时不得因非 GBK 字符崩溃。

回归背景（2026-09-26）：`tests/test_paper_bib.py` 用 `capture_output=True` 跑
`scripts/make_bib.py --check`。子进程 stdout 被重定向 ⇒ Python 回落到 locale 编码
（中文 Windows = GBK）⇒ 打印 `✅` 抛 `UnicodeEncodeError` ⇒ 门禁红灯。
修法见 `evogenesis/experiment/console.py`；本文件把这个坑钉成测试。

测试策略：先用**反证**证明该失败模式真实存在（不装守护确实崩），
再证明装了守护就不崩 —— 否则「守护有效」只是自说自话。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from evogenesis.experiment.console import force_utf8_stdout

ROOT = Path(__file__).resolve().parents[1]
BIB_SCRIPT = ROOT / "scripts" / "make_bib.py"
CHECK_MARK = "✅"  # ✅

#: 强制子进程 stdout 用 GBK —— 精确复刻「被重定向的中文 Windows」。
GBK_PIPE = {**os.environ, "PYTHONIOENCODING": "gbk"}


def _run(code: str, *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=cwd or ROOT,
        env=GBK_PIPE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_gbk_pipe_really_crashes_without_guard():
    """反证：本测试若通过，说明「GBK 管道 + 符号」确实会崩，守护才有存在意义。"""
    proc = _run(f"print({CHECK_MARK!r})")
    assert proc.returncode != 0, (
        "预期 GBK 管道下打印 ✅ 会失败；若这里通过了，说明环境行为已变，"
        "本文件的其余断言不再有保护意义，请复核 console.force_utf8_stdout 的必要性。"
    )
    assert "UnicodeEncodeError" in (proc.stderr or "")


def test_gbk_pipe_survives_with_guard():
    """装了守护：同一个符号在同样的 GBK 管道下正常输出。"""
    code = (
        "from evogenesis.experiment.console import force_utf8_stdout; "
        f"force_utf8_stdout(); print({CHECK_MARK!r})"
    )
    proc = _run(code)
    assert proc.returncode == 0, proc.stderr
    assert CHECK_MARK in (proc.stdout or "")


def test_make_bib_check_survives_gbk_pipe():
    """**用户可见的回归**：`make_bib.py --check` 在重定向下必须退出码 0。"""
    proc = subprocess.run(
        [sys.executable, str(BIB_SCRIPT), "--check"],
        cwd=ROOT,
        env=GBK_PIPE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    detail = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode == 0, (
        "make_bib.py --check 在 GBK 管道下失败 —— 入口是否漏调 force_utf8_stdout()？"
        + chr(10)
        + detail
    )


def test_helper_is_idempotent_and_returns_bool():
    """幂等、不抛（pytest 的 capture 对象不一定可重配，也不该因此报错）。"""
    assert isinstance(force_utf8_stdout(), bool)
    assert isinstance(force_utf8_stdout(), bool)
