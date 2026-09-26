"""DanioNet → Arena：发育 → 过滤 viable → 单 episode 驱动。

owner：`pipeline/模型链装配.md` §4。上游：`development`（发育/viability）、`connectome`
（DanioNet）、`arena`（世界与 `step`）。本模块只编排。

**范围与约定**：只把通过 `RGCD §7` viability 的个体放进 Arena（其保证 motor 左右池非空
⇒ DanioNet 可构造），`population.n_fish` 按实际数覆盖。Arena 实体 id 直接用 `core §3.1`
的稳定 `fish_id`（`ChainIndividual.fish_id`，本模块传入 `DanioArena(fish_ids=...)`）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np
import torch

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.env import DanioArena, Event
from evogenesis.connectome.danionet import DanioNet
from evogenesis.core.seed import SeedManager
from evogenesis.development.config import DEFAULT_CONFIG as DEFAULT_RGCD_CONFIG
from evogenesis.development.config import RGCDConfig
from evogenesis.development.rgcd import ConnectomePhenotype
from evogenesis.pipeline.model_chain import (
    ChainIndividual,
    ModelChainConfig,
    danionet_of,
    motif_catalog,
    phenotypes_of,
)


@dataclass(frozen=True)
class ArenaEpisodeResult:
    """一次 Arena episode 的结果（供实验层落盘/出指标）。"""

    evaluated_individuals: int
    steps: int
    per_fish: dict[str, dict]
    events: tuple[Event, ...]


@dataclass(frozen=True)
class PopulationEvaluation:
    """一整代的评估结果（`experiment/代循环编排.md` §2）。

    `phenotypes` 与输入个体**同序等长**（含 non-viable）；`episode` 只覆盖 `viable_indices`
    选中的个体（无 viable 时为 `None`）。
    """

    phenotypes: tuple[ConnectomePhenotype, ...]
    episode: ArenaEpisodeResult | None
    viable_indices: tuple[int, ...]


def arena_seeds_for(master_seed: int, index: int = 0) -> tuple[int, int]:
    """Arena 的两个整数子种子（`core §3`）：``(arena_spawn, arena_dynamics)``。

    - `arena_spawn`：出生/再生（`reset()` 的布局与 `_free_spot`）；
    - `arena_dynamics`：逐步动力学（猎物游走）。

    Arena 只接受整数种子（`core §3` 例外条款），由编排层派生后传入；**不得**把
    `master_seed` 根部直接交给 Arena（会与 `development` / `network_init` 等命名空间同根）。
    `index` 为 `core §3` 的实体序号 `t`：单次评估取 0；代循环内取**本代世代号**
    （`experiment/代循环编排.md` §4），使各代随机流独立。
    """
    manager = SeedManager(master_seed)
    return manager.seed("arena_spawn", index), manager.seed("arena_dynamics", index)


def viable_pairs(
    individuals: Sequence[ChainIndividual],
    motifs: Sequence[str],
    *,
    master_seed: int,
    config: RGCDConfig = DEFAULT_RGCD_CONFIG,
    device: str = "cpu",
) -> list[tuple[ChainIndividual, ConnectomePhenotype]]:
    """发育并保留 `viable` 个体（`RGCD §7`）；其余不入 Arena。"""
    phenotypes = phenotypes_of(
        individuals, motifs, master_seed=master_seed, config=config, device=device
    )
    return [
        (individual, phenotype)
        for individual, phenotype in zip(individuals, phenotypes, strict=True)
        if phenotype.viable
    ]


def evaluate_population(
    individuals: Sequence[ChainIndividual],
    *,
    master_seed: int,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    steps: int | None = None,
    generation: int = 0,
    device: str = "cpu",
) -> PopulationEvaluation:
    """评估一整代：全体发育（记 viability），仅 viable 进 DanioNet + Arena。

    `phenotypes` 与 `individuals` 同序等长，供编排层按 `viable_indices` 折算 `F`
    （`experiment/代循环编排.md` §3）。无 viable 个体时 `episode=None`（不抛异常）。
    """
    motifs = motif_catalog(master_seed, chain.layout)
    phenotypes = phenotypes_of(
        individuals, motifs, master_seed=master_seed, config=chain.rgcd, device=device
    )
    viable_indices = tuple(i for i, p in enumerate(phenotypes) if p.viable)
    if not viable_indices:
        return PopulationEvaluation(tuple(phenotypes), None, ())
    pairs = [(individuals[i], phenotypes[i]) for i in viable_indices]
    episode = _drive_arena(
        pairs,
        master_seed=master_seed,
        chain=chain,
        arena_config=arena_config,
        steps=steps,
        generation=generation,
        device=device,
    )
    return PopulationEvaluation(tuple(phenotypes), episode, viable_indices)


def drive_arena_with_net(
    individuals: Sequence[ChainIndividual],
    net: DanioNet,
    *,
    master_seed: int,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    steps: int | None = None,
    generation: int = 0,
) -> ArenaEpisodeResult:
    """用**给定的** `DanioNet` 驱动 Arena 跑一局（不重新发育/构造网络）。

    供生命周期学习（`experiment/learning_run.py`）在**同一批 arena 子种子**下复用同一
    网络对象做训练前后对照：``individuals`` 与 ``net`` 的 batch 必须同序等长。
    """
    if len(individuals) != len(net.n_neurons):
        raise ValueError(
            f"individuals 数 {len(individuals)} 与 net batch {len(net.n_neurons)} 不一致"
        )
    fish_ids = [individual.fish_id for individual in individuals]
    genome_ids = [individual.genome_id for individual in individuals]
    n_eval = len(individuals)

    config = replace(arena_config, population=replace(arena_config.population, n_fish=n_eval))
    spawn_seed, dynamics_seed = arena_seeds_for(master_seed, generation)
    arena = DanioArena(
        config,
        spawn_seed=spawn_seed,
        dynamics_seed=dynamics_seed,
        fish_ids=fish_ids,
        genome_ids=genome_ids,
        generation=generation,
    )
    arena.reset()

    total = config.world.episode_steps if steps is None else steps
    for _ in range(total):
        observation = np.zeros((n_eval, chain.network.sensory_dim), dtype=np.float32)
        alive: list[tuple[int, str]] = []
        for slot, fish_id in enumerate(fish_ids):
            if arena.fish[fish_id].alive:
                observation[slot] = arena.observe(fish_id)
                alive.append((slot, fish_id))
        with torch.no_grad():
            omega, v = net.step(observation)
        actions = {fish_id: (float(omega[slot]), float(v[slot])) for slot, fish_id in alive}
        if arena.step(actions).done:
            break

    return ArenaEpisodeResult(
        evaluated_individuals=n_eval,
        steps=arena.step_idx,
        per_fish=arena.per_fish_log(),
        events=tuple(arena.events),
    )


def _drive_arena(
    pairs: Sequence[tuple[ChainIndividual, ConnectomePhenotype]],
    *,
    master_seed: int,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    steps: int | None,
    generation: int,
    device: str,
) -> ArenaEpisodeResult:
    """用 DanioNet 驱动 Arena 跑一局（`pairs` 非空，全为 viable 个体）。"""
    phenotypes = [phenotype for _, phenotype in pairs]
    individuals = [individual for individual, _ in pairs]
    net = danionet_of(phenotypes, master_seed=master_seed, config=chain.network, device=device)
    return drive_arena_with_net(
        individuals,
        net,
        master_seed=master_seed,
        chain=chain,
        arena_config=arena_config,
        steps=steps,
        generation=generation,
    )


def run_arena_episode(
    individuals: Sequence[ChainIndividual],
    *,
    master_seed: int,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    steps: int | None = None,
    generation: int = 0,
    device: str = "cpu",
) -> ArenaEpisodeResult:
    """用 DanioNet 驱动 Arena 跑一局（`steps=None` 取 `world.episode_steps`）。

    便捷封装：无 viable 个体时抛 `ValueError`（供单代入口显式失败）；需要「无 viable 也
    返回结果」的代循环请用 `evaluate_population`。
    """
    evaluation = evaluate_population(
        individuals,
        master_seed=master_seed,
        chain=chain,
        arena_config=arena_config,
        steps=steps,
        generation=generation,
        device=device,
    )
    if evaluation.episode is None:
        raise ValueError("没有 viable 个体可进 Arena（RGCD §7）")
    return evaluation.episode
