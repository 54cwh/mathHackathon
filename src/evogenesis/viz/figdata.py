"""图表 ↔ Excel 数据导出（所有出图脚本共用；长期要求：图必须有配套数据表）。

约定（用户 2026-09-26 要求「对应、命名、保存」）：
- **一个图 = 一个 .xlsx**，文件名与图**同名不同后缀**，放在图同级的 `data/` 目录：
      figs/<exp>/fig_metrics_mean_std.png
      figs/<exp>/data/fig_metrics_mean_std.xlsx
  同名即对应，不靠人工记忆。
- 每个 .xlsx **第一个 sheet 固定为 `_manifest`**：逐 sheet 写明「这张 sheet 是什么、
  来自哪个脚本、什么口径」——让拿到文件的人不看代码也知道数据含义。
- 其余 sheet 一律**原始数据**（未做美化加工），供后续统一美化时改样式不改数据。

本模块只做导出，不读 run 目录、不做统计。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

MANIFEST_SHEET = "_manifest"


def data_dir(fig_dir: Path) -> Path:
    """图目录对应的数据目录（`<fig_dir>/data`）。"""
    return fig_dir / "data"


def workbook_path(fig_path: Path) -> Path:
    """由图路径推同名 Excel 路径（同名不同后缀 + `data/` 子目录）。"""
    return data_dir(fig_path.parent) / (fig_path.stem + ".xlsx")


def export_workbook(
    fig_path: Path,
    sheets: dict[str, pd.DataFrame],
    *,
    caption: str,
    sources: dict[str, str] | None = None,
    provenance: dict[str, str] | None = None,
) -> Path:
    """把一张图的全部底层数据写成一个 .xlsx，文件名与图同名。

    `sheets`  : sheet 名 -> DataFrame（写成 Excel 表；列名保持原始英文，便于再加工）
    `caption` : 这张图讲什么（进 `_manifest`）
    `sources` : sheet 名 -> 该 sheet 的数据来源/口径说明
    `provenance` : 额外溯源键值（如 experiment_id / git_commit / seeds），一并进 `_manifest`
    """
    if not sheets:
        raise ValueError("sheets 不能为空：一张图至少要有一份底层数据")
    out = workbook_path(fig_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for name, df in sheets.items():
        rows.append(
            {
                "sheet": name,
                "figure": fig_path.name,
                "caption": caption,
                "shape": f"{df.shape[0]} rows x {df.shape[1]} cols",
                "columns": ", ".join(str(c) for c in df.columns),
                "source": (sources or {}).get(name, ""),
            }
        )
    for key, value in (provenance or {}).items():
        rows.append(
            {
                "sheet": MANIFEST_SHEET,
                "figure": fig_path.name,
                "caption": f"{key} = {value}",
                "shape": "",
                "columns": "",
                "source": "provenance",
            }
        )
    manifest = pd.DataFrame(rows)

    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        manifest.to_excel(writer, sheet_name=MANIFEST_SHEET, index=False)
        for name, df in sheets.items():
            safe = name[:31]  # Excel sheet 名上限 31 字符
            df.to_excel(writer, sheet_name=safe, index=False)
    return out


__all__ = ["MANIFEST_SHEET", "data_dir", "export_workbook", "workbook_path"]
