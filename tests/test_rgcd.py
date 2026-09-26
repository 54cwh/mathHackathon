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


def test_trace_does_not_change_development():
    """开/关 `collect_trace` 的发育结果**逐位相同**（护栏：记录只读张量、不抽随机数）。

    这是本特性最重要的约束：trace 是给前端画「§4 动画顺序」用的观测口，
    一旦它扰动随机流，全项目的发育数值就不再可复现。
    """
    plain = develop(Q, master_seed=42, index=0)
    traced = develop(Q, master_seed=42, index=0, collect_trace=True)
    assert plain.trace is None
    assert traced.trace is not None
    assert torch.equal(plain.adjacency, traced.adjacency)
    assert torch.equal(plain.weights0, traced.weights0)
    assert torch.equal(plain.tau, traced.tau)
    assert torch.equal(plain.cell_type, traced.cell_type)
    assert torch.equal(plain.positions, traced.positions)
    assert torch.equal(plain.z, traced.z)
    assert plain.viable == traced.viable
    assert plain.viability_reason == traced.viability_reason


def test_trace_stages_cover_the_pipeline_in_order():
    """轨迹阶段顺序与 `交互与可视化.md` §4 的动画顺序一致，且数量守恒可对账。"""
    phenotype = develop(Q, master_seed=42, index=0, collect_trace=True)
    trace = list(phenotype.trace or [])
    stages = [sample["stage"] for sample in trace]
    assert stages[0] == "grn"
    assert stages[-1] == "connectome"
    assert "proliferate" in stages
    # GRN 采样 = 初态 + 每步一个（development_steps）
    assert stages.count("grn") == DEFAULT_CONFIG.development_steps + 1
    assert stages.count("proliferate") == 1
    assert stages.count("connectome") == 1

    # 神经元数单调不减（precursor -> 分裂子代），且与最终一致
    counts = [sample["n_neurons"] for sample in trace]
    assert counts == sorted(counts)
    assert counts[-1] == int(phenotype.cell_type.numel())

    # 终点采样必须对上真实连接数（不能是另算的一版）
    assert trace[-1]["n_edges"] == int((phenotype.adjacency != 0).sum().item())
    # 早期阶段没有的量记 None（缺失 ≠ 0）
    assert trace[0]["n_edges"] is None
    assert trace[0]["n_divisions"] is None
    assert trace[-1]["mean_abs"] >= 0.0


def test_trace_carries_real_geometry_and_fates():
    """轨迹要带**逐神经元坐标**（画真实几何）与终点 fate；坐标在单位方域内。"""
    phenotype = develop(Q, master_seed=42, index=0, collect_trace=True)
    trace = list(phenotype.trace or [])

    for sample in trace:
        positions = sample["positions"]
        assert positions is not None, f"{sample['stage']} 缺少坐标"
        assert len(positions) == sample["n_neurons"]
        for x, y in positions:
            assert 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0, "坐标必须在单位方域（§3）"

    # 早期阶段 fate 未定 -> None；终点给出与神经元等长的 fate 序号（0..5）
    assert trace[0]["cell_type"] is None
    assert trace[-1]["cell_type"] is not None
    assert len(trace[-1]["cell_type"]) == trace[-1]["n_neurons"]
    assert set(trace[-1]["cell_type"]) <= set(range(len(DEFAULT_CONFIG.domains)))

    # 坐标随阶段变化（分裂产生子代 -> 末阶段坐标与初态不同）
    assert trace[0]["positions"] != trace[-1]["positions"]


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


def test_theta_d_is_per_seed_not_per_individual(monkeypatch):
    """Θ_D 每 seed 一套（RGCD §1/§13）：参数取自 ``development_params``（``t`` 恒 0），
    与 ξ 的逐个体流（``development``、``t = index``）**分离**。

    这是 penetrance 观测轴可辨识的前提 —— Θ_D 若逐个体重抽，每个个体一套发育规则，
    「基因型→表型」不具良定义（实测把 N 的类内 sd 由纯二项 2.26 抬到 3.3–4.0，
    并使两观测轴的 AUC 落到 0.50 附近）。
    """
    calls: list[tuple[str, int]] = []
    real = SeedManager.torch_generator

    def spy(self, name, index=0, device="cpu"):
        calls.append((name, index))
        return real(self, name, index, device)

    monkeypatch.setattr(SeedManager, "torch_generator", spy)
    develop(Q, master_seed=42, index=7)

    assert ("development_params", 0) in calls, "Θ_D 必须取自 development_params 的 t=0"
    assert ("development", 7) in calls, "ξ 必须仍走逐个体流（t=index）"
    assert [c for c in calls if c[0] == "development_params"] == [("development_params", 0)]


