"""learning/train.py 测试：episode 级 BPTT、覆盖率、可复现、符号约束、梯度屏蔽（§3 v1.4）。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch
from test_learning_common import (
    MASTER_SEED,
    make_actions,
    make_dataset,
    make_net,
    make_observations,
    make_phenotype,
)

from evogenesis.connectome.danionet import DanioNet
from evogenesis.core.config import ModelConfig, load_config
from evogenesis.core.seed import SeedManager
from evogenesis.learning.data import TrajectoryDataset
from evogenesis.learning.train import compute_coverage_stats, train_bc

ROOT = Path(__file__).resolve().parents[1]
BASE_CFG = load_config(ROOT / "configs" / "default_model.yaml", model=ModelConfig).learning


def _cfg(**updates):
    return BASE_CFG.model_copy(update=updates)


def _train(net, dataset, cfg, *, seed_index=0):
    return train_bc(
        net,
        dataset,
        cfg,
        seed_manager=SeedManager(MASTER_SEED),
        seed_index=seed_index,
    )


def test_compute_coverage_stats_contract_numbers():
    stats = compute_coverage_stats(20, 64, 200, 600)
    assert stats.epochs == pytest.approx(6.4)
    assert stats.coverage_episodes == pytest.approx(6.4)
    assert stats.visible_steps == 768_000
    assert stats.total_steps == 120_000
    assert stats.coverage_steps == pytest.approx(6.4)


def test_updates_batch_size_and_coverage_small():
    net = make_net()
    dataset = make_dataset(n_episodes=10, episode_steps=4)
    result = _train(net, dataset, _cfg(mini_batch_updates=3, batch_size=2))
    assert result.n_updates == 3
    assert result.update_batch_sizes == (2, 2, 2)
    assert result.batch_size == 2
    assert result.n_episodes == 10
    assert result.episode_steps == 4
    assert result.epochs == pytest.approx(3 * 2 / 10)
    assert result.coverage_episodes == pytest.approx(0.6)
    assert result.visible_steps == 3 * 2 * 4
    assert result.total_steps == 40
    assert result.coverage_steps == pytest.approx(0.6)
    assert len(result.loss_history) == 3
    assert all(np.isfinite(loss) for loss in result.loss_history)


def test_batch_is_64_episodes():
    net = make_net()
    dataset = make_dataset(n_episodes=100, episode_steps=2)
    result = _train(net, dataset, _cfg(mini_batch_updates=1, batch_size=64))
    assert result.update_batch_sizes == (64,)
    assert result.batch_size == 64
    assert result.epochs == pytest.approx(64 / 100)


def test_training_changes_weights_and_grad_is_nonzero():
    net = make_net()
    dataset = make_dataset(n_episodes=8, episode_steps=4)
    before = net.effective_weights.detach().clone()
    result = _train(net, dataset, _cfg(mini_batch_updates=2, batch_size=2))
    assert len(result.loss_history) == 2
    # ΔW 非零、W 相对 W⁰ 变化
    assert float(net.delta_weights.detach().abs().max()) > 0.0
    assert not torch.allclose(net.effective_weights.detach(), before)
    # 梯度在活跃支撑上非零
    grad = net.theta.grad
    assert grad is not None
    assert float(grad[net.support].abs().sum()) > 0.0


def test_single_step_has_zero_gradient_two_steps_have_positive():
    cfg = _cfg(mini_batch_updates=1, batch_size=1)
    one_step = make_dataset(n_episodes=1, episode_steps=1)
    net1 = make_net()
    _train(net1, one_step, cfg)
    assert float(net1.theta.grad[net1.support].abs().sum()) == 0.0

    two_steps = make_dataset(n_episodes=1, episode_steps=2)
    net2 = make_net()
    _train(net2, two_steps, cfg)
    assert float(net2.theta.grad[net2.support].abs().sum()) > 0.0


def test_sign_constraint_preserved_on_active_support():
    net = make_net()
    _train(net, make_dataset(8, 4), _cfg(mini_batch_updates=2, batch_size=2))
    mask = net.support & (net.sign0 != 0)
    assert int(mask.sum()) > 0
    assert torch.equal(torch.sign(net.effective_weights[mask]), net.sign0[mask])


def test_delta_weights_identity_holds():
    net = make_net()
    _train(net, make_dataset(8, 4), _cfg(mini_batch_updates=2, batch_size=2))
    assert torch.equal(net.delta_weights, net.effective_weights - net.weights0)


def test_gradients_only_on_support_and_not_padding():
    net = make_net()
    _train(net, make_dataset(8, 4), _cfg(mini_batch_updates=2, batch_size=2))
    grad = net.theta.grad
    assert grad is not None
    assert float(grad[~net.support].abs().sum()) == 0.0
    n = net.n_neurons[0]
    assert float(grad[:, n:, :].abs().sum()) == 0.0
    assert float(grad[:, :, n:].abs().sum()) == 0.0


def test_same_seed_reproduces_losses_and_theta():
    dataset = make_dataset(8, 4)
    cfg = _cfg(mini_batch_updates=2, batch_size=2)
    net_a = make_net()
    result_a = _train(net_a, dataset, cfg, seed_index=0)
    net_b = make_net()
    result_b = _train(net_b, dataset, cfg, seed_index=0)
    assert result_a.loss_history == result_b.loss_history
    assert torch.equal(net_a.theta.detach(), net_b.theta.detach())


def test_different_seed_index_differs():
    dataset = make_dataset(10, 4)
    cfg = _cfg(mini_batch_updates=3, batch_size=2)
    first = _train(make_net(), dataset, cfg, seed_index=0)
    second = _train(make_net(), dataset, cfg, seed_index=1)
    assert first.loss_history != second.loss_history


def test_empty_dataset_raises():
    with pytest.raises(ValueError, match="训练集为空"):
        _train(make_net(), make_dataset(0, 4), _cfg(mini_batch_updates=2, batch_size=2))


def test_non_uniform_episodes_rejected():
    dataset = TrajectoryDataset(
        observations=make_observations(5, seed=0),
        expert_actions=make_actions(5, seed=1),
        headers=({"episode_id": "a", "total_steps": 2}, {"episode_id": "b", "total_steps": 3}),
        episode_paths=(),
        episode_lengths=(2, 3),
    )
    with pytest.raises(ValueError, match="不等长"):
        _train(make_net(), dataset, _cfg(mini_batch_updates=2, batch_size=2))


def test_multi_individual_net_rejected():
    net = DanioNet([make_phenotype(), make_phenotype()], master_seed=MASTER_SEED)
    with pytest.raises(ValueError, match="一个个体"):
        _train(net, make_dataset(4, 2), _cfg(mini_batch_updates=1, batch_size=2))


def test_sign_constrained_false_raises():
    with pytest.raises(NotImplementedError, match="sign_constrained"):
        train_bc(
            make_net(),
            make_dataset(4, 2),
            _cfg(mini_batch_updates=1, batch_size=2),
            seed_manager=SeedManager(MASTER_SEED),
            seed_index=0,
            sign_constrained=False,
        )


def test_unsupported_optimizer_raises():
    with pytest.raises(NotImplementedError, match="optimizer"):
        _train(make_net(), make_dataset(4, 2), _cfg(optimizer="sgd"))


def test_unsupported_normalization_raises():
    with pytest.raises(NotImplementedError, match="loss_weight_normalization"):
        _train(make_net(), make_dataset(4, 2), _cfg(loss_weight_normalization="uniform"))
