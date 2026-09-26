"""F7 连接矩阵 / 拓扑图（读 connectome_matrix.json 落盘产物）。

薄 CLI：业务逻辑 owner = `evogenesis.viz.fig_connectome`（`src/evogenesis/viz/fig_connectome.py`）；
本文件只做包内入口，argparse 在被调模块内（与 `scripts/run_arena.py` 同一约定）。
"""

from evogenesis.viz.fig_connectome import main

if __name__ == "__main__":
    raise SystemExit(main())
