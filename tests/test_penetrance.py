"""penetrance 报告层测试（契约：`genome §3`；实验：`experiment §3.9`）。

覆盖：Mendel 装置构造（q 值）、`CV_τ`、Wilson CI、两种校准口径、**分离度诊断**、**分层平衡
抽样**、端到端 payload 与 schema。端到端用小样本，真实规模见 `configs/penetrance.yaml`
（草案待确认）。
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import jsonschema
import numpy as np
import pytest
import torch

from evogenesis.experiment import penetrance as P
from evogenesis.genome import genome as G
from evogenesis.genome.config import DEFAULT_LAYOUT
from evogenesis.pipeline.model_chain import load_model_chain_config, motif_catalog

ROOT = Path(__file__).resolve().parents[1]
MODEL_CONFIG = ROOT / "configs" / "default_model.yaml"
PER_CLASS = 16


# ---------------------------------------------------------------------------
# Mendel 装置（genome §3）
# ---------------------------------------------------------------------------


def test_least_frequent_base_picks_rarest():
    assert G.least_frequent_base("AAACCC") == "G"  # A/C 各 3，G/T 各 0，取字母序 G
    assert G.least_frequent_base("GGGTAA") == "C"


def test_functional_and_loss_chromosome_affinities():
    chain = load_model_chain_config(MODEL_CONFIG)
    motifs = motif_catalog(1103, chain.layout)
    for motif in (motifs[0], motifs[1]):
        func = G.functional_chromosome(motif, layout=DEFAULT_LAYOUT)
        loss = G.loss_chromosome(motif, layout=DEFAULT_LAYOUT)
        assert float(G.chain_affinity(func, motif)) == pytest.approx(1.0)
        assert float(G.chain_affinity(loss, motif)) <= 1.0 / 6.0 + 1e-6


def test_mendel_founder_is_double_heterozygote():
    chain = load_model_chain_config(MODEL_CONFIG)
    motifs = motif_catalog(1103, chain.layout)
    founder = G.mendel_founder(motifs[0], motifs[1], layout=DEFAULT_LAYOUT)
    e_a = float(G.expression_A(founder, motifs, (0,)))
    e_b = float(G.expression_B(founder, motifs, (1,)))
    assert G.architecture(np.float32(e_a), np.float32(e_b), 0.25, 0.25).class_label == "A_B_"


# ---------------------------------------------------------------------------
# 观测量与统计
# ---------------------------------------------------------------------------


def test_cv_tau_on_active_subset():
    tau = torch.tensor([1.0, 3.0, 99.0], dtype=torch.float32)
    active = torch.tensor([True, True, False])
    assert P.cv_tau(tau, active) == pytest.approx(float(np.sqrt(2.0)) / 2.0)
    assert P.cv_tau(tau, torch.tensor([True, False, False])) == 0.0  # 单神经元


def test_observed_architecture_uses_physical_thresholds():
    arch = P.observed_architecture(30, 0.5, theta_N_obs=28.0, theta_H_obs=0.02)
    assert arch == G.Architecture(True, True)
    assert arch.class_label == "A_B_"
    low = P.observed_architecture(20, 0.001, theta_N_obs=28.0, theta_H_obs=0.02)
    assert low.class_label == "aabb"


def test_wilson_interval_bounds_and_none():
    assert P.wilson_interval(0, 0) is None
    low_interval = P.wilson_interval(0, 10)
    assert low_interval is not None
    assert low_interval[0] == 0.0 and 0.2 < low_interval[1] < 0.35
    high_interval = P.wilson_interval(10, 10)
    assert high_interval is not None
    assert high_interval[1] <= 1.0 and high_interval[0] > 0.65
    with pytest.raises(ValueError):
        P.wilson_interval(11, 10)


def test_min_misclassification_threshold():
    values = [1.0, 2.0, 3.0, 4.0]
    theta, rate = P.min_misclassification_threshold(values, [False, False, True, True])
    assert theta == pytest.approx(2.5) and rate == 0.0
    _, rate_low = P.min_misclassification_threshold(values, [False, False, False, False])
    assert rate_low == 0.0
    with pytest.raises(ValueError):
        P.min_misclassification_threshold([], [])


def test_median_midpoint_threshold():
    assert P.median_midpoint_threshold([1.0, 3.0, 10.0], [False, True, True]) == pytest.approx(
        (1.0 + 6.5) / 2.0
    )
    with pytest.raises(ValueError):
        P.median_midpoint_threshold([1.0, 2.0], [True, True])


def test_axis_separation_detects_signal_and_noise():
    # 有信号：8+8 完全分离 ⇒ AUC=1，p 远低于门禁水平（n=4 时 Mann–Whitney 最小 p=1/3，
    # 达不到任何常规显著水平，故正例用 8+8）
    separable = P.axis_separation([float(v) for v in range(1, 17)], [False] * 8 + [True] * 8)
    assert separable["separable"] is True
    assert separable["auc"] == pytest.approx(1.0)
    assert separable["mannwhitney_p"] is not None
    assert separable["mannwhitney_p"] < P.SEPARATION_ALPHA

    # 两组完全重叠 ⇒ 不可分离：错分 = 多数类基线
    noise = P.axis_separation([1.0, 2.0, 1.0, 2.0], [False, False, True, True])
    assert noise["separable"] is False
    assert noise["min_misclassification_error"] == pytest.approx(noise["majority_baseline_error"])


def test_axis_separation_gate_rejects_chance_level_axis():
    """回归：值-标签**秩完全交错**的零信号轴，旧判据「错分 < 多数类基线」会误判为可分离。

    ``values=1..8`` 配 ``F,T,T,F,F,T,T,F`` ⇒ ``AUC=0.5``、``p=1.0``；但 min-错分率（0.375）
    确实**低于**多数类基线（0.5）—— 因为候选阈值含约 n 个秩切分，其最优者**以极高概率**
    略优于多数类分类器，与是否有信号无关。故门禁必须取 AUC + p（抽样不变），min-错分只作上报诊断。
    """
    axis = P.axis_separation(
        [float(v) for v in range(1, 9)], [False, True, True, False, False, True, True, False]
    )
    assert axis["auc"] == pytest.approx(0.5)
    assert axis["mannwhitney_p"] is not None and axis["mannwhitney_p"] > P.SEPARATION_ALPHA
    # 下行即旧判据的判决：它会翻成 True —— 该断言把回归钉死
    assert axis["min_misclassification_error"] < axis["majority_baseline_error"]
    assert axis["separable"] is False


def test_axis_separation_gate_rejects_inverted_axis():
    """反序轴（high 档取值反而更低）无法用 ``1[v > θ]`` 口径恢复 ⇒ 判不可分离。

    ``p`` 本身显著（0.029 < 0.05），拦住它的是方向条件 ``AUC > 0.5``。
    """
    axis = P.axis_separation(
        [float(v) for v in range(1, 9)], [True, True, True, True, False, False, False, False]
    )
    assert axis["auc"] == pytest.approx(0.0)
    assert axis["mannwhitney_p"] is not None and axis["mannwhitney_p"] < P.SEPARATION_ALPHA
    assert axis["separable"] is False


# ---------------------------------------------------------------------------
# 分层抽样
# ---------------------------------------------------------------------------


def test_stratified_offspring_is_class_balanced():
    chain = load_model_chain_config(MODEL_CONFIG)
    motifs = motif_catalog(1103, chain.layout)
    founder = P._founder_for(motifs, chain.layout)
    individuals, counts = P.stratified_offspring(
        founder,
        motifs,
        theta_N=0.25,
        theta_H=0.25,
        per_class=8,
        master_seed=1103,
        namespace="penetrance_calibration",
        experiment_id="pen-test",
        layout=chain.layout,
    )
    assert counts == {label: 8 for label in P.CLASS_ORDER}
    assert len(individuals) == 32
    # genome_id 紧凑重编号（供 phenotypes_of 反解 index）
    assert [ind.genome_id.split(":")[-1] for ind in individuals[:3]] == [
        "genome0000",
        "genome0001",
        "genome0002",
    ]


# ---------------------------------------------------------------------------
# 端到端（小样本）
# ---------------------------------------------------------------------------


def _small_config() -> P.PenetranceConfig:
    base = P.load_penetrance_config()
    return dataclasses.replace(
        base,
        calibration_master_seeds=(1103,),
        calibration_per_class=PER_CLASS,
        calibration_max_offspring=None,
        report_master_seeds=(1103, 2207),
        report_per_class=PER_CLASS,
        report_max_offspring=None,
        report_demo_offspring=32,
    )


def test_calibration_payload_is_deterministic_and_reports_separation():
    cfg = _small_config()
    first = P.run_calibration("pen-test", penetrance_config=cfg)
    second = P.run_calibration("pen-test", penetrance_config=cfg)
    assert first["digest"] == second["digest"]
    cal = first["calibration"]
    assert cal["n_rows"] == len(P.CLASS_ORDER) * PER_CLASS
    assert first["sampled_per_class"] == {label: PER_CLASS for label in P.CLASS_ORDER}
    # N 轴 θ 自 2026-09-27 起是**逐 seed 居中**刻度 ⇒ 可正可负；H 轴未居中仍须 > 0。
    for key in ("theta_N_obs_min_misclass", "theta_N_obs_median_midpoint"):
        assert abs(cal[key]) < 1e3
    assert cal["theta_H_obs_min_misclass"] > 0
    for axis in ("separation_N", "separation_H"):
        assert set(cal[axis]) >= {
            "separable",
            "auc",
            "mannwhitney_p",
            "min_misclassification_error",
        }


def test_report_requires_frozen_thresholds():
    with pytest.raises(ValueError, match="报告模式要求"):
        P.run_report("pen-test", penetrance_config=_small_config())


def test_report_payload_matches_schema():
    cfg = _small_config()
    cal = P.run_calibration("pen-test", penetrance_config=cfg)["calibration"]
    frozen = dataclasses.replace(
        cfg,
        theta_N_obs=cal["theta_N_obs_min_misclass"],
        theta_H_obs=cal["theta_H_obs_min_misclass"],
        threshold_status="placeholder",
    )
    payload = P.run_report("pen-test", penetrance_config=frozen)
    schema = json.loads((ROOT / "schemas" / "penetrance.schema.json").read_text("utf-8"))
    jsonschema.validate(payload, schema)

    report = payload["report"]
    # 分层平衡：每类每 seed 恰 PER_CLASS，跨 2 seed
    assert sum(report["sampled_per_class"].values()) == len(P.CLASS_ORDER) * PER_CLASS * 2
    pooled = report["pooled"]
    # 出货配置是**单轴**（H 已退役）⇒ 两轴的 4 格观测分箱与 4 类反推必须**缺席**
    assert pooled["readout"] == "N"
    assert pooled["observed_architecture_counts"] is None
    for label in P.CLASS_ORDER:
        stat = pooled["per_class"][label]
        assert stat["n"] == PER_CLASS * 2
        assert 0.0 <= stat["wilson_low"] <= stat["penetrance"] <= stat["wilson_high"] <= 1.0
        assert stat["observed_2x2"] is None
        assert list(stat["observed_bins"]) == ["N"]  # 只有生效轴
        assert sum(stat["observed_bins"]["N"].values()) == PER_CLASS * 2
    # 未分层演示样本仅用于计数（与 pen 估计分开）；4 类反推需两轴 ⇒ 单轴下为 None
    demo = report["demo_9331"]
    assert sum(demo["pooled_expected_counts"].values()) == 32 * 2
    assert demo["observed_counts"] is None


# ---------------------------------------------------------------------------
# 效应量下限（separation_auc_floor）
# ---------------------------------------------------------------------------


def test_auc_floor_off_by_default_is_bit_identical():
    """`auc_floor=None`（默认）不得改动任何既有字段 —— 口径与历史逐位一致。"""
    values = [float(v) for v in range(1, 17)]
    labels = [False] * 8 + [True] * 8
    base = P.axis_separation(values, labels)
    explicit_none = P.axis_separation(values, labels, auc_floor=None)
    assert explicit_none == base
    assert base["auc_floor"] is None
    assert base["separable"] is True


def test_auc_floor_filters_a_significant_but_small_effect():
    """floor 的用处：把「显著但效应小」的轴拦下。

    此前后两条只查 ``AUC > 0.5`` 与 ``p < α`` —— 大 n 下 ``AUC=0.51`` 也能过。
    边界用实测 AUC 自身（不手算），使断言与实现同源。
    """
    values = [float(v) for v in range(1, 17)] + [float(v) for v in range(9, 25)]
    labels = [False] * 16 + [True] * 16
    bare = P.axis_separation(values, labels)
    assert bare["separable"] is True  # 前两条仍过
    assert 0.5 < bare["auc"] < 1.0  # 但效应远非完美
    auc = bare["auc"]
    assert P.axis_separation(values, labels, auc_floor=auc + 1e-6)["separable"] is False
    assert P.axis_separation(values, labels, auc_floor=auc)["separable"] is True
    floored = P.axis_separation(values, labels, auc_floor=auc + 1e-6)
    assert floored["auc_floor"] == pytest.approx(auc + 1e-6)


# ---------------------------------------------------------------------------
# 生效轴（active_axes）—— 2026-09-27 裁决：H 轴退役，门禁只看 N
# ---------------------------------------------------------------------------


def test_active_axes_default_is_single_axis_n():
    assert P.SEPARATION_AXES == ("N", "H")  # 两轴仍可声明
    assert P._parse_active_axes(None) == ("N",)
    assert P._parse_active_axes(["N", "H"]) == ("N", "H")


def test_active_axes_rejects_empty_unknown_and_duplicate():
    for bad in ([], ["X"], ["N", "N"]):
        with pytest.raises(ValueError):
            P._parse_active_axes(bad)


def _rows_n_separable_h_not() -> list[P.PenetranceRow]:
    """N 轴完全分离、H 轴恒值（不可分离）的最小样本 —— 复现 H 轴退役的现场。"""
    rows: list[P.PenetranceRow] = []
    for i, label in enumerate(P.CLASS_ORDER):
        for k in range(4):
            rows.append(
                P.PenetranceRow(
                    genome_id=f"g{i:02d}{k}",
                    fish_id=f"f{i:02d}{k}",
                    expected_class=label,
                    master_seed=1103,
                    e_a=1.0 if label in P.EXPECTED_HIGH_N else 0.0,
                    e_b=1.0 if label in P.EXPECTED_HIGH_H else 0.0,
                    n_neurons=(40 if label in P.EXPECTED_HIGH_N else 20) + k,
                    cv_tau=0.010 + 0.001 * k,
                    viable=True,
                )
            )
    return rows


def test_confirmable_ignores_retired_axis():
    """门禁只看生效轴：N 可分离而 H 不可分离时，`active_axes=("N",)` ⇒ confirmable=True。

    这就是 2026-09-27 裁决要兑现的行为 —— 此前「两轴都要可分离」会让 θ 永远无法签署。
    旧行为仍可显式复现（`active_axes=("N","H")`），故不是把判据改松，而是把它参数化。
    """
    rows = _rows_n_separable_h_not()
    only_n = P.calibrate(rows, active_axes=("N",))
    assert only_n.separation_N["separable"] is True
    assert only_n.separation_H["separable"] is False  # H 仍被测量上报
    assert only_n.confirmable is True  # 但不阻塞
    assert only_n.to_dict()["active_axes"] == ["N"]
    assert only_n.to_dict()["confirmable"] is True

    both = P.calibrate(rows, active_axes=("N", "H"))
    assert both.confirmable is False  # 旧行为可复现


def test_config_parses_active_axes_and_floor():
    base = {
        "theta_N_obs": None,
        "theta_H_obs": None,
        "threshold_status": "unset",
        "calibration": {"master_seeds": [1103], "per_class": 4},
        "report": {"master_seeds": [1103], "per_class": 4, "demo_offspring": 8},
    }
    default = P.PenetranceConfig.from_dict(base)
    assert default.active_axes == ("N",)  # 缺省即单轴 N
    assert default.separation_auc_floor is None  # floor 缺省不启用

    explicit = P.PenetranceConfig.from_dict(
        {**base, "active_axes": ["N", "H"], "separation_auc_floor": 0.7}
    )
    assert explicit.active_axes == ("N", "H")
    assert explicit.separation_auc_floor == pytest.approx(0.7)


def test_shipped_penetrance_config_declares_single_axis_n():
    cfg = P.load_penetrance_config()
    assert cfg.active_axes == ("N",)
    assert cfg.separation_auc_floor is None


def test_report_two_axis_mode_is_unchanged():
    """显式声明两轴时报告回到历史口径（4 格观测分箱 + 4 类反推）。

    这条保证「单轴化」是**参数化**：判据没有被改松，只是默认为单轴。
    """
    cfg = dataclasses.replace(_small_config(), active_axes=("N", "H"))
    cal = P.run_calibration("pen-test", penetrance_config=cfg)["calibration"]
    frozen = dataclasses.replace(
        cfg,
        theta_N_obs=cal["theta_N_obs_min_misclass"],
        theta_H_obs=cal["theta_H_obs_min_misclass"],
        threshold_status="placeholder",
    )
    payload = P.run_report("pen-test", penetrance_config=frozen)
    schema = json.loads((ROOT / "schemas" / "penetrance.schema.json").read_text("utf-8"))
    jsonschema.validate(payload, schema)

    pooled = payload["report"]["pooled"]
    total = len(P.CLASS_ORDER) * PER_CLASS * 2
    assert pooled["readout"] == "two_axis"
    assert sum(pooled["observed_architecture_counts"].values()) == total
    for label in P.CLASS_ORDER:
        stat = pooled["per_class"][label]
        assert sum(stat["observed_2x2"].values()) == PER_CLASS * 2
        assert sorted(stat["observed_bins"]) == ["H", "N"]
    assert sum(payload["report"]["demo_9331"]["observed_counts"].values()) == 32 * 2
    assert payload["report"]["continuous"]["A_B_"]["cv_tau"]["n"] == PER_CLASS * 2


def test_report_single_axis_needs_no_theta_H_obs():
    """H 退役后不再需要「展示用 θ_H^obs」—— 只要求**生效轴**的阈值；两轴模式仍要求两者。"""
    cal = P.run_calibration("pen-test", penetrance_config=_small_config())["calibration"]
    single = dataclasses.replace(
        _small_config(),
        theta_N_obs=cal["theta_N_obs_min_misclass"],
        theta_H_obs=None,  # H 退役 ⇒ 不签
        threshold_status="placeholder",
    )
    payload = P.run_report("pen-test", penetrance_config=single)
    assert payload["observation_thresholds"]["theta_H_obs"] is None
    assert payload["report"]["pooled"]["readout"] == "N"
    # cv_tau 仍照常进连续摘要（退役 ≠ 不测量）
    assert payload["report"]["continuous"]["aabb"]["cv_tau"]["n"] == PER_CLASS * 2

    two = dataclasses.replace(single, active_axes=("N", "H"))
    with pytest.raises(ValueError, match="生效轴"):
        P.run_report("pen-test", penetrance_config=two)


def test_penetrance_stats_single_axis_counts_n_agreement():
    """单轴读数的定义：``hits`` = 观测 N 档与**期望 N 档**一致的个体数。"""
    rows = _rows_n_separable_h_not()  # N 完全分离、H 恒值
    # θ 是居中刻度：本样本 16 行的池化中位 31.5 ⇒ 高类 +8.5..+11.5、低类 -11.5..-8.5
    stats = P.penetrance_stats(rows, theta_N_obs=0.0, theta_H_obs=None, active_axes=("N",))
    assert stats["readout"] == "N"
    assert stats["observed_architecture_counts"] is None
    for label in P.CLASS_ORDER:
        stat = stats["per_class"][label]
        assert stat["n"] == 4
        assert stat["hits"] == 4 and stat["penetrance"] == 1.0  # N 档与期望档逐个体一致
        assert stat["observed_2x2"] is None
        expected_high = label in P.EXPECTED_HIGH_N
        assert stat["observed_bins"]["N"]["high" if expected_high else "low"] == 4


def _row(seed: int, label: str, n_neurons: int, uid: str) -> P.PenetranceRow:
    """玩具行：N 轴读数 + master_seed（其余字段与本组断言无关）。"""
    return P.PenetranceRow(
        genome_id=f"g{uid}",
        fish_id=f"f{uid}",
        expected_class=label,
        master_seed=seed,
        e_a=0.0,
        e_b=0.0,
        n_neurons=n_neurons,
        cv_tau=0.01,
        viable=True,
    )


def test_seed_offset_is_removed_by_centering():
    """seed 级基线漂移必须被居中消掉 —— 2026-09-27 实测现场的最小复现。

    四个 seed 依次错开（远大于类间效应）：不居中时池化 AUC≈0.59（seed 级偏移把组间
    差异抵消掉一半）、门禁判**不可分离**；居中后 AUC≈0.83、p<0.05 ⇒ 可分离。
    （每 seed 类数相等 ⇒ 组内/跨 seed 对数各半，原始 AUC 的下限即约 0.6。）
    真实 3 seed 实测同向（0.626 → 0.870）。
    """
    rows: list[P.PenetranceRow] = []
    for seed, offset in ((1103, 0), (2207, 15), (3301, 30), (4409, 45)):
        for label in P.CLASS_ORDER:
            for k in range(6):
                base = 3 if label in P.EXPECTED_HIGH_N else 0
                rows.append(_row(seed, label, offset + base + k, f"{seed}-{label}-{k}"))
    labels = [r.expected_class in P.EXPECTED_HIGH_N for r in rows]
    raw = P.axis_separation([float(r.n_neurons) for r in rows], labels)
    centered = P.axis_separation(P.centered_n(rows), labels)
    assert raw["auc"] < 0.65 and raw["separable"] is False
    assert centered["auc"] > 0.8 and centered["separable"] is True
    baselines = P.seed_baselines(rows)
    assert baselines[4409] - baselines[1103] > 14  # 漂移是真的，不是舍入


def test_seed_baseline_is_reusable_across_samples():
    """未分层样本必须复用**分层集**的基线：自身中位会被多数类拉偏。

    9:3:3:1 演示集不分层；若按自身中位居中，多数类会把基线抬到自己身上、人为压平读数。
    故 ``run_report`` 把分层集估计的基线下传给演示集（``_genotype_counts(baselines=...)``）。
    """
    balanced = [
        _row(1103, "A_B_", 1, "b1"),
        _row(1103, "A_bb", 1, "b2"),
        _row(1103, "aaB_", -1, "b3"),
        _row(1103, "aabb", -1, "b4"),
    ]
    baselines = P.seed_baselines(balanced)
    assert baselines[1103] == 0.0  # 分层 ⇒ 中位与基因型无关

    skewed = [_row(1103, "A_B_", 1, f"s{i}") for i in range(18)]
    skewed += [_row(1103, "aabb", -1, f"t{i}") for i in range(2)]

    own = P.centered_n(skewed)
    reused = P.centered_n(skewed, baselines)
    assert max(own) == 0.0 and min(own) == -2.0  # 自身中位 = +1 ⇒ 多数类被压成 0
    assert max(reused) == 1.0 and min(reused) == -1.0  # 分层基线 = 0 ⇒ 保留真实偏移
