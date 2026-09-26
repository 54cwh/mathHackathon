"""learning/loss.py 测试：加权 MSE 数值正确性。"""

from __future__ import annotations

import pytest
import torch

from evogenesis.learning.loss import per_dim_mse, weighted_action_mse
from evogenesis.learning.stats import LossWeights


def _weights(omega: float = 0.8, v: float = 1.2) -> LossWeights:
    return LossWeights(omega=omega, v=v, sigma_omega=1.0, sigma_v=1.0, used_fallback=False)


def test_per_dim_mse_values():
    pred = torch.tensor([[1.0, 0.0], [1.0, 2.0]], dtype=torch.float32)
    target = torch.tensor([[0.0, 0.0], [3.0, 2.0]], dtype=torch.float32)
    mse = per_dim_mse(pred, target)
    assert torch.allclose(mse, torch.tensor([2.5, 0.0], dtype=torch.float32))


def test_weighted_action_mse_matches_manual_formula():
    pred = torch.tensor([[0.2, 0.9], [0.8, 0.1], [0.5, 0.5]], dtype=torch.float32)
    target = torch.tensor([[0.0, 1.0], [1.0, 0.0], [0.5, 0.5]], dtype=torch.float32)
    weights = _weights()
    expected = (
        weights.omega * ((pred[:, 0] - target[:, 0]) ** 2).mean()
        + weights.v * ((pred[:, 1] - target[:, 1]) ** 2).mean()
    )
    assert torch.allclose(weighted_action_mse(pred, target, weights), expected)


def test_weighted_mse_is_scale_of_per_dim_mse():
    pred = torch.rand(4, 2)
    target = torch.rand(4, 2)
    weights = _weights(omega=0.4, v=1.6)
    mse = per_dim_mse(pred, target)
    expected = 0.4 * mse[0] + 1.6 * mse[1]
    assert torch.allclose(weighted_action_mse(pred, target, weights), expected)


def test_shape_mismatch_raises():
    with pytest.raises(ValueError):
        per_dim_mse(torch.zeros(3, 2), torch.zeros(4, 2))


def test_wrong_dimension_raises():
    with pytest.raises(ValueError):
        per_dim_mse(torch.zeros(3, 3), torch.zeros(3, 3))
