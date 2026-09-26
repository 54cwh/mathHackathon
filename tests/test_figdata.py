"""图表 ↔ Excel 数据导出的守护测试（长期要求：图必须有配套数据表）。

守住三件事：
1. **命名对应**：Excel 与图**同名不同后缀**，且落在图同级的 `data/` 下（同名即可对应）；
2. **`_manifest` 必在**且位于第一个 sheet：逐 sheet 写明 caption / 形状 / 来源；
3. **数值可回读**：写出的数据与内存中的 DataFrame 逐值一致（不是只写个壳）。
"""

from pathlib import Path

import pandas as pd
import pytest

from evogenesis.experiment.figdata import (
    MANIFEST_SHEET,
    data_dir,
    export_workbook,
    workbook_path,
)


def test_workbook_path_is_same_stem_under_data_dir():
    """命名对应：只换后缀、加 `data/`；同名即对应，不靠人工映射。"""
    fig = Path("results/figs/exp_a") / "fig_metrics_mean_std.png"
    assert workbook_path(fig) == Path("results/figs/exp_a/data/fig_metrics_mean_std.xlsx")
    assert workbook_path(fig).stem == fig.stem
    assert data_dir(fig.parent) == fig.parent / "data"


def test_export_writes_manifest_first_and_data(tmp_path: Path):
    fig = tmp_path / "fig_demo.png"
    fig.write_bytes(b"")  # 图的占位（本模块不读图，只按路径定名）
    df = pd.DataFrame({"metric": ["a", "b"], "mean": [0.1, 0.2], "std": [0.01, 0.02]})
    out = export_workbook(
        fig,
        {"metrics": df},
        caption="demo caption",
        sources={"metrics": "unit test"},
        provenance={"experiment_id": "exp_test", "git_commit": "abc1234"},
    )
    assert out.exists() and out.suffix == ".xlsx"
    xl = pd.ExcelFile(out)
    assert xl.sheet_names[0] == MANIFEST_SHEET  # manifest 必须第一个
    assert "metrics" in xl.sheet_names

    man = xl.parse(MANIFEST_SHEET)
    assert set(["sheet", "figure", "caption", "shape", "columns", "source"]) <= set(man.columns)
    # manifest 里能找到该数据表与两条 provenance
    assert "metrics" in set(man["sheet"])
    prov = man[man["source"] == "provenance"]
    assert any("exp_test" in str(c) for c in prov["caption"])
    assert any("abc1234" in str(c) for c in prov["caption"])


def test_roundtrip_values_identical(tmp_path: Path):
    """回读必须逐值一致 —— 防止只写一个壳。"""
    fig = tmp_path / "fig_rt.png"
    df = pd.DataFrame(
        {
            "seed": [1103, 2207, 3301],
            "prey_capture": [0.4355, 0.6684, 0.5184],
            "std": [None, 0.1, 0.2],
        }
    )
    out = export_workbook(fig, {"by_seed": df}, caption="rt")
    back = pd.read_excel(out, sheet_name="by_seed")
    pd.testing.assert_frame_equal(back, df, check_dtype=False)


def test_empty_sheets_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        export_workbook(tmp_path / "fig_x.png", {}, caption="empty")


def test_long_sheet_name_truncated_to_excel_limit(tmp_path: Path):
    """Excel sheet 名上限 31 字符；超长名须截断而不是报错。"""
    name = "x" * 40
    fig = tmp_path / "fig_long.png"
    out = export_workbook(fig, {name: pd.DataFrame({"a": [1]})}, caption="long name")
    xl = pd.ExcelFile(out)
    assert MANIFEST_SHEET in xl.sheet_names
    assert all(len(s) <= 31 for s in xl.sheet_names)
