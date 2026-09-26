"""F6 发育 viability 图（`scripts/make_fig_viability.py`）的守护测试。

守住三件事：

1. **可复现**：固定 seed + 固定尝试次数 → 逐次 viable / 判因 / ρ(W⁰) 完全一致
   （这是 F6 存在的理由：把冒烟读数从口头结论变成可重跑的数据）。
2. **配套 Excel 合规**：与图**同名**、落在同级 `data/`、首 sheet 为 `_manifest`，
   且 manifest 里能查到 master_seed / 次数 / 通过数（不看代码也能复核 14/14）。
3. **不迁就结论**：`q` 口径（uniform vs pipeline ``q(G)``）与判因词表必须与
   `development.rgcd` 的实际输出对得上 —— 词表漂移要在这里被抓住。

测试用 ``n=8``/``n=3`` 的小样本跑（`develop` 单次约 10ms，不必跑满 1000）。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from evogenesis.development.config import DEFAULT_CONFIG
from evogenesis.viz import fig_viability
from evogenesis.viz.figdata import MANIFEST_SHEET, workbook_path


@pytest.fixture(scope="module")
def figmod():
    return fig_viability


# ---------------------------------------------------------------------------
# 1. 可复现
# ---------------------------------------------------------------------------


def test_uniform_q_stream_is_deterministic_and_in_unit_cube(figmod):
    a = figmod.uniform_q_stream(1103, 8)
    b = figmod.uniform_q_stream(1103, 8)
    np.testing.assert_array_equal(a, b)
    assert a.shape == (8, DEFAULT_CONFIG.grn_dim)
    assert a.dtype == np.float32
    assert a.min() >= 0.0 and a.max() <= 1.0
    # 不同 seed 必须给出不同流，否则「seed 依赖」就是假的
    assert not np.array_equal(a, figmod.uniform_q_stream(2207, 8))


def test_run_variant_is_reproducible(figmod):
    q = figmod.uniform_q_stream(1103, 6)
    first = figmod.run_variant(1103, q, "uniform_q")
    second = figmod.run_variant(1103, q, "uniform_q")
    pd.testing.assert_frame_equal(first, second)


def test_run_variant_records_every_attempt_with_rho_and_fates(figmod):
    q = figmod.uniform_q_stream(1103, 5)
    df = figmod.run_variant(1103, q, "uniform_q")
    assert len(df) == 5
    for column in ("viable", "reason", "n_active", "rho_w0", *(f"n_{d}" for d in figmod.DOMAINS)):
        assert column in df.columns
    assert df["rho_w0"].notna().all() and (df["rho_w0"] > 0).all()
    # fate 计数只在活跃神经元上统计，故合计必须等于 n_active
    fate_sum = df[[f"n_{d}" for d in figmod.DOMAINS]].to_numpy().sum(axis=1)
    np.testing.assert_array_equal(fate_sum, df["n_active"].to_numpy())


def test_headline_14_reproduces_14_of_14_at_seed_1103(figmod):
    """14 次冒烟读数必须在固定 seed 下可重算 —— 这是本图的立身之本。

    **2026-09-26 由 2/14 改为 14/14**：判据 (ii)``|h|<1``、判据 (iv)``ρ<1`` 与 ``missing_fate``
    被判为**设计约定**（恒真），发育期门禁在正式配置下不再淘汰个体。
    此改动**不是「改断言迁就」** —— 依据是配对反事实实测（臂 A-D）与 κ 标定扫描（无可用工作点），
    见 `research/notes/契约决策记录.md`「§7 发育良构门禁的区分力裁决」与 `rgcd` 的钳制 docstring。
    若此断言**再次**失败：先查 `SeedManager` 与 `rgcd.develop` 的派生式，再看是否又动了设计约定。
    """
    df = figmod.run_variant(figmod.DEFAULT_MASTER_SEED, figmod.uniform_q_stream(1103, 14), "u")
    head = figmod.head_line(df)
    assert head["n_attempts"] == 14
    assert head["n_passed"] == 14, f"seed 1103 的前 14 次应全部通过，实得 {head['n_passed']}"


def test_headline_interval_contains_the_full_sample_rate(figmod):
    """诚实性断言：n=14 的**自身区间**宽到能容纳全样本率（小样本读法）。

    旧版另钉了「n=14 读数约为系统率的 2 倍」。2026-09-26 起结构率本身即 ~1.0
    （判据 (ii)(iv) 与 ``missing_fate`` 均为设计约定，见上一条与本文件模块 docstring），
    该比值不再有内容，故只保留**区间包含**一条 —— 它在两种口径下都成立，
    且是图注必须写对的方向（宽的是小样本那个区间）。
    """
    headline = figmod.head_line(figmod.run_variant(1103, figmod.uniform_q_stream(1103, 14), "u"))
    full = figmod.head_line(figmod.run_variant(1103, figmod.uniform_q_stream(1103, 1000), "u"))
    # 方向正确：宽的是 n=14 那个区间
    assert (headline["wilson_hi"] - headline["wilson_lo"]) > 4 * (
        full["wilson_hi"] - full["wilson_lo"]
    )
    assert headline["wilson_lo"] <= full["pass_rate"] <= headline["wilson_hi"]


def test_genome_q_stream_is_deterministic_and_narrower_than_uniform(figmod):
    """pipeline 的 `q(G)` 明确不是 U[0,1]^8 —— 面板 (D) 的口径警告靠这条守住。"""
    a = figmod.genome_q_stream(1103, 3)
    np.testing.assert_array_equal(a, figmod.genome_q_stream(1103, 3))
    assert a.shape == (3, DEFAULT_CONFIG.grn_dim)
    # 实测 q(G) 落在 ~[0.64, 0.83]；这里只钉「明显窄于单位区间」这个弱得多的事实
    assert a.min() > 0.0 and a.max() < 1.0


# ---------------------------------------------------------------------------
# 2. 统计助手
# ---------------------------------------------------------------------------


def test_wilson_interval_brackets_point_estimate_and_is_bounded(figmod):
    for passed, total in ((2, 14), (0, 14), (14, 14), (71, 1000), (0, 0)):
        lo, hi = figmod.wilson(passed, total)
        assert 0.0 <= lo <= hi <= 1.0
        if total:
            assert lo <= passed / total <= hi
    # n 越大区间越窄（同一点估计）
    assert (figmod.wilson(70, 1000)[1] - figmod.wilson(70, 1000)[0]) < (
        figmod.wilson(7, 100)[1] - figmod.wilson(7, 100)[0]
    )


def test_running_rate_is_monotone_in_n_and_matches_head_line(figmod):
    df = figmod.run_variant(1103, figmod.uniform_q_stream(1103, 20), "u")
    run = figmod.running_rate(df)
    assert list(run["n_attempts"]) == list(range(1, 21))
    assert run["n_passed"].is_monotonic_increasing
    head = figmod.head_line(df)
    assert run["n_passed"].iloc[-1] == head["n_passed"]
    assert run["pass_rate"].iloc[-1] == pytest.approx(head["pass_rate"])


# ---------------------------------------------------------------------------
# 3. 判因词表不漂移
# ---------------------------------------------------------------------------


def test_statuses_splits_multi_cause_and_expands_missing_fate(figmod):
    reason = "missing_fate:prey,motor;motor_side_empty;weight_spectral_radius_not_contractive"
    assert figmod.statuses(reason) == {
        "missing_fate:prey",
        "missing_fate:motor",
        "motor_side_empty",
        "weight_spectral_radius_not_contractive",
    }
    assert figmod.statuses("ok") == set()


def test_observed_reasons_stay_inside_the_documented_vocabulary(figmod):
    """实跑出现的**每个**判因 token 都必须在脚本声明的词表里 —— 漂移即失败。"""
    df = figmod.run_variant(1103, figmod.uniform_q_stream(1103, 40), "u")
    known = {
        *figmod.CRITERIA,
        *(f"{figmod.MISSING_FATE_PREFIX}{d}" for d in DEFAULT_CONFIG.domains),
    }
    for reason in df["reason"]:
        assert figmod.statuses(reason) <= known, f"未登记的判因：{reason!r}"


def test_criteria_table_counts_fate_misses_per_fate(figmod):
    df = pd.DataFrame(
        {"reason": ["missing_fate:prey,motor;motor_side_empty", "ok", "motor_side_empty"]}
    )
    table = figmod.criteria_table(df).set_index("criterion")
    assert table.loc["motor_side_empty", "n_failed"] == 2
    assert table.loc["missing_fate:prey", "n_failed"] == 1
    assert table.loc["missing_fate:motor", "n_failed"] == 1
    assert table.loc["missing_fate:sensory", "n_failed"] == 0
    # 词表齐全：判据 + 六类 fate 一行不少
    assert len(table) == len(figmod.CRITERIA) + len(DEFAULT_CONFIG.domains)


# ---------------------------------------------------------------------------
# 4. 配套 Excel（长期要求：图必须有同名数据表）
# ---------------------------------------------------------------------------


def _tiny_frames(figmod):
    """小样本（冒烟用）：uniform 取 20 次（> HEADLINE_N，使 headline 是真前缀）。"""
    uniform = figmod.run_variant(1103, figmod.uniform_q_stream(1103, 20), "uniform_q")
    genome = figmod.run_variant(1103, figmod.genome_q_stream(1103, 3), "genome_q")
    formal = pd.concat(
        [
            figmod.run_variant(seed, figmod.uniform_q_stream(seed, figmod.HEADLINE_N), "uniform_q")
            for seed in figmod.FORMAL_SEEDS
        ],
        ignore_index=True,
    )
    return uniform, genome, formal


def test_build_figure_writes_png_and_same_stem_workbook(figmod, tmp_path, monkeypatch):
    """一个调用 = 一张图 + 一份**同名不同后缀**的数据表，Excel 落在图同级 `data/`。"""
    monkeypatch.setattr(figmod, "OUT", tmp_path)
    uniform, genome, formal = _tiny_frames(figmod)
    fig_path, workbook, _sheets, _prov = figmod.build_figure(
        uniform, genome, formal, figmod.criteria_table(uniform), "unit test note"
    )
    assert fig_path == tmp_path / "fig_viability.png"
    assert fig_path.is_file() and fig_path.stat().st_size > 0
    assert workbook_path(fig_path) == workbook == tmp_path / "data" / "fig_viability.xlsx"
    assert workbook.is_file()
    assert workbook.stem == fig_path.stem


def test_workbook_has_manifest_first_and_traceable_counts(figmod, tmp_path, monkeypatch):
    monkeypatch.setattr(figmod, "OUT", tmp_path)
    uniform, genome, formal = _tiny_frames(figmod)
    fig_path, workbook, sheets, provenance = figmod.build_figure(
        uniform, genome, formal, figmod.criteria_table(uniform), "unit test note"
    )
    xl = pd.ExcelFile(workbook)
    assert xl.sheet_names[0] == MANIFEST_SHEET, "manifest 必须是第一个 sheet"

    manifest = xl.parse(MANIFEST_SHEET)
    for column in ("sheet", "figure", "caption", "shape", "columns", "source"):
        assert column in manifest.columns
    assert set(sheets) <= set(manifest["sheet"])
    # 每个数据 sheet 都被写明形状与来源（空串经 Excel 往返会变 NaN，故先填回）
    data_rows = manifest[manifest["sheet"].isin(sheets)]
    assert data_rows["shape"].fillna("").str.contains("rows x").all()
    assert data_rows["source"].fillna("").ne("").all()

    # 不看代码也能复核 2/14：seed / 次数 / 通过数都在 manifest 里
    texts = " ".join(manifest["caption"].fillna("").astype(str)) + " ".join(
        manifest["source"].fillna("").astype(str)
    )
    assert str(figmod.DEFAULT_MASTER_SEED) in texts
    assert "headline_n" in texts
    assert "uniform_q" in texts
    assert provenance["headline_passed"] == "14"

    # 数据 sheet 可回读，且与内存中的帧逐值一致
    back = xl.parse("headline_14")
    pd.testing.assert_frame_equal(
        back, sheets["headline_14"], check_dtype=False, check_column_type=False
    )


def test_module_entry_point_uses_utf8_guard():
    """出图模块入口必须调 `force_utf8_stdout()`（`experiment/console.py` 的约定）。"""
    source = Path(fig_viability.__file__).read_text(encoding="utf-8")
    assert "force_utf8_stdout()" in source
    assert "force_utf8_stdout" in source.split("def main")[1]
