"""环境对照图（E-F 前置检查，读 exp_env_* 汇总）。

薄 CLI：业务逻辑 owner = `evogenesis.viz.env_compare`（`src/evogenesis/viz/env_compare.py`）；
本文件只做包内入口，argparse 在被调模块内（与 `scripts/run_arena.py` 同一约定）。
"""

from evogenesis.viz.env_compare import main

if __name__ == "__main__":
    raise SystemExit(main())
