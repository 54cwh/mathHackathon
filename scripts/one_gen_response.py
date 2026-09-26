# -*- coding: utf-8 -*-
"""单代响应实验：K 平均是否让「选一次」真的产生遗传改进。

设计：对同一 master seed，**亲代与子代都在同一组 K 个 episode 下标上打分**
（固定标尺 ⇒ 配对比较），比较

    Delta = mean(raw 复合分 | 子代) - mean(raw 复合分 | 亲代)

在 K=1（rho~0.069）与 K=K 下的差异。相比 20 代轨迹，本设计成本低一个数量级，
因而可上更多种子做严格的精确置换检验。

用法::

    uv run python scripts/one_gen_response.py --seed 1103 --episodes 8
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import evogenesis.experiment.evolution_run as er
from evogenesis.arena.config import load_arena_config
from evogenesis.evolution.config import load_evolution_config
from evogenesis.evolution.population import Individual
from evogenesis.pipeline import initial_population, load_model_chain_config
from evogenesis.pipeline.arena_episode import evaluate_population

KEYS = ("survival", "prey_capture", "escape_success", "energy_efficiency")
WEIGHT_VECTOR = np.array([0.35, 0.25, 0.20, 0.20])


def _score(inds, indices, seed, experiment_id, chain, arena):
    """在给定的一组 episode 下标上评估，返回 (逐个体均值 raw, 逐个体 viable)。"""
    chain_individuals = er.to_chain_individuals(inds, experiment_id=experiment_id)
    raws, masks, evaluations = [], [], []
    for generation in indices:
        evaluation = evaluate_population(
            chain_individuals,
            master_seed=seed,
            chain=chain,
            arena_config=arena,
            steps=None,
            generation=generation,
        )
        # 必须传**已铸 fish_id 的 chain 个体**（子代 Individual 的 fish_id 为 None）
        mask, components = er._components_from_evaluation(chain_individuals, evaluation, arena)
        matrix = np.stack([components[k] for k in KEYS], axis=1).astype(float)
        raws.append(matrix @ WEIGHT_VECTOR)
        masks.append(mask)
        evaluations.append(evaluation)
    return np.mean(raws, axis=0), np.any(masks, axis=0), chain_individuals, evaluations


def run(seed: int, episodes: int, population: int) -> dict:
    chain = load_model_chain_config()
    arena = load_arena_config()
    evolution_config = load_evolution_config(
        "configs/evolution.yaml", overrides={"population_size": population}
    )
    experiment_id = f"oneResp-s{seed}"
    layout = chain.layout
    found = initial_population(
        master_seed=seed, experiment_id=experiment_id, n=population, layout=layout
    )
    parents_in = tuple(
        Individual(genome_id=c.genome_id, genome=c.genome, fish_id=c.fish_id) for c in found
    )
    indices = tuple(range(episodes))  # 亲代与子代共用同一组环境 ⇒ 固定标尺
    parent_raw, parent_ok, chain_parents, parent_evals = _score(
        parents_in, indices, seed, experiment_id, chain, arena
    )
    weights = evolution_config.fitness_weights.model_dump()
    if episodes == 1:
        parents = er.assemble_individuals(
            chain_parents, parent_evals[0], arena_config=arena, weights=weights
        )
    else:
        parents = er.assemble_individuals_averaged(
            chain_parents, parent_evals, arena_config=arena, weights=weights
        )
    advanced = er.advance_generation(
        parents,
        experiment_id=experiment_id,
        generation=1,
        seed_manager=er.SeedManager(seed),
        config=evolution_config,
        layout=layout,
    )
    if not advanced.success:
        return {"seed": seed, "episodes": episodes, "ok": False, "event": advanced.event}
    offspring_raw, offspring_ok, _, _ = _score(
        advanced.offspring, indices, seed, experiment_id + "-g1", chain, arena
    )
    parent_mean = float(parent_raw[parent_ok].mean())
    offspring_mean = float(offspring_raw[offspring_ok].mean())
    return {
        "seed": seed,
        "episodes": episodes,
        "ok": True,
        "n_viable_parent": int(parent_ok.sum()),
        "n_viable_offspring": int(offspring_ok.sum()),
        "parent_mean": parent_mean,
        "offspring_mean": offspring_mean,
        "delta": offspring_mean - parent_mean,
        "n_selected_parents": len(advanced.selected_parent_ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="单代响应实验（K 平均 vs 单次实现）")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--episodes", type=int, default=8)
    parser.add_argument("--population", type=int, default=48)
    parser.add_argument("--out-dir", default="results/tmp/onegen")
    args = parser.parse_args()
    record = run(args.seed, args.episodes, args.population)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"s{args.seed}-K{args.episodes}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
