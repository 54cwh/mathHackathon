"""跨平台控制台输出：让脚本在 Windows 上被重定向时也不炸。

**为什么需要**：Windows 上 Python 的 `sys.stdout` 在**接终端**时用 UTF-8 控制台 API，
但被**管道/重定向**（`| tee`、`capture_output=True`、CI、`> log.txt`）时回落到
locale 编码（中文 Windows = GBK）。GBK 能编码中文，但**不能**编码 `\u2705`、`\u26a0` 这类符号，
于是 `print` 直接抛 `UnicodeEncodeError` —— 脚本在终端里好好的，一进管道就崩。

实测触发电机（2026-09-26）：`tests/test_paper_bib.py` 用 `capture_output=True` 跑
`scripts/make_bib.py --check`，子进程 stdout 被重定向成 GBK，打印 `\u2705` 抛异常 ⇒ 门禁红灯。

**约定**：脚本入口（`main()` 第一行）调用 `force_utf8_stdout()`。库模块**不得**调用它
（改变宿主进程的全局流不是库该做的事）。
"""

from __future__ import annotations

import sys


def force_utf8_stdout() -> bool:
    """把 `sys.stdout` / `sys.stderr` 切到 UTF-8 + `errors="replace"`；幂等。

    返回是否**至少成功重配了一个流**（供测试断言用）。

    - `errors="replace"`：即便终端真的显示不了某字符，也只把**那一个字符**降级成 `?`，
      绝不让整条脚本崩掉。这是「输出难看」与「脚本失败」之间的取舍，选前者。
    - 已被关闭或不可重配的流会被跳过（不抛）。
    """
    changed = False
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:  # 例如 pytest 的 capture 对象
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # 流已关闭 / detached
            continue
        changed = True
    return changed
