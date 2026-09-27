"""F7 连接矩阵图（`scripts/make_fig_connectome.py`）的守护测试。

守住四件事：

1. **图与落盘矩阵同源**：图脚本**只读** `connectome_matrix.json`，不重新发育、不重算
   尺寸 —— 故「图上写的支撑边数」== 「CSV 里的支撑边数」是结构性的，不是巧合。
   缺件时必须给出能照着做的报错，而不是静默画一张空图。
2. **配套 Excel 合规**（`paper/图表-数据对照表.md` §1）：与图**同名**、落在同级 `data/`、
   首 sheet 为 `_manifest`，且 `matrix` / `summary` / `cell_types` 三个必需 sheet 在册。
3. **长表可读**：48x48 摊成 2304 行的长表（可筛可排序），而不是把 2304 行塞进一张宽表；
   宽表只保留 primary 个体的 48x49 两张（`w0_wide` / `support_wide`）。
4. **图里两组易混对比有落点**：`w0_wide` 的补零区恒 0（容量 48 vs 实际 N），
   `representatives` 的 `probe_support_edges` 与 `support_edges` 相等（支撑 vs 全张量）。

小样本跑（1 seed x 14 个体），payload 在 module 级共享。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from evogenesis.viz import fig_connectome
from evogenesis.viz.figdata import MANIFEST_SHEET, workbook_path

ROOT = Path(__file__).resolve().parents[1]
#: 出图 CLI（薄壳，命令路径不变）与数据落盘脚本（数据层，仍属 `scripts/`）。
SCRIPT = ROOT / "scripts" / "make_fig_connectome.py"
DUMP_SCRIPT = ROOT / "scripts" / "dump_connectome_matrix.py"

PROBE_SEED = 1103
SAMPLE_N = 14
#: 必需的三个数据 sheet（`paper/图表-数据对照表.md` §1 的「至少含」清单）。
REQUIRED_SHEETS = ("matrix", "summary", "cell_types")


def _load_script(name: str, path: Path):
    """把脚本当模块载入（`scripts/` 不是包，故走 importlib 按路径载入）。"""
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def dump():
    return _load_script("dump_connectome_matrix", DUMP_SCRIPT)


@pytest.fixture(scope="module")
def figmod():
    return fig_connectome


@pytest.fixture(scope="module")
def payload(dump):
    return dump.build_payload([PROBE_SEED], n_individuals=SAMPLE_N)


@pytest.fixture(scope="module")
def built(figmod, payload, tmp_path_factory):
    """一次出图 + 出表（module 级共享；图脚本本身只读 payload）。"""
    out_dir = tmp_path_factory.mktemp("fig_connectome")
    note = "unit test note"
    fig_path, workbook, sheets, provenance = figmod.build_figure(payload, out_dir, note)
    return fig_path, workbook, sheets, provenance


# ---------------------------------------------------------------------------
# 1. 图与落盘矩阵同源
# ---------------------------------------------------------------------------


def test_load_matrix_payload_round_trips(figmod, payload, tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    assert figmod.load_matrix_payload(path) == payload


def test_missing_matrix_json_gives_actionable_error(figmod, tmp_path):
    """缺件时必须说清「先跑哪个脚本」—— 否则只会得到一句 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError, match="dump_connectome_matrix"):
        figmod.load_matrix_payload(tmp_path / "nope.json")


