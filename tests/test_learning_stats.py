"""learning/stats.py 测试：σ(ddof=0)、λ 下限与缩放、回退值。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from evogenesis.core.config import ModelConfig, load_config
from evogenesis.learning.stats import (
    DEFAULT_ACTION_RANGES,
    compute_loss_weights,
    population_std,
)

ROOT = Path(__file__).resolve().parents[1]
CFG = load_config(ROOT / "configs" / "default_model.yaml", model=ModelConfig).learning
FLOOR_RATIO = CFG.loss_variance_floor_ratio
FALLBACK_OMEGA = CFG.loss_weight_fallback_omega
FALLBACK_V = CFG.loss_weight_fallback_v


def _weights(actions: np.ndarray):
    return compute_loss_weights(
        actions,
        floor_ratio=FLOOR_RATIO,
        fallback_omega=FALLBACK_OMEGA,
        fallback_v=FALLBACK_V,
    )


def test_population_std_uses_ddof_zero():
    actions = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]], dtype=np.float32)
    sigma = population_std(actions)
    assert np.allclose(sigma, actions.std(axis=0, ddof=0), atol=0.0)


def test_loss_weights_sum_to_two():
    actions = np.array([[-1.0, 0.1], [0.0, 0.2], [1.0, 0.4], [0.5, 0.9]], dtype=np.float32)
    weights = _weights(actions)
    assert weights.omega + weights.v == pytest.approx(2.0, abs=1e-6)
    assert not weights.used_fallback


def test_floor_ratio_applies_when_sigma_is_zero_for_one_dim():
    actions = np.zeros((4, 2), dtype=np.float32)
    actions[:, 0] = 0.7  # σ_ω = 0 → 触发下限 0.05·R_ω
    # 对称取值 ±0.3 的总体 std 恰为 0.3
    actions[:, 1] = np.array([0.0, 0.0, 0.3, -0.3], dtype=np.float32)
    floor = FLOOR_RATIO * np.asarray(DEFAULT_ACTION_RANGES, dtype=np.float32)
    sigma = population_std(actions)
    assert sigma[0] == pytest.approx(0.0)
    raw = 1.0 / np.maximum(sigma, floor) ** 2
    expected = raw * (2.0 / raw.sum())
    weights = _weights(actions)
    assert weights.omega == pytest.approx(float(expected[0]), rel=1e-5)
    assert weights.v == pytest.approx(float(expected[1]), rel=1e-5)
    assert weights.omega + weights.v == pytest.approx(2.0, abs=1e-6)
    # 下限使 σ=0 维不再除零，且权重有限
    assert np.isfinite(weights.omega) and np.isfinite(weights.v)


def test_both_sigma_zero_reduces_to_preregistered_fallback():
    actions = np.array([[0.5, 0.25], [0.5, 0.25]], dtype=np.float32)
    weights = _weights(actions)
    assert weights.sigma_omega == pytest.approx(0.0)
    assert weights.sigma_v == pytest.approx(0.0)
    assert weights.omega == pytest.approx(FALLBACK_OMEGA, abs=1e-6)
    assert weights.v == pytest.approx(FALLBACK_V, abs=1e-6)
    assert weights.omega + weights.v == pytest.approx(2.0, abs=1e-6)


def test_empty_dataset_uses_fallback_with_flag():
    actions = np.empty((0, 2), dtype=np.float32)
    weights = _weights(actions)
    assert weights.used_fallback
    assert weights.omega == pytest.approx(FALLBACK_OMEGA)
    assert weights.v == pytest.approx(FALLBACK_V)


def test_invalid_floor_ratio_raises():
    actions = np.zeros((2, 2), dtype=np.float32)
    with pytest.raises(ValueError, match="floor_ratio"):
        compute_loss_weights(actions, floor_ratio=0.0, fallback_omega=0.4, fallback_v=1.6)


def test_wrong_action_shape_raises():
    with pytest.raises(ValueError, match="形状"):
        _weights(np.zeros((3, 3), dtype=np.float32))
