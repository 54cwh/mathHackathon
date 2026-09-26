"""DanioNet → Arena：发育 → 过滤 viable → 单 episode 驱动。

owner：`pipeline/模型链装配.md` §4。上游：`development`（发育/viability）、`connectome`
（DanioNet）、`arena`（世界与 `step`）。本模块只编排。

**范围与约定（草案待确认：Arena 个体集）**：只把通过 `RGCD §7` viability 的个体放进 Arena
（其保证 motor 左右池非空 ⇒ DanioNet 可构造），`population.n_fish` 按实际数覆盖。
`fish_id ↔ 稳定 ID` 的映射**未定**（用户暂缓），故本模块只用 Arena 内部 id（`fish_XX`）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np
import torch

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.env import DanioArena, Event
from evogenesis.development.config import DEFAULT_CONFIG as DEFAULT_RGCD_CONFIG
from evogenesis.development.config import RGCDConfig
from evogenesis.development.rgcd import ConnectomePhenotype
from evogenesis.pipeline.model_chain import (
    Individual,
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


def viable_pairs(
    individuals: Sequence[Individual],
    motifs: Sequence[str],
    *,
    master_seed: int,
    config: RGCDConfig = DEFAULT_RGCD_CONFIG,
    device: str = "cpu",
) -> list[tuple[Individual, ConnectomePhenotype]]:
    """发育并保留 `viable` 个体（`RGCD §7`）；其余不入 Arena。"""
    phenotypes = phenotypes_of(
        individuals, motifs, master_seed=master_seed, config=config, device=device
    )
    return [
        (individual, phenotype)
        for individual, phenotype in zip(individuals, phenotypes, strict=True)
        if phenotype.viable
    ]


def run_arena_episode(
    individuals: Sequence[Individual],
    *,
    master_seed: int,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    steps: int | None = None,
    device: str = "cpu",
) -> ArenaEpisodeResult:
    """用 DanioNet 驱动 Arena 跑一局（`steps=None` 取 `world.episode_steps`）。"""
    motifs = motif_catalog(master_seed, chain.layout)
    pairs = viable_pairs(
        individuals, motifs, master_seed=master_seed, config=chain.rgcd, device=device
    )
    if not pairs:
        raise ValueError("没有 viable 个体可进 Arena（RGCD §7）")
    phenotypes = [phenotype for _, phenotype in pairs]
    n_eval = len(phenotypes)

    config = replace(arena_config, population=replace(arena_config.population, n_fish=n_eval))
    arena = DanioArena(config, master_seed=master_seed)
    arena.reset()
    net = danionet_of(phenotypes, master_seed=master_seed, config=chain.network, device=device)

    total = config.world.episode_steps if steps is None else steps
    fish_ids = sorted(arena.fish)
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
