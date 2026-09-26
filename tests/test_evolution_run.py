"""代循环编排测试（`experiment/代循环编排.md`）。

单元：`to_chain_individuals` 的稳定 `fish_id` 铸造、`assemble_individuals` 的分量→F→回填。
集成：`run_evolution` 用**合成评估**（monkeypatch `evaluate_population`）跑 2 代，验证
逐代产物、`evolution.jsonl`、`metadata.json.status` 与下一代种群规模。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from evogenesis.arena.config import ArenaConfig
from evogenesis.evolution.config import load_evolution_config
from evogenesis.evolution.population import Individual
from evogenesis.experiment import evolution_run
from evogenesis.experiment.evolution_run import (
    assemble_individuals,
    run_evolution,
    to_chain_individuals,
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


def test_to_chain_individuals_mints_stable_fish_ids():
    individuals = (
        Individual(genome_id="exp:g2:genome0003", genome=_genome(1)),
        Individual(genome_id="exp:g2:genome0000", genome=_genome(2), fish_id="exp:g2:fish0000"),
    )
    chain = to_chain_individuals(individuals, experiment_id="exp")
    assert [c.fish_id for c in chain] == ["exp:g2:fish0003", "exp:g2:fish0000"]
    assert [c.genome_id for c in chain] == [i.genome_id for i in individuals]


def test_assemble_individuals_maps_components_to_fitness():
    chain = tuple(
        ChainIndividual(
            genome_id=f"exp:g0:genome{i:04d}", fish_id=f"exp:g0:fish{i:04d}", genome=_genome(i)
        )
        for i in range(3)
    )
    evaluation = PopulationEvaluation(
        phenotypes=(
            _phenotype(viable=True, reason="ok"),
            _phenotype(viable=True, reason="ok"),
            _phenotype(viable=False, reason="missing_fate:motor"),
        ),
        episode=ArenaEpisodeResult(
            evaluated_individuals=2,
            steps=10,
            per_fish={
                "exp:g0:fish0000": {
                    "survival_steps": 10,
                    "captures": 2,
                    "escape_successes": 1,
                    "energy_trajectory": [1.0, 0.5],
                },
                "exp:g0:fish0001": {
                    "survival_steps": 5,
                    "captures": 0,
                    "escape_successes": 0,
                    "energy_trajectory": [1.0, 0.8],
                },
            },
            events=(),
        ),
        viable_indices=(0, 1),
    )
    result = assemble_individuals(chain, evaluation, arena_config=ArenaConfig(), weights=WEIGHTS)
    assert [i.viable for i in result] == [True, True, False]
    assert result[2].failure_reason == "missing_fate:motor"
    assert result[2].fish_id is None
    assert result[2].fitness == 0.0
    assert result[0].fish_id == "exp:g0:fish0000"
    # 两个 viable 的 survival 为 10 / 5 → min-max 后 1 / 0；F 因此严格递减
    assert 0.0 <= result[1].fitness < result[0].fitness <= 1.0


def _synthetic_evaluate(individuals, **kwargs):
    """把整代判为 viable 的合成评估（绕过发育，专测编排）。"""
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
            evaluated_individuals=len(individuals),
            steps=10,
            per_fish=per_fish,
            events=(),
        ),
        viable_indices=tuple(range(len(individuals))),
    )


def _no_viable_evaluate(individuals, **kwargs):
    """整代无 viable 的合成评估：`episode=None`、全体 non-viable。"""
    return PopulationEvaluation(
        phenotypes=tuple(
            _phenotype(viable=False, reason="weight_spectral_radius_not_contractive")
            for _ in individuals
        ),
        episode=None,
        viable_indices=(),
    )


def test_run_evolution_handles_generation_without_viable(tmp_path, monkeypatch):
    """整代无 viable：不写 arena 五件套、status=bottleneck、event 落盘。"""
    monkeypatch.setattr(evolution_run, "evaluate_population", _no_viable_evaluate)
    evolution_config = load_evolution_config(
        ROOT / "configs" / "evolution.yaml", overrides={"population_size": 8}
    )
    (tmp_path / "metadata.json").write_text('{"status": "created"}', encoding="utf-8")
    result = run_evolution(
        experiment_id="exp-evo",
        master_seed=1103,
        generations=3,
        chain=load_model_chain_config(),
        arena_config=ArenaConfig(),
        evolution_config=evolution_config,
        run_dir=tmp_path,
        steps=10,
    )
    assert result.bottleneck is True and result.generations_run == 1
    gen_dir = tmp_path / "generations" / "g0000"
    names = {path.name for path in gen_dir.iterdir()}
    assert names == {"fitness.jsonl"}
    row = json.loads(
        (tmp_path / "evolution.jsonl").read_text(encoding="utf-8").strip().splitlines()[0]
    )
    assert row["bottleneck"] is True
    assert row["event"] == "evolution.population_bottleneck"
    assert row["n_viable"] == 0
    assert json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))["status"] == (
        "bottleneck"
    )


def test_run_evolution_loop_writes_per_generation_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(evolution_run, "evaluate_population", _synthetic_evaluate)
    evolution_config = load_evolution_config(
        ROOT / "configs" / "evolution.yaml", overrides={"population_size": 8}
    )
    (tmp_path / "metadata.json").write_text('{"status": "created"}', encoding="utf-8")
    result = run_evolution(
        experiment_id="exp-evo",
        master_seed=1103,
        generations=2,
        chain=load_model_chain_config(),
        arena_config=ArenaConfig(),
        evolution_config=evolution_config,
        run_dir=tmp_path,
        steps=10,
    )
    assert result.generations_run == 2 and result.bottleneck is False
    assert len(result.final_population) == 8
    for gen in (0, 1):
        gen_dir = tmp_path / "generations" / f"g{gen:04d}"
        assert {"metrics.csv", "events.jsonl", "fitness.jsonl", "seed_summary.json"} <= {
            p.name for p in gen_dir.iterdir()
        }
        rows = [
            json.loads(line)
            for line in (gen_dir / "fitness.jsonl").read_text(encoding="utf-8").splitlines()
            if line
        ]
        assert len(rows) == 8
        assert all(row["generation"] == gen for row in rows)
        assert all(row["fish_id"].startswith(f"exp-evo:g{gen}:fish") for row in rows)
    evolution_lines = (tmp_path / "evolution.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(evolution_lines) == 2
    assert json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))["status"] == (
        "completed"
    )
