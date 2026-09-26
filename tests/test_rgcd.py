import numpy as np
import torch

from evogenesis.core.seed import SeedManager
from evogenesis.development.config import DEFAULT_CONFIG
from evogenesis.development.rgcd import (
    apply_dale_sign,
    centered_bilinear,
    compatibility_prior,
    connection_logits,
    develop,
    expected_off_diagonal_density,
    initial_weights,
    initialize_parameters,
    softplus_inverse,
    solve_bias_for_density,
    tau_from_grn,
    viability_check,
)

DOMAINS = DEFAULT_CONFIG.domains
N_TYPES = len(DOMAINS)
Q = np.linspace(0.0, 1.0, DEFAULT_CONFIG.grn_dim).astype(np.float32)


def _off_diagonal_density(adjacency: torch.Tensor) -> float:
    n = adjacency.shape[0]
    off = adjacency.sum() - adjacency.diagonal().sum()
    return float((off / (n * (n - 1))).item())


def _synthetic(
    cell_types: list[int],
    *,
    adjacency: torch.Tensor | None = None,
    weights0: torch.Tensor | None = None,
    tau: torch.Tensor | None = None,
    neuron_bias: torch.Tensor | None = None,
) -> tuple[bool, str]:
    n = len(cell_types)
    cell_type = torch.tensor(cell_types, dtype=torch.int64)
    positions = torch.stack(
        [torch.arange(n, dtype=torch.float32) / n, torch.zeros(n, dtype=torch.float32)], dim=-1
    )
    if adjacency is None:
        adjacency = torch.ones((n, n)) - torch.eye(n)
    if weights0 is None:
        weights0 = torch.zeros((n, n))
    if tau is None:
        tau = torch.full((n,), 2.0)
    active_mask = torch.ones(n, dtype=torch.bool)
    return viability_check(
        adjacency,
        cell_type,
        positions,
        tau,
        weights0,
        active_mask,
        domains=DOMAINS,
        neuron_bias=neuron_bias,
    )


# ---------------------------------------------------------------------------
# §1 输出形状 / dtype / 数值契约
# ---------------------------------------------------------------------------


def test_develop_output_contract():
    pheno = develop(Q, master_seed=1, index=0)
    n = pheno.adjacency.shape[0]
    assert DEFAULT_CONFIG.initial_precursors <= n <= DEFAULT_CONFIG.max_neurons
    assert pheno.adjacency.shape == (n, n)
    assert pheno.weights0.shape == (n, n)
    assert pheno.tau.shape == (n,)
    assert pheno.cell_type.shape == (n,)
    assert pheno.positions.shape == (n, 2)
    assert pheno.active_mask.shape == (n,)
    for tensor in (pheno.adjacency, pheno.weights0, pheno.tau, pheno.positions, pheno.z):
        assert tensor.dtype == torch.float32
    assert bool(pheno.active_mask.all())
    assert int(pheno.active_mask.sum()) == n


def test_density_in_contract_range_and_no_self_loops():
    for seed in range(1, 6):
        pheno = develop(Q, master_seed=seed, index=0)
        density = _off_diagonal_density(pheno.adjacency)
        assert 0.10 <= density <= 0.20, (seed, density)
        assert float(pheno.adjacency.diagonal().sum()) == 0.0
        assert set(pheno.adjacency.unique().tolist()) <= {0.0, 1.0}


def test_tau_bounds_and_identity_is_argmax():
    pheno = develop(Q, master_seed=1, index=0)
    assert torch.all(pheno.tau >= DEFAULT_CONFIG.tau_min)
    assert torch.all(pheno.tau <= DEFAULT_CONFIG.tau_max)
    assert torch.allclose(pheno.z.sum(dim=-1), torch.ones(pheno.z.shape[0]), atol=1e-5)
    assert torch.equal(pheno.cell_type, pheno.z.argmax(dim=-1))


# ---------------------------------------------------------------------------
# §10 Dale sign / 初权
# ---------------------------------------------------------------------------


def test_dale_sign_determined_by_presynaptic_type():
    pheno = develop(Q, master_seed=1, index=0)
    inhibitory = DOMAINS.index("inhibitory")
    support = pheno.adjacency > 0
    inhibitory_rows = pheno.cell_type == inhibitory
    assert torch.all(pheno.weights0[inhibitory_rows] <= 0.0)
    assert torch.all(pheno.weights0[~inhibitory_rows] >= 0.0)
    # 支撑外（含 self-loop）恒 0
    assert torch.all(pheno.weights0[~support] == 0.0)


def test_apply_dale_sign_by_presynaptic_row():
    weights = torch.ones(3, 3)
    types = torch.tensor([0, 4, 5])
    signed = apply_dale_sign(weights, types)
    assert torch.all(signed[0] > 0)
    assert torch.all(signed[1] < 0)
    assert torch.all(signed[2] > 0)


