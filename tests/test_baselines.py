"""§8 对照基线（MLP / GRU / Fixed Sparse RNN）的契约守护测试。"""

from __future__ import annotations

import math

import numpy as np
import pytest
import torch

from evogenesis.connectome.baselines import BASELINES, N_OURS, build_baselines

MASTER_SEED = 250927
SENSORY_DIM = 12
HIDDEN = {"mlp": 14, "gru": 4, "fixed_sparse_rnn": 12}


def _obs() -> np.ndarray:
    obs = np.zeros((1, SENSORY_DIM), dtype=np.float32)
    obs[0, 11] = 1.0
    return obs


@pytest.fixture(params=sorted(BASELINES))
def baseline(request):
    return request.param, BASELINES[request.param](master_seed=MASTER_SEED, index=0)


def test_connection_count_within_one_order_of_magnitude(baseline):
    name, net = baseline
    edges = net.complexity()["active_edges"]
    assert abs(math.log10(edges) - math.log10(N_OURS)) <= 1.0
    assert abs(math.log10(edges) - math.log10(N_OURS)) <= 0.05


def test_hidden_width_matches_spec(baseline):
    name, net = baseline
    assert net.n_neurons == [HIDDEN[name]]
    assert net.active_counts == [HIDDEN[name]]
    assert net.config.max_nodes == HIDDEN[name]
    assert net.config.sensory_dim == SENSORY_DIM


def test_interface_matches_train_bc_requirements(baseline):
    name, net = baseline
    assert net.sign_constrained is False
    assert len(net.n_neurons) == 1
    assert isinstance(net.theta, torch.nn.Parameter)
    assert [p for p in net.parameters()] == [net.theta]
    net.reset()
    omega, v = net.step(_obs())
    assert omega.shape == (1,) and v.shape == (1,)
    assert omega.dtype == torch.float32 and v.dtype == torch.float32
    assert torch.isfinite(omega).all() and torch.isfinite(v).all()
    assert float(omega.abs().max()) <= 1.0 and float(v.abs().max()) <= 1.0
    one_d = net.step(_obs()[0])
    assert one_d[0].shape == (1,)


def test_deterministic_and_index_dependent():
    first = build_baselines(MASTER_SEED, index=0)
    second = build_baselines(MASTER_SEED, index=0)
    other = build_baselines(MASTER_SEED, index=1)
    for name in first:
        obs = _obs()
        first[name].reset()
        second[name].reset()
        other[name].reset()
        assert torch.equal(first[name].theta, second[name].theta)
        assert not torch.equal(first[name].theta, other[name].theta)
        assert torch.equal(first[name].step(obs)[0], second[name].step(obs)[0])
        first[name].reset()
        assert not torch.equal(first[name].step(obs)[0], other[name].step(obs)[0])


def test_gradients_flow_to_theta(baseline):
    name, net = baseline
    net.reset()
    omega, v = net.step(_obs())
    (omega.sum() + v.sum()).backward()
    assert net.theta.grad is not None
    assert float(net.theta.grad.abs().sum()) > 0.0


def test_sparse_rnn_mask_is_frozen_and_masked_grad_zero():
    net = BASELINES["fixed_sparse_rnn"](master_seed=MASTER_SEED, index=0)
    assert 0 < int(net.support.sum()) < net.support.numel()
    net.reset()
    loss = 0.0
    for _ in range(2):
        omega, v = net.step(_obs())
        loss = loss + omega.sum() + v.sum()
    loss.backward()
    rec = net.theta.grad[: net.hidden * net.hidden].view(12, 12)
    assert float(rec[~net.support].abs().sum()) == 0.0
    assert float(rec[net.support].abs().sum()) > 0.0


def test_complexity_reports_sparse_theoretical_cost():
    net = BASELINES["fixed_sparse_rnn"](master_seed=MASTER_SEED, index=0)
    got = net.complexity()
    assert got["macs_theoretical"] < got["macs_implemented"]
    assert got["flops_theoretical"] == 2 * got["macs_theoretical"]
    dense = BASELINES["mlp"](master_seed=MASTER_SEED, index=0).complexity()
    assert dense["macs_theoretical"] == dense["macs_implemented"]


def test_action_ranges_match_danionet(baseline):
    """§4/§8 定稿：基线 (ω, v) 与 DanioNet 同映射——ω=tanh∈[-1,1]、v=σ∈[0,1]。"""
    name, net = baseline
    net.reset()
    omega, v = net.step(_obs())
    assert float(omega.abs().max()) <= 1.0
    assert float(v.min()) >= 0.0 and float(v.max()) <= 1.0


def test_sparse_support_is_independent_of_initial_weights():
    """`baseline_support` 守护：支撑 mask 与初始递归幅度分属两条流，激活权重不系统性偏号。

    回归背景：曾让 mask 与 θ 取自同一 `baseline_init` 子序列（重开流），使被选中的递归权重
    全为负（全抑制），人为削弱该臂。此处断言各 index 下激活权重同时含正负。
    """
    for index in (0, 1, 6):
        net = BASELINES["fixed_sparse_rnn"](master_seed=MASTER_SEED, index=index)
        rec = net.theta[: net.hidden * net.hidden].detach().view(net.hidden, net.hidden)
        active = rec[net.support]
        assert int(active.numel()) > 0
        assert float(active.max()) > 0.0 and float(active.min()) < 0.0
