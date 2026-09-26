"""penetrance 报告层测试（契约：`genome §3`；实验：`experiment §3.9`）。

覆盖：Mendel 装置构造（q 值）、`CV_τ`、Wilson CI、两种校准口径、观测档、逐类 pen 的
端到端 payload 与 schema。端到端用小样本（校准 120 / 报告 40），真实规模见
`configs/penetrance.yaml`（草案待确认）。
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


# ---------------------------------------------------------------------------
# 端到端（小样本）
# ---------------------------------------------------------------------------


def _small_config() -> P.PenetranceConfig:
    base = P.load_penetrance_config()
    return dataclasses.replace(
        base,
        calibration_master_seeds=(1103,),
        calibration_offspring=120,
        report_master_seeds=(1103, 2207),
        report_offspring=40,
    )


def test_calibration_payload_is_deterministic_and_reports_both_rules():
    cfg = _small_config()
    first = P.run_calibration("pen-test", penetrance_config=cfg)
    second = P.run_calibration("pen-test", penetrance_config=cfg)
    assert first["digest"] == second["digest"]
    cal = first["calibration"]
    assert cal["n_rows"] == 120
    assert sum(first["genotype_counts"].values()) == 120
    for key in ("theta_N_obs_min_misclass", "theta_N_obs_median_midpoint"):
        assert cal[key] > 0
    for key in ("theta_H_obs_min_misclass", "theta_H_obs_median_midpoint"):
        assert cal[key] > 0
    # AaBb×AaBb 四类都应出现（120 例下 aabb 期望 7.5，允许极端种子缺失但此处固定种子恒有）
    assert set(first["genotype_counts"]) == set(P.CLASS_ORDER)


def test_report_requires_frozen_thresholds():
    with pytest.raises(ValueError, match="已冻结"):
        P.run_report("pen-test", penetrance_config=_small_config())


def test_report_payload_matches_schema():
    cfg = _small_config()
    cal = P.run_calibration("pen-test", penetrance_config=cfg)["calibration"]
    frozen = dataclasses.replace(
        cfg,
        theta_N_obs=cal["theta_N_obs_min_misclass"],
        theta_H_obs=cal["theta_H_obs_min_misclass"],
    )
    payload = P.run_report("pen-test", penetrance_config=frozen)
    schema = json.loads((ROOT / "schemas" / "penetrance.schema.json").read_text("utf-8"))
    jsonschema.validate(payload, schema)

    pooled = payload["report"]["pooled"]
    assert sum(pooled["observed_architecture_counts"].values()) == 2 * 40
    for label in P.CLASS_ORDER:
        stat = pooled["per_class"][label]
        if stat["n"] > 0:
            assert stat["penetrance"] is not None
            assert 0.0 <= stat["wilson_low"] <= stat["penetrance"] <= stat["wilson_high"] <= 1.0
        else:
            assert stat["penetrance"] is None
