"""繁殖：gamete → fertilization，并铸造子代 ``genome_id``。

meiosis / fertilization 的算子 owner 是 ``genome``（``genome/生物学与进化遗传学基础.md``
§4/§5），本模块**只复用** ``genome.make_gamete`` / ``genome.fertilize``，不另写一版：
- 配子的 crossover / mutation 随机源沿用 ``crossover`` / ``mutation`` 命名空间；
- mutation 率 ``μ`` 与每对染色体交叉概率取自 ``EvolutionConfig``（``evolution §8``）。

子代 ID 由 ``core/ids.py::mint_id`` 铸造（``evolution §5``，格式 owner = ``core §3.1``）。
配子级随机源序号 ``t`` 由子代 ``genome_id`` 的代内稳定序号 ``index`` 确定性解析（``core §3``）。
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from evogenesis.core.ids import mint_id, parse_id
from evogenesis.genome.config import DEFAULT_LAYOUT, GenomeLayout
from evogenesis.genome.genome import DiploidGenome, fertilize, make_gamete

_GENOME_ROLE_PREFIX = "genome"


def gamete_seed_index(genome_id: str, *, population_size: int) -> int:
    """由子代 ``genome_id`` 求配子级随机源序号 ``t = generation * N + index``（``core §3``）。

    ``genome_id`` 形如 ``<experiment_id>:g<generation>:genome<index:04d>``，``N`` 为每代
    出生数 ``population_size``。该式使 ``t`` **全局唯一**（跨代同 ``index`` 不复用随机流）。
    纯函数、不使用调用顺序。
    """
    if not genome_id:
        raise ValueError("genome_id 不能为空")
    if population_size <= 0:
        raise ValueError("population_size 必须为正")
    try:
        _, generation, role, index = parse_id(genome_id)
    except ValueError as exc:  # core §3.1 的唯一解析器
        raise ValueError(f"genome_id 格式非法：{genome_id!r}") from exc
    if role != _GENOME_ROLE_PREFIX:
        raise ValueError(f"genome_id 的 role 必须为 {_GENOME_ROLE_PREFIX!r}，实际 {role!r}")
    return generation * population_size + index


def offspring_genome(
    parent_a: DiploidGenome,
    parent_b: DiploidGenome,
    *,
    mu: float,
    crossover_probability: float,
    crossover_rng: np.random.Generator,
    mutation_rng: np.random.Generator,
    layout: GenomeLayout = DEFAULT_LAYOUT,
) -> DiploidGenome:
    """两个亲本各产一枚 gamete 后受精，得到子代基因组（尚无 ``genome_id``）。"""
    gamete_a = make_gamete(
        parent_a, mu, crossover_probability, crossover_rng, mutation_rng, layout=layout
    )
    gamete_b = make_gamete(
        parent_b, mu, crossover_probability, crossover_rng, mutation_rng, layout=layout
    )
    return fertilize(gamete_a, gamete_b, layout=layout)


def with_genome_id(
    genome: DiploidGenome, *, experiment_id: str, generation: int, index: int
) -> DiploidGenome:
    """给子代基因组写入稳定 ``genome_id``（``core §3.1``）；``index`` 为代内稳定序号。"""
    genome_id = mint_id(experiment_id, "genome", generation, index)
    return replace(genome, genome_id=genome_id)
