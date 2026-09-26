"""Experiment E — Robustness：删边退化（owner：`experiment/实验与评价体系.md` §3.5）。

口径（§3.5，**草案待确认**）：不重发育/不重训练，只在**活跃支撑边** `support=A∧M` 上随机
清零 \(f\in\{0,5,10,20\}\%\) 的边；对照（\(f=0\)）与各删除组共用同一底物 \(W^{(0)}\) 与同一
arena 子种子。删边随机源 = `core §3` 的 `robustness` 命名空间（id=14），实体
\(t=\text{seed\_slot}\cdot|\text{fractions}|+\text{fraction\_index}\)。

**因变量（2026-09-27 实测修订）**：仅用 outcome 指标（survival / captures）区分力不足——
1 agent × 1 episode 下 survival 恒 1、captures 0–1、复合分近常数。故**主指标取「行为发散」**：
把控制网络在 Arena 里跑出的**同一 observation 序列**回放给删边网络，比较逐步动作
\(\overline{|\Delta\omega|},\overline{|\Delta v|}\)（开环、确定性、对被删边敏感）；outcome 指标
（§2.1 分量 + 复合分）作为**次要**证据并报。

本模块只编排：网络构造归 `pipeline`，指标口径归 `experiment/metrics.py`，Arena 驱动归
`pipeline/arena_episode.py`；不新造数值（fractions / seeds 来自 §3.5、§1.1）。
"""

from __future__ import annotations

import copy
import statistics
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import torch

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.env import DanioArena
from evogenesis.connectome.danionet import DanioNet
from evogenesis.core.seed import SeedManager
from evogenesis.evolution.config import load_evolution_config
from evogenesis.experiment.metrics import (
    SCALAR_METRICS,
    episode_metrics,
    summarise_over_seeds,
)
from evogenesis.pipeline import (
    ChainIndividual,
    ModelChainConfig,
    arena_seeds_for,
    danionet_of,
    drive_arena_with_ids,
    initial_population,
    motif_catalog,
    phenotypes_of,
)

#: §3.5 定稿的删边比例 + 对照（0.0，用于算 \(\Delta\)）
FRACTIONS: tuple[float, ...] = (0.0, 0.05, 0.10, 0.20)
#: `core §3` 的删边随机源命名空间
ROBUSTNESS_NAMESPACE = "robustness"
#: 每 seed 候选个体数（实测：首个 viable 与 12 一致；48 基本消除「无 viable」空底物）
DEFAULT_N_DANIO = 48
#: 行为发散的两个分量名（主指标）
DIVERGENCE_METRICS: tuple[str, ...] = ("mean_abs_omega", "mean_abs_v")
#: 求 rel 退化时的分母下限（避免除零；`|m(0)| ≤ eps` 时只报绝对差）
_REL_EPS = 1e-12


def dropped_edge_count(n_edges: int, fraction: float) -> int:
    """删边条数 \(k=\mathrm{round}(f\cdot n)\)，并夹到 ``[0, n]``。"""
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(f"fraction 须落在 [0,1]，得到 {fraction}")
    if n_edges < 0:
        raise ValueError(f"n_edges 必须非负，得到 {n_edges}")
    return min(n_edges, int(round(fraction * n_edges)))


def drop_edges(net: DanioNet, fraction: float, *, rng: np.random.Generator) -> int:
    """在 ``net``（batch=1）的活跃支撑上**无放回**清零 ``fraction`` 比例的边；返回删除条数。

    删除方式：把选中边的 `support` / `support_sign0` / `support_f32` 与 `weights0` 置 0，
    使有效权重（约束/非约束路径）在该处恒为 0；其余权重与 \(W^{(0)}\) 逐元素不变。
    """
    with torch.no_grad():
        support = net.support[0]
        coords = torch.nonzero(support, as_tuple=False)
        n_edges = int(coords.shape[0])
        k = dropped_edge_count(n_edges, fraction)
        if k == 0:
            return 0
        pick = rng.choice(n_edges, size=k, replace=False)
        sel = coords[torch.as_tensor(pick, dtype=torch.long, device=coords.device)]
        rows, cols = sel[:, 0], sel[:, 1]
        net.support[0, rows, cols] = False
        net.support_sign0[0, rows, cols] = 0.0
        net.support_f32[0, rows, cols] = 0.0
        net.weights0[0, rows, cols] = 0.0
    return k