def test_retarget_spectral_radius_hits_target_and_preserves_structure():
    """§7(iv) 失配修复：重定后 ρ == target，且支撑与 Dale 符号不变（确定性、不耗随机数）。"""
    from evogenesis.development.grn import spectral_radius
    from evogenesis.development.rgcd import retarget_spectral_radius

    g = torch.Generator().manual_seed(0)
    adjacency = (torch.rand(10, 10, generator=g) < 0.3).to(torch.float32)
    adjacency.fill_diagonal_(0.0)
    w = adjacency * torch.randn(10, 10, generator=g)

    out = retarget_spectral_radius(w, 0.9)
    assert abs(spectral_radius(out) - 0.9) < 1e-5
    assert torch.equal(out != 0, w != 0), "支撑必须不变（A 的零元仍为零）"
    assert torch.equal(torch.sign(out), torch.sign(w)), "符号必须不变"

    # 非有限输入原样返回（不在此处吞掉失因，交 §7 判据记因）
    bad = w.clone()
    bad[0, 0] = float("nan")
    assert retarget_spectral_radius(bad, 0.9) is bad


def test_viability_positive_with_nonzero_contractive_weights():
    n = 7
    weights0 = torch.eye(n, dtype=torch.float32) * 0.3  # rho_spec=0.3 < 1
    viable, reason = _synthetic([0, 1, 2, 3, 4, 5, 5], weights0=weights0)
    assert viable is True, reason
    assert reason == "ok"


def test_domain_identity_spread_clamp_makes_missing_fate_unreachable():
    """§7 ``missing_fate`` 抽签修复：``U`` 的跨域散布被确定性收紧到**解析上界**。

    判据：域 k 的细胞被 §6 改判，需要 ``max_{j != k} g·(U_j - U_k) >= c_domain_bonus``。
    又 ``g`` 是 sigmoid 输出的凸组合（``g^0 = 0``，§4），逐分量严格落在 ``(0, 1)``，
    故 ``||g||_2 < sqrt(dim)`` 对一切可达 g 成立，于是

        max_{j,k} ||U_j - U_k|| <= c_domain_bonus / sqrt(dim)

    是该判据**永不触发**的解析充分条件（同 §7 判据 (ii) 的解析保证性质）。
    """
    dim, n_types = DEFAULT_CONFIG.grn_dim, len(DOMAINS)
    bonus = DEFAULT_CONFIG.c_domain_bonus
    assert dim > 1 and n_types > 1

    for seed in (1103, 2207, 3301, 42, 999):
        params = initialize_parameters(
            SeedManager(seed).torch_generator("development_params", 0), DEFAULT_CONFIG
        )
        centred = params.U - params.U.mean(dim=0, keepdim=True)
        spread = float((centred.unsqueeze(0) - centred.unsqueeze(1)).norm(dim=-1).max())
        assert spread <= bonus / dim**0.5 + 1e-6, f"seed {seed} 散布 {spread} 超上界"

        # 可达 g 集合内的最坏情形抽样：任一 g 都不应触发改判（gap 严格小于 bonus）
        generator = torch.Generator().manual_seed(seed)
        g = torch.rand((n_types * 40, dim), generator=generator)
        logits = g @ params.U.T
        worst = -float("inf")
        for k in range(n_types):
            other = logits.clone()
            other[:, k] = -float("inf")
            worst = max(worst, float((other.max(dim=1).values - logits[:, k]).max()))
        assert worst < bonus, f"seed {seed}: gap {worst} 不应达到 bonus {bonus}"


def test_domain_identity_spread_clamp_only_tightens_and_keeps_row_mean():
    """收紧是**单向**的（已在界内原样返回，不放大幸运抽样），且逐行均值不变。"""
    from evogenesis.development.rgcd import _clamp_domain_identity_spread

    dim, n_types, bonus = DEFAULT_CONFIG.grn_dim, len(DOMAINS), DEFAULT_CONFIG.c_domain_bonus
    target = bonus / dim**0.5

    tight = torch.randn(n_types, dim, generator=torch.Generator().manual_seed(0)) * 0.01
    assert _clamp_domain_identity_spread(tight, bonus, dim) is tight, "已在界内不得改动"

    loose = torch.randn(n_types, dim, generator=torch.Generator().manual_seed(1))
    before_mean = loose.mean(dim=0)
    out = _clamp_domain_identity_spread(loose, bonus, dim)
    centred = out - out.mean(dim=0, keepdim=True)
    spread = float((centred.unsqueeze(0) - centred.unsqueeze(1)).norm(dim=-1).max())
    assert abs(spread - target) < 1e-5, f"应恰好收到上界，实得 {spread} vs {target}"
    assert torch.allclose(out.mean(dim=0), before_mean, atol=1e-6), "逐行均值必须不变"