def test_initial_weights_softplus_magnitude_on_support():
    gen = SeedManager(2).torch_generator("development", 0)
    n = 6
    grn = torch.rand(n, 8, generator=gen)
    z = torch.softmax(torch.randn(n, N_TYPES, generator=gen), dim=-1)
    cell_type = z.argmax(dim=-1)
    adjacency = torch.ones(n, n) - torch.eye(n)
    u = torch.randn(DEFAULT_CONFIG.weight_feature_dim, generator=gen) * 0.1
    weights = initial_weights(adjacency, grn, z, cell_type, u, torch.zeros(()), 4)
    assert torch.all(torch.isfinite(weights))
    assert torch.all(weights[adjacency == 0] == 0.0)


# ---------------------------------------------------------------------------
# §4/§11 参数与公式
# ---------------------------------------------------------------------------


def test_spectral_radius_is_calibrated():
    gen = SeedManager(3).torch_generator("development", 0)
    params = initialize_parameters(gen)
    radius = float(torch.linalg.eigvals(params.Wg).abs().max().item())
    assert abs(radius - DEFAULT_CONFIG.grn_spectral_radius) < 1e-4


def test_tau_formula_range():
    gen = SeedManager(3).torch_generator("development", 0)
    grn = torch.randn(20, 8, generator=gen)
    a = torch.randn(8, generator=gen)
    b = torch.zeros(())
    tau = tau_from_grn(grn, a, b)
    assert torch.all(tau > 1.0) and torch.all(tau < 10.0)


def test_softplus_inverse_roundtrip():
    value = softplus_inverse(0.5)
    assert abs(torch.nn.functional.softplus(torch.tensor(value)).item() - 0.5) < 1e-6


def test_centered_bilinear_range_and_zero_std_handling():
    gen = SeedManager(6).torch_generator("development", 0)
    grn = torch.randn(10, 8, generator=gen)
    grn[:, 0] = 0.3  # 常量分量 -> std=0，须显式处理
    r = centered_bilinear(grn)
    assert torch.all(torch.isfinite(r))
    assert torch.allclose(r, r.T, atol=1e-5)


# ---------------------------------------------------------------------------
# §8 b_A 二分反解
# ---------------------------------------------------------------------------


def test_solve_bias_converges_to_target_density():
    gen = SeedManager(8).torch_generator("development", 0)
    n = 24
    z = torch.softmax(torch.randn(n, N_TYPES, generator=gen), dim=-1)
    positions = torch.rand(n, 2, generator=gen)
    regulatory = centered_bilinear(torch.rand(n, 8, generator=gen))
    logits = connection_logits(
        z,
        positions,
        compatibility_prior(),
        distance_lambda=DEFAULT_CONFIG.distance_lambda,
        regulatory_gamma=DEFAULT_CONFIG.regulatory_gamma,
        regulatory_term=regulatory,
    )
    target = DEFAULT_CONFIG.target_density
    bias = solve_bias_for_density(logits, target)
    assert abs(expected_off_diagonal_density(logits, bias) - target) < 1e-6


def test_solve_bias_does_not_consume_random_numbers():
    gen_used = SeedManager(9).torch_generator("development", 0)
    gen_control = SeedManager(9).torch_generator("development", 0)
    logits = torch.zeros(10, 10)
    solve_bias_for_density(logits, 0.15)
    assert torch.equal(torch.rand(5, generator=gen_used), torch.rand(5, generator=gen_control))


# ---------------------------------------------------------------------------
# §7 viability 四判据
# ---------------------------------------------------------------------------


def test_viability_positive_case():
    viable, reason = _synthetic([0, 1, 2, 3, 4, 5, 5])
    assert viable is True
    assert reason == "ok"


def test_viability_missing_fate():
    viable, reason = _synthetic([0, 0, 0, 0, 0, 0])
    assert viable is False
    assert "missing_fate:prey" in reason


def test_viability_motor_side_empty():
    viable, reason = _synthetic([0, 1, 2, 3, 4, 5])
    assert viable is False
    assert "motor_side_empty" in reason


def test_viability_no_sensory_to_motor_path():
    n = 7
    adjacency = torch.ones((n, n)) - torch.eye(n)
    adjacency[0, :] = 0.0  # sensory 无出边
    viable, reason = _synthetic([0, 1, 2, 3, 4, 5, 5], adjacency=adjacency)
    assert viable is False
    assert "no_sensory_to_motor_path" in reason


def test_viability_persistent_saturation():
    n = 7
    # zero-input 且 h^0=0 时无 bias 会停在全零不动点；用饱和级 bias 触发持续饱和（|h|<1 仍成立）
    neuron_bias = torch.full((n,), 7.0)
    tau = torch.ones(n)
    viable, reason = _synthetic([0, 1, 2, 3, 4, 5, 5], tau=tau, neuron_bias=neuron_bias)
    assert viable is False
    assert "persistent_saturation" in reason