def _first_viable(
    population: Sequence[ChainIndividual], phenotypes: Sequence[Any]
) -> tuple[ChainIndividual, Any] | None:
    for individual, phenotype in zip(population, phenotypes, strict=True):
        if phenotype.viable:
            return individual, phenotype
    return None


def _control_rollout(
    net: DanioNet,
    individual: ChainIndividual,
    *,
    master_seed: int,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    steps: int,
    generation: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any], tuple]:
    """控制网络跑一局 Arena，返回 ``(obs 序列 (T,12), 动作 (T,2), per_fish, events)``。

    obs 序列与动作序列用于「同一 obs 回放」计算行为发散；per_fish/events 供 outcome 指标。
    """
    config = replace(arena_config, population=replace(arena_config.population, n_fish=1))
    spawn_seed, dynamics_seed = arena_seeds_for(master_seed, generation)
    arena = DanioArena(
        config,
        spawn_seed=spawn_seed,
        dynamics_seed=dynamics_seed,
        fish_ids=[individual.fish_id],
        genome_ids=[individual.genome_id],
        generation=generation,
    )
    arena.reset()
    observations: list[np.ndarray] = []
    actions: list[tuple[float, float]] = []
    for _ in range(steps):
        if not arena.fish[individual.fish_id].alive:
            break
        observation = np.asarray(arena.observe(individual.fish_id), dtype=np.float32)
        with torch.no_grad():
            omega, v = net.step(observation[None, :])
        action = (float(omega[0]), float(v[0]))
        observations.append(observation)
        actions.append(action)
        if arena.step({individual.fish_id: action}).done:
            break
    return (
        np.asarray(observations, dtype=np.float32),
        np.asarray(actions, dtype=np.float32),
        arena.per_fish_log(),
        tuple(arena.events),
    )


def _replay_divergence(
    observations: np.ndarray, control_actions: np.ndarray, net: DanioNet
) -> dict[str, float]:
    """把控制网络的 obs 序列回放给 ``net``，返回逐步动作发散 ``(mean|Δω|, mean|Δv|)``。"""
    net.reset()
    replayed: list[tuple[float, float]] = []
    with torch.no_grad():
        for step in range(observations.shape[0]):
            omega, v = net.step(observations[step][None, :])
            replayed.append((float(omega[0]), float(v[0])))
    damaged = np.asarray(replayed, dtype=np.float32)
    delta = np.abs(damaged - control_actions).mean(axis=0)
    return {
        "mean_abs_omega": float(delta[0]),
        "mean_abs_v": float(delta[1]),
        "n_steps": int(damaged.shape[0]),
    }


def _degradation(per_seed: dict[str, Any], fractions: Sequence[float]) -> dict[str, Any]:
    """按 seed 对 \(f=0\) 取差，再跨 seed 汇总 outcome 指标的 ``mean_abs`` / ``mean_rel``。"""
    out: dict[str, Any] = {}
    for fraction in fractions:
        if fraction == 0.0:
            continue
        per_metric: dict[str, Any] = {}
        for metric in SCALAR_METRICS:
            diffs: list[float] = []
            rels: list[float] = []
            for entry in per_seed.values():
                conds = {c["fraction"]: c["metrics"] for c in entry["conditions"]}
                if 0.0 not in conds or fraction not in conds:
                    continue
                base = conds[0.0].get(metric)
                cur = conds[fraction].get(metric)
                if base is None or cur is None:
                    continue
                diffs.append(cur - base)
                if abs(base) > _REL_EPS:
                    rels.append((cur - base) / abs(base))
            per_metric[metric] = {
                "mean_abs": statistics.fmean(diffs) if diffs else None,
                "mean_rel": statistics.fmean(rels) if rels else None,
                "n": len(diffs),
            }
        out[f"{fraction:g}"] = per_metric
    return out