def test_payload_without_representatives_is_rejected(figmod, payload, tmp_path):
    """样本里没有可构造个体时不能出图（否则会画一张没有矩阵的空图）。"""
    hollow = json.loads(json.dumps(payload))
    hollow["representatives"] = []
    path = tmp_path / "m.json"
    path.write_text(json.dumps(hollow, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="代表个体"):
        figmod.load_matrix_payload(path)


def test_unknown_payload_is_rejected(figmod, tmp_path):
    path = tmp_path / "m.json"
    path.write_text('{"probe": "something-else"}', encoding="utf-8")
    with pytest.raises(ValueError, match="connectome_matrix"):
        figmod.load_matrix_payload(path)


def test_primary_representative_is_the_first_seed(figmod, payload):
    rep = figmod.primary_representative(payload)
    assert rep["is_primary"] is True
    assert rep["master_seed"] == payload["master_seeds"][0]
    assert sum(1 for r in payload["representatives"] if r.get("is_primary")) == 1


def test_matrix_sheet_equals_the_dumped_long_table(figmod, dump, payload, built):
    """Excel 的 `matrix` sheet 必须**逐值**等于 dump 脚本的长表 —— 图与 CSV 不得分叉。"""
    _fig_path, _workbook, sheets, _provenance = built
    expected = pd.DataFrame(dump.long_records(payload))
    pd.testing.assert_frame_equal(
        sheets["matrix"], expected, check_dtype=False, check_column_type=False
    )
    assert tuple(sheets["matrix"].columns) == dump.LONG_COLUMNS
    assert len(sheets["matrix"]) == payload["max_nodes"] ** 2 * len(payload["representatives"])


# ---------------------------------------------------------------------------
# 2. 配套 Excel 合规
# ---------------------------------------------------------------------------


def test_build_figure_writes_png_and_same_stem_workbook(figmod, payload, tmp_path):
    fig_path, workbook, _sheets, _prov = figmod.build_figure(payload, tmp_path, "note")
    assert fig_path == tmp_path / "fig_connectome.png"
    assert fig_path.is_file() and fig_path.stat().st_size > 0
    assert workbook_path(fig_path) == workbook == tmp_path / "data" / "fig_connectome.xlsx"
    assert workbook.is_file()
    assert workbook.stem == fig_path.stem


def test_workbook_has_manifest_first_and_required_sheets(figmod, built):
    _fig_path, workbook, sheets, _provenance = built
    xl = pd.ExcelFile(workbook)
    assert xl.sheet_names[0] == MANIFEST_SHEET, "manifest 必须是第一个 sheet"

    manifest = xl.parse(MANIFEST_SHEET)
    for column in ("sheet", "figure", "caption", "shape", "columns", "source"):
        assert column in manifest.columns
    assert set(REQUIRED_SHEETS) <= set(sheets)
    assert set(sheets) <= set(manifest["sheet"])

    data_rows = manifest[manifest["sheet"].isin(sheets)]
    assert data_rows["shape"].fillna("").str.contains("rows x").all()
    assert data_rows["source"].fillna("").ne("").all()


def test_manifest_carries_traceable_provenance(figmod, payload, built):
    """不看代码也能复核：来源脚本、digest、primary 个体、E/I 边数、张量容量都在 manifest 里。"""
    _fig_path, workbook, _sheets, provenance = built
    manifest = pd.ExcelFile(workbook).parse(MANIFEST_SHEET)
    texts = " ".join(manifest["caption"].fillna("").astype(str)) + " ".join(
        manifest["source"].fillna("").astype(str)
    )

    assert str(PROBE_SEED) in texts
    assert "digest" in texts
    assert "connectome_matrix.json" in texts
    assert provenance["matrix_json_digest"] == payload["digest"]
    assert provenance["tensor_cells_per_individual"] == str(payload["max_nodes"] ** 2)
    assert provenance["primary_representative"] == "seed 1103 index 0"

    rep = figmod.primary_representative(payload)
    assert provenance["primary_n_neurons"] == str(rep["n_neurons"])
    assert provenance["primary_support_edges"] == str(rep["support_edges"])
    assert provenance["primary_excitatory_edges"] == str(rep["excitatory_edges"])
    assert provenance["primary_inhibitory_edges"] == str(rep["inhibitory_edges"])


def test_data_sheets_round_trip(figmod, built):
    _fig_path, workbook, sheets, _provenance = built
    xl = pd.ExcelFile(workbook)
    for name in sheets:
        back = xl.parse(name)
        pd.testing.assert_frame_equal(
            back, sheets[name], check_dtype=False, check_column_type=False
        )


# ---------------------------------------------------------------------------
# 3. 长表可读 / 两组易混对比有落点
# ---------------------------------------------------------------------------


def test_wide_sheets_are_48_by_49_not_2304_rows(figmod, payload, built):
    """48x48 宽表是 48 行 x 49 列（含行号列）；2304 行那种宽表在 Excel 里不可读。"""
    _fig_path, _workbook, sheets, _provenance = built
    max_nodes = payload["max_nodes"]
    for name in ("w0_wide", "support_wide"):
        assert sheets[name].shape == (max_nodes, max_nodes + 1), name
        assert sheets[name]["row"].tolist() == list(range(max_nodes))


def test_wide_sheets_show_capacity_48_vs_realized_n(figmod, payload, built):
    """补零区恒 0：这正是 F7 (a) 面板要展示的「容量 48 != 实际 N」。"""
    _fig_path, _workbook, sheets, _provenance = built
    rep = figmod.primary_representative(payload)
    n = rep["n_neurons"]
    w0 = sheets["w0_wide"].drop(columns=["row"]).to_numpy()
    support = sheets["support_wide"].drop(columns=["row"]).to_numpy()
    assert w0.shape == (payload["max_nodes"], payload["max_nodes"])
    assert abs(w0[n:, :]).sum() == 0.0
    assert abs(w0[:, n:]).sum() == 0.0
    assert support[n:, :].sum() == 0
    assert support[:, n:].sum() == 0
    # 活跃块内确实有支撑（否则这张图什么也没画）
    assert support[:n, :n].sum() == rep["support_edges"]


def test_representatives_sheet_cross_checks_the_probe_caliber(figmod, payload, built):
    """支撑 vs 全张量：`support_edges` 必须等于 probe 的读数，且远小于 2304。"""
    _fig_path, _workbook, sheets, _provenance = built
    frame = sheets["representatives"]
    assert len(frame) == len(payload["representatives"])
    for row in frame.itertuples():
        assert row.support_edges == row.probe_support_edges
        assert row.trainable_elements == row.support_edges == row.probe_trainable_elements
        assert row.support_edges < row.tensor_elements
        assert 0.0 < row.support_share_of_tensor < 0.5


def test_summary_sheet_is_the_probe_records_verbatim(figmod, payload, built):
    """`summary` 是 probe 的逐个体记录原样搬运：不漏个体、不插补可训练数。

    2026-09-26 实测：本档 14/14 全部可构造（旧档含 2 个 motor 池为空的失败者），
    故「失败行留痕」改由下一条**显式注入**守护；此处钉住逐个体搬运与「数值即守护」。
    """
    _fig_path, _workbook, sheets, _provenance = built
    frame = sheets["summary"]
    records = payload["architecture_probe"]["per_individual"]
    assert len(frame) == len(records)
    assert int(frame["danionet_built"].sum()) == sum(1 for r in records if r["danionet_built"])
    assert int(frame["is_representative"].sum()) == len(payload["representatives"])

    # 数值即守护：本档全部可构造，口径再变时这里红灯
    assert int(frame["danionet_built"].sum()) == len(records)
    for row in frame.itertuples():
        assert row.danionet_built
        assert row.trainable_elements == row.support_edges


def test_summary_sheet_does_not_drop_unbuildable_rows(figmod, dump, payload):
    """注入一行构造失败记录：`summary_records` 必须保留它，且**不插补**可训练数。

    「不静默丢 + 不插补」是 `summary` sheet 的核心承诺；本档真实数据已无失败个体，
    故显式构造最小 payload 走 `dump.summary_records` 直接验证该承诺。
    """
    domains = tuple(payload["domains"])
    good = {
        "master_seed": PROBE_SEED, "index": 0, "n_neurons": 40, "active_neurons": 40,
        "support_edges": 238, "support_density": 0.152564, "trainable_elements": 238,
        "phenotype_viable": True, "danionet_built": True,
        "cell_type_counts": {d: 6 for d in domains},
    }
    bad = dict(good)
    bad.update({
        "index": 1, "n_neurons": 36, "active_neurons": 36, "support_edges": 195,
        "support_density": 0.154762, "trainable_elements": None,
        "phenotype_viable": False, "danionet_built": False,
    })
    rows = dump.summary_records({
        "representatives": [],
        "architecture_probe": {"per_individual": [good, bad]},
    })
    assert len(rows) == 2, "失败行不得被静默丢弃"
    assert [r["danionet_built"] for r in rows] == [True, False]
    assert rows[1]["trainable_elements"] is None, "失败行不得插补可训练数"
    assert rows[1]["support_edges"] > 0, "支撑本身仍应可测（失败只发生在 DanioNet 装配）"
    assert all(r["is_representative"] is False for r in rows)


def test_cell_types_sheet_covers_all_six_types(figmod, payload, built):
    _fig_path, _workbook, sheets, _provenance = built
    frame = sheets["cell_types"]
    assert set(frame["cell_type"]) == set(payload["domains"])
    per_individual = frame.groupby(["master_seed", "individual_index"])["n_cells"].sum()
    expected = {
        (r["master_seed"], r["index"]): r["n_neurons"]
        for r in payload["architecture_probe"]["per_individual"]
    }
    for key, total in per_individual.items():
        assert int(total) == expected[key]


def test_population_sheet_reports_the_method_section_sizes(figmod, payload, built):
    """population sheet 必须能查到论文引用的那三个尺寸口径。"""
    _fig_path, _workbook, sheets, _provenance = built
    frame = sheets["population"]
    pooled = frame[(frame["scope"] == "all_individuals") & (frame["quantity"] == "n_neurons")]
    assert len(pooled) == 1
    row = pooled.iloc[0]
    probe_pooled = payload["architecture_probe"]["pooled"]["n_neurons"]
    assert (row["min"], row["median"], row["max"]) == (
        probe_pooled["min"],
        probe_pooled["median"],
        probe_pooled["max"],
    )
    assert (
        frame[frame["quantity"] == "tensor_elements_per_individual"]["median"].iloc[0]
        == payload["max_nodes"] ** 2
    )


# ---------------------------------------------------------------------------
# 4. CLI
# ---------------------------------------------------------------------------


def test_cli_writes_figure_and_workbook(payload, tmp_path):
    """入口可跑：`--json` / `--out-dir` 生效，两个产物都落盘。"""
    import subprocess

    json_path = tmp_path / "m.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "figs"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--json",
            str(json_path),
            "--out-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out_dir / "fig_connectome.png").is_file()
    assert (out_dir / "data" / "fig_connectome.xlsx").is_file()


def test_module_entry_point_uses_utf8_guard():
    """出图模块入口必须调 `force_utf8_stdout()`（`experiment/console.py` 的约定）。"""
    source = Path(fig_connectome.__file__).read_text(encoding="utf-8")
    assert "force_utf8_stdout()" in source
    assert "force_utf8_stdout" in source.split("def main")[1]
