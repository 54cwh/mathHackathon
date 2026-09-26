"""F6 发育 viability 通过率图（固定 seed 重算）。

薄 CLI：业务逻辑 owner = `evogenesis.viz.fig_viability`（`src/evogenesis/viz/fig_viability.py`）；
本文件只做包内入口，argparse 在被调模块内（与 `scripts/run_arena.py` 同一约定）。
"""

from evogenesis.viz.fig_viability import main

if __name__ == "__main__":
    raise SystemExit(main())
