"""BC 加权 MSE（`learning/行为克隆学习.md` v1.4 §3 定稿）。

    L = λ_ω · MSE(ω̂, ω*) + λ_v · MSE(v̂, v*)

`train.py` 的 BPTT 在每一步调用本模块得到该步加权 MSE，再按 §3 聚合：先对单条 episode
的逐步损失取**步均值**，再对 episode batch 取**均值**。``λ_ω, λ_v`` 为
:class:`~evogenesis.learning.stats.LossWeights` 冻结权重。损失只改尺度、不改网络输出映射
（`DanioNet §4` 的 ``tanh``/``σ`` 不变）。
"""

from __future__ import annotations

import torch

from evogenesis.learning.stats import LossWeights


def per_dim_mse(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """逐维 mini-batch 均方误差；``pred`` / ``target`` 形状 ``(B, 2)``，返回 ``(2,)``。"""
    if pred.shape != target.shape:
        raise ValueError(
            f"pred/target 形状须一致，实际 {tuple(pred.shape)} vs {tuple(target.shape)}"
        )
    if pred.ndim != 2 or pred.shape[1] != 2:
        raise ValueError(f"pred/target 形状应为 (B, 2)，实际 {tuple(pred.shape)}")
    return ((pred - target) ** 2).mean(dim=0)


def weighted_action_mse(
    pred: torch.Tensor, target: torch.Tensor, weights: LossWeights
) -> torch.Tensor:
    """§3 加权 MSE：``λ_ω·MSE(ω̂,ω*) + λ_v·MSE(v̂,v*)``。"""
    mse = per_dim_mse(pred, target)
    omega_w = torch.as_tensor(weights.omega, dtype=mse.dtype, device=mse.device)
    v_w = torch.as_tensor(weights.v, dtype=mse.dtype, device=mse.device)
    return omega_w * mse[0] + v_w * mse[1]


__all__ = ["per_dim_mse", "weighted_action_mse"]
