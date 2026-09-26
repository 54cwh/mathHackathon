"""K-episode 平均评估（2026-09-26 诊断 → 修复）。

诊断：单次 episode 的**排序可靠性**实测 `rho_1 = 0.069`（固定种群 × 11 个独立下标
的面板），即选择分数里约 93% 是代特异噪声 —— 这解释了「3 复制 × 2 臂」（选择 vs
漂变）为何测不到正向响应（选择 − 漂变 = −0.0088，3/3 vs 0/3 完全分离，精确置换
`p = 2/20 = 0.100`，即 3v3 设计的理论下限）。

本模块守护修复：`generation_episode_indices` 的下标调度、`assemble_individuals_averaged`
的**均值 + viable 并集**语义，以及 `run_evolution` 确实每代评估 K 次**互不重复**的实现。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

from evogenesis.arena.config import ArenaConfig
from evogenesis.evolution.config import load_evolution_config
from evogenesis.experiment import evolution_run
from evogenesis.experiment.evolution_run import (
    assemble_individuals,
    assemble_individuals_averaged,
    generation_episode_indices,
    run_evolution,
)
from evogenesis.genome.config import DEFAULT_LAYOUT
from evogenesis.genome.genome import random_genome
from evogenesis.pipeline.arena_episode import ArenaEpisodeResult, PopulationEvaluation
from evogenesis.pipeline.model_chain import ChainIndividual, load_model_chain_config

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = {
    "survival": 0.35,
    "prey_capture": 0.25,
    "escape_success": 0.20,
    "energy_efficiency": 0.20,
}


def _genome(seed: int):
    rng = np.random.default_rng(seed)
    return random_genome(DEFAULT_LAYOUT, rng=rng, genome_id=f"exp:g0:genome{seed:04d}")


def _phenotype(*, viable: bool, reason: str) -> object:
    from evogenesis.development.rgcd import ConnectomePhenotype

    return ConnectomePhenotype(
        adjacency=torch.zeros((1, 1)),
        weights0=torch.zeros((1, 1)),
        tau=torch.ones(1),
        cell_type=torch.zeros(1, dtype=torch.long),
        positions=torch.zeros((1, 2)),
        active_mask=torch.ones(1, dtype=torch.bool),
        viable=viable,
        viability_reason=reason,
        z=torch.ones((1, 6)),
    )


def _chain(n: int) -> tuple[ChainIndividual, ...]:
    return tuple(
        ChainIndividual(
            genome_id=f"exp:g0:genome{i:04d}", fish_id=f"exp:g0:fish{i:04d}", genome=_genome(i)
        )
        for i in range(n)
    )


def _evaluation(n: int, stats: dict[str, tuple[int, int, int]], viable_indices):
    """stats: fish_id -> (survival_steps, captures, escape_successes)。"""
    viable = tuple(viable_indices)
    per_fish = {
        fish_id: {
            "survival_steps": steps,
            "captures": captures,
            "escape_successes": escapes,
            "energy_trajectory": [1.0, 0.9],
        }
        for fish_id, (steps, captures, escapes) in stats.items()
    }
    return PopulationEvaluation(
        phenotypes=tuple(
            _phenotype(viable=index in viable, reason="ok") for index in range(n)
        ),
        episode=ArenaEpisodeResult(
            evaluated_individuals=len(stats), steps=10, per_fish=per_fish, events=()
        ),
        viable_indices=viable,
    )


def _nonviable_evaluation(n: int, reason: str) -> PopulationEvaluation:
    return PopulationEvaluation(
        phenotypes=tuple(_phenotype(viable=False, reason=reason) for _ in range(n)),
        episode=None,
        viable_indices=(),
    )


def _synthetic_evaluate(individuals, **kwargs) -> PopulationEvaluation:
    per_fish = {
        c.fish_id: {
            "survival_steps": 10,
            "captures": 1,
            "capture_attempts": 1,
            "encounters": 3,
            "predator_encounters": 1,
            "escape_successes": 0,
            "collisions": 0,
            "energy_trajectory": [1.0, 0.9],
        }
        for c in individuals
    }
    return PopulationEvaluation(
        phenotypes=tuple(_phenotype(viable=True, reason="ok") for _ in individuals),
        episode=ArenaEpisodeResult(
            evaluated_individuals=len(individuals), steps=10, per_fish=per_fish, events=()
        ),
        viable_indices=tuple(range(len(individuals))),
    )


# ---------------------------------------------------------------- 下标调度

def test_episode_indices_k1_reproduces_the_legacy_schedule():
    """K=1 必须逐字节延续旧行为：第 g 代只用下标 g。"""
    assert [generation_episode_indices(g, 1) for g in range(4)] == [(0,), (1,), (2,), (3,)]


def test_episode_indices_k_below_one_degrades_to_single():
    assert generation_episode_indices(5, 0) == (5,)
    assert generation_episode_indices(5, -3) == (5,)


def test_episode_indices_are_disjoint_and_dense_across_generations():
    """跨代的 K 个下标互不重复 —— 保证 K 次实现独立、不同代不共享同一次实现。"""
    blocks = [generation_episode_indices(g, 3) for g in range(4)]
    assert blocks[0] == (0, 1, 2) and blocks[1] == (3, 4, 5)
    flat = [index for block in blocks for index in block]
    assert len(flat) == len(set(flat))
    assert sorted(flat) == list(range(12))


# ---------------------------------------------------------------- 均值 / 并集语义

def test_averaging_identical_evaluations_reproduces_the_single_score():
    """K 份同一实现取均值 = 该实现本身 ⇒ 分数必须与 K=1 相同（加性不变量守护）。"""
    chain = _chain(3)
    stats = {
        "exp:g0:fish0000": (10, 2, 1),
        "exp:g0:fish0001": (5, 0, 0),
        "exp:g0:fish0002": (8, 1, 1),
    }
    evaluation = _evaluation(3, stats, (0, 1, 2))
    single = assemble_individuals(
        chain, evaluation, arena_config=ArenaConfig(), weights=WEIGHTS
    )
    averaged = assemble_individuals_averaged(
        chain, (evaluation, evaluation, evaluation), arena_config=ArenaConfig(), weights=WEIGHTS
    )
    assert [i.fitness for i in averaged] == pytest.approx([i.fitness for i in single])
    assert [i.viable for i in averaged] == [i.viable for i in single]


def test_viable_is_the_union_across_episodes():
    chain = _chain(2)
    ev_a = _evaluation(2, {"exp:g0:fish0000": (10, 1, 0)}, (0,))
    ev_b = _evaluation(2, {"exp:g0:fish0001": (7, 1, 0)}, (1,))
    out = assemble_individuals_averaged(
        chain, (ev_a, ev_b), arena_config=ArenaConfig(), weights=WEIGHTS
    )
    assert [i.viable for i in out] == [True, True]
    assert [i.fish_id for i in out] == ["exp:g0:fish0000", "exp:g0:fish0001"]


def test_dying_in_some_episodes_lowers_the_averaged_score():
    """偶尔死亡按死亡频率折价（期望口径 E[survival]），而非被掩码抹平。"""
    chain = _chain(2)
    alive = _evaluation(
        2, {"exp:g0:fish0000": (10, 1, 0), "exp:g0:fish0001": (10, 1, 0)}, (0, 1)
    )
    fish0_dead = _evaluation(2, {"exp:g0:fish0001": (10, 1, 0)}, (1,))
    out = assemble_individuals_averaged(
        chain, (alive, fish0_dead), arena_config=ArenaConfig(), weights=WEIGHTS
    )
    assert all(i.viable for i in out)
    assert out[0].fitness < out[1].fitness


def test_failure_reason_comes_from_the_first_nonviable_episode():
    chain = _chain(1)
    out = assemble_individuals_averaged(
        chain,
        (
            _nonviable_evaluation(1, "missing_fate:motor"),
            _nonviable_evaluation(1, "weight_spectral_radius_not_contractive"),
        ),
        arena_config=ArenaConfig(),
        weights=WEIGHTS,
    )
    assert out[0].viable is False
    assert out[0].failure_reason == "missing_fate:motor"
    assert out[0].fish_id is None
    assert out[0].fitness == 0.0


def test_empty_evaluations_is_rejected():
    with pytest.raises(ValueError):
        assemble_individuals_averaged(
            _chain(1), (), arena_config=ArenaConfig(), weights=WEIGHTS
        )


# ---------------------------------------------------------------- 编排接线

def _run(tmp_path, monkeypatch, *, episode_budget: int, generations: int):
    seen: list[int] = []

    def recorder(individuals, **kwargs):
        seen.append(kwargs["generation"])
        return _synthetic_evaluate(individuals, **kwargs)

    monkeypatch.setattr(evolution_run, "evaluate_population", recorder)
    evolution_config = load_evolution_config(
        ROOT / "configs" / "evolution.yaml", overrides={"population_size": 8}
    )
    (tmp_path / "metadata.json").write_text('{"status": "created"}', encoding="utf-8")
    run_evolution(
        experiment_id="exp-k",
        master_seed=1103,
        generations=generations,
        chain=load_model_chain_config(),
        arena_config=ArenaConfig(),
        evolution_config=evolution_config,
        run_dir=tmp_path,
        steps=10,
        episodes_per_generation=episode_budget,
    )
    return seen


def test_run_evolution_k1_keeps_the_legacy_generation_indices(tmp_path, monkeypatch):
    assert _run(tmp_path, monkeypatch, episode_budget=1, generations=2) == [0, 1]


def test_run_evolution_evaluates_k_independent_episodes_per_generation(tmp_path, monkeypatch):
    assert _run(tmp_path, monkeypatch, episode_budget=3, generations=2) == [0, 1, 2, 3, 4, 5]
