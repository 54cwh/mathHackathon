"""仓库路径基准（viz 出图模块共用）。

`ROOT` = 仓库根：本文件位于 ``src/evogenesis/viz/``，向上三级。出图脚本只**只读**
`results/` 下的 run 产物（`docs/` 中的目录布局 owner 为 `experiment/实验与评价体系.md` §5.1）。
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
