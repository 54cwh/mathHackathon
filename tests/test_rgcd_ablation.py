"""w/o GRN 消融测试（`connectome §9`；数学口径 `RGCD §8` 消融段）。"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from evogenesis.development.config import DEFAULT_CONFIG, load_development_config
from evogenesis.development.rgcd import develop

MASTER_SEED = 1103
Q = np.full(8, 0.5, dtype=np.float32)


def _develop(config):
    return develop(Q, master_seed=MASTER_SEED, index=0, config=config)


def test_default_is_control_path():
    assert DEFAULT_CONFIG.ablation_w_grn is False
    phenotype = _develop(DEFAULT_CONFIG)
    # 控制路径（GRN 布线）禁用 self-loop，且发育产出可判定 viability
    assert float(phenotype.adjacency.diagonal().abs().max()) == 0.0
    assert isinstance(phenotype.viable, bool)


def test_w_grn_ablation_is_independent_bernoulli():
    cfg = replace(DEFAULT_CONFIG, ablation_w_grn=True, ablation_random_density=0.15)
    phenotype = _develop(cfg)
    adjacency = phenotype.adjacency
    n = int(adjacency.shape[0])
    assert n > 1
    # 禁 self-loop
    assert float(adjacency.diagonal().abs().max()) == 0.0
    # off-diagonal 密度 ≈ p（Bernoulli 抽样波动；N≥~24 ⇒ 224 自由度内 tol 0.05 安全）
    off = adjacency - adjacency.diagonal().diag()
    density = float(off.sum()) / (n * (n - 1))
    assert abs(density - 0.15) < 0.05


def test_w_grn_ablation_preserves_n_and_tau():
    control = _develop(DEFAULT_CONFIG)
    cfg = replace(DEFAULT_CONFIG, ablation_w_grn=True)
    ablated = _develop(cfg)
    # 只隔离「GRN 布线」：N 与 τ 必须一致
    assert ablated.adjacency.shape == control.adjacency.shape
    assert bool((ablated.tau == control.tau).all())


def test_w_grn_ablation_is_deterministic_for_seed():
    cfg = replace(DEFAULT_CONFIG, ablation_w_grn=True)
    first = _develop(cfg)
    second = _develop(cfg)
    assert bool((first.adjacency == second.adjacency).all())


def test_ablation_flag_reaches_config_via_override():
    cfg = load_development_config(overrides={"connectome": {"ablation_w_grn": True}})
    assert cfg.ablation_w_grn is True
    assert load_development_config().ablation_w_grn is False


def test_invalid_density_raises():
    cfg = replace(DEFAULT_CONFIG, ablation_w_grn=True, ablation_random_density=1.5)
    with pytest.raises(ValueError, match="ablation_random_density"):
        _develop(cfg)
