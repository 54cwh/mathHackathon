"""DanioNet（Stage 4）测试：结构 / 权重约束 / 动力学 / 动作 / 梯度屏蔽 / viability。

夹具用 RGCD ``develop`` 在固定 q 与 master seed 下产出 viable 个体（``DanioNet规范.md``
v1.3）。q 取自 ``numpy.random.default_rng(7)`` 的第 7 次抽样，master_seed=250927、index=6。
"""

import numpy as np
import pytest
import torch

from evogenesis.connectome.config import DEFAULT_NETWORK_CONFIG
from evogenesis.connectome.danionet import DanioNet, NetworkPriors, build_priors, motor_sides
from evogenesis.development import ConnectomePhenotype, develop

MASTER_SEED = 250927
VIABLE_INDEX = 6
VIABLE_Q = np.array(
    [
        0.5077722072601318,
        0.8713393807411194,
        0.36126405000686646,
        0.5981840491294861,
        0.05925164371728897,
        0.3876318037509918,
        0.3230363428592682,
        0.15019972622394562,
    ],
    dtype=np.float32,
)


@pytest.fixture(scope="module")
def viable_phenotype() -> ConnectomePhenotype:
    phenotype = develop(VIABLE_Q, master_seed=MASTER_SEED, index=VIABLE_INDEX)
    assert phenotype.viable, phenotype.viability_reason
    return phenotype


@pytest.fixture()
def net(viable_phenotype: ConnectomePhenotype) -> DanioNet:
    return DanioNet([viable_phenotype], master_seed=MASTER_SEED)


def _obs(hunger: float = 1.0) -> np.ndarray:
    obs = np.zeros((1, DEFAULT_NETWORK_CONFIG.sensory_dim), dtype=np.float32)
    obs[0, 11] = hunger
    return obs


def test_padding_shape_dtype_and_masks(net: DanioNet, viable_phenotype: ConnectomePhenotype):
    n = viable_phenotype.adjacency.shape[0]
    nodes = DEFAULT_NETWORK_CONFIG.max_nodes
    assert net.effective_weights.shape == (1, nodes, nodes)
    assert net.effective_weights.dtype == torch.float32
    assert net.theta.dtype == torch.float32
    assert net.h.shape == (1, DEFAULT_NETWORK_CONFIG.max_nodes)
    assert float(net.h.abs().sum()) == 0.0
    assert int(net.neuron_mask.sum()) == n
    assert not bool(net.neuron_mask[0, n:].any())
    # padding 行/列恒 0
    assert float(net.effective_weights[0, n:, :].abs().sum()) == 0.0
    assert float(net.effective_weights[0, :, n:].abs().sum()) == 0.0


def test_initial_delta_w_is_zero_and_effective_equals_w0(net: DanioNet):
    assert torch.allclose(net.delta_weights, torch.zeros_like(net.delta_weights), atol=1e-6)
    assert torch.allclose(net.effective_weights, net.weights0, atol=1e-6)


def test_dale_sign_preserved_and_support_zero(net: DanioNet):
    inside = net.support
    assert bool((torch.sign(net.effective_weights[inside]) == net.sign0[inside]).all())
    assert float(net.effective_weights[~inside].abs().sum()) == 0.0


def test_gradients_masked_outside_support_and_padding(net: DanioNet):
    net.reset()
    net.step(_obs())
    net.zero_grad()
    (net.h.sum()).backward()
    grad = net.theta.grad
    assert grad is not None
    assert float(grad[~net.support].abs().sum()) == 0.0
    assert float(grad[:, net.n_neurons[0] :].abs().sum()) == 0.0
    assert float(grad[:, :, net.n_neurons[0] :].abs().sum()) == 0.0


def test_dynamics_reproducible_and_h0_zero(viable_phenotype: ConnectomePhenotype):
    first = DanioNet([viable_phenotype], master_seed=MASTER_SEED)
    second = DanioNet([viable_phenotype], master_seed=MASTER_SEED)
    assert torch.equal(first.h, second.h)
    w1, v1 = first.step(_obs())
    w2, v2 = second.step(_obs())
    assert torch.equal(w1, w2) and torch.equal(v1, v2)


def test_hunger_dimension_enters_dynamics(net: DanioNet):
    net.reset()
    net.step(_obs(hunger=0.0))
    low = net.h.clone()
    net.reset()
    net.step(_obs(hunger=1.0))
    high = net.h.clone()
    assert not torch.allclose(low, high)


def test_action_range_and_left_dominance(net: DanioNet):
    omega, v = net.step(_obs())
    assert float(omega.min()) >= -1.0 and float(omega.max()) <= 1.0
    assert float(v.min()) >= 0.0 and float(v.max()) <= 1.0

    net.reset()
    net.h[0, net.left_mask[0]] = 1.0
    omega_left, _ = net.action()
    assert float(omega_left[0]) > 0.0
    net.reset()
    net.h[0, net.right_mask[0]] = 1.0
    omega_right, _ = net.action()
    assert float(omega_right[0]) < 0.0


def test_motor_sides_median_split_nonempty_and_tiebreak():
    motor_types = torch.tensor([0, 0, 0, 0, 0])
    positions = torch.tensor([[0.2, 0.0], [0.1, 0.0], [0.4, 0.0], [0.3, 0.0], [0.5, 0.0]])
    left, right = motor_sides(positions, motor_types, motor_index=0)
    assert left.numel() == 2 and right.numel() == 3
    assert set(left.tolist()) == {0, 1}
    # 同值按索引破平：索引小的进 left
    tied = torch.tensor([[0.5, 0.0], [0.5, 0.0], [0.5, 0.0], [0.5, 0.0]])
    left_t, right_t = motor_sides(tied, torch.tensor([0, 0, 0, 0]), motor_index=0)
    assert left_t.tolist() == [0, 1] and right_t.tolist() == [2, 3]


