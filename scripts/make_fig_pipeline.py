"""F12 数据流总览图（按 core §2）。

薄 CLI：业务逻辑 owner = `evogenesis.viz.fig_pipeline`（`src/evogenesis/viz/fig_pipeline.py`）；
本文件只做包内入口，argparse 在被调模块内（与 `scripts/run_arena.py` 同一约定）。
"""

from evogenesis.viz.fig_pipeline import main

if __name__ == "__main__":
    raise SystemExit(main())
