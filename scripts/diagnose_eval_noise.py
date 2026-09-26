# -*- coding: utf-8 -*-
"""评估噪声诊断：单次 episode 的排序可靠性，与达到目标可靠性所需的 K。

**为什么需要这个诊断**（2026-09-26）：代循环的 `F` 若由**单次** Arena episode
折算，则选择是在一个可靠性极低的分数上进行。实测（seed 1103，48 个体 × 11 个
独立 generation 下标）：

* 单次实现的排序可靠性 `rho_1 ≈ 0.069` —— 两个不同实现之间，个体排序的
  Spearman 相关几乎为 0（范围 −0.26~0.40）。即选择分数里约 **93% 是代特异噪声**。
* 同一个体换一个下标，其归一分数波动 SD ≈ 0.20、峰值可达 0.75，而选择分数的
  总跨度恰为 1 —— 噪声与整个选择差**同量级**。
* 下标还驱动一个系统性难度漂移：raw 复合分与下标显著负相关
  （斜率约 −0.66 raw/代，n=11，r ≈ −0.66，p ≈ 0.03）。

**结论**：单次评估下「选择」几乎无法产生正向响应（实测 3 复制 × 2 臂的
选择 − 漂变 = −0.0088，3/3 vs 0/3 完全分离，精确置换 p = 2/20 = 0.100，即
3v3 设计的理论下限；方向为负 = 选择噪声的典型表现）。修正在评估层：
`experiment/evolution_run.py` 的 `episodes_per_generation`（K 次独立实现取均值），
本脚本给出应选的 K。

用法::

    uv run python scripts/diagnose_eval_noise.py --seed 1103 --n-indices 11
"""

from __future__ import annotations

import argparse
import itertools
import math

import numpy as np

