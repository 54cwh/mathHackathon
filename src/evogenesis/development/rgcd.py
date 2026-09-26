"""RGCD 发育：连接概率（§8）、初权（§10）、时间常数（§11）、viability（§7）与入口。

范围：``RGCD数学模型.md`` §1–§11（v1.8 已定稿）。不实现 §12 Genome Sensitivity，
不做 batch>1 / padding（形状与 DanioNet 兼容：``N ≤ max_neurons``、``M`` active mask）。

随机数纪律：**两条**经 ``core §3`` 派生的流，不用 Python ``random`` / 裸 ``torch.manual_seed``
—— (1) 发育参数集 Θ_D：``torch_generator("development_params", 0)``，**每 seed 一套**
（§1/§13：发育参数是「该 run 的发育系统」，不随个体重抽）；(2) ξ（位置 / 分裂 Bernoulli /
ε_p / ε_g）：``torch_generator("development", index)``，**逐个体**。
dtype 统一 ``float32``（`core §7`）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch

from evogenesis.core.seed import SeedManager
from evogenesis.core.tensors import to_float32_tensor
from evogenesis.development.config import DEFAULT_CONFIG, DOMAIN_ORDER, RGCDConfig
from evogenesis.development.development import (
    cell_identity,
    place_precursors,
    proliferate,
)
from evogenesis.development.grn import discrete_grn, spectral_radius

# §9 固定兼容性 prior（pre \\ post，顺序 [S,P,T,M,I,O]）。人工 prior，MVP 不学习。
_COMPATIBILITY_PRIOR: tuple[tuple[float, ...], ...] = (
    (-2.0, 1.8, 1.8, 0.6, 0.2, -0.5),
    (-2.0, 0.2, -0.8, 1.4, 0.3, 1.2),
    (-2.0, -0.8, 0.2, 1.2, 0.8, 1.5),
    (-1.5, 0.3, 0.3, 1.3, 1.0, 1.4),
    (-2.0, 0.4, 0.4, 0.9, 0.0, 1.5),
    (-2.0, -1.5, -1.5, -0.5, -0.5, -1.0),
)


@dataclass
class ConnectomePhenotype:
    """RGCD 发育产物。字段名沿用冻结契约（RGCD §1）。

    ``z`` 为 §1 输出 ``Z``（``z_i = softmax(l_i)``，§6），必填；``cell_type`` 与
    ``positions`` 为发育附加字段（`DanioNet` 消费）。
    """

    adjacency: torch.Tensor
    weights0: torch.Tensor
    tau: torch.Tensor
    cell_type: torch.Tensor
    positions: torch.Tensor
    active_mask: torch.Tensor
    viable: bool
    viability_reason: str
    z: torch.Tensor


@dataclass(frozen=True)
class RGCDParameters:
    """§13 参数集合 ``Theta_D``（由 seed 确定性初始化；本模块不保存随机源）。"""

    Wg: torch.Tensor
    B: torch.Tensor
    P: torch.Tensor
    b: torch.Tensor
    U: torch.Tensor
    c_domain: torch.Tensor
    w_div: torch.Tensor
    b_div: torch.Tensor
    compatibility: torch.Tensor
    weight_vector: torch.Tensor
    b_w: torch.Tensor
    tau_vector: torch.Tensor
    b_tau: torch.Tensor
    distance_lambda: float
    regulatory_gamma: float


def compatibility_prior(*, dtype: torch.dtype = torch.float32, device: str = "cpu") -> torch.Tensor:
    """§9 的 6×6 固定 prior 矩阵 ``C``。"""
    return torch.tensor(_COMPATIBILITY_PRIOR, dtype=dtype, device=device)


def softplus_inverse(value: float) -> float:
    """``softplus^{-1}(v) = log(exp(v) - 1)``（§10 的 ``b_w``；要求 ``v > 0``）。"""
    if value <= 0.0:
        raise ValueError("softplus 的反函数仅在正输入上有定义")
    return math.log(math.expm1(value))


def _clamp_domain_identity_spread(
    U: torch.Tensor, bonus: float, dim: int
) -> torch.Tensor:
    r"""把 §6 的 ``U`` 跨域散布**确定性收紧**到解析最坏情形 = ``c_domain_bonus``。

    §7 Developmental viability 的 ``missing_fate:<域>`` 判据是「存在域 k 使 ``argmax z``
    不含 k」。由 `development.development.cell_identity` 的 ``z = softmax(g U^T + c_domain)``，
    域 k 的某个细胞被改判的充要条件是

    .. math:: \max_{j \neq k} g \cdot (U_j - U_k) \ge c_{\mathrm{domain}}.

    该差值对 ``U`` 的逐行均值不敏感：均值在 ``U_j - U_k`` 中抵消，且对 softmax 只是整体
    平移，故只有**中心化部分** ``\tilde U`` 决定判据。又 ``g`` 是 sigmoid 输出的凸组合
    （``g^0 = 0``，§4），逐分量严格落在 ``(0, 1)``，故 ``\|g\|_2 < \sqrt{\dim}`` 对
    **一切可达 g** 恒成立，于是得解析充分条件

    .. math:: \max_{j,k} \|\tilde U_j - \tilde U_k\|_2 \le
              \frac{c_{\mathrm{domain}}}{\sqrt{\dim}}
              \;\Longrightarrow\; \text{missing\_fate 严格不可达}.

    本函数把中心化部分按该上界线性收紧（逐行均值不变）；**只收紧、不放大**——散布已在界内
    时原样返回，避免把一次幸运抽样放大成风险。不吃随机数、不改符号/支撑结构，与 §4 对
    ``W_g`` 的谱半径重定同源（同一种「确定性重定到判据工作点」的做法）。

    口径说明：该上界是**解析**的（同 §7 判据 (ii)），代价是默认配置下 §6 的 ``argmax z``
    恒等于谱系域，``missing_fate`` 在默认配置下不再触发；判因词表仍保留该 token（非默认
    配置或更大的 ``U`` 仍需它上报）。
    """
    mean_row = U.mean(dim=0, keepdim=True)
    centred = U - mean_row
    spread = float((centred.unsqueeze(0) - centred.unsqueeze(1)).norm(dim=-1).max().item())
    target = bonus / math.sqrt(dim)
    if not spread > target > 0.0:
        return U
    return mean_row + centred * (target / spread)


def initialize_parameters(
    generator: torch.Generator, config: RGCDConfig = DEFAULT_CONFIG
) -> RGCDParameters:
    """按 §4/§5/§6/§10/§11/§13 由同一个 ``torch.Generator`` 确定性初始化 ``Theta_D``。

    抽取顺序固定：``W_g → B → P → b → U → w_d → u → a``（可复现性依赖此顺序）。
    """
    device = str(generator.device)
    dtype = torch.float32
    dim = config.grn_dim
    n_types = config.n_domains
    weight_std = 1.0 / math.sqrt(dim)
    feature_std = 1.0 / math.sqrt(config.weight_feature_dim)

    # §4: W_g 取 Xavier(Glorot) uniform 后重标定谱半径 rho_spec。
    if config.grn_weight_init != "xavier":
        raise NotImplementedError(
            f"未实现 grn.weight_init={config.grn_weight_init!r}（冻结为 xavier）"
        )
    xavier_a = math.sqrt(6.0 / (dim + dim))
    Wg = torch.empty((dim, dim), dtype=dtype, device=device).uniform_(
        -xavier_a, xavier_a, generator=generator
    )
    radius = spectral_radius(Wg)
    if radius > 0.0:
        Wg = Wg * (config.grn_spectral_radius / radius)

    B = torch.randn((dim, dim), dtype=dtype, generator=generator, device=device) * weight_std
    P = torch.randn((dim, 2), dtype=dtype, generator=generator, device=device) * weight_std
    b = torch.randn((dim,), dtype=dtype, generator=generator, device=device) * config.init_b_std

    # §6: U ~ N(0,(1/sqrt(dim))^2)；c_domain one-hot * bonus。
    U = torch.randn((n_types, dim), dtype=dtype, generator=generator, device=device) * weight_std
    # §7 ``missing_fate`` 抽签修复：``U`` 的跨域散布原本是每 seed 一次的自由抽签，
    # 实测 20 个 seed 中 5 个（25%）使某个域被系统性改判，该 seed 下 33%–67% 个体
    # 因 ``missing_fate:prey|threat`` 不可育（同 ρ(W^0) 一路的「每-seed 抽签型门禁」）。
    # 按解析上界确定性收紧（见 helper docstring）；不吃随机数。
    U = _clamp_domain_identity_spread(U, config.c_domain_bonus, dim)
    c_domain = config.c_domain_bonus * torch.eye(n_types, dtype=dtype, device=device)

    # §5: w_d ~ N(0,(1/sqrt(dim))^2)、b_d=0。
    w_div = torch.randn((dim,), dtype=dtype, generator=generator, device=device) * weight_std
    b_div = torch.zeros((), dtype=dtype, device=device)

    # §10: u ~ N(0,(1/sqrt(feature_dim))^2)、b_w = softplus^{-1}(w_bar)。
    weight_vector = torch.randn(
        (config.weight_feature_dim,), dtype=dtype, generator=generator, device=device
    )
    weight_vector = weight_vector * feature_std
    b_w = torch.tensor(softplus_inverse(config.w_bar_initial), dtype=dtype, device=device)

    # §11: a ~ N(0,(1/sqrt(dim))^2)、b_tau=0。
    tau_vector = torch.randn((dim,), dtype=dtype, generator=generator, device=device) * weight_std
    b_tau = torch.zeros((), dtype=dtype, device=device)

    return RGCDParameters(
        Wg=Wg,
        B=B,
        P=P,
        b=b,
        U=U,
        c_domain=c_domain,
        w_div=w_div,
        b_div=b_div,
        compatibility=compatibility_prior(device=device),
        weight_vector=weight_vector,
        b_w=b_w,
        tau_vector=tau_vector,
        b_tau=b_tau,
        distance_lambda=config.distance_lambda,
        regulatory_gamma=config.regulatory_gamma,
    )


def tau_from_grn(
    grn: torch.Tensor,
    a: torch.Tensor,
    b: torch.Tensor,
    *,
    tau_min: float = 1.0,
    tau_max: float = 10.0,
) -> torch.Tensor:
    """§11 ``tau_i = tau_min + (tau_max - tau_min) * sigmoid(...)``。"""
    return tau_min + (tau_max - tau_min) * torch.sigmoid(grn @ a + b)


def apply_dale_sign(
    weights_abs: torch.Tensor,
    cell_type: torch.Tensor,
    inhibitory_index: int = DOMAIN_ORDER.index("inhibitory"),
) -> torch.Tensor:
    """§10 Dale sign：符号由**突触前**（行 ``i``）类型定，Inhibitory→−1，否则 +1。"""
    sign = torch.ones(weights_abs.shape[0], dtype=weights_abs.dtype, device=weights_abs.device)
    sign[cell_type == inhibitory_index] = -1.0
    return weights_abs * sign[:, None]


def centered_bilinear(grn: torch.Tensor) -> torch.Tensor:
    """§8 ``R_{ij} = (1/8) sum_k ghat_ik ghat_jk``（本代中心化，``ghat = (g - mean)/std``）。

    ``std`` 为 0 的分量显式置 1（分子同时为 0，贡献 0），避免除零。
    """
    if grn.ndim != 2:
        raise ValueError("centered_bilinear 需要 (N, dim) 的 GRN 终态")
    mean = grn.mean(dim=0)
    std = grn.std(dim=0, unbiased=False)
    safe_std = torch.where(std > 0.0, std, torch.ones_like(std))
    centered = (grn - mean) / safe_std
    return (centered @ centered.T) / grn.shape[1]


def connection_logits(
    z: torch.Tensor,
    positions: torch.Tensor,
    compatibility: torch.Tensor,
    *,
    distance_lambda: float,
    regulatory_gamma: float,
    regulatory_term: torch.Tensor,
) -> torch.Tensor:
    """§8 ``ell_ij = z_i^T C z_j - lambda d_ij + gamma R_ij``（不含 ``b_A``）。"""
    type_term = z @ compatibility @ z.T
    distance = torch.cdist(positions, positions)
    return type_term - distance_lambda * distance + regulatory_gamma * regulatory_term


def expected_off_diagonal_density(logits: torch.Tensor, bias: float) -> float:
    """给定额外 bias 的**期望** off-diagonal 密度 ``mean_{i≠j} sigmoid(logits+bias)``。"""
    n = logits.shape[0]
    if n < 2:
        return 0.0
    probs = torch.sigmoid(logits + bias)
    off = probs.sum() - probs.diagonal().sum()
    return float((off / (n * (n - 1))).item())


def solve_bias_for_density(
    logits: torch.Tensor, target_density: float, *, tol: float = 1e-8, max_iter: int = 200
) -> float:
    """§8 ``b_A`` 二分反解：使期望 off-diagonal density = ``target_density``。

    确定性、**不消耗随机数**（只用 ``logits`` 的解析 sigmoid 均值）。
    """
    if not 0.0 < target_density < 1.0:
        raise ValueError("target_density 必须落在 (0, 1)")
    if logits.ndim != 2 or logits.shape[0] != logits.shape[1]:
        raise ValueError(f"logits 必须为方阵，实际 {tuple(logits.shape)}")
    if logits.shape[0] < 2:
        raise ValueError("bias 反解需要 ≥2 个神经元（否则 off-diagonal density 无定义）")
    lo, hi = -60.0, 60.0
    while expected_off_diagonal_density(logits, lo) > target_density:
        lo -= 60.0
    while expected_off_diagonal_density(logits, hi) < target_density:
        hi += 60.0
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if expected_off_diagonal_density(logits, mid) < target_density:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def initial_weights(
    adjacency: torch.Tensor,
    grn: torch.Tensor,
    z: torch.Tensor,
    cell_type: torch.Tensor,
    weight_vector: torch.Tensor,
    b_w: torch.Tensor,
    inhibitory_index: int,
) -> torch.Tensor:
    """§10 ``|w_ij| = softplus(u^T[g_i;g_j;z_i;z_j] + b_w)``，符号由突触前定。

    结果与 ``A`` 逐元素相乘（支撑外恒 0，与 DanioNet §3 的 ``W = A ⊙ ...`` 及
    ``ΔW`` 支撑外为 0 自洽）。
    """
    n = grn.shape[0]
    grn_i = grn[:, None, :].expand(n, n, grn.shape[1])
    grn_j = grn[None, :, :].expand(n, n, grn.shape[1])
    z_i = z[:, None, :].expand(n, n, z.shape[1])
    z_j = z[None, :, :].expand(n, n, z.shape[1])
    features = torch.cat([grn_i, grn_j, z_i, z_j], dim=-1)
    magnitude = torch.nn.functional.softplus(features @ weight_vector + b_w)
    signed = apply_dale_sign(magnitude, cell_type, inhibitory_index)
    return adjacency * signed


def retarget_spectral_radius(weights: torch.Tensor, target: float) -> torch.Tensor:
    r"""把 ``ρ_spec(W)`` **确定性**重定到 ``target``（§7(iv) 失配修复；仿 §4 对 ``W_g`` 的做法）。

    **动因（§7 实测工作点，2026-09-26 可复现）**：判据 (iv) ``ρ(W^{(0)})<1`` 是**唯一绑定约束**
    —— 89.8% 的发育尝试因 ``ρ≥1`` 被拒、活跃子矩阵的 ρ 中位数 **1.63**、仅 10.2% 落于阈下。
    根因是 §10 的 ``w_bar=0.5`` 与 ``ρ<1`` **不自洽**（``ρ ≈ w_bar × 平均度``）。逐个体重抽 Θ_D
    曾把该拒绝率**摊薄**为「每个体约 10% 通过」；Θ_D 改为每 seed 一套后它变成**整跑一枚硬币**
    （实测逐 seed viability 率 0%–52%），管线在部分 seed 上产不出**任何** viable 个体。

    **修法**：沿用 §4 对 ``W_g`` 的既有惯例（Xavier → 重定谱半径 ``ρ=0.9``），把 ``W^{(0)}``
    重定到 ``target``，使 (iv) 对**任意** Θ_D 成立。缩放系数为正标量 ⇒ Dale 符号、支撑
    （``A`` 的零元）与掩码结构全部不变。**不消耗随机数**。

    非有限或零谱半径时**原样返回**，交由 §7 的 ``nonfinite_activation`` / (iv) 判据如实记因
    （不在此处吞掉失因）。
    """
    if target <= 0.0:
        raise ValueError(f"ρ 目标须为正，得到 {target}")
    if not bool(torch.isfinite(weights).all()):
        return weights
    radius = spectral_radius(weights)
    if radius <= 0.0:
        return weights
    return weights * (target / radius)


def _reachability(adjacency: torch.Tensor) -> torch.Tensor:
    """``A`` 的有向可达闭包（bool ``(N, N)``）；``A_ij`` 为 ``i → j``。"""
    n = adjacency.shape[0]
    reach = (adjacency > 0).to(torch.float32)
    for _ in range(max(n, 2).bit_length()):
        reach = ((reach + reach @ reach) > 0).to(torch.float32)
    return reach > 0


def _motor_sides(
    positions: torch.Tensor, cell_type: torch.Tensor, motor_index: int
) -> tuple[torch.Tensor, torch.Tensor]:
    """DanioNet §5：motor 池按发育坐标 ``x`` 中位数二分；同值按索引破平。"""
    motor = torch.nonzero(cell_type == motor_index, as_tuple=False).squeeze(-1)
    if motor.numel() == 0:
        return motor, motor
    order = torch.argsort(positions[motor, 0], stable=True)
    left_count = motor.numel() // 2
    left = motor[order[:left_count]]
    right = motor[order[left_count:]]
    return left, right


def _zero_input_trajectory(
    weights0: torch.Tensor,
    tau: torch.Tensor,
    steps: int,
    activation: str,
    neuron_bias: torch.Tensor | None,
) -> torch.Tensor:
    """DanioNet §3 更新式的 zero-input 特例（``x≡0``、``H≡0``），返回 ``(steps+1, N)``。

    ``weights0`` 已按 ``A`` 掩码；``neuron_bias`` 为 ``b_i``（RGCD 契约不含，缺省 0）。
    """
    if activation != "tanh":
        raise NotImplementedError(f"未实现 activation={activation!r}（DanioNet 冻结 phi=tanh）")
    inv_tau = 1.0 / tau
    h = torch.zeros(weights0.shape[0], dtype=torch.float32, device=weights0.device)
    trajectory = [h]
    for _ in range(steps):
        drive = weights0 @ h
        if neuron_bias is not None:
            drive = drive + neuron_bias
        h = (1.0 - inv_tau) * h + inv_tau * torch.tanh(drive)
        trajectory.append(h)
    return torch.stack(trajectory)


def viability_check(
    adjacency: torch.Tensor,
    cell_type: torch.Tensor,
    positions: torch.Tensor,
    tau: torch.Tensor,
    weights0: torch.Tensor,
    active_mask: torch.Tensor,
    *,
    domains: tuple[str, ...] = DEFAULT_CONFIG.domains,
    zero_input_steps: int = DEFAULT_CONFIG.zero_input_steps,
    saturation_ratio_max: float = DEFAULT_CONFIG.saturation_ratio_max,
    saturation_eps: float = DEFAULT_CONFIG.saturation_eps,
    activation: str = DEFAULT_CONFIG.network_activation,
    neuron_bias: torch.Tensor | None = None,
) -> tuple[bool, str]:
    """§7 viability：developmental + functional + dynamical，返回 ``(viable, 失因)``。

    失因是具体字符串（多因以 ``;`` 连接）；viable 时为 ``"ok"``。
    """
    active = active_mask.to(torch.bool)
    if int(active.sum()) == 0:
        return False, "no_active_neurons"
    idx = torch.nonzero(active, as_tuple=False).squeeze(-1)
    ct = cell_type[idx]
    pos = positions[idx]
    adjacency = adjacency[idx][:, idx]
    weights0 = weights0[idx][:, idx]
    tau = tau[idx]
    bias = None if neuron_bias is None else neuron_bias[idx]

    reasons: list[str] = []

    # Developmental viability（§7）
    present = set(ct.tolist())
    missing = [name for index, name in enumerate(domains) if index not in present]
    if missing:
        reasons.append("missing_fate:" + ",".join(missing))
    motor_index = domains.index("motor")
    left, right = _motor_sides(pos, ct, motor_index)
    if left.numel() == 0 or right.numel() == 0:
        reasons.append("motor_side_empty")

    # Functional viability（§7）：sensory ↝ motor 有向路径
    sensory_index = domains.index("sensory")
    sources = torch.nonzero(ct == sensory_index, as_tuple=False).squeeze(-1)
    targets = torch.nonzero(ct == motor_index, as_tuple=False).squeeze(-1)
    if sources.numel() == 0 or targets.numel() == 0:
        reasons.append("no_sensory_to_motor_path")
    else:
        reach = _reachability(adjacency)
        if not bool(reach[sources][:, targets].any()):
            reasons.append("no_sensory_to_motor_path")

    # Dynamical viability（§7）
    trajectory = _zero_input_trajectory(weights0, tau, zero_input_steps, activation, bias)
    if not bool(torch.isfinite(trajectory).all()):
        reasons.append("nonfinite_activation")
    elif not bool((trajectory.abs() <= 1.0).all()):
        reasons.append("activation_bound_violated")
    tail = trajectory[max(0, zero_input_steps - 10) : zero_input_steps]
    if tail.numel() > 0:
        saturation = float((tail.abs() > 1.0 - saturation_eps).to(torch.float32).mean().item())
        if saturation >= saturation_ratio_max:
            reasons.append("persistent_saturation")
    # 非有限 W⁰（如 softplus 溢出）时谱半径无定义，直接记「非收敛」失因，不调用
    # `spectral_radius`（后者对 NaN/Inf 抛错，会把失因上报变成崩溃）。
    if not bool(torch.isfinite(weights0).all()) or not spectral_radius(weights0) < 1.0:
        reasons.append("weight_spectral_radius_not_contractive")

    if reasons:
        return False, ";".join(reasons)
    return True, "ok"


def _to_float32_tensor(value: np.ndarray | torch.Tensor, device: str = "cpu") -> torch.Tensor:
    """跨框架边界转换（RGCD §1 / core §7）：NumPy ``float32`` → ``torch.float32``。

    NumPy 路径走 core 公开函数 ``core/tensors.py::to_float32_tensor``；已是张量时只对齐
    dtype/device（禁止隐式 ``float64``）。
    """
    if isinstance(value, torch.Tensor):
        return value.to(dtype=torch.float32, device=device)
    return to_float32_tensor(value, device=device)


def develop(
    q: np.ndarray | torch.Tensor,
    *,
    master_seed: int,
    index: int,
    config: RGCDConfig = DEFAULT_CONFIG,
    device: str = "cpu",
) -> ConnectomePhenotype:
    """§1–§11 单个体发育入口：``q(G) → (A, Z, tau, W^0, M)`` + viability。

    ``q`` 为 genome 侧 ``q(G) ∈ [0,1]^8``（NumPy ``float32`` 或 ``torch.float32``）；
    ``index`` 为命名空间内稳定实体序号（`core §3`，不得用调用顺序）。

    §7 动力学检查在发育期以 ``b_i = 0`` 近似（``b_i`` 归 DanioNet §3，本模块不产出）；
    最终 viability 由 DanioNet 用其 ``b_{type_i}`` 复核。
    """
    if q.shape[-1] != config.grn_dim:
        raise ValueError(f"q(G) 维数 {q.shape[-1]} 与 grn.dim {config.grn_dim} 不一致")
    if config.distance_space != "unit_square":
        raise NotImplementedError(
            "仅实现 distance_space='unit_square'（RGCD §8 的 λ 口径），"
            f"实际 {config.distance_space!r}"
        )
    if config.placement != "domain_blocked" or config.position_space != "unit_square":
        raise NotImplementedError("仅实现冻结的 domain_blocked / unit_square 放置（RGCD §3）")
    if config.grn_activation != "sigmoid":
        raise NotImplementedError(f"未实现 grn.activation={config.grn_activation!r}")

    # Θ_D 每 seed 一套（§1/§13；命名空间 ``development_params``、`t` 恒 0，同 ``network_init``
    # 先例）。ξ 仍走 ``development`` 的逐个体流（`t = index`），故同 seed 不同 index 的
    # 位置/分裂/ε 依然不同 —— ``test_different_entity_index_differs`` 仍成立。
    params = initialize_parameters(
        SeedManager(master_seed).torch_generator("development_params", 0, device=device),
        config,
    )
    generator = SeedManager(master_seed).torch_generator("development", index, device=device)
    q_tensor = _to_float32_tensor(q, device=str(generator.device))

    positions, domain_index = place_precursors(
        config.domains, config.precursors_per_domain, generator=generator
    )
    n0 = positions.shape[0]
    if n0 != config.initial_precursors:
        raise ValueError(
            f"初始 precursor 数 {n0} 与 development.initial_precursors "
            f"{config.initial_precursors} 不一致（§3）"
        )

    g0 = torch.zeros((n0, config.grn_dim), dtype=torch.float32, device=str(generator.device))
    grn = discrete_grn(
        g0,
        q_tensor,
        positions,
        params.Wg,
        params.B,
        params.P,
        params.b,
        rho=config.grn_rho,
        steps=config.development_steps,
    )
    state = proliferate(
        grn,
        positions,
        domain_index,
        params.w_div,
        params.b_div,
        split_noise=config.split_noise,
        gene_noise=config.gene_noise,
        max_divisions_per_precursor=config.max_divisions_per_precursor,
        generator=generator,
    )
    if state.grn.shape[0] > config.max_neurons:
        raise ValueError(
            f"神经元数 {state.grn.shape[0]} 超过 max_neurons {config.max_neurons}（§5）"
        )

    z = cell_identity(state.grn, params.U, params.c_domain[state.domain_index])
    cell_type = z.argmax(dim=-1)

    tau = tau_from_grn(
        state.grn,
        params.tau_vector,
        params.b_tau,
        tau_min=config.tau_min,
        tau_max=config.tau_max,
    )

    if config.ablation_w_grn:
        # `connectome §9` w/o GRN：A ~ Bernoulli(p) 独立采样（禁 self-loop），与 GRN/几何无关；
        # 其余（N / τ / W⁰ 幅度 / Dale / viability）全部保持，只隔离「GRN 布线」变量。
        density = float(config.ablation_random_density)
        if not 0.0 <= density <= 1.0:
            raise ValueError(f"ablation_random_density 须在 [0,1]，得到 {density}")
        n = int(state.grn.shape[0])
        probs = torch.full((n, n), density, dtype=torch.float32, device=state.grn.device)
    else:
        regulatory = centered_bilinear(state.grn)
        logits = connection_logits(
            z,
            state.positions,
            params.compatibility,
            distance_lambda=params.distance_lambda,
            regulatory_gamma=params.regulatory_gamma,
            regulatory_term=regulatory,
        )
        b_a = solve_bias_for_density(logits, config.target_density)
        probs = torch.sigmoid(logits + b_a)
    if not config.allow_self_loops:
        probs.fill_diagonal_(0.0)
    adjacency = (
        torch.rand(probs.shape, dtype=torch.float32, device=probs.device, generator=generator)
        < probs
    ).to(torch.float32)

    inhibitory_index = config.domains.index("inhibitory")
    weights0 = initial_weights(
        adjacency,
        state.grn,
        z,
        cell_type,
        params.weight_vector,
        params.b_w,
        inhibitory_index,
    )
    # §7(iv)：谱半径重定 —— 见 `retarget_spectral_radius` 的动因（修复 §10 与 (iv) 的失配）
    weights0 = retarget_spectral_radius(weights0, config.rho_w0_target)

    viable, reason = viability_check(
        adjacency,
        cell_type,
        state.positions,
        tau,
        weights0,
        state.active_mask,
        domains=config.domains,
        zero_input_steps=config.zero_input_steps,
        saturation_ratio_max=config.saturation_ratio_max,
        saturation_eps=config.saturation_eps,
        activation=config.network_activation,
    )
    return ConnectomePhenotype(
        adjacency=adjacency,
        weights0=weights0,
        tau=tau,
        cell_type=cell_type,
        positions=state.positions,
        active_mask=state.active_mask,
        viable=viable,
        viability_reason=reason,
        z=z,
    )