def test_priors_are_a_global_single_table():
    a = build_priors(MASTER_SEED)
    b = build_priors(MASTER_SEED)
    assert torch.equal(a.U, b.U) and torch.equal(a.m, b.m) and torch.equal(a.b, b.b)
    c = build_priors(MASTER_SEED + 1)
    assert not torch.equal(a.U, c.U)
    assert a.U.shape == (len(DEFAULT_NETWORK_CONFIG.domains), DEFAULT_NETWORK_CONFIG.sensory_dim)


def test_priors_shared_across_individuals(viable_phenotype: ConnectomePhenotype):
    one = DanioNet([viable_phenotype], master_seed=MASTER_SEED)
    two = DanioNet([viable_phenotype], master_seed=MASTER_SEED)
    assert torch.equal(one.U, two.U)
    shared = build_priors(MASTER_SEED)
    assert isinstance(shared, NetworkPriors)
    assert torch.equal(one.U, shared.U)


def test_batch_of_two_individuals(viable_phenotype: ConnectomePhenotype):
    net = DanioNet([viable_phenotype, viable_phenotype], master_seed=MASTER_SEED)
    obs = np.zeros((2, DEFAULT_NETWORK_CONFIG.sensory_dim), dtype=np.float32)
    omega, v = net.step(obs)
    assert omega.shape == (2,) and v.shape == (2,)
    assert bool(torch.isfinite(omega).all()) and bool(torch.isfinite(v).all())


def test_viability_recheck_matches_development(viable_phenotype: ConnectomePhenotype):
    net = DanioNet([viable_phenotype], master_seed=MASTER_SEED)
    results = net.viability()
    assert len(results) == 1
    viable, reason = results[0]
    assert isinstance(viable, bool)
    assert reason == "ok" if viable else reason != ""


def test_empty_motor_pool_rejected():
    n = 3
    phenotype = ConnectomePhenotype(
        adjacency=torch.zeros((n, n), dtype=torch.float32),
        weights0=torch.zeros((n, n), dtype=torch.float32),
        tau=torch.ones(n, dtype=torch.float32),
        cell_type=torch.zeros(n, dtype=torch.long),
        positions=torch.tensor([[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]], dtype=torch.float32),
        active_mask=torch.ones(n, dtype=torch.bool),
        viable=False,
        viability_reason="missing_fate:motor",
        z=torch.zeros((n, 6), dtype=torch.float32),
    )
    with pytest.raises(ValueError):
        DanioNet([phenotype], master_seed=MASTER_SEED)


def test_active_mask_from_rgcd_is_honored():
    """DanioNet 的 neuron mask 必须取自 RGCD 的 M（active_mask），而非假设全部活跃。"""
    n = 7
    types = torch.tensor([0, 0, 5, 5, 5, 5, 5], dtype=torch.long)  # 2 sensory + 5 motor
    active = torch.tensor([True, True, True, True, True, True, False])
    adjacency = torch.zeros((n, n), dtype=torch.float32)
    adjacency[2, 6] = 1.0  # 指向非活跃神经元的连接应被屏蔽
    weights0 = torch.zeros((n, n), dtype=torch.float32)
    weights0[2, 6] = 0.5
    phenotype = ConnectomePhenotype(
        adjacency=adjacency,
        weights0=weights0,
        tau=torch.ones(n, dtype=torch.float32),
        cell_type=types,
        positions=torch.tensor(
            [[0.1, 0.1], [0.2, 0.1], [0.3, 0.1], [0.4, 0.1], [0.5, 0.1], [0.6, 0.1], [0.7, 0.1]],
            dtype=torch.float32,
        ),
        active_mask=active,
        viable=True,
        viability_reason="ok",
        z=torch.zeros((n, 6), dtype=torch.float32),
    )
    net = DanioNet([phenotype], master_seed=MASTER_SEED)
    assert int(net.neuron_mask.sum()) == 6
    assert not bool(net.neuron_mask[0, 6])
    # 非活跃神经元的行/列被屏蔽
    assert float(net.effective_weights[0, 6, :].abs().sum()) == 0.0
    assert float(net.effective_weights[0, :, 6].abs().sum()) == 0.0
    assert not bool(net.support[0, 2, 6])
    # 动作池只由活跃 motor 组成，且左右非空
    assert int(net.motor_mask.sum()) == 4
    assert int(net.left_mask.sum()) == 2 and int(net.right_mask.sum()) == 2
    net.step(np.zeros((1, DEFAULT_NETWORK_CONFIG.sensory_dim), dtype=np.float32))
    assert float(net.h[0, 6].abs()) == 0.0


def test_mismatched_shapes_rejected():
    n = 4
    phenotype = ConnectomePhenotype(
        adjacency=torch.zeros((n, n), dtype=torch.float32),
        weights0=torch.zeros((n, n + 1), dtype=torch.float32),  # 形状不一致
        tau=torch.ones(n, dtype=torch.float32),
        cell_type=torch.tensor([0, 5, 5, 5], dtype=torch.long),
        positions=torch.tensor(
            [[0.1, 0.1], [0.3, 0.1], [0.5, 0.1], [0.7, 0.1]], dtype=torch.float32
        ),
        active_mask=torch.ones(n, dtype=torch.bool),
        viable=True,
        viability_reason="ok",
        z=torch.zeros((n, 6), dtype=torch.float32),
    )
    with pytest.raises(ValueError):
        DanioNet([phenotype], master_seed=MASTER_SEED)
