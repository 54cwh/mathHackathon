"""发育阶段：domain 放置（RGCD §3）、分裂（§5）、cell identity（§6）。

随机数纪律：所有随机过程接收 ``torch.Generator``（由 ``SeedManager(master).torch_generator``
派生，命名空间 ``development=2``，`core §3`）；不使用 Python ``random`` / ``np.random.seed`` /
裸 ``torch.manual_seed``。dtype 统一 ``float32``（`core §7`）。
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

from evogenesis.development.config import DOMAIN_ORDER


@dataclass
class DevelopmentState:
    """发育中间态：末态 GRN、位置、谱系 domain 索引、active mask。"""

    grn: torch.Tensor
    positions: torch.Tensor
    domain_index: torch.Tensor
    active_mask: torch.Tensor


def block_origins(
    domains: tuple[str, ...] = DOMAIN_ORDER, *, device: torch.device | str | None = None
) -> torch.Tensor:
    """§3 的 ``2 行 × 3 列`` block 原点 ``origin_domain``（形状 ``(D, 2)``）。

    单位方域划为 3 列 × 2 行（block 尺寸 ``1/3 × 1/2``，x 步长 ``1/3``、y 步长 ``1/2``）；
    domain 按 ``[S,P,T,M,I,O]`` 顺序**行优先**填入（RGCD §3）。
    """
    n = len(domains)
    if n != 6:
        raise ValueError(f"§3 的 3 列 × 2 行 block 要求恰 6 个 domain，实际 {n}")
    origins = torch.empty((n, 2), dtype=torch.float32, device=device)
    for index in range(n):
        col = index % 3
        row = index // 3
        origins[index, 0] = col / 3.0
        origins[index, 1] = row / 2.0
    return origins


def place_precursors(
    domains: tuple[str, ...],
    precursors_per_domain: int,
    *,
    generator: torch.Generator,
) -> tuple[torch.Tensor, torch.Tensor]:
    """§3 domain-blocked 均匀随机放置，每域 ``precursors_per_domain`` 个。

    ``p_i = origin_domain + (u1/3, u2/2)``、``u ~ U[0,1]^2``；返回
    ``positions (N0, 2) float32`` 与 ``domain_index (N0,) int64``（前体按 domain 分组）。
    """
    if precursors_per_domain < 1:
        raise ValueError("precursors_per_domain 必须 ≥ 1")
    device = generator.device
    origins = block_origins(domains, device=device)
    block_size = torch.tensor([1.0 / 3.0, 1.0 / 2.0], dtype=torch.float32, device=device)
    positions: list[torch.Tensor] = []
    domain_indices: list[int] = []
    for domain in range(len(domains)):
        u = torch.rand((precursors_per_domain, 2), generator=generator, device=device)
        positions.append(origins[domain] + u * block_size)
        domain_indices.extend([domain] * precursors_per_domain)
    return torch.cat(positions, dim=0), torch.tensor(
        domain_indices, dtype=torch.int64, device=device
    )


def division_probability(
    grn: torch.Tensor, w_div: torch.Tensor, b_div: torch.Tensor
) -> torch.Tensor:
    """§5 分裂概率 ``sigma(w_d^T g + b_d)``（``(N,)``）。"""
    return torch.sigmoid(grn @ w_div + b_div)


def cell_identity(grn: torch.Tensor, U: torch.Tensor, domain_bias: torch.Tensor) -> torch.Tensor:
    """§6 ``z = softmax(U g + c_domain)``（``(N, n_domains)``）。"""
    return torch.softmax(grn @ U.T + domain_bias, dim=-1)


def proliferate(
    grn: torch.Tensor,
    positions: torch.Tensor,
    domain_index: torch.Tensor,
    w_div: torch.Tensor,
    b_div: torch.Tensor,
    *,
    split_noise: float,
    gene_noise: float,
    max_divisions_per_precursor: int,
    generator: torch.Generator,
) -> DevelopmentState:
    """§5 增殖：每个 precursor 至多分裂一次，子代 ``p+ε_p``（裁 ``[0,1]^2``）、``g+ε_g``。

    返回原细胞在前、子代在后的拼接态；``N = N0 + k``，``k`` 为分裂前体数。
    """
    if max_divisions_per_precursor != 1:
        raise ValueError("§5 冻结为每 precursor 至多分裂一次（max_divisions_per_precursor=1）")
    divide_prob = division_probability(grn, w_div, b_div)
    divide = torch.rand(grn.shape[0], generator=generator, device=grn.device) < divide_prob
    parent = torch.nonzero(divide, as_tuple=False).squeeze(-1)
    k = int(parent.numel())
    if k > 0:
        eps_p = (
            torch.randn((k, positions.shape[1]), generator=generator, device=grn.device)
            * split_noise
        )
        eps_g = torch.randn((k, grn.shape[1]), generator=generator, device=grn.device) * gene_noise
        daughter_pos = torch.clamp(positions[parent] + eps_p, 0.0, 1.0)
        daughter_grn = grn[parent] + eps_g
        daughter_domain = domain_index[parent]
        positions = torch.cat([positions, daughter_pos], dim=0)
        grn = torch.cat([grn, daughter_grn], dim=0)
        domain_index = torch.cat([domain_index, daughter_domain], dim=0)
    active_mask = torch.ones(grn.shape[0], dtype=torch.bool)
    return DevelopmentState(
        grn=grn, positions=positions, domain_index=domain_index, active_mask=active_mask
    )
