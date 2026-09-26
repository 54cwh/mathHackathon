"""BC 训练报告（`learning/行为克隆学习.md` v1.4 §3/§4）。

汇总训练损失曲线、episode/step 级覆盖率、符号翻转率 ``flip_rate`` 与有效权重谱半径。
报告口径（§4 定稿）：``flip_rate`` 在**活跃支撑**（``A ∧ sign(W⁰)≠0``）上统计；谱半径
逐个体对 ``effective_weights`` 全矩阵取 ``max|λ|``；报告产物**不落盘**（位置占位，待
`experiment` run 布局接入）。
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

from evogenesis.connectome.danionet import DanioNet
from evogenesis.learning.stats import LossWeights
from evogenesis.learning.train import CoverageStats, TrainResult


@dataclass(frozen=True)
class TrainingReport:
    """一次训练的汇总报告（不落盘；`learning §4` 占位）。"""

    loss_history: tuple[float, ...]
    coverage_stats: CoverageStats
    loss_weights: LossWeights
    flip_rate: float
    spectral_radius: tuple[float, ...]
    delta_w_identity_max_error: float

    @property
    def n_updates(self) -> int:
        return len(self.loss_history)

    @property
    def epochs(self) -> float:
        return self.coverage_stats.epochs

    @property
    def coverage_episodes(self) -> float:
        return self.coverage_stats.coverage_episodes

    @property
    def coverage_steps(self) -> float:
        return self.coverage_stats.coverage_steps

    @property
    def visible_steps(self) -> int:
        return self.coverage_stats.visible_steps


def active_support(net: DanioNet) -> torch.Tensor:
    """符号约束的有效支撑：``A ∧ (sign(W⁰) ≠ 0)``（逐元素，形状同 ``W``，§4）。"""
    return net.support & (net.sign0 != 0)


def sign_flip_rate(net: DanioNet) -> float:
    """``flip_rate``：活跃支撑上 ``sign(W) ≠ sign(W⁰)`` 的占比（§4）。

    有符号约束时 ``W = sign(W⁰)·softplus(Θ)`` 且 ``softplus>0``，故恒为 0；无约束消融
    路径（`DanioNet §3` 接口，尚未实现）下会大于 0，用于对照。
    """
    mask = active_support(net)
    count = int(mask.sum())
    if count == 0:
        return 0.0
    with torch.no_grad():
        signs = torch.sign(net.effective_weights[mask])
        reference = net.sign0[mask]
        return float((signs != reference).to(torch.float32).mean())


def spectral_radius(net: DanioNet) -> tuple[float, ...]:
    """逐个体有效权重 ``W`` 的谱半径 ``max|λ(W)|``（§4）。

    口径（§4 定稿）：对 ``effective_weights[b]``（含 padding，形状 ``max_nodes×max_nodes``）
    直接取特征值最大模；padding/非活跃行列恒 0，只贡献 0 特征值。
    """
    radii: list[float] = []
    with torch.no_grad():
        for b in range(net.effective_weights.shape[0]):
            eigenvalues = torch.linalg.eigvals(net.effective_weights[b])
            radii.append(float(eigenvalues.abs().max()) if eigenvalues.numel() else 0.0)
    return tuple(radii)


def delta_w_identity_error(net: DanioNet) -> float:
    """``ΔW = W − W⁰`` 恒等式的最大绝对偏差（`DanioNet §3`）。"""
    with torch.no_grad():
        error = net.delta_weights - (net.effective_weights - net.weights0)
        return float(error.abs().max())


def build_report(net: DanioNet, result: TrainResult) -> TrainingReport:
    """由训练结果与更新后的网络汇总 :class:`TrainingReport`。"""
    return TrainingReport(
        loss_history=result.loss_history,
        coverage_stats=result.coverage_stats,
        loss_weights=result.loss_weights,
        flip_rate=sign_flip_rate(net),
        spectral_radius=spectral_radius(net),
        delta_w_identity_max_error=delta_w_identity_error(net),
    )


__all__ = [
    "TrainingReport",
    "active_support",
    "build_report",
    "delta_w_identity_error",
    "sign_flip_rate",
    "spectral_radius",
]
