"""DanioNet：六类神经元网络（`DanioNet设计规范.md` v1.7 §1–§9）。

产出：activation ``h`` / 连续动作 ``(ω, v)`` / 当代 ``ΔW``。消费 RGCD 的
``ConnectomePhenotype``（``A, Z, τ, W⁰, M``）；``ΔW`` 不遗传（§7）。

实现约定（§3 定稿段）：``h₀ = 0``；padding 宽度取 ``development.max_neurons``；
``U/m/b`` 为按 cell type 的**全局单表**，在 ``network_init`` 命名空间（`core §3`，id=5）
下由 master seed 初始化一次。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import torch
from torch.nn import functional as F

from evogenesis.connectome.config import (
    DEFAULT_NETWORK_CONFIG,
    DOMAIN_ORDER,
    NetworkReadoutConfig,
)
from evogenesis.core.seed import SeedManager
from evogenesis.core.tensors import to_float32_tensor
from evogenesis.development import ConnectomePhenotype
from evogenesis.development.rgcd import viability_check

_ACTIVATIONS = {"tanh": torch.tanh}
# 数值实现常量：softplus⁻¹ 在 y 超过该值时改用渐近式（float32 下 expm1 约在 88 溢出）
_SOFTPLUS_INVERSE_SWITCH = 40.0


def motor_sides(
    positions: torch.Tensor, cell_type: torch.Tensor, motor_index: int
) -> tuple[torch.Tensor, torch.Tensor]:
    """§5：motor 池按发育坐标 ``x`` 中位数二分，``x`` 低于中位者 left、其余 right。

    同值按神经元索引破平（``stable`` 排序）。返回两池的神经元索引（可空）。
    """
    motor = torch.nonzero(cell_type == motor_index, as_tuple=False).squeeze(-1)
    if motor.numel() == 0:
        return motor, motor
    order = torch.argsort(positions[motor, 0], stable=True)
    left_count = motor.numel() // 2
    return motor[order[:left_count]], motor[order[left_count:]]


@dataclass(frozen=True)
class NetworkPriors:
    """§3：按 cell type 的固定先验，全局单表（全体个体共享）。"""

    U: torch.Tensor  # (n_cell_types, sensory_dim) float32
    m: torch.Tensor  # (n_cell_types,) float32
    b: torch.Tensor  # (n_cell_types,) float32


def build_priors(
    master_seed: int,
    *,
    config: NetworkReadoutConfig = DEFAULT_NETWORK_CONFIG,
    device: str = "cpu",
) -> NetworkPriors:
    """在 ``network_init`` 命名空间（``core §3``，id=5，index=0）初始化 ``U/m/b`` 一次。"""
    generator = SeedManager(master_seed).torch_generator("network_init", 0, device=device)
    shape = (config.n_cell_types, config.sensory_dim)
    U = torch.randn(shape, generator=generator, device=device, dtype=torch.float32)
    U = U * config.input_weight_std
    m = (
        torch.randn((config.n_cell_types,), generator=generator, device=device, dtype=torch.float32)
        * config.hunger_gain_std
    )
    b = (
        torch.randn((config.n_cell_types,), generator=generator, device=device, dtype=torch.float32)
        * config.neuron_bias_std
    )
    return NetworkPriors(U=U, m=m, b=b)


class DanioNet(torch.nn.Module):
    """一个或多个个体的 DanioNet（batch 内 padding 到 ``max_nodes``，掩码驱动）。

    可训练参数只有 ``theta``（与 ``W⁰`` 同形状、同 dtype 的 ``float32``）；支撑 ``A`` 与
    ``sign(W⁰)`` 训练期冻结，padding 行列恒 0 且不参与梯度。
    """

    def __init__(
        self,
        phenotypes: Sequence[ConnectomePhenotype],
        *,
        master_seed: int,
        config: NetworkReadoutConfig = DEFAULT_NETWORK_CONFIG,
        device: str = "cpu",
        sign_constrained: bool = True,
        priors: NetworkPriors | None = None,
    ) -> None:
        super().__init__()
        if len(phenotypes) == 0:
            raise ValueError("至少需要一个个体")
        if config.activation not in _ACTIVATIONS:
            raise NotImplementedError(f"未实现 activation={config.activation!r}")
        self.config = config
        self.device = device
        self.sign_constrained = sign_constrained
        self._phi = _ACTIVATIONS[config.activation]

        batch = len(phenotypes)
        max_nodes = config.max_nodes
        dtype = torch.float32

        adjacency = torch.zeros((batch, max_nodes, max_nodes), dtype=dtype, device=device)
        weights0 = torch.zeros((batch, max_nodes, max_nodes), dtype=dtype, device=device)
        tau = torch.ones((batch, max_nodes), dtype=dtype, device=device)
        cell_type = torch.zeros((batch, max_nodes), dtype=torch.long, device=device)
        positions = torch.zeros((batch, max_nodes, 2), dtype=dtype, device=device)
        neuron_mask = torch.zeros((batch, max_nodes), dtype=torch.bool, device=device)
        left_mask = torch.zeros((batch, max_nodes), dtype=torch.bool, device=device)
        right_mask = torch.zeros((batch, max_nodes), dtype=torch.bool, device=device)
        motor_mask = torch.zeros((batch, max_nodes), dtype=torch.bool, device=device)

        motor_index = config.domains.index("motor")
        self._n_neurons: list[int] = []
        for b, phenotype in enumerate(phenotypes):
            n = int(phenotype.adjacency.shape[0])
            if n > max_nodes:
                raise ValueError(f"个体 {b} 的神经元数 {n} 超过 max_nodes {max_nodes}")
            if phenotype.adjacency.shape != (n, n):
                raise ValueError(
                    f"个体 {b} 的 adjacency 必须为方阵，实际 {tuple(phenotype.adjacency.shape)}"
                )
            if phenotype.weights0.shape != (n, n):
                raise ValueError(f"个体 {b} 的 weights0 形状应与 adjacency 一致 (n, n)")
            if (
                phenotype.tau.shape != (n,)
                or phenotype.cell_type.shape != (n,)
                or phenotype.active_mask.shape != (n,)
                or phenotype.positions.shape != (n, 2)
            ):
                raise ValueError(
                    f"个体 {b} 的 tau/cell_type/active_mask/positions 长度与 n={n} 不一致"
                )
            adjacency[b, :n, :n] = to_float32_tensor(phenotype.adjacency, device=device)
            weights0[b, :n, :n] = to_float32_tensor(phenotype.weights0, device=device)
            tau[b, :n] = to_float32_tensor(phenotype.tau, device=device)
            cell_type[b, :n] = phenotype.cell_type.to(device=device, dtype=torch.long)
            positions[b, :n] = to_float32_tensor(phenotype.positions, device=device)
            neuron_mask[b, :n] = phenotype.active_mask.to(device=device, dtype=torch.bool)
            self._n_neurons.append(n)

            types = phenotype.cell_type.to(device=device, dtype=torch.long)
            active = phenotype.active_mask.to(device=device, dtype=torch.bool)
            motor_local = torch.nonzero((types == motor_index) & active, as_tuple=False).squeeze(-1)
            left_local, right_local = motor_sides(
                phenotype.positions[motor_local].to(device=device), types[motor_local], motor_index
            )
            left_local = motor_local[left_local]
            right_local = motor_local[right_local]
            if left_local.numel() == 0 or right_local.numel() == 0:
                raise ValueError(f"个体 {b} 的 motor 左右池为空（§5 / RGCD §7）")
            left_mask[b, left_local] = True
            right_mask[b, right_local] = True
            motor_mask[b, motor_local] = True

        tau_min = self.config.tau_min
        if not bool((tau >= tau_min).all() and torch.isfinite(tau).all()):
            raise ValueError(
                f"tau 必须 ≥ {tau_min}（`connectome.tau_min`，RGCD §11）且有限；§3 按 1/τ 更新"
            )
        # §3：非活跃神经元（M=False）的行/列恒 0 —— W⁰ 亦按 M 屏蔽，
        # 使 sign(W⁰)、Θ 初值与 ΔW 在非活跃处天然为 0（初始 ΔW=0 全局成立）。
        weights0 = weights0 * neuron_mask[:, :, None] * neuron_mask[:, None, :]
        support = (adjacency != 0) & neuron_mask[:, :, None] & neuron_mask[:, None, :]
        self.register_buffer("adjacency", adjacency)
        self.register_buffer("weights0", weights0)
        self.register_buffer("sign0", torch.sign(weights0))
        self.register_buffer("support", support)
        # 预算 support ⊙ sign(W⁰)（训练期冻结），effective_weights 只需再乘 softplus(Θ)。
        self.register_buffer("support_sign0", support.to(torch.float32) * torch.sign(weights0))
        self.register_buffer("support_f32", support.to(torch.float32))
        self.register_buffer("tau", tau)
        self.register_buffer("cell_type", cell_type)
        self.register_buffer("positions", positions)
        self.register_buffer("neuron_mask", neuron_mask)
        self.register_buffer("left_mask", left_mask)
        self.register_buffer("right_mask", right_mask)
        self.register_buffer("motor_mask", motor_mask)
        self.register_buffer("h", torch.zeros((batch, max_nodes), dtype=dtype, device=device))

        # 约束路径：Θ 初值 = softplus^{-1}(|W⁰|) ⇒ 初始 ΔW = 0（§3）；非约束路径（消融）
        # 参数直接就是有效权重 W，故初值取 W⁰，使两路径**同一起点**。支撑外均由 support 置零。
        theta_init = (
            self._softplus_inverse(torch.abs(weights0)) if sign_constrained else weights0.clone()
        )
        self.theta = torch.nn.Parameter(theta_init)

        if priors is None:
            priors = build_priors(master_seed, config=config, device=device)
        self.register_buffer("U", to_float32_tensor(priors.U, device=device))
        self.register_buffer("m", to_float32_tensor(priors.m, device=device))
        self.register_buffer("b", to_float32_tensor(priors.b, device=device))

    @staticmethod
    def _softplus_inverse(value: torch.Tensor) -> torch.Tensor:
        r"""``softplus^{-1}(y) = log(exp(y) - 1)``（``y > 0``）；``y = 0`` 处取 0。

        ``y`` 较大时改用等价式 ``y + log1p(-exp(-y))``（float32 下避免 ``expm1`` 溢出为 inf）。
        """
        small = value <= _SOFTPLUS_INVERSE_SWITCH
        direct = torch.log(torch.expm1(torch.where(small, value, torch.zeros_like(value))))
        asymptotic = value + torch.log1p(-torch.exp(-value))
        result = torch.where(small, direct, asymptotic)
        return torch.where(value > 0, result, torch.zeros_like(value))

    @property
    def n_neurons(self) -> list[int]:
        """每个个体占用的 real slot 数（padding 前），用于按 n 切片。"""
        return list(self._n_neurons)

    @property
    def active_counts(self) -> list[int]:
        """每个个体**活跃**神经元数（``M`` 为真者），可小于 ``n_neurons``。"""
        return [int(mask.sum()) for mask in self.neuron_mask]

    @property
    def effective_weights(self) -> torch.Tensor:
        """有效权重（§3）。

        - 约束路径（默认）：``W = A ⊙ (sign(W⁰) ⊙ softplus(Θ))``，符号由突触前类型固定；
        - 非约束路径（``sign_constrained=False``，消融对照）：``W = A ⊙ Θ``，参数即权重，
          符号自由可翻转。支撑/非活跃屏蔽两路径相同。
        """
        if self.sign_constrained:
            return self.support_sign0 * F.softplus(self.theta)
        return self.support_f32 * self.theta

    @property
    def delta_weights(self) -> torch.Tensor:
        """``ΔW = W − W⁰``（当代表型；不遗传，§6/§7）。"""
        return self.effective_weights - self.weights0

    def reset(self) -> None:
        self.h = torch.zeros_like(self.h)

    def _drive(self) -> torch.Tensor:
        weights = self.effective_weights
        return (weights @ self.h.unsqueeze(-1)).squeeze(-1)

    def step(self, observations: np.ndarray | torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """推进一步：``h^{t+1}`` 由 §3 动力学给出，返回 ``(ω, v)``。

        ``observations`` 形状 ``(batch, sensory_dim)``（也接受单样本 ``(sensory_dim,)``，
        自动升一维）；§2，``[0,1]`` ``float32``；``H_t`` 取第 11 维 hunger。
        """
        if isinstance(observations, torch.Tensor):
            x = observations.to(dtype=torch.float32, device=self.device)
        else:
            x = to_float32_tensor(observations, device=self.device)
        if x.dim() == 1:
            x = x.unsqueeze(0)
        if x.dim() != 2:
            raise ValueError(f"observation 必须为 1-D 或 2-D，实际 {x.dim()}-D")
        if x.shape[0] != self.h.shape[0] or x.shape[-1] != self.config.sensory_dim:
            expected = (self.h.shape[0], self.config.sensory_dim)
            raise ValueError(f"observation 形状应为 {expected}，实际 {tuple(x.shape)}")
        hunger = x[:, 11].unsqueeze(-1)
        types = self.cell_type
        drive = self._drive()
        sensory = torch.bmm(self.U[types], x.unsqueeze(-1)).squeeze(-1)
        pre = drive + sensory + self.m[types] * hunger + self.b[types]
        h_next = (1.0 - 1.0 / self.tau) * self.h + (1.0 / self.tau) * self._phi(pre)
        self.h = h_next * self.neuron_mask.to(torch.float32)
        return self.action()

    def action(self) -> tuple[torch.Tensor, torch.Tensor]:
        """§4：均值池化 ``y_ω = mean(h[M_L]) − mean(h[M_R])``、``y_v = mean(h[M_motor])``。"""
        h = self.h
        n_left = self.left_mask.sum(dim=-1).clamp_min(1).to(torch.float32)
        n_right = self.right_mask.sum(dim=-1).clamp_min(1).to(torch.float32)
        n_motor = self.motor_mask.sum(dim=-1).clamp_min(1).to(torch.float32)
        y_omega = (h * self.left_mask).sum(dim=-1) / n_left - (h * self.right_mask).sum(
            dim=-1
        ) / n_right
        y_v = (h * self.motor_mask).sum(dim=-1) / n_motor
        return torch.tanh(y_omega), torch.sigmoid(y_v)

    def viability(self) -> list[tuple[bool, str]]:
        """§3 末段：用本模块的 ``b_{type_i}`` 对 RGCD §7 判据复核，作为最终判定。"""
        results: list[tuple[bool, str]] = []
        for b, n in enumerate(self._n_neurons):
            viable, reason = viability_check(
                self.adjacency[b, :n, :n],
                self.cell_type[b, :n],
                self.positions[b, :n],
                self.tau[b, :n],
                self.weights0[b, :n, :n],
                self.neuron_mask[b, :n],
                domains=self.config.domains,
                zero_input_steps=self.config.zero_input_steps,
                saturation_ratio_max=self.config.saturation_ratio_max,
                saturation_eps=self.config.saturation_eps,
                activation=self.config.activation,
                neuron_bias=self.b[self.cell_type[b, :n]],
            )
            results.append((viable, reason))
        return results


__all__ = [
    "DOMAIN_ORDER",
    "DanioNet",
    "NetworkPriors",
    "build_priors",
    "motor_sides",
]
