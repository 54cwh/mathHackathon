"""唯一正式离散 GRN（RGCD §4，v1.8 已定稿）。

    g^{r+1} = (1 - rho) g^r + rho * sigmoid(W_g g^r + B q(G) + P p_i + b)

形状（§4）：``g_i ∈ R^8``、``q(G) ∈ R^8``、``p_i ∈ R^2`` 原样输入（不 embedding）；
``W_g ∈ R^{8×8}``、``B ∈ R^{8×8}``、``P ∈ R^{8×2}``、``b ∈ R^8``。默认 steps=12、rho=0.35、sigmoid。

随机数纪律：本模块不派生随机数；参数由调用方（``rgcd.initialize_parameters``）用
``SeedManager(master).torch_generator("development_params", 0)`` 初始化（`core §3`；
Θ_D 每 seed 一套，非逐个体）。
dtype 统一 ``float32``（`core §7`）。
"""

from __future__ import annotations

import torch


def spectral_radius(matrix: torch.Tensor) -> float:
    """矩阵谱半径 ``max |lambda_i|``（RGCD §4 稳定性启发式、§7 判据 (iv)）。"""
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"spectral_radius 需要方阵，实际形状 {tuple(matrix.shape)}")
    if not bool(torch.isfinite(matrix).all()):
        raise ValueError("spectral_radius 不接受含 NaN/Inf 的矩阵（LAPACK 会崩溃）")
    eigenvalues = torch.linalg.eigvals(matrix.to(torch.float32))
    return float(eigenvalues.abs().max().item())


def discrete_grn(
    g0: torch.Tensor,
    q: torch.Tensor,
    pos: torch.Tensor,
    Wg: torch.Tensor,
    B: torch.Tensor,
    P: torch.Tensor,
    bias: torch.Tensor,
    rho: float = 0.35,
    steps: int = 12,
    trace: list[dict] | None = None,
) -> torch.Tensor:
    """按 §4 字面迭代 ``steps`` 步并返回 ``g``（``(..., N, dim)``）。

    ``g0``/``pos`` 共享神经元维，``q`` 为 ``(..., dim)``。支持单个体 ``(N, dim)``
    与 ``(B, N, dim)`` 两种前导批量形状（本任务只用单个体）。
    """
    if g0.shape[-1] != Wg.shape[0]:
        raise ValueError(f"g0 末维 {g0.shape[-1]} 与 Wg 维数 {Wg.shape[0]} 不一致")
    if q.shape[-1] != B.shape[1]:
        raise ValueError(f"q 末维 {q.shape[-1]} 与 B 输入维 {B.shape[1]} 不一致")
    if pos.shape[-1] != P.shape[1]:
        raise ValueError(f"pos 末维 {pos.shape[-1]} 与 P 输入维 {P.shape[1]} 不一致")
    if steps < 0:
        raise ValueError("steps 必须非负")

    g = g0.to(torch.float32)
    Wg = Wg.to(torch.float32)
    B = B.to(torch.float32)
    P = P.to(torch.float32)
    bias = bias.to(torch.float32)
    if trace is not None:
        trace.append(_grn_sample(g, step=0, stage="grn"))
    for step in range(steps):
        recurrent = torch.einsum("...nd,de->...ne", g, Wg)
        genome_term = torch.einsum("...d,ed->...e", q, B).unsqueeze(-2)
        pos_term = torch.einsum("...np,ep->...ne", pos, P)
        target = torch.sigmoid(recurrent + genome_term + pos_term + bias)
        g = (1.0 - rho) * g + rho * target
        if trace is not None:
            trace.append(_grn_sample(g, step=step + 1, stage="grn"))
    return g


def _grn_sample(g: torch.Tensor, *, step: int, stage: str) -> dict:
    """逐步状态摘要（**只读**：不抽随机数，故开关 trace 不改变任何数值）。

    统一键集合，便于前端把三个阶段画成同一条时间线：
    ``stage`` / ``step`` / ``n_neurons`` / ``n_divisions`` / ``n_edges`` /
    ``mean_abs`` / ``max_abs``；早期阶段没有的量记 ``None``（缺失 ≠ 0）。
    """
    with torch.no_grad():
        return {
            "stage": stage,
            "step": int(step),
            "n_neurons": int(g.shape[-2]),
            "n_divisions": None,
            "n_edges": None,
            "mean_abs": float(g.abs().mean().item()),
            "max_abs": float(g.abs().max().item()),
        }