COMPONENT_NAMES = ("survival", "prey_capture", "escape_success", "energy_efficiency")


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman 秩相关（无并列修正，足够本诊断使用）。"""
    ra = np.argsort(np.argsort(np.asarray(a, dtype=float))).astype(float)
    rb = np.argsort(np.argsort(np.asarray(b, dtype=float))).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    denom = math.sqrt(float(ra @ ra) * float(rb @ rb))
    return 0.0 if denom == 0.0 else float(ra @ rb) / denom


def spearman_brown(rho_single: float, k: int) -> float:
    """K 次独立实现取均值后的可靠性（Spearman-Brown 预言公式）。"""
    if k < 1:
        raise ValueError("k 必须 >= 1")
    if rho_single <= 0.0:
        return 0.0
    return k * rho_single / (1.0 + (k - 1) * rho_single)


def required_k(rho_single: float, target: float, *, k_max: int = 5000) -> int | None:
    """达到 `target` 可靠性所需的最少实现数；不可达返回 None。"""
    for k in range(1, k_max + 1):
        if spearman_brown(rho_single, k) >= target:
            return k
    return None


def _normal_two_sided_p(t: float) -> float:
    """正态近似的双侧 p 值（避免引入 scipy）。"""
    return math.erfc(abs(t) / math.sqrt(2.0))


def build_panel(*, seed: int, indices, n_individuals: int):
    """把**同一个固定种群**依次放在每个下标下评估，返回 {下标: (掩码, 分量)}。"""
    from evogenesis.evolution.population import Individual
    from evogenesis.experiment.evolution_run import (
        _components_from_evaluation,
        to_chain_individuals,
    )
    from evogenesis.pipeline import initial_population, load_model_chain_config
    from evogenesis.pipeline.arena_episode import evaluate_population

    from evogenesis.arena.config import load_arena_config

    chain = load_model_chain_config()
    arena = load_arena_config()
    population = initial_population(
        master_seed=seed, experiment_id="evalnoise", n=n_individuals, layout=chain.layout
    )
    individuals = tuple(
        Individual(genome_id=c.genome_id, genome=c.genome, fish_id=c.fish_id) for c in population
    )
    chain_individuals = to_chain_individuals(individuals, experiment_id="evalnoise")
    panel = {}
    for generation in indices:
        evaluation = evaluate_population(
            chain_individuals,
            master_seed=seed,
            chain=chain,
            arena_config=arena,
            steps=None,
            generation=generation,
        )
        panel[int(generation)] = _components_from_evaluation(individuals, evaluation, arena)
    return panel


def _raw_and_normalized(components, weights, mask):
    matrix = np.stack([components[name] for name in COMPONENT_NAMES], axis=1).astype(float)
    weight_vector = np.array(
        [
            weights["survival"],
            weights["prey_capture"],
            weights["escape_success"],
            weights["energy_efficiency"],
        ]
    )
    raw = matrix @ weight_vector
    low, high = matrix.min(axis=0), matrix.max(axis=0)
    span = np.where(high - low > 0, high - low, 1.0)
    normalized = ((matrix - low) / span) @ weight_vector
    return raw, normalized, mask


def summarize(panel, weights) -> dict:
    """打印两张表并返回关键标量（趋势斜率与 r、单次可靠性、所需 K）。"""
    indices = sorted(panel)
    raws, normals = {}, {}
    for index in indices:
        mask, components = panel[index]
        raw, normalized, _ = _raw_and_normalized(components, weights, mask)
        raws[index] = raw[mask]
        normals[index] = normalized[mask]

    print(f"{'下标':>6}{'n':>5}{'raw均值':>11}{'raw SD':>10}{'raw极差':>11}")
    for index in indices:
        raw = raws[index]
        print(
            f"{index:>6}{raw.size:>5}{raw.mean():>11.3f}{raw.std(ddof=1):>10.3f}"
            f"{raw.max() - raw.min():>11.3f}"
        )

    x = np.array(indices, dtype=float)
    y = np.array([raws[index].mean() for index in indices])
    xc, yc = x - x.mean(), y - y.mean()
    slope = float(xc @ yc / (xc @ xc))
    r = float(xc @ yc / math.sqrt((xc @ xc) * (yc @ yc)))
    dof = len(indices) - 2
    t_stat = r * math.sqrt(dof / max(1e-12, 1.0 - r * r))
    print(
        f"\nraw 复合分对下标的线性趋势: 斜率 {slope:+.3f} raw/下标, r = {r:+.3f}, "
        f"n = {len(indices)}, 正态近似 p ≈ {_normal_two_sided_p(t_stat):.3f}"
    )

    pairs = [spearman(raws[a], raws[b]) for a, b in itertools.combinations(indices, 2)]
    rho1 = float(np.mean(pairs))
    print(
        f"\n单次实现的**排序可靠性** rho_1 = {rho1:.3f} "
        f"（{len(pairs)} 对下标平均 Spearman，范围 {min(pairs):+.3f} ~ {max(pairs):+.3f}）"
    )
    per_index_shift = np.mean(
        [
            np.abs(normals[index] - normals[indices[0]]).std(ddof=1)
            for index in indices[1:]
        ]
    )
    print(
        f"同一个体归一分数的扰动 SD ≈ {per_index_shift:.3f}"
        f"（选择分数的总跨度恒为 1 → 噪声与整个选择差同量级）"
    )

    if rho1 <= 0.0:
        # 可靠性不可能为负：非正估计是小面板的抽样伪影，须显式提示而非静默给 0。
        print(
            f"\n注意：rho_1 = {rho1:+.3f} <= 0 属小面板抽样伪影，本例仅 {len(pairs)} 对下标；"
            "请增大 --n-indices（完整 11 下标面板实测 rho_1 = 0.069）。"
        )
    print(f"\n{'K':>5}{'rho_K':>9}   备注")
    for k in (1, 2, 3, 5, 8, 10, 14, 20, 32, 50, 100):
        value = spearman_brown(rho1, k)
        note = " ← 当前配置" if k == 1 else ("  可用(>=0.5)" if value >= 0.5 else "")
        print(f"{k:>5}{value:>9.3f}{note}")
    for target in (0.5, 0.7, 0.8):
        print(f"达到 rho_K >= {target}: 需 K ≈ {required_k(rho1, target)} 个 episode/代")
    return {"rho_1": rho1, "slope": slope, "r": r}


def main() -> int:
    parser = argparse.ArgumentParser(description="评估噪声诊断（单次 episode 的排序可靠性）")
    parser.add_argument("--seed", type=int, default=1103)
    parser.add_argument("--n-indices", type=int, default=11)
    parser.add_argument("--n-individuals", type=int, default=48)
    parser.add_argument("--index-stride", type=int, default=1)
    parser.add_argument("--fitness-config", default="configs/evolution.yaml")
    args = parser.parse_args()

    from evogenesis.evolution.config import load_evolution_config

    weights = load_evolution_config(args.fitness_config).fitness_weights.model_dump()
    indices = [index * args.index_stride for index in range(args.n_indices)]
    print(
        f"固定种群 seed {args.seed}（{args.n_individuals} 个体）；"
        f"仅改 generation 下标：{indices}\n"
    )
    summarize(build_panel(seed=args.seed, indices=indices, n_individuals=args.n_individuals), weights)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
