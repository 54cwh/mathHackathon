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
    grn: torch.Tensor,
    w_div: torch.Tensor,
    b_div: torch.Tensor,
    *,
    drive_gain: float = 1.0,
    locus_gain: float = 0.0,
    locus_channel: float | torch.Tensor | None = None,
) -> torch.Tensor:
    """§5 分裂概率（``(N,)``）。默认（``drive_gain=1.0``、``locus_gain=0.0``）与
    ``sigma(w_d^T g + b_d)`` **逐位一致**。两个增益即 RGCD §5 的 ``alpha``/``beta``：

    * ``drive_gain``(α)：作用在**逐个体中心化**的 GRN 驱动上。中心化等价于按 §8
      ``solve_bias_for_density`` 的方式反解 ``b_d``，把 sigmoid 钉在灵敏段（§5 自述「分裂
      概率约 0.5」）；**若不中心化，叠加基因组通道后整体饱和、区分力归零**（实测）。
    * ``locus_gain``(β)：作用在**基因组通道** ``locus_channel`` 上。这是把「基因型→增殖」从
      **随机方向投影**（``w_d``）改为**确定性通道**的关键：消除每-seed 的方向抽签。
      **通道值须由调用方预先中心化**（见 `rgcd.develop`：取 A 位点亲和减本个体全 motif
      均值）——`q_A ∈ [0,1]` 原样相加会给全体前体一个正偏置、令 sigmoid 饱和、区分力归零。
    """
    drive = grn @ w_div + b_div
    if drive_gain != 1.0:
        drive = drive_gain * (drive - drive.mean())
    if locus_channel is not None and locus_gain != 0.0:
        drive = drive + locus_gain * torch.as_tensor(
            locus_channel, dtype=drive.dtype, device=drive.device
        )
    return torch.sigmoid(drive)


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
    trace: list[dict] | None = None,
    drive_gain: float = 1.0,
    locus_gain: float = 0.0,
    locus_channel: float | torch.Tensor | None = None,
) -> DevelopmentState:
    """§5 增殖：每个 precursor 至多分裂一次，子代 ``p+ε_p``（裁 ``[0,1]^2``）、``g+ε_g``。

    返回原细胞在前、子代在后的拼接态；``N = N0 + k``，``k`` 为分裂前体数。
    """
    if max_divisions_per_precursor != 1:
        raise ValueError("§5 冻结为每 precursor 至多分裂一次（max_divisions_per_precursor=1）")
    divide_prob = division_probability(
        grn, w_div, b_div,
        drive_gain=drive_gain, locus_gain=locus_gain, locus_channel=locus_channel,
    )
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
    if trace is not None:
        with torch.no_grad():
            trace.append(
                {
                    "stage": "proliferate",
                    "step": 1,
                    "n_neurons": int(grn.shape[0]),
                    "n_divisions": int(k),
                    "n_edges": None,
                    "mean_abs": float(grn.abs().mean().item()),
                    "max_abs": float(grn.abs().max().item()),
                    "positions": [[float(v) for v in row] for row in positions.tolist()],
                    "cell_type": None,  # fate 在连接组阶段才确定
                    "edges": None,  # 邻接表仅在连接组阶段存在（统一键集合）
                    # 逐神经元表达强度 `expr[i] = mean_d |g_id|`（§4）
                    "expr": [float(v) for v in grn.abs().mean(dim=-1).tolist()],
                    "fate_conf": None,  # §6：fate 尚未落定
                    "probs": None,  # §8：连接概率场尚未计算
                }
            )
    return DevelopmentState(
        grn=grn, positions=positions, domain_index=domain_index, active_mask=active_mask
    )
