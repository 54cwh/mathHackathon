"""世代推进：选择亲本 → 随机配对 → 生 ``N`` 子代（``evolution §5``）。

``advance_generation`` 串起本模块的选择（``selection.py``）、繁殖（``reproduction.py``）；
世代**不重叠**——产出的 ``N`` 个 offspring 即下一代，亲代不保留；non-viable 新生儿仍计入
下一代（``F=0``，不进亲本池）。当代 viable 个体 ``<2`` 时记 ``evolution.population_bottleneck``
事件并返回失败结果（不抛裸异常、不静默）。

``Individual`` / ``GenerationResult`` 是世代推进的边界对象（``evolution §5.1``）：当代个体携带
``genome_id / fish_id / genome / fitness / viable / failure_reason``；新生儿的 ``viable`` 与
``failure_reason`` 尚待评估（初值 ``False`` / ``None``，``F=0``），由编排层在发育/评估后更新。
随机源由 ``SeedManager`` 派生（``selection`` 取子代世代号；``crossover`` / ``mutation`` 每子代
独立，序号 ``t`` 由该子代 ``genome_id`` 解析，``core §3``）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from evogenesis.core.ids import mint_id
from evogenesis.core.seed import SeedManager
from evogenesis.evolution.config import EvolutionConfig
from evogenesis.evolution.reproduction import (
    gamete_seed_index,
    offspring_genome,
    with_genome_id,
)
from evogenesis.evolution.selection import binary_tournament, is_population_bottleneck, random_pairs
from evogenesis.genome.config import DEFAULT_LAYOUT, GenomeLayout
from evogenesis.genome.genome import DiploidGenome

#: 繁殖失败事件名（``evolution §5``；运行级事件，不入 arena 事件流）。
EVENT_POPULATION_BOTTLENECK = "evolution.population_bottleneck"


@dataclass(frozen=True)
class Individual:
    """世代推进的个体边界对象（``evolution §5.1``）。

    ``genome_id`` 为 ``core §3.1`` 稳定 ID，同时也是个体身份；``fish_id`` 为可选的本代 Arena
    身份（未评估 / 未进 Arena 时为 ``None``）。
    """

    genome_id: str
    genome: DiploidGenome
    fish_id: str | None = None
    fitness: float = 0.0
    viable: bool = False
    failure_reason: str | None = None


@dataclass(frozen=True)
class GenerationResult:
    """一次繁殖的结果（``evolution §5.1``）。

    失败时 ``success=False``、``event="evolution.population_bottleneck"``、无 offspring。
    ``selection_mode`` 为 ``"natural"``（锦标赛）或 ``"artificial"``（用户强制亲本，
    ``evolution §5``）。``forced_parent_ids`` 仅在人工选择时非空（去重、首次出现顺序）。
    """

    success: bool
    event: str | None
    offspring: tuple[Individual, ...]
    selected_parent_ids: tuple[str, ...]
    selection_mode: str = "natural"
    forced_parent_ids: tuple[str, ...] = ()


def _dedup(ids: Sequence[str]) -> tuple[str, ...]:
    """按首次出现顺序去重。"""
    seen: dict[str, None] = {}
    for gid in ids:
        seen.setdefault(gid, None)
    return tuple(seen)


def _forced_pairs(
    parents: Sequence[Individual],
    *,
    count: int,
    forced_pair: tuple[str, str] | None,
    forced_pairs: Sequence[tuple[str, str]] | None,
) -> tuple[np.ndarray, np.ndarray, tuple[str, ...]]:
    """解析强制亲本 → ``(pairs (count,2) intp, selected (2*count,) intp, forced_ids)``。

    亲本以稳定 ``genome_id`` 指定；不在当代、非 viable、对数不符即抛 ``ValueError``
    （``evolution §5`` 回退规则）。``id_a == id_b`` 允许（自交）。
    """
    index_of: dict[str, int] = {}
    for i, parent in enumerate(parents):
        if parent.genome_id in index_of:
            raise ValueError(f"parents 的 genome_id 必须互异，重复 {parent.genome_id!r}")
        index_of[parent.genome_id] = i

    if forced_pair is not None:
        specs: list[tuple[str, str]] = [forced_pair] * count
    else:
        if forced_pairs is None:
            raise ValueError("forced 解析错误：既无 forced_pair 也无 forced_pairs")
        if len(forced_pairs) != count:
            raise ValueError(
                f"forced_pairs 长度 {len(forced_pairs)} 须等于 population_size {count}"
            )
        specs = []
        for pair in forced_pairs:
            if len(pair) != 2:
                raise ValueError(f"forced_pairs 每项须为 (id_a, id_b)，实际 {pair!r}")
            specs.append((pair[0], pair[1]))

    pairs = np.empty((count, 2), dtype=np.intp)
    flat: list[str] = []
    for slot, (id_a, id_b) in enumerate(specs):
        for pid in (id_a, id_b):
            if pid not in index_of:
                raise ValueError(f"forced 亲本 {pid!r} 不在当代 parents")
            if not parents[index_of[pid]].viable:
                raise ValueError(f"forced 亲本 {pid!r} 非 viable，人工选择要求可育")
        pairs[slot, 0] = index_of[id_a]
        pairs[slot, 1] = index_of[id_b]
        flat.extend((id_a, id_b))
    return pairs, pairs.reshape(-1).astype(np.intp), _dedup(flat)


def advance_generation(
    parents: Sequence[Individual],
    *,
    experiment_id: str,
    generation: int,
    seed_manager: SeedManager,
    config: EvolutionConfig,
    layout: GenomeLayout = DEFAULT_LAYOUT,
    forced_pair: tuple[str, str] | None = None,
    forced_pairs: Sequence[tuple[str, str]] | None = None,
) -> GenerationResult:
    """由当代 ``parents`` 产出下一代 ``config.population_size`` 个个体。

    ``generation`` 为**子代**世代号（子代 ``genome_id`` 用之铸造）；``parents`` 中
    ``viable=False`` 者不进候选池。``F`` 由调用方先行用 ``fitness.composite_fitness`` 算好并写入。

    ``forced_pair`` / ``forced_pairs``（``evolution §5`` Artificial Selection，互斥）以稳定
    ``genome_id`` 强制指定亲本、替换锦标赛；非空时不消费 ``selection`` 命名空间、不判 bottleneck。
    """
    if forced_pair is not None and forced_pairs is not None:
        raise ValueError("forced_pair 与 forced_pairs 互斥，只给其一")
    count = int(config.population_size)
    if forced_pair is not None or forced_pairs is not None:
        pairs, selected, forced_ids = _forced_pairs(
            parents, count=count, forced_pair=forced_pair, forced_pairs=forced_pairs
        )
        selection_mode = "artificial"
    else:
        eligible = np.array([i for i, parent in enumerate(parents) if parent.viable], dtype=np.intp)
        if is_population_bottleneck(eligible):
            return GenerationResult(
                success=False,
                event=EVENT_POPULATION_BOTTLENECK,
                offspring=(),
                selected_parent_ids=(),
                selection_mode="natural",
                forced_parent_ids=(),
            )
        fitness = np.array([parent.fitness for parent in parents], dtype=np.float32)
        selection_rng = seed_manager.spawn_rng("selection", generation)
        selected = binary_tournament(
            fitness,
            eligible,
            tournament_size=config.tournament_size,
            rng=selection_rng,
            n_selections=2 * count,
        )
        pairs = random_pairs(selected, selection_rng)
        selection_mode = "natural"
        forced_ids = ()

    offspring: list[Individual] = []
    for index in range(count):
        parent_a = parents[int(pairs[index, 0])]
        parent_b = parents[int(pairs[index, 1])]
        child_genome_id = mint_id(experiment_id, "genome", generation, index)
        t = gamete_seed_index(child_genome_id, population_size=count)
        child_genome = offspring_genome(
            parent_a.genome,
            parent_b.genome,
            mu=config.mutation_rate_per_base_per_gamete,
            crossover_probability=config.crossover_probability_per_chromosome,
            crossover_rng=seed_manager.spawn_rng("crossover", t),
            mutation_rng=seed_manager.spawn_rng("mutation", t),
            layout=layout,
        )
        child_genome = with_genome_id(
            child_genome, experiment_id=experiment_id, generation=generation, index=index
        )
        offspring.append(Individual(genome_id=child_genome.genome_id, genome=child_genome))

    selected_parent_ids = tuple(parents[int(i)].genome_id for i in selected)
    return GenerationResult(
        success=True,
        event=None,
        offspring=tuple(offspring),
        selected_parent_ids=selected_parent_ids,
        selection_mode=selection_mode,
        forced_parent_ids=forced_ids,
    )
