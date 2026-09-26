"""Motif 目录：跨个体 / 跨代固定的 8×6 bp 目录（genome §6）。

目录由 **`motif_catalog` 命名空间**（core §3）在 master seed 下一次性抽样后固定：
每个位置在 `alphabet` 上均匀 i.i.d.。目录供 `q(G)` 的调用方持有并复用；
RGCD 只消费派生量 `q(G)`，不直接读目录。
"""

from __future__ import annotations

import numpy as np

from evogenesis.core.seed import SeedManager
from evogenesis.genome.config import DEFAULT_LAYOUT, GenomeLayout


def generate_motif_catalog(
    layout: GenomeLayout = DEFAULT_LAYOUT, *, rng: np.random.Generator
) -> tuple[str, ...]:
    """从 `alphabet` 上按位置均匀 i.i.d. 抽 `motif_count` 条长度 `motif_length` 的 motif。"""
    if layout.motif_count < 1 or layout.motif_length < 1:
        raise ValueError("motif_count 与 motif_length 必须 ≥ 1")
    alphabet = layout.alphabet
    draws = rng.integers(0, len(alphabet), size=(layout.motif_count, layout.motif_length))
    return tuple("".join(alphabet[int(code)] for code in row) for row in draws)


def motif_catalog_for(master_seed: int, layout: GenomeLayout = DEFAULT_LAYOUT) -> tuple[str, ...]:
    """给定实验 master seed，取该 run 固定的 motif 目录（`motif_catalog` 命名空间）。"""
    return generate_motif_catalog(layout, rng=SeedManager(master_seed).rng("motif_catalog"))
