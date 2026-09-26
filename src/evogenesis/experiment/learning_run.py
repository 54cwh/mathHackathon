"""BC 生命周期学习编排（`experiment §3.8/§5.3`；`learning §1–§6`）。

把「Stage 1 专家轨迹 → Stage 2 逐个体训练自己的 `DanioNet` → **训练前后同一局评估** →
**非遗传证据**」串成可执行 run。owner：`experiment/实验与评价体系.md` §3.8。本模块只编排，
不定义算法/数值：训练契约 `learning §3`、发育与 viability `RGCD §7`、DanioNet→Arena 驱动
`pipeline §4`、run 布局 `experiment §5.1`。

非遗传证据（`learning §4` 定稿）：训练只改运行时 `Θ`；训练后**重新发育同一 genome** 得到的
新网络必须 `ΔW=0`（回到 `W⁰`），且其 `W⁰` 与训练用网络逐元素相同——据此证明 `ΔW` 未进入
遗传通路。本模块 `noninheritance` 字段给出该判据的实测值。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch

from evogenesis.arena.config import ArenaConfig
from evogenesis.core.config import LearningConfig, ModelConfig, load_config
from evogenesis.core.seed import SeedManager
from evogenesis.evolution.config import load_evolution_config
from evogenesis.evolution.reproduction import gamete_seed_index
from evogenesis.experiment.metrics import episode_metrics
from evogenesis.learning.data import TrajectoryDataset, load_trajectories
from evogenesis.learning.report import TrainingReport, build_report
from evogenesis.learning.train import TrainResult, train_bc
from evogenesis.pipeline import (
    ArenaEpisodeResult,
    ChainIndividual,
    ModelChainConfig,
    danionet_of,
    drive_arena_with_net,
    initial_population,
    motif_catalog,
    phenotypes_of,
)

#: 轨迹文件名模式（`core §4.5`：`trajectories/episode_<episode_id>.jsonl`）
TRAJECTORY_GLOB = "episode_*.jsonl"


@dataclass(frozen=True)
class NonInheritanceEvidence:
    """`ΔW` 不入遗传通路的实测判据（`learning §4`）。"""

    fresh_delta_w_max_abs: float  # 重新发育同 genome 的网络 `max|ΔW|`（须为 0）
    weights0_max_abs_diff: float  # 训练网络与新鲜网络的 `W⁰` 最大逐元素差（须为 0）


@dataclass(frozen=True)
class LifetimeLearningResult:
    """一次生命周期学习 run 的结果（供编排层落盘）。"""

    n_individuals: int
    viable_indices: tuple[int, ...]
    viable_individuals: tuple[ChainIndividual, ...]
    pre: ArenaEpisodeResult | None
    post: ArenaEpisodeResult | None
    train_results: tuple[TrainResult, ...]
    reports: tuple[TrainingReport, ...]
    delta_w_norm: tuple[float, ...]  # 逐 viable 个体 `max|ΔW|`
    noninheritance: NonInheritanceEvidence | None
    sign_constrained: bool

    @property
    def n_viable(self) -> int:
        return len(self.viable_indices)

    @property
    def mean_final_loss(self) -> float:
        if not self.train_results:
            return 0.0
        return sum(r.final_loss for r in self.train_results) / len(self.train_results)


def load_learning_config(path: str | Path | None = None) -> LearningConfig:
    """读 `configs/default_model.yaml::learning`（`core §config`）。

    `learning` 参数无冻结镜像（`LearningConfig` 字段均必填），故 `path=None` 显式报错——
    与 `core §0` 一致（`path=None` 不套用 env/overrides，且此处无默认值可返回）。
    """
    if path is None:
        raise ValueError("learning 无内置默认值，必须提供 config 文件（core §7）")
    return load_config(path, model=ModelConfig).learning


def _train_one(
    individual: ChainIndividual,
    phenotype,
    dataset: TrajectoryDataset,
    cfg: LearningConfig,
    *,
    master_seed: int,
    n_individuals: int,
    chain: ModelChainConfig,
    device: str,
    sign_constrained: bool,
) -> tuple[torch.Tensor, TrainResult]:
    """训练单个体自己的 `DanioNet`，返回 (训练后 `θ` 副本, 训练结果)。

    训练粒度（`learning §1`）：逐个体现构造 batch=1 网络、只更新其 `Θ`。BC 采样序号
    `t = generation*N + index`（`learning §3`：与配子级同规则，`core §3`）。
    """
    net = danionet_of(
        [phenotype],
        master_seed=master_seed,
        config=chain.network,
        device=device,
        sign_constrained=sign_constrained,
    )
    result = train_bc(
        net,
        dataset,
        cfg,
        seed_manager=SeedManager(master_seed),
        seed_index=gamete_seed_index(individual.genome_id, population_size=n_individuals),
        device=device,
        sign_constrained=sign_constrained,
    )
    return net.theta.detach().clone(), result


def run_lifetime_learning(
    *,
    experiment_id: str,
    master_seed: int,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    learning_config: LearningConfig,
    trajectories_dir: str | Path,
    generation: int = 0,
    n: int = 12,
    steps: int | None = None,
    sign_constrained: bool = True,
    device: str = "cpu",
) -> LifetimeLearningResult:
    """跑一次 BC 生命周期学习（`experiment §3.8`）：采集→训练→前后对照→非遗传证据。

    每条轨迹只记录 1 条受控鱼（`learning §2`），全部作训练集；`steps=None` 取
    `world.episode_steps`。`n` 为当代个体数（默认 12 = `ExpertPolicy` pre-check 规模，
    `experiment §4`）。
    """
    population = initial_population(
        master_seed=master_seed,
        experiment_id=experiment_id,
        n=n,
        layout=chain.layout,
    )
    motifs = motif_catalog(master_seed, chain.layout)
    phenotypes = phenotypes_of(
        population, motifs, master_seed=master_seed, config=chain.rgcd, device=device
    )
    viable_indices = tuple(i for i, p in enumerate(phenotypes) if p.viable)
    viable_individuals = tuple(population[i] for i in viable_indices)
    viable_phenotypes = [phenotypes[i] for i in viable_indices]
    if not viable_indices:
        return LifetimeLearningResult(
            n_individuals=n,
            viable_indices=(),
            viable_individuals=(),
            pre=None,
            post=None,
            train_results=(),
            reports=(),
            delta_w_norm=(),
            noninheritance=None,
            sign_constrained=sign_constrained,
        )

    trajectory_paths = sorted(Path(trajectories_dir).glob(TRAJECTORY_GLOB))
    if not trajectory_paths:
        raise ValueError(f"{trajectories_dir} 下无 {TRAJECTORY_GLOB} 轨迹，无法训练（§3）")
    dataset = load_trajectories(trajectory_paths)

    # 训练前：同一批 arena 子种子（generation）下评估未训练网络
    eval_net = danionet_of(
        viable_phenotypes,
        master_seed=master_seed,
        config=chain.network,
        device=device,
        sign_constrained=sign_constrained,
    )
    pre = drive_arena_with_net(
        viable_individuals,
        eval_net,
        master_seed=master_seed,
        chain=chain,
        arena_config=arena_config,
        steps=steps,
        generation=generation,
    )

    # 逐个体训练自己的 DanioNet
    thetas: list[torch.Tensor] = []
    train_results: list[TrainResult] = []
    reports: list[TrainingReport] = []
    for individual, phenotype in zip(viable_individuals, viable_phenotypes, strict=True):
        theta, result = _train_one(
            individual,
            phenotype,
            dataset,
            learning_config,
            master_seed=master_seed,
            n_individuals=n,
            chain=chain,
            device=device,
            sign_constrained=sign_constrained,
        )
        thetas.append(theta)
        train_results.append(result)
        # 报告按**逐个体单网络**生成（`learning §4`）：`flip_rate`/谱半径是该个体的量，
        # 不能对批量网络池化后再分发给每个个体。
        single = danionet_of(
            [phenotype],
            master_seed=master_seed,
            config=chain.network,
            device=device,
            sign_constrained=sign_constrained,
        )
        with torch.no_grad():
            single.theta.data[0].copy_(theta[0])
        reports.append(build_report(single, result))

    # 训练后：把逐个体 Θ 注入批量网络（W⁰/支撑/先验与单个体构造一致，见 connectome §3），
    # 在同一批 arena 子种子与同一网络对象上复评，保证「训练前后」仅有 Θ 不同。
    with torch.no_grad():
        for slot, theta in enumerate(thetas):
            eval_net.theta.data[slot].copy_(theta[0])

    post = drive_arena_with_net(
        viable_individuals,
        eval_net,
        master_seed=master_seed,
        chain=chain,
        arena_config=arena_config,
        steps=steps,
        generation=generation,
    )

    with torch.no_grad():
        delta_w_norm = tuple(
            float(eval_net.delta_weights[slot].abs().max())
            for slot in range(len(viable_individuals))
        )

    # 非遗传取证（`learning §4`）：**重新发育同一 genome** → 新 `W⁰` 必须与训练用网络逐元素相同，
    # 且新网络 `ΔW = 0`（Θ 初值 = softplus⁻¹|W⁰|，由构造保证）。判别力在 `W⁰` 复现——它检验
    # `genome → q(G) → 发育 → DanioNet` 全链确定性；`ΔW` 只存在于运行时 `Θ`，不写入 genome。
    fresh_phenotypes = phenotypes_of(
        viable_individuals,
        motifs,
        master_seed=master_seed,
        config=chain.rgcd,
        device=device,
    )
    fresh = danionet_of(
        fresh_phenotypes,
        master_seed=master_seed,
        config=chain.network,
        device=device,
        sign_constrained=sign_constrained,
    )
    with torch.no_grad():
        evidence = NonInheritanceEvidence(
            fresh_delta_w_max_abs=float(fresh.delta_weights.abs().max()),
            weights0_max_abs_diff=float((fresh.weights0 - eval_net.weights0).abs().max()),
        )

    return LifetimeLearningResult(
        n_individuals=n,
        viable_indices=viable_indices,
        viable_individuals=viable_individuals,
        pre=pre,
        post=post,
        train_results=tuple(train_results),
        reports=tuple(reports),
        delta_w_norm=delta_w_norm,
        noninheritance=evidence,
        sign_constrained=sign_constrained,
    )


def metric_rows(
    result: LifetimeLearningResult,
    *,
    seed: int,
    episode_steps: int,
    arena_config: ArenaConfig,
    generation: int = 0,
) -> list[dict]:
    """把训练前 / 训练后逐个体指标摊平成 `metrics.csv` 行（`experiment §5.1`）。"""
    weights = load_evolution_config().fitness_weights.model_dump()
    rows: list[dict] = []
    for phase, episode in (("pre", result.pre), ("post", result.post)):
        if episode is None:
            continue
        for fish_id, rec in sorted(episode.per_fish.items()):
            rows.append(
                {
                    "seed": seed,
                    "generation": generation,
                    "phase": phase,
                    "fish_id": fish_id,
                    **episode_metrics(
                        rec,
                        episode_steps=episode_steps,
                        e_max=arena_config.energy.e_max,
                        capture_success_prob=arena_config.growth.capture_success_prob,
                        weights=weights,
                    ),
                }
            )
    return rows


def learning_records(result: LifetimeLearningResult) -> list[dict]:
    """逐 viable 个体一行的学习记录（`learning.jsonl`，`experiment §5.1`）。"""
    records: list[dict] = []
    for slot, individual in enumerate(result.viable_individuals):
        report = result.reports[slot]
        train = result.train_results[slot]
        records.append(
            {
                "fish_id": individual.fish_id,
                "genome_id": individual.genome_id,
                "sign_constrained": result.sign_constrained,
                "final_loss": train.final_loss,
                "n_updates": report.n_updates,
                "epochs": report.epochs,
                "coverage_steps": report.coverage_steps,
                "visible_steps": report.visible_steps,
                "flip_rate": report.flip_rate,
                "spectral_radius": report.spectral_radius[0],
                "delta_w_norm": result.delta_w_norm[slot],
                "loss_weight_omega": train.loss_weights.omega,
                "loss_weight_v": train.loss_weights.v,
            }
        )
    return records


def learning_summary(result: LifetimeLearningResult, *, seed: int) -> dict:
    """`learning.jsonl` 的 seed 级汇总（`seed_summary.json` 的 `learning` 段）。"""
    return {
        "seed": seed,
        "sign_constrained": result.sign_constrained,
        "n_individuals": result.n_individuals,
        "n_viable": result.n_viable,
        "mean_final_loss": result.mean_final_loss,
        "mean_epochs": (
            sum(r.epochs for r in result.reports) / len(result.reports) if result.reports else 0.0
        ),
        "mean_delta_w_norm": (
            sum(result.delta_w_norm) / len(result.delta_w_norm) if result.delta_w_norm else 0.0
        ),
        "noninheritance": (
            None
            if result.noninheritance is None
            else {
                "fresh_delta_w_max_abs": result.noninheritance.fresh_delta_w_max_abs,
                "weights0_max_abs_diff": result.noninheritance.weights0_max_abs_diff,
            }
        ),
    }


__all__ = [
    "TRAJECTORY_GLOB",
    "LifetimeLearningResult",
    "NonInheritanceEvidence",
    "learning_records",
    "learning_summary",
    "load_learning_config",
    "metric_rows",
    "run_lifetime_learning",
]
