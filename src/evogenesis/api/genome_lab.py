"""基因组实验室（进程内 store + 参考基因组）：支撑模型侧端点（`API接口.md` §2.3）。

**草案待确认（实现已先行、待确认 2026-09-26）** —— 以下为本实现自行选定的语义，须经用户
确认后方可作为契约：

- **参考种子** = `configs/demo_seed.yaml::master_seed`（`250927`）；参考基因组与 motif
  目录由它派生。
- **`genome_id`** 由 `core.ids.mint_id("lab", "genome", 0, index)` 铸造（`core §3.1`）。
- **单点位置约定（已定稿 2026-09-27）**：`position ∈ [0, 512)` 线性覆盖二倍体，顺序
  `pair0.maternal[0:128] → pair0.paternal[0:128] → pair1.maternal[0:128] → pair1.paternal[0:128]`
  （`MutationRequest` 不含 haplotype 字段，故位置须唯一编码；`story-mutations` 同坐标）。
- **随机源**：创建/变异/繁殖经 `SeedManager(参考种子)` 的独立命名空间 + 全局序号派生，
  不在本层自建全局随机源（`core §3`）。
- **纯内存、无持久化**（同会话语义）；进程重启即失。

本模块只做 store 与基因组原语；发育/繁殖算法归 `pipeline` / `genome` / `evolution`。
"""

from __future__ import annotations

import threading
from dataclasses import replace
from pathlib import Path

import numpy as np

from evogenesis.core.config import read_yaml
from evogenesis.core.ids import mint_id, parse_index
from evogenesis.core.seed import SeedManager
from evogenesis.genome.config import DEFAULT_LAYOUT, GenomeLayout
from evogenesis.genome.genome import ChromosomePair, DiploidGenome, genome_affinity, random_genome
from evogenesis.genome.motifs import motif_catalog_for

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEMO_SEED_PATH = _REPO_ROOT / "configs" / "demo_seed.yaml"
_EXPERIMENT_ID = "lab"
_ROLE = "genome"

_lock = threading.Lock()
_genomes: dict[str, DiploidGenome] = {}
_lineage: dict[str, str | None] = {}
_counter = 0


def reference_seed() -> int:
    """参考种子（`configs/demo_seed.yaml::master_seed`）。"""
    data = read_yaml(_DEMO_SEED_PATH) or {}
    seed = data.get("master_seed")
    if not isinstance(seed, int):
        raise ValueError(f"demo_seed.yaml 缺 master_seed：{_DEMO_SEED_PATH}")
    return seed


def motifs(layout: GenomeLayout = DEFAULT_LAYOUT) -> tuple[str, ...]:
    """参考 motif 目录（`motif_catalog` 命名空间，`genome §6`）。"""
    return motif_catalog_for(reference_seed(), layout)


def _next_index() -> int:
    global _counter
    _counter += 1
    return _counter


def _mint() -> tuple[str, int]:
    index = _next_index()
    return mint_id(_EXPERIMENT_ID, _ROLE, 0, index), index


def _store(genome: DiploidGenome, parent: str | None) -> DiploidGenome:
    with _lock:
        _genomes[genome.genome_id] = genome
        _lineage[genome.genome_id] = parent
    return genome


def create(seed: int | None = None) -> DiploidGenome:
    """创建一个随机基因组（均匀 i.i.d.，`genome §2`）并入 store。"""
    genome_id, index = _mint()
    manager = SeedManager(reference_seed() if seed is None else seed)
    genome = random_genome(
        DEFAULT_LAYOUT, rng=manager.spawn_rng("initial_population", index), genome_id=genome_id
    )
    return _store(genome, parent=None)


def get(genome_id: str) -> DiploidGenome | None:
    return _genomes.get(genome_id)


def lineage(genome_id: str) -> str | None:
    return _lineage.get(genome_id)


def affinity(genome: DiploidGenome) -> np.ndarray:
    """`q(G)`（`genome §6`）。"""
    return genome_affinity(genome, motifs())


def _split_position(genome: DiploidGenome, position: int) -> tuple[int, int, int]:
    per = genome.layout.bp_per_haplotype_chromosome
    span = 2 * per
    pair_idx, remainder = divmod(position, span)
    haplotype, offset = divmod(remainder, per)
    return pair_idx, haplotype, offset


def mutate_at_site(genome: DiploidGenome, position: int, base: str) -> DiploidGenome:
    """单点替换（Free Edit）→ 新基因组（新 `genome_id`，血缘 = 旧 id）并入 store。"""
    if base not in genome.layout.alphabet:
        raise ValueError(f"base 须在 {genome.layout.alphabet}，实际 {base!r}")
    total = genome.layout.diploid_bp
    if not 0 <= position < total:
        raise ValueError(f"position 须在 [0, {total})，实际 {position}")
    pair_idx, haplotype, offset = _split_position(genome, position)
    pair = genome.pairs[pair_idx]
    if haplotype == 0:
        new_maternal, new_paternal = _replace_base(pair.maternal, offset, base), pair.paternal
    else:
        new_maternal, new_paternal = pair.maternal, _replace_base(pair.paternal, offset, base)
    pairs = list(genome.pairs)
    pairs[pair_idx] = ChromosomePair(new_maternal, new_paternal, layout=genome.layout)
    new_id, _ = _mint()
    child = replace(genome, pairs=tuple(pairs), genome_id=new_id)
    return _store(child, parent=genome.genome_id)


def _replace_base(seq: str, offset: int, base: str) -> str:
    return seq[:offset] + base + seq[offset + 1 :]


def base_at(genome: DiploidGenome, position: int) -> str:
    """`position` 处的碱基（与 `mutate_at_site` 同一坐标约定）。"""
    total = genome.layout.diploid_bp
    if not 0 <= position < total:
        raise ValueError(f"position 须在 [0, {total})，实际 {position}")
    pair_idx, haplotype, offset = _split_position(genome, position)
    pair = genome.pairs[pair_idx]
    return (pair.maternal if haplotype == 0 else pair.paternal)[offset]


def breed(
    parent_a: DiploidGenome,
    parent_b: DiploidGenome,
    *,
    n_offspring: int,
    mu: float,
    crossover_probability: float,
) -> list[DiploidGenome]:
    """繁殖 `n_offspring` 个子代（`genome §4` / `evolution §3`）并入 store。"""
    from evogenesis.evolution.reproduction import offspring_genome

    manager = SeedManager(reference_seed())
    offspring: list[DiploidGenome] = []
    for _ in range(n_offspring):
        new_id, index = _mint()
        child = offspring_genome(
            parent_a,
            parent_b,
            mu=mu,
            crossover_probability=crossover_probability,
            crossover_rng=manager.spawn_rng("crossover", index),
            mutation_rng=manager.spawn_rng("mutation", index),
            layout=parent_a.layout,
        )
        offspring.append(_store(replace(child, genome_id=new_id), parent=parent_a.genome_id))
    return offspring


def stable_index(genome_id: str) -> int:
    """由 `genome_id` 取代内稳定序号（`core §3`，发育随机源 index）。"""
    return parse_index(genome_id)


__all__ = [
    "affinity",
    "base_at",
    "breed",
    "create",
    "get",
    "lineage",
    "motifs",
    "mutate_at_site",
    "reference_seed",
    "stable_index",
]