def run_robustness(
    *,
    experiment_id: str,
    seeds: Sequence[int],
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    fractions: Sequence[float] = FRACTIONS,
    n_danio: int = DEFAULT_N_DANIO,
    steps: int | None = None,
    device: str = "cpu",
) -> dict[str, Any]:
    """跑 Experiment E：每 seed 取首个 viable 底物，逐删边比例评估（行为发散为主 + outcome）。"""
    if n_danio < 1:
        raise ValueError(f"n_danio 必须 ≥ 1，得到 {n_danio}")
    steps_used = arena_config.world.episode_steps if steps is None else int(steps)
    weights = load_evolution_config().fitness_weights.model_dump()

    per_seed: dict[str, Any] = {}
    rows_outcome: dict[str, list[dict[str, Any]]] = {f"{f:g}": [] for f in fractions}
    rows_divergence: dict[str, list[dict[str, Any]]] = {f"{f:g}": [] for f in fractions}
    for slot, seed in enumerate(seeds):
        population = initial_population(
            master_seed=seed, experiment_id=experiment_id, n=n_danio, layout=chain.layout
        )
        motifs = motif_catalog(seed, chain.layout)
        phenotypes = phenotypes_of(
            population, motifs, master_seed=seed, config=chain.rgcd, device=device
        )
        picked = _first_viable(population, phenotypes)
        if picked is None:
            per_seed[str(seed)] = {
                "substrate": None,
                "n_edges": None,
                "conditions": [],
                "note": f"n_danio={n_danio} 内无 viable 个体",
            }
            continue
        individual, phenotype = picked
        net0 = danionet_of(
            [phenotype],
            master_seed=seed,
            config=chain.network,
            device=device,
            sign_constrained=True,
        )
        observations, control_actions, _, _ = _control_rollout(
            net0,
            individual,
            master_seed=seed,
            chain=chain,
            arena_config=arena_config,
            steps=steps_used,
            generation=0,
        )
        conditions: list[dict[str, Any]] = []
        for fraction_index, fraction in enumerate(fractions):
            net = copy.deepcopy(net0)
            rng = SeedManager(seed).spawn_rng(
                ROBUSTNESS_NAMESPACE, slot * len(fractions) + fraction_index
            )
            removed = drop_edges(net, fraction, rng=rng)
            divergence = _replay_divergence(observations, control_actions, net)
            episode = drive_arena_with_ids(
                fish_ids=[individual.fish_id],
                genome_ids=[individual.genome_id],
                net=net,
                master_seed=seed,
                chain=chain,
                arena_config=arena_config,
                steps=steps_used,
                generation=0,
            )
            metrics = episode_metrics(
                episode.per_fish[individual.fish_id],
                episode_steps=steps_used,
                e_max=arena_config.energy.e_max,
                capture_success_prob=arena_config.growth.capture_success_prob,
                weights=weights,
            )
            conditions.append(
                {
                    "fraction": fraction,
                    "n_removed": removed,
                    "metrics": metrics,
                    "divergence": divergence,
                }
            )
            rows_outcome[f"{fraction:g}"].append({"seed": seed, **metrics})
            rows_divergence[f"{fraction:g}"].append({"seed": seed, **divergence})
        per_seed[str(seed)] = {
            "substrate": {"genome_id": individual.genome_id, "fish_id": individual.fish_id},
            "n_edges": int(net0.support.sum().item()),
            "conditions": conditions,
            "note": None,
        }

    behavior_divergence = {
        key: summarise_over_seeds(rows, metrics=DIVERGENCE_METRICS)
        for key, rows in rows_divergence.items()
    }
    return {
        "kind": "robustness",
        "experiment_id": experiment_id,
        "generated_by": "experiment/robustness_run.py::run_robustness",
        "status": "草案待确认",
        "seeds": list(seeds),
        "fractions": list(fractions),
        "n_danio": n_danio,
        "steps": steps_used,
        "metrics": list(SCALAR_METRICS),
        "per_seed": per_seed,
        "aggregate": {
            key: summarise_over_seeds(rows, metrics=SCALAR_METRICS)
            for key, rows in rows_outcome.items()
        },
        "behavior_divergence": behavior_divergence,
        "degradation": _degradation(per_seed, fractions),
    }


def table_path(experiment_id: str, root: str | Path) -> Path:
    """跨 seed 产物路径 `results/tables/<experiment_id>_robustness.json`。"""
    return Path(root) / "tables" / f"{experiment_id}_robustness.json"


__all__ = [
    "DEFAULT_N_DANIO",
    "DIVERGENCE_METRICS",
    "FRACTIONS",
    "ROBUSTNESS_NAMESPACE",
    "drop_edges",
    "dropped_edge_count",
    "run_robustness",
    "table_path",
]
