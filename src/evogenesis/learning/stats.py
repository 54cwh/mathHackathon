"""BC 损失权重（`learning/行为克隆学习.md` §3 定稿）。

对训练集动作按**目标尺度归一化**取权重：

    λ_i = 1 / max(σ_i, 0.05·R_i)²,   i ∈ {ω, v}
    再整体缩放使 λ_ω + λ_v = 2

其中 ``σ_i`` 为训练集第 ``i`` 维动作的**总体标准差（``ddof=0``，§3 定稿）**；
``R_ω=2``、``R_v=1`` 为两维取值跨度（``ω∈[-1,1]``、``v∈[0,1]``）；下限比例
``0.05`` 由 ``learning.loss_variance_floor_ratio`` 承载。缩放后权重无量纲、非自由超参，
计算一次后全实验冻结（§3）。

退化情形：训练集无样本（``N=0``，统计量未取到）时按 §3 使用 **config 预注册回退值**
``learning.loss_weight_fallback_omega`` / ``_v``；两维 ``σ=0`` 时下限 ``0.05·R_i`` 生效，
其结果恰为同一组回退值（``λ_ω:λ_v = 1:4``，缩放至和为 2 即 0.4/1.6）。本模块不发明数值：
回退值与下限比例均由调用方从 ``learning`` 配置传入。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: `learning §3` 定稿：两维动作取值跨度 ``R_ω=2``、``R_v=1``
DEFAULT_ACTION_RANGES: tuple[float, float] = (2.0, 1.0)


@dataclass(frozen=True)
class LossWeights:
    """两维加权 MSE 的冻结权重及其来源统计量。"""

    omega: float
    v: float
    sigma_omega: float
    sigma_v: float
    used_fallback: bool


def population_std(expert_actions: np.ndarray) -> np.ndarray:
    """训练集动作逐维**总体**标准差（``ddof=0``，`learning §3`）；返回 ``(2,)`` float32。"""
    actions = np.asarray(expert_actions, dtype=np.float32)
    if actions.ndim != 2 or actions.shape[1] != 2:
        raise ValueError(f"expert_actions 形状应为 (N, 2)，实际 {tuple(actions.shape)}")
    return actions.std(axis=0, ddof=0).astype(np.float32)


def compute_loss_weights(
    expert_actions: np.ndarray,
    *,
    floor_ratio: float,
    fallback_omega: float,
    fallback_v: float,
    ranges: tuple[float, float] = DEFAULT_ACTION_RANGES,
) -> LossWeights:
    """按 §3 由训练集动作统计量计算 ``(λ_ω, λ_v)``，缩放至 ``λ_ω + λ_v = 2``。

    参数（均来自 config / 文档，不由本模块选定）：``floor_ratio`` =
    ``learning.loss_variance_floor_ratio``；``fallback_omega`` / ``fallback_v`` =
    ``learning.loss_weight_fallback_omega`` / ``_v``；``ranges`` = ``(R_ω, R_v)``。

    训练集为空（``N=0``）时无法取统计量，返回预注册回退值并置 ``used_fallback=True``。
    """
    if not np.isfinite(floor_ratio) or floor_ratio <= 0.0:
        raise ValueError(f"floor_ratio 必须为正有限值，实际 {floor_ratio!r}")
    if not all(np.isfinite(value) and value > 0.0 for value in ranges):
        raise ValueError(f"ranges 必须为正有限值，实际 {ranges!r}")
    if not all(np.isfinite(value) and value > 0.0 for value in (fallback_omega, fallback_v)):
        raise ValueError(f"回退权重必须为正有限值，实际 ({fallback_omega!r}, {fallback_v!r})")

    actions = np.asarray(expert_actions, dtype=np.float32)
    if actions.ndim != 2 or actions.shape[1] != 2:
        raise ValueError(f"expert_actions 形状应为 (N, 2)，实际 {tuple(actions.shape)}")

    if actions.shape[0] == 0:
        return LossWeights(
            omega=float(fallback_omega),
            v=float(fallback_v),
            sigma_omega=float("nan"),
            sigma_v=float("nan"),
            used_fallback=True,
        )

    sigma = population_std(actions)
    floor = (floor_ratio * np.asarray(ranges, dtype=np.float32)).astype(np.float32)
    raw = 1.0 / np.maximum(sigma, floor) ** 2
    scaled = raw * (2.0 / raw.sum())
    return LossWeights(
        omega=float(scaled[0]),
        v=float(scaled[1]),
        sigma_omega=float(sigma[0]),
        sigma_v=float(sigma[1]),
        used_fallback=False,
    )


__all__ = [
    "DEFAULT_ACTION_RANGES",
    "LossWeights",
    "compute_loss_weights",
    "population_std",
]