def test_viability_nonfinite_activation():
    # §7(i)：tau=0 使 1/tau=inf，零输入轨迹出现非有限 → nonfinite_activation
    n = 7
    tau = torch.zeros(n)
    viable, reason = _synthetic([0, 1, 2, 3, 4, 5, 5], tau=tau)
    assert viable is False
    assert "nonfinite_activation" in reason


def test_viability_saturated_but_bounded_passes_bound_check():
    # §7(ii)：float32 下 |h| 可恰为 1.0（舍入），不得据此判 non-viable
    n = 7
    weights0 = torch.zeros((n, n))
    neuron_bias = torch.full((n,), 50.0)
    _, reason = _synthetic([0, 1, 2, 3, 4, 5, 5], weights0=weights0, neuron_bias=neuron_bias)
    assert "activation_bound_violated" not in reason


def test_viability_weight_spectral_radius_negative():
    # §7(iv)：对象是有效权重矩阵 W^0（非 GRN W_g）；构造 ρ_spec(W^0)=1.5 > 1
    n = 7
    weights0 = torch.eye(n, dtype=torch.float32) * 1.5
    viable, reason = _synthetic([0, 1, 2, 3, 4, 5, 5], weights0=weights0)
    assert viable is False
    assert "weight_spectral_radius_not_contractive" in reason


def test_viability_no_active_neurons():
    viable, reason = viability_check(
        torch.zeros(3, 3),
        torch.zeros(3, dtype=torch.int64),
        torch.zeros(3, 2),
        torch.ones(3),
        torch.zeros(3, 3),
        torch.zeros(3, dtype=torch.bool),
    )
    assert viable is False
    assert reason == "no_active_neurons"


# ---------------------------------------------------------------------------
# 可复现性
# ---------------------------------------------------------------------------


def test_same_seed_reproducible():
    first = develop(Q, master_seed=42, index=0)
    second = develop(Q, master_seed=42, index=0)
    assert torch.equal(first.adjacency, second.adjacency)
    assert torch.equal(first.weights0, second.weights0)
    assert torch.equal(first.tau, second.tau)
    assert torch.equal(first.cell_type, second.cell_type)
    assert torch.equal(first.positions, second.positions)
    assert first.viability_reason == second.viability_reason


def test_different_seed_differs():
    first = develop(Q, master_seed=42, index=0)
    second = develop(Q, master_seed=43, index=0)
    assert not torch.equal(first.adjacency, second.adjacency)
    assert not torch.equal(first.weights0, second.weights0)


def test_different_entity_index_differs():
    first = develop(Q, master_seed=42, index=0)
    second = develop(Q, master_seed=42, index=1)
    assert not torch.equal(first.adjacency, second.adjacency)


def test_spectral_radius_rejects_nonfinite():
    import pytest

    from evogenesis.development.grn import spectral_radius

    matrix = torch.eye(3)
    matrix[0, 1] = float("nan")
    with pytest.raises(ValueError):
        spectral_radius(matrix)


def test_centered_bilinear_zero_variance_component_contributes_zero():
    # 常量分量 std=0：该分量不贡献（避免除零，且不等于 NaN）
    from evogenesis.development.rgcd import centered_bilinear

    grn = torch.tensor([[1.0, 5.0], [2.0, 5.0], [3.0, 5.0]], dtype=torch.float32)
    r = centered_bilinear(grn)
    assert torch.isfinite(r).all()
    manual_first_dim = ((grn[:, 0] - grn[:, 0].mean()) / grn[:, 0].std(unbiased=False)) ** 2 / 2
    assert torch.allclose(r.diagonal(), manual_first_dim, atol=1e-6)


def test_motor_sides_tie_break_by_index():
    # DanioNet §5：motor 同 x 值时按索引破平，两侧均非空
    from evogenesis.development.rgcd import _motor_sides

    positions = torch.tensor([[0.5, 0.1], [0.5, 0.2], [0.5, 0.3], [0.5, 0.4]])
    cell_type = torch.tensor([5, 5, 5, 5], dtype=torch.int64)
    left, right = _motor_sides(positions, cell_type, motor_index=5)
    assert left.tolist() == [0, 1] and right.tolist() == [2, 3]


def test_viability_positive_with_nonzero_contractive_weights():
    n = 7
    weights0 = torch.eye(n, dtype=torch.float32) * 0.3  # rho_spec=0.3 < 1
    viable, reason = _synthetic([0, 1, 2, 3, 4, 5, 5], weights0=weights0)
    assert viable is True, reason
    assert reason == "ok"
