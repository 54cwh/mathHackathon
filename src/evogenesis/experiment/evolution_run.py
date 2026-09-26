"""代循环编排（owner：`experiment/代循环编排.md`）。

把「评估一代 → 折算 `F` → 回填 `Individual` → `advance_generation` → 下一代」串成可执行循环。
本模块只做编排：分量口径归 `experiment/metrics.py` 与 `evolution §6`，选择/繁殖算法归
`evolution`，发育/viability 归 `development`，Arena 驱动归 `pipeline`。
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np

from evogenesis.arena.config import ArenaConfig
from evogenesis.core.ids import mint_id, parse_id
from evogenesis.core.io import write_jsonl
from evogenesis.core.seed import SeedManager
from evogenesis.evolution.config import EvolutionConfig
from evogenesis.evolution.fitness import composite_fitness
from evogenesis.evolution.population import (
    EVENT_POPULATION_BOTTLENECK,
    Individual,
    advance_generation,
)
from evogenesis.experiment import runlayout
from evogenesis.experiment.events import episode_event_header, write_event_log
from evogenesis.experiment.metrics import (
    aggregate_by_seed,
    energy_efficiency,
    episode_metrics,
)
from evogenesis.experiment.run_artifacts import (
    dump_json,
    episode_row,
    write_metrics_csv,
    write_population,
)
from evogenesis.pipeline.arena_episode import (
    PopulationEvaluation,
    arena_seeds_for,
    evaluate_population,
)
from evogenesis.pipeline.model_chain import ChainIndividual, ModelChainConfig, initial_population


@dataclass(frozen=True)
class GenerationSummary:
    """一代的汇总行（`evolution.jsonl` 的一行）。"""

    generation: int
    n_individuals: int
    n_viable: int
    fitness_mean: float | None
    fitness_std: float | None
    bottleneck: bool
    event: str | None = None


@dataclass(frozen=True)
class EvolutionRunResult:
    """代循环结果。"""

    generations_run: int
    bottleneck: bool
    summaries: tuple[GenerationSummary, ...]
    final_population: tuple[Individual, ...]


def to_chain_individuals(
    individuals: tuple[Individual, ...], *, experiment_id: str
) -> tuple[ChainIndividual, ...]:
    """把 `evolution.Individual` 转为 pipeline 的 `ChainIndividual`（铸造本代 `fish_id`）。

    `fish_id = mint_id(experiment_id, "fish", generation, index)`，其中 `generation` / `index`
    由 `genome_id` 解析（`core §3`：不得用调用顺序）。若 `Individual` 已带本代 `fish_id`（gen 0
    由 `initial_population` 铸造），则沿用。
    """
    out: list[ChainIndividual] = []
    for individual in individuals:
        _, generation, _, index = parse_id(individual.genome_id)
        fish_id = individual.fish_id or mint_id(experiment_id, "fish", generation, index)
        out.append(
            ChainIndividual(
                genome_id=individual.genome_id, fish_id=fish_id, genome=individual.genome
            )
        )
    return tuple(out)


def assemble_individuals(
    individuals: tuple[ChainIndividual, ...],
    evaluation: PopulationEvaluation,
    *,
    arena_config: ArenaConfig,
    weights: dict[str, float],
) -> tuple[Individual, ...]:
    """按 `代循环编排.md` §3 把评估结果折算为选择用 `F` 并回填 `Individual`。

    分量取**原始量**（`survival_steps` / `captures` / `escape_successes` / `energy_efficiency`），
    对齐全长；non-viable 置 0（由 `composite_fitness` 的掩码处理）。存活步数为 0 的个体
    `energy_efficiency` 记 0（函数定义域要求 `T_i>0`）。
    """
    n = len(individuals)
    mask = np.zeros(n, dtype=bool)
    components: dict[str, np.ndarray] = {
        "survival": np.zeros(n, dtype=np.float32),
        "prey_capture": np.zeros(n, dtype=np.float32),
        "escape_success": np.zeros(n, dtype=np.float32),
        "energy_efficiency": np.zeros(n, dtype=np.float32),
    }
    per_fish = evaluation.episode.per_fish if evaluation.episode is not None else {}
    e_max = arena_config.energy.e_max
    for index in evaluation.viable_indices:
        fish_id = individuals[index].fish_id
        rec = per_fish[fish_id]
        steps = int(rec["survival_steps"])
        mask[index] = True
        components["survival"][index] = np.float32(steps)
        components["prey_capture"][index] = np.float32(rec["captures"])
        components["escape_success"][index] = np.float32(rec["escape_successes"])
        energy_traj = rec.get("energy_trajectory") or []
        energy_final = float(energy_traj[-1]) if energy_traj else e_max
        # `T_i == 0` 的边界由 `metrics.energy_efficiency`（§2.1）统一处理（返回 0）。
        components["energy_efficiency"][index] = np.float32(
            energy_efficiency(energy_final, e_max, steps)
        )
    fitness = composite_fitness(components, viable=mask, weights=weights)
    out: list[Individual] = []
    for index, chain_individual in enumerate(individuals):
        viable = bool(mask[index])
        phenotype = evaluation.phenotypes[index]
        out.append(
            Individual(
                genome_id=chain_individual.genome_id,
                genome=chain_individual.genome,
                fish_id=chain_individual.fish_id if viable else None,
                fitness=float(fitness[index]),
                viable=viable,
                failure_reason=None if viable else phenotype.viability_reason,
            )
        )
    return tuple(out)


def _write_generation_artifacts(
    run_dir: Path,
    *,
    experiment_id: str,
    environment_id: str,
    generation: int,
    seed: int,
    individuals: tuple[Individual, ...],
    evaluation: PopulationEvaluation,
    arena_config: ArenaConfig,
    weights: dict[str, float],
    steps: int,
    elapsed: float,
) -> None:
    """落一代的产物到 `<run>/generations/g<gen:04d>/`（`代循环编排.md` §5）。"""
    gen_dir = run_dir / "generations" / f"g{generation:04d}"
    gen_dir.mkdir(parents=True, exist_ok=True)
    episode = evaluation.episode
    rows: list[dict] = []
    if episode is not None:
        rows = [
            {
                "seed": seed,
                "fish_id": fish_id,
                **episode_metrics(
                    rec,
                    episode_steps=steps,
                    e_max=arena_config.energy.e_max,
                    capture_success_prob=arena_config.growth.capture_success_prob,
                    weights=weights,
                ),
            }
            for fish_id, rec in sorted(episode.per_fish.items())
        ]
        spawn_seed, _ = arena_seeds_for(seed, generation)
        write_event_log(
            gen_dir / "events.jsonl",
            episode_event_header(
                experiment_id=experiment_id,
                episode_id="ep0001",
                environment_id=environment_id,
                generation=generation,
                episode_seed=spawn_seed,
                n_events=len(episode.events),
            ),
            episode.events,
        )
        write_metrics_csv(gen_dir, rows)
        write_population(gen_dir, seed, episode.per_fish)
        write_jsonl(
            gen_dir / "episodes.jsonl",
            [episode_row(seed, list(episode.events), episode.per_fish, steps, elapsed)],
        )
    write_jsonl(
        gen_dir / "fitness.jsonl",
        (
            {
                "generation": generation,
                "genome_id": individual.genome_id,
                "fish_id": individual.fish_id,
                "viable": individual.viable,
                "failure_reason": individual.failure_reason,
                "fitness": individual.fitness,
            }
            for individual in individuals
        ),
    )
    if episode is not None:
        dump_json(gen_dir / "seed_summary.json", aggregate_by_seed(rows), indent=2)


def run_evolution(
    *,
    experiment_id: str,
    master_seed: int,
    generations: int,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    evolution_config: EvolutionConfig,
    run_dir: Path,
    environment_id: str = "default",
    steps: int | None = None,
    device: str = "cpu",
) -> EvolutionRunResult:
    """跑 `generations` 代；`run_dir` 须已由 `runlayout.create_run_dir` 建好。

    逐代写 `<run>/generations/g<gen:04d>/` 与 `<run>/evolution.jsonl`；`metadata.json.status`
    依 `created → running → completed | bottleneck` 更新。
    """
    steps = arena_config.world.episode_steps if steps is None else steps
    weights = evolution_config.fitness_weights.model_dump()
    seed_manager = SeedManager(master_seed)

    population = initial_population(
        master_seed=master_seed,
        experiment_id=experiment_id,
        n=evolution_config.population_size,
        layout=chain.layout,
    )
    individuals: tuple[Individual, ...] = tuple(
        Individual(genome_id=c.genome_id, genome=c.genome, fish_id=c.fish_id) for c in population
    )

    summaries: list[GenerationSummary] = []
    bottleneck = False
    generations_run = 0
    runlayout.update_run_status(run_dir, "running")
    for generation in range(generations):
        chain_individuals = to_chain_individuals(individuals, experiment_id=experiment_id)
        t0 = time.perf_counter()
        evaluation = evaluate_population(
            chain_individuals,
            master_seed=master_seed,
            chain=chain,
            arena_config=arena_config,
            steps=steps,
            generation=generation,
            device=device,
        )
        elapsed = time.perf_counter() - t0
        individuals = assemble_individuals(
            chain_individuals, evaluation, arena_config=arena_config, weights=weights
        )
        _write_generation_artifacts(
            run_dir,
            experiment_id=experiment_id,
            environment_id=environment_id,
            generation=generation,
            seed=master_seed,
            individuals=individuals,
            evaluation=evaluation,
            arena_config=arena_config,
            weights=weights,
            steps=steps,
            elapsed=elapsed,
        )
        viable_fitness = [i.fitness for i in individuals if i.viable]
        summary = GenerationSummary(
            generation=generation,
            n_individuals=len(individuals),
            n_viable=len(viable_fitness),
            fitness_mean=(float(np.mean(viable_fitness)) if viable_fitness else None),
            fitness_std=(
                float(np.std(viable_fitness, ddof=1)) if len(viable_fitness) > 1 else None
            ),
            bottleneck=False,
            event=None,
        )
        generations_run += 1

        result = advance_generation(
            individuals,
            experiment_id=experiment_id,
            generation=generation + 1,
            seed_manager=seed_manager,
            config=evolution_config,
            layout=chain.layout,
        )
        if not result.success:
            bottleneck = True
            summary = replace(summary, bottleneck=True, event=result.event)
        summaries.append(summary)
        if bottleneck:
            break
        individuals = result.offspring

    write_jsonl(run_dir / "evolution.jsonl", [asdict(s) for s in summaries])
    runlayout.update_run_status(run_dir, "bottleneck" if bottleneck else "completed")
    return EvolutionRunResult(
        generations_run=generations_run,
        bottleneck=bottleneck,
        summaries=tuple(summaries),
        final_population=individuals,
    )


__all__ = [
    "EVENT_POPULATION_BOTTLENECK",
    "EvolutionRunResult",
    "GenerationSummary",
    "assemble_individuals",
    "run_evolution",
    "to_chain_individuals",
]
