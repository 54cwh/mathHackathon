"""Experiment D 消融对照编排（owner：`实验与评价体系.md` §3.4）。

三臂 + 控制，均只改**一个变量**（变量口径 owner = `connectome/DanioNet设计规范.md` §9）：

- 架构臂（DanioNet 驱动，同 §3.3）：`full`（控制）/ `tau_homo`（`tau_min=tau_max=τ*`）/
  `no_wiring_cost`（`distance_lambda=0`）。
- BC 臂（`learning §4` 口径）：`bc_dale`（有 Dale 符号约束）/ `bc_no_dale`（无）。

**评估口径（用户 2026-09-27 裁定，镜像 §3.3/§3.5）**：每 arm 每 seed 取**首个 viable 个体 ×
1 episode**；架构臂报 §2 指标 + §2.4 效率（active-edge efficiency / 参数量 / active edges /
FLOPs / latency），BC 臂报任务指标 + `flip_rate` + 谱半径。仅编排：模型构造/变量口径归
`connectome §9`，指标归 `experiment §2`，Arena 驱动归 `pipeline §4`。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from evogenesis.arena.config import ArenaConfig
from evogenesis.connectome.danionet import DanioNet
from evogenesis.core.config import LearningConfig
from evogenesis.evolution.config import EvolutionConfig
from evogenesis.experiment.learning_run import learning_records, run_lifetime_learning
from evogenesis.experiment.measure import measure_latency, network_complexity
from evogenesis.experiment.metrics import (
    SCALAR_METRICS,
    episode_metrics,
    summarise_over_seeds,
)
from evogenesis.pipeline import (
    ChainIndividual,
    ModelChainConfig,
    danionet_of,
    drive_arena_with_ids,
    initial_population,
    load_model_chain_config,
    motif_catalog,
    phenotypes_of,
)

#: 架构臂（DanioNet 驱动；`connectome §9` 变量口径）。
ARCH_ARMS: tuple[str, ...] = ("full", "tau_homo", "no_wiring_cost")
#: BC 臂（仅 Dale 符号约束一个变量）。
BC_ARMS: tuple[str, ...] = ("bc_dale", "bc_no_dale")
ARMS: tuple[str, ...] = (*ARCH_ARMS, *BC_ARMS)
#: 控制臂。
FULL_ARM = "full"
#: 架构臂对照表的指标列：§2 标量 + §2.4 active-edge efficiency。
ARCH_METRICS: tuple[str, ...] = (*SCALAR_METRICS, "active_edge_efficiency")
#: BC 臂对照表的指标列：§2 标量 + `flip_rate` / `spectral_radius`（`learning §4`）。
BC_METRICS: tuple[str, ...] = (*SCALAR_METRICS, "flip_rate", "spectral_radius")


@dataclass(frozen=True)
class ArmResult:
    """单个消融臂在单 seed 下的评估结果。"""

    seed: int
    arm: str
    kind: str  # "architecture" | "bc"
    metrics: dict[str, Any]
    complexity: dict[str, float | int] | None
    learning: dict[str, Any] | None
    note: str | None = None


@dataclass(frozen=True)
class AblationComparisonResult:
    """Experiment D 对照结果（跨 seed 汇总）。"""

    experiment_id: str
    seeds: tuple[int, ...]
    steps: int
    tau: float
    arms: tuple[dict[str, Any], ...]  # 每臂：arm / kind / metrics / complexity / learning / note


def arm_overrides(arm: str, tau: float) -> dict[str, Any] | None:
    """该臂相对 `full` 的**唯一**覆盖（`connectome §9`）；`full` 返回 `None`。"""
    if arm == "full":
        return None
    if arm == "tau_homo":
        return {"connectome": {"tau_min": tau, "tau_max": tau}}
    if arm == "no_wiring_cost":
        return {"connectome": {"distance_lambda": 0.0}}
    if arm in BC_ARMS:
        return None
    raise ValueError(f"未知消融臂：{arm!r}（可选 {ARMS}）")


def _complexity(net: Any, *, sensory_dim: int) -> dict[str, float | int]:
    """归一化复杂度：参数量 / active edges / FLOPs 双口径 / latency（`measure §2.4`）。"""
    raw = network_complexity(net) if isinstance(net, DanioNet) else net.complexity()
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


def active_edge_efficiency(composite_fitness: float, active_edges: int, steps: int) -> float | None:
    """`§2.4`：`TaskPerformance / (ActiveConnections × Timesteps)`；分母非正时 `None`。"""
    denominator = active_edges * steps
    if denominator <= 0:
        return None
    return composite_fitness / denominator


def _metrics_for(
    per_fish: dict[str, dict],
    fish_id: str,
    *,
    steps: int,
    arena_config: ArenaConfig,
    weights: dict[str, float],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = episode_metrics(
        per_fish[fish_id],
        episode_steps=steps,
        e_max=arena_config.energy.e_max,
        capture_success_prob=arena_config.growth.capture_success_prob,
        weights=weights,
    )
    if extra:
        row.update(extra)
    return row


def _first_viable(
    population: tuple[ChainIndividual, ...], phenotypes: list
) -> tuple[ChainIndividual, Any] | None:
    for individual, phenotype in zip(population, phenotypes, strict=True):
        if phenotype.viable:
            return individual, phenotype
    return None


def _arch_arm(
    arm: str,
    *,
    seed: int,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    weights: dict[str, float],
    experiment_id: str,
    n: int,
    steps: int,
    generation: int,
    device: str,
) -> ArmResult | None:
    """架构臂：首个 viable 个体 × 1 episode（DanioNet 驱动）。"""
    population = initial_population(
        master_seed=seed, experiment_id=experiment_id, n=n, layout=chain.layout
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
    complexity = _complexity(net, sensory_dim=chain.network.sensory_dim)
    metrics = _metrics_for(
        episode.per_fish,
        individual.fish_id,
        steps=steps,
        arena_config=arena_config,
        weights=weights,
    )
    metrics["active_edge_efficiency"] = active_edge_efficiency(
        metrics["composite_fitness"], int(complexity["active_edges"]), steps
    )
    return ArmResult(
        seed=seed,
        arm=arm,
        kind="architecture",
        metrics=metrics,
        complexity=complexity,
        learning=None,
    )


def _bc_arm(
    arm: str,
    *,
    seed: int,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    learning_config: LearningConfig,
    weights: dict[str, float],
    trajectories_dir: str | Path,
    experiment_id: str,
    n: int,
    steps: int,
    generation: int,
    device: str,
) -> ArmResult | None:
    """BC 臂：一次生命周期学习（训练后评估首个 viable 个体），只变 Dale 符号约束。"""
    sign_constrained = arm == "bc_dale"
    result = run_lifetime_learning(
        experiment_id=experiment_id,
        master_seed=seed,
        chain=chain,
        arena_config=arena_config,
        learning_config=learning_config,
        trajectories_dir=trajectories_dir,
        generation=generation,
        n=n,
        steps=steps,
        sign_constrained=sign_constrained,
        device=device,
    )
    if result.post is None:
        return None
    records = learning_records(result)
    if not records:
        return None
    first = records[0]
    metrics = _metrics_for(
        result.post.per_fish,
        first["fish_id"],
        steps=steps,
        arena_config=arena_config,
        weights=weights,
        extra={"flip_rate": first["flip_rate"], "spectral_radius": first["spectral_radius"]},
    )
    learning = {
        "delta_w_norm": first["delta_w_norm"],
        "final_loss": first["final_loss"],
        "n_updates": first["n_updates"],
        "coverage_steps": first["coverage_steps"],
        "visible_steps": first["visible_steps"],
    }
    return ArmResult(
        seed=seed, arm=arm, kind="bc", metrics=metrics, complexity=None, learning=learning
    )


def _summarise_arms(results: list[ArmResult], *, tau: float) -> tuple[dict[str, Any], ...]:
    """按臂分组，沿 seed 轴 mean±std（§1.2）；复杂度取该臂首个有结果的 seed。"""
    out: list[dict[str, Any]] = []
    for arm in ARMS:
        rows = [r for r in results if r.arm == arm]
        if not rows:
            out.append(
                {
                    "arm": arm,
                    "kind": "bc" if arm in BC_ARMS else "architecture",
                    "metrics": None,
                    "complexity": None,
                    "learning": None,
                    "note": "无结果（未提供轨迹目录或该 seed 无 viable 个体）",
                }
            )
            continue
        metric_names = BC_METRICS if rows[0].kind == "bc" else ARCH_METRICS
        seed_rows = [{"seed": r.seed, **r.metrics} for r in rows]
        out.append(
            {
                "arm": arm,
                "kind": rows[0].kind,
                "metrics": summarise_over_seeds(seed_rows, metrics=metric_names),
                "complexity": rows[0].complexity,
                "learning": rows[0].learning,
                "note": (
                    "BC 臂：`τ*` 不适用"
                    if rows[0].kind == "bc"
                    else ("控制臂（无覆盖）" if arm == FULL_ARM else f"单变量消融；τ*={tau}")
                ),
            }
        )
    return tuple(out)


def run_ablation_comparison(
    *,
    experiment_id: str,
    seeds: Sequence[int],
    model_config_path: str | Path,
    arena_config: ArenaConfig,
    learning_config: LearningConfig,
    evolution_config: EvolutionConfig,
    trajectories_dir: str | Path | None = None,
    tau: float = 5.5,
    n: int = 12,
    steps: int | None = None,
    generation: int = 0,
    device: str = "cpu",
    run_dir_of: Callable[[int], Path] | None = None,
) -> AblationComparisonResult:
    """跑 Experiment D：每 seed 每臂 1 agent × 1 episode，返回跨 seed 对照（落盘由 CLI）。

    `trajectories_dir=None` 时跳过 BC 臂（表中标 `note`）。`run_dir_of(seed) -> Path` 给出时，
    每个 seed 写 ``<run>/metrics.csv``（含 `arm` 列）。
    """
    steps = arena_config.world.episode_steps if steps is None else steps
    weights = evolution_config.fitness_weights.model_dump()
    seeds = tuple(seeds)

    all_rows: list[dict[str, Any]] = []
    results: list[ArmResult] = []
    for seed in seeds:
        for arm in ARMS:
            if arm in BC_ARMS:
                if trajectories_dir is None:
                    continue
                chain = load_model_chain_config(
                    model_config_path, overrides=arm_overrides(arm, tau)
                )
                result = _bc_arm(
                    arm,
                    seed=seed,
                    chain=chain,
                    arena_config=arena_config,
                    learning_config=learning_config,
                    weights=weights,
                    trajectories_dir=trajectories_dir,
                    experiment_id=experiment_id,
                    n=n,
                    steps=steps,
                    generation=generation,
                    device=device,
                )
            else:
                chain = load_model_chain_config(
                    model_config_path, overrides=arm_overrides(arm, tau)
                )
                result = _arch_arm(
                    arm,
                    seed=seed,
                    chain=chain,
                    arena_config=arena_config,
                    weights=weights,
                    experiment_id=experiment_id,
                    n=n,
                    steps=steps,
                    generation=generation,
                    device=device,
                )
            if result is None:
                continue
            results.append(result)
            row: dict[str, Any] = {"seed": seed, "arm": arm, **result.metrics}
            if result.complexity:
                row.update(result.complexity)
            all_rows.append(row)
        if run_dir_of is not None:
            write_rows = [r for r in all_rows if r["seed"] == seed]
            run_dir = run_dir_of(seed)
            run_dir.mkdir(parents=True, exist_ok=True)
            _write_metrics_csv(run_dir / "metrics.csv", write_rows)

    return AblationComparisonResult(
        experiment_id=experiment_id,
        seeds=seeds,
        steps=steps,
        tau=tau,
        arms=_summarise_arms(results, tau=tau),
    )


def _write_metrics_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """写 `<run>/metrics.csv`（键取并集，缺失留空；与 `run_artifacts` 同风格）。"""
    import csv

    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def comparison_payload(result: AblationComparisonResult) -> dict[str, Any]:
    """`results/tables/<experiment_id>_ablations.json` 的 payload。"""
    return {
        "experiment_id": result.experiment_id,
        "seeds": list(result.seeds),
        "steps": result.steps,
        "tau": result.tau,
        "n_agents": 1,
        "arms": list(result.arms),
    }


def table_path(experiment_id: str, root: str | Path) -> Path:
    """跨 seed 对照表路径 `results/tables/<experiment_id>_ablations.json`。"""
    return Path(root) / "tables" / f"{experiment_id}_ablations.json"


def write_comparison_table(result: AblationComparisonResult, path: str | Path) -> Path:
    """落 `results/tables/<id>_ablations.json`（schema `ablation_comparison.schema.json`）。"""
    import json

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(comparison_payload(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


__all__ = [
    "ARMS",
    "ARCH_ARMS",
    "BC_ARMS",
    "FULL_ARM",
    "AblationComparisonResult",
    "ArmResult",
    "active_edge_efficiency",
    "arm_overrides",
    "comparison_payload",
    "run_ablation_comparison",
    "table_path",
    "write_comparison_table",
]
