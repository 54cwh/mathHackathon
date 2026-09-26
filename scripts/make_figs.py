"""把 run 目录数据画成报告图（逐 seed 诊断图 + 跨 seed 图）。

薄 CLI：业务逻辑 owner = `evogenesis.viz.figs`（`src/evogenesis/viz/figs.py`）；
本文件只做包内入口，argparse 在被调模块内（与 `scripts/run_arena.py` 同一约定）。
"""

from evogenesis.viz.figs import main

if __name__ == "__main__":
    raise SystemExit(main())
