"""learning/report.py 测试：flip_rate、谱半径、ΔW 恒等与报告汇总（§4 v1.4）。"""

from __future__ import annotations

from pathlib import Path

import pytest
import torch
from test_learning_common import MASTER_SEED, make_dataset, make_net

from evogenesis.core.config import ModelConfig, load_config
from evogenesis.core.seed import SeedManager
from evogenesis.learning.report import (
    build_report,
    delta_w_identity_error,
    sign_flip_rate,
    spectral_radius,
)
from evogenesis.learning.train import train_bc

ROOT = Path(__file__).resolve().parents[1]
BASE_CFG = load_config(ROOT / "configs" / "default_model.yaml", model=ModelConfig).learning


def _trained():
    net = make_net()
    cfg = BASE_CFG.model_copy(update={"mini_batch_updates": 2, "batch_size": 2})
    result = train_bc(
        net,
        make_dataset(8, 4),
        cfg,
        seed_manager=SeedManager(MASTER_SEED),
        seed_index=0,
    )
    return net, result


def test_flip_rate_is_zero_under_sign_constraint():
    net, _ = _trained()
    assert sign_flip_rate(net) == pytest.approx(0.0)


def test_spectral_radius_shape_and_finite():
    net, _ = _trained()
    radii = spectral_radius(net)
    assert len(radii) == 1
    assert radii[0] >= 0.0
    assert all(value == value for value in radii)  # 非 NaN


def test_spectral_radius_matches_torch_eigvals():
    net, _ = _trained()
    weights = net.effective_weights[0].detach()
    expected = float(torch.linalg.eigvals(weights).abs().max())
    assert spectral_radius(net)[0] == pytest.approx(expected)


def test_delta_w_identity_error_is_zero():
    net, _ = _trained()
    assert delta_w_identity_error(net) == pytest.approx(0.0)


def test_build_report_is_consistent_with_result():
    net, result = _trained()
    report = build_report(net, result)
    assert report.loss_history == result.loss_history
    assert report.n_updates == result.n_updates == 2
    assert report.coverage_stats is result.coverage_stats
    assert report.epochs == pytest.approx(result.epochs)
    assert report.coverage_episodes == pytest.approx(result.coverage_episodes)
    assert report.coverage_steps == pytest.approx(result.coverage_steps)
    assert report.visible_steps == result.visible_steps
    assert report.loss_weights is result.loss_weights
    assert report.flip_rate == pytest.approx(0.0)
    assert report.delta_w_identity_max_error == pytest.approx(0.0)
