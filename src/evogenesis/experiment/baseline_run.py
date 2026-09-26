"""Experiment C baseline 对照编排（owner：`实验与评价体系.md` §3.3）。

对照 MLP / GRU / Fixed Sparse RNN（`connectome/baselines.py`）与 DanioNet：**同数据、同 BC
预算、同 evaluation episode**，逐模型给出任务指标（mean ± std，沿 seed 轴）与复杂度
（参数量 / 活跃边 / FLOPs 双口径 / latency）。

本模块只编排：模型构造与尺寸反解归 `connectome §8`；BC 契约归 `learning §3`；Arena 驱动归
`pipeline §4`；指标口径归 `experiment §2`。**实现选择（草案待确认）**：每模型每 seed 用
**1 个 agent、1 个 episode**（§3.3「每 seed 1 个 episode」）；DanioNet 条件取**首个 viable
个体**（在 `n_danio` 个候选内按稳定 index 扫描），BC 训练后评估；基线 `bc` 采样序号固定取
模型槽位（`baseline_init` 命名空间已按 `index` 分离）。

**动作口径一致**：基线与 DanioNet 的 `(ω, v)` 同映射（`ω = tanh`、`v = σ`，`connectome §4/§8`），
`v ∈ [0,1]`，与 `Arena` 把 `v` 截到 `[0,1]` 的读出口径一致；本模块不加任何按模型的读出修正。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from evogenesis.arena.config import ArenaConfig
from evogenesis.connectome.baselines import BASELINES
from evogenesis.connectome.danionet import DanioNet
from evogenesis.core.config import LearningConfig
from evogenesis.core.ids import mint_id
from evogenesis.core.seed import SeedManager
from evogenesis.evolution.config import EvolutionConfig
from evogenesis.experiment.measure import measure_latency, network_complexity
from evogenesis.experiment.metrics import (
    SCALAR_METRICS,
    episode_metrics,
    summarise_over_seeds,
)
from evogenesis.experiment.run_artifacts import write_metrics_csv
from evogenesis.learning.data import TrajectoryDataset, load_trajectory_dir
from evogenesis.learning.train import train_bc
from evogenesis.pipeline import (
    ChainIndividual,
    ModelChainConfig,
    danionet_of,
    drive_arena_with_ids,
    initial_population,
    motif_catalog,
    phenotypes_of,
)

#: Experiment C 的模型集合与槽位（槽位用于 `baseline_init` / `bc` 序号与稳定 ID）。
MODELS: tuple[str, ...] = (*BASELINES, "danionet")
DANIONET_MODEL = "danionet"


@dataclass(frozen=True)
class ModelResult:
    """单个模型在单 seed 下的评估结果。"""

    seed: int
    model: str
    metrics: dict[str, Any]
    complexity: dict[str, float | int]


@dataclass(frozen=True)
class BaselineComparisonResult:
    """Experiment C 对照结果（跨 seed 汇总）。"""

    experiment_id: str
    seeds: tuple[int, ...]
    steps: int
    models: tuple[dict[str, Any], ...]  # 每模型：model / metrics(mean,std,n) / complexity / note


def _complexity(net: Any, *, sensory_dim: int) -> dict[str, float | int]:
    """归一化复杂度：参数量 / 活跃边 / FLOPs 双口径 / latency（`measure §2.4`）。"""
    if isinstance(net, DanioNet):
        raw = network_complexity(net)
    else:  # baseline：自身 complexity()（`connectome §8`）
        raw = net.complexity()
    observation = np.zeros((1, sensory_dim), dtype=np.float32)
    latency = measure_latency(net, observation)
    return {
        "parameter_count": int(raw["parameter_count"]),
        "active_edges": int(raw["active_edges"]),
        "macs_implemented": int(raw["macs_implemented"]),
        "macs_theoretical": int(raw["macs_theoretical"]),
        "flops_implemented": int(raw["flops_implemented"]),
        "flops_theoretical": int(raw["flops_theoretical"]),
        "latency_p50_ms": float(latency["p50_ms"]),
        "latency_p95_ms": float(latency["p95_ms"]),
    }


def _metrics_for(
    per_fish: dict[str, dict],
    fish_id: str,
    *,
    steps: int,
    arena_config: ArenaConfig,
    weights: dict[str, float],
) -> dict[str, Any]:
    return episode_metrics(
        per_fish[fish_id],
        episode_steps=steps,
        e_max=arena_config.energy.e_max,
        capture_success_prob=arena_config.growth.capture_success_prob,
        weights=weights,
    )


def _evaluate_baseline(
    name: str,
    *,
    slot: int,
    seed: int,
    dataset: TrajectoryDataset,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    learning_config: LearningConfig,
    weights: dict[str, float],
    experiment_id: str,
    steps: int,
    generation: int,
    device: str,
) -> ModelResult:
    net = BASELINES[name](
        master_seed=seed, index=slot, sensory_dim=chain.network.sensory_dim, device=device
    )
    train_bc(
        net,
        dataset,
        learning_config,
        seed_manager=SeedManager(seed),
        seed_index=slot,
        device=device,
        sign_constrained=False,
    )
    fish_id = mint_id(experiment_id, "fish", generation, slot)
    genome_id = mint_id(experiment_id, "genome", generation, slot)
    episode = drive_arena_with_ids(
        fish_ids=[fish_id],
        genome_ids=[genome_id],
        net=net,
        master_seed=seed,
        chain=chain,
        arena_config=arena_config,
        steps=steps,
        generation=generation,
    )
    return ModelResult(
        seed=seed,
        model=name,
        metrics=_metrics_for(
            episode.per_fish, fish_id, steps=steps, arena_config=arena_config, weights=weights
        ),
        complexity=_complexity(net, sensory_dim=chain.network.sensory_dim),
    )


def _first_viable(
    population: tuple[ChainIndividual, ...], phenotypes: list
) -> tuple[ChainIndividual, Any] | None:
    for individual, phenotype in zip(population, phenotypes, strict=True):
        if phenotype.viable:
            return individual, phenotype
    return None


def _evaluate_danionet(
    *,
    slot: int,
    seed: int,
    dataset: TrajectoryDataset,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    learning_config: LearningConfig,
    weights: dict[str, float],
    experiment_id: str,
    n_danio: int,
    steps: int,
    generation: int,
    device: str,
) -> ModelResult | None:
    population = initial_population(
        master_seed=seed, experiment_id=experiment_id, n=n_danio, layout=chain.layout
    )
    motifs = motif_catalog(seed, chain.layout)
    phenotypes = phenotypes_of(
        population, motifs, master_seed=seed, config=chain.rgcd, device=device
    )
    picked = _first_viable(population, phenotypes)
    if picked is None:
        return None
    individual, phenotype = picked
    net = danionet_of(
        [phenotype], master_seed=seed, config=chain.network, device=device, sign_constrained=True
    )
    train_bc(
        net,
        dataset,
        learning_config,
        seed_manager=SeedManager(seed),
        seed_index=slot,
        device=device,
        sign_constrained=True,
    )
    episode = drive_arena_with_ids(
        fish_ids=[individual.fish_id],
        genome_ids=[individual.genome_id],
        net=net,
        master_seed=seed,
        chain=chain,
        arena_config=arena_config,
        steps=steps,
        generation=generation,
    )
    return ModelResult(
        seed=seed,
        model=DANIONET_MODEL,
        metrics=_metrics_for(
            episode.per_fish,
            individual.fish_id,
            steps=steps,
            arena_config=arena_config,
            weights=weights,
        ),
        complexity=_complexity(net, sensory_dim=chain.network.sensory_dim),
    )


def _summarise_models(results: list[ModelResult], *, seeds: tuple[int, ...]) -> tuple[dict, ...]:
    """按模型分组，沿 seed 轴 mean±std（§1.2）；复杂度取该模型首个有结果的 seed。"""
    out: list[dict] = []
    for name in MODELS:
        rows = [r for r in results if r.model == name]
        if not rows:
            out.append(
                {
                    "model": name,
                    "metrics": None,
                    "complexity": None,
                    "note": "无结果（DanioNet 在 n_danio 候选内无 viable 个体）"
                    if name == DANIONET_MODEL
                    else "无结果",
                }
            )
            continue
        seed_rows = [{"seed": r.seed, **r.metrics} for r in rows]
        out.append(
            {
                "model": name,
                "metrics": summarise_over_seeds(seed_rows, metrics=SCALAR_METRICS),
                "complexity": rows[0].complexity,
                "note": "复杂度取首 seed" if name != DANIONET_MODEL else None,
            }
        )
    return tuple(out)


def run_baseline_comparison(
    *,
    experiment_id: str,
    seeds: tuple[int, ...],
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    learning_config: LearningConfig,
    evolution_config: EvolutionConfig,
    trajectories_dir: str | Path,
    run_dir_of: Any = None,
    n_danio: int = 12,
    steps: int | None = None,
    generation: int = 0,
    device: str = "cpu",
) -> BaselineComparisonResult:
    """跑 Experiment C：每 seed 每模型 1 agent × 1 episode，落 `metrics.csv` 与跨 seed 表。

    ``run_dir_of(seed) -> Path`` 为可选的 run 目录提供者（由 CLI 用 `runlayout` 建）；给出时
    每个 seed 写 ``<run>/metrics.csv``（含 `model` 列）。跨 seed 汇总由本函数返回，落盘由 CLI
    写 `results/tables/<experiment_id>_baselines.json`。
    """
    steps = arena_config.world.episode_steps if steps is None else steps
    weights = evolution_config.fitness_weights.model_dump()
    dataset = load_trajectory_dir(trajectories_dir)

    all_rows: list[dict] = []
    results: list[ModelResult] = []
    for seed in seeds:
        seed_results: list[ModelResult] = []
        for slot, name in enumerate(MODELS):
            if name == DANIONET_MODEL:
                result = _evaluate_danionet(
                    slot=slot,
                    seed=seed,
                    dataset=dataset,
                    chain=chain,
                    arena_config=arena_config,
                    learning_config=learning_config,
                    weights=weights,
                    experiment_id=experiment_id,
                    n_danio=n_danio,
                    steps=steps,
                    generation=generation,
                    device=device,
                )
            else:
                result = _evaluate_baseline(
                    name,
                    slot=slot,
                    seed=seed,
                    dataset=dataset,
                    chain=chain,
                    arena_config=arena_config,
                    learning_config=learning_config,
                    weights=weights,
                    experiment_id=experiment_id,
                    steps=steps,
                    generation=generation,
                    device=device,
                )
            if result is None:
                continue
            seed_results.append(result)
            results.append(result)
            all_rows.append({"seed": seed, "model": result.model, **result.metrics})
        if run_dir_of is not None:
            run_dir = run_dir_of(seed)
            rows = [r for r in all_rows if r["seed"] == seed]
            write_metrics_csv(run_dir, rows)

    models = _summarise_models(results, seeds=seeds)
    return BaselineComparisonResult(
        experiment_id=experiment_id, seeds=seeds, steps=steps, models=models
    )


def comparison_payload(result: BaselineComparisonResult, *, n_agents: int) -> dict:
    """跨 seed 对照表的落盘 payload（schema = `schemas/baseline_comparison.schema.json`）。"""
    return {
        "experiment_id": result.experiment_id,
        "seeds": list(result.seeds),
        "steps": result.steps,
        "n_agents": n_agents,
        "models": list(result.models),
    }


def table_path(experiment_id: str, root: str | Path) -> Path:
    """跨 seed 对照表路径 `results/tables/<experiment_id>_baselines.json`。"""
    return Path(root) / "tables" / f"{experiment_id}_baselines.json"


__all__ = [
    "DANIONET_MODEL",
    "MODELS",
    "BaselineComparisonResult",
    "ModelResult",
    "comparison_payload",
    "run_baseline_comparison",
    "table_path",
]
