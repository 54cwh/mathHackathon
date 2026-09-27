"""代循环编排（owner：`experiment/代循环编排.md`）。

把「评估一代 → 折算 `F` → 回填 `Individual` → `advance_generation` → 下一代」串成可执行循环。
本模块只做编排：分量口径归 `experiment/metrics.py` 与 `evolution §6`，选择/繁殖算法归
`evolution`，发育/viability 归 `development`，Arena 驱动归 `pipeline`。
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field, replace
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
from evogenesis.experiment.events import write_episode_log
from evogenesis.experiment.metrics import (
    energy_efficiency,
)
from evogenesis.experiment.run_artifacts import (
    individual_metric_rows,
    write_seed_artifacts,
)
from evogenesis.genome.genome import architecture, expression_A, expression_B
from evogenesis.pipeline.arena_episode import (
    PopulationEvaluation,
    arena_seeds_for,
    evaluate_population,
)
from evogenesis.pipeline.model_chain import (
    ChainIndividual,
    ModelChainConfig,
    initial_population,
    motif_catalog,
)

#: 四类架构档（`genome §3`）。
_PHENOTYPE_CLASSES = ("A_B_", "A_bb", "aaB_", "aabb")


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
    p_A: float = 0.0
    p_B: float = 0.0
    phenotype_freq: dict = field(default_factory=dict)
    mean_neuron: float = 0.0
    mean_edge: float = 0.0
    mean_tau: float = 0.0


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


def _components_from_evaluation(
    individuals: tuple[ChainIndividual, ...],
    evaluation: PopulationEvaluation,
    arena_config: ArenaConfig,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """单次 episode 实现 → (viable 掩码, 四分量原始量)。

    非 viable 个体的分量记 0（由 `composite_fitness` 的掩码处理）；存活步数为 0 的
    个体 `energy_efficiency` 记 0（`metrics.energy_efficiency` §2.1 的定义域要求
    `T_i > 0`）。
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
    return mask, components


def assemble_individuals(
    individuals: tuple[ChainIndividual, ...],
    evaluation: PopulationEvaluation,
    *,
    arena_config: ArenaConfig,
    weights: dict[str, float],
    fitness_mode: str = "minmax",
    fitness_floor: float = 1e-3,
    drift_seed: int | None = None,
) -> tuple[Individual, ...]:
    """按 `代循环编排.md` §3 把评估结果折算为选择用 `F` 并回填 `Individual`。

    分量取**原始量**（`survival_steps` / `captures` / `escape_successes` / `energy_efficiency`），
    对齐全长；non-viable 置 0（由 `composite_fitness` 的掩码处理）。存活步数为 0 的个体
    `energy_efficiency` 记 0（函数定义域要求 `T_i>0`）。

    `fitness_mode` 决定喂给选择机制的分数（见 `_selection_score`）：``minmax`` 为
    `evolution §6` 现状；``drop_degenerate`` / ``drift`` 为 2026-09-26 引入的实验臂。
    """
    mask, components = _components_from_evaluation(individuals, evaluation, arena_config)
    fitness = _selection_score(
        components,
        viable=mask,
        weights=weights,
        mode=fitness_mode,
        floor=fitness_floor,
        drift_seed=drift_seed,
    )
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


def generation_episode_indices(generation: int, episodes_per_generation: int) -> tuple[int, ...]:
    """第 `generation` 代使用的 K 个 episode 下标：`generation*K + k, k=0..K-1`。

    `K=1` 时退化为 `(generation,)`，即与旧行为**逐字节一致**。各代的索引区间互不
    相交，故 K 次实现互相独立，且不同代不会重复同一次实现 —— 这是把「环境实现」
    与「代数」解耦的关键：旧实现下同一个体在 gen `g` 的分数含 `g` 特异噪声，
    实测排序可靠性仅 `rho_1 = 0.069`。
    """
    k_episodes = max(1, int(episodes_per_generation))
    return tuple(generation * k_episodes + k for k in range(k_episodes))


def assemble_individuals_averaged(
    individuals: tuple[ChainIndividual, ...],
    evaluations: tuple[PopulationEvaluation, ...],
    *,
    arena_config: ArenaConfig,
    weights: dict[str, float],
    fitness_mode: str = "minmax",
    fitness_floor: float = 1e-3,
    drift_seed: int | None = None,
) -> tuple[Individual, ...]:
    """K 次独立 episode 实现后折算 `F`：**分量取 K 次均值**，viable 取并集。

    2026-09-26 诊断：单次 episode 的**排序可靠性**实测仅 `rho_1 = 0.069`
    （固定种群 × 11 个独立下标的面板；见 `results/tmp/reliability.py`），即选择分数里
    约 93% 是代特异噪声 —— 这解释了「3 复制 × 2 臂」（选择 vs 漂变）为何测不到正向
    响应。按 Spearman-Brown，K 次平均把可靠性抬到 `K*rho_1 / (1 + (K-1)*rho_1)`：
    `K=14 → 0.53`、`K=32 → 0.69`、`K=50 → 0.79`。

    分量语义与 `K=1` 一致：每次实现中非 viable 记 0，再对 K 次取均值，即**期望口径**
    （`E[survival]` / `E[captures]` / ...），故「偶尔死亡」按死亡频率自然折价。
    viable 取**并集**：个体在任一实现中通过即计入；正式配置下发育通过率实测为 100%，
    故与交集口径等价。
    """
    if not evaluations:
        raise ValueError("evaluations 不能为空")
    parts = [
        _components_from_evaluation(individuals, evaluation, arena_config)
        for evaluation in evaluations
    ]
    mask = np.zeros(len(individuals), dtype=bool)
    for part_mask, _ in parts:
        mask |= part_mask
    components: dict[str, np.ndarray] = {
        name: np.mean([part[1][name] for part in parts], axis=0).astype(np.float32)
        for name in ("survival", "prey_capture", "escape_success", "energy_efficiency")
    }
    fitness = _selection_score(
        components,
        viable=mask,
        weights=weights,
        mode=fitness_mode,
        floor=fitness_floor,
        drift_seed=drift_seed,
    )
    out: list[Individual] = []
    for index, chain_individual in enumerate(individuals):
        viable = bool(mask[index])
        reason = None
        if not viable:
            for evaluation, (part_mask, _) in zip(evaluations, parts, strict=True):
                if not part_mask[index]:
                    reason = evaluation.phenotypes[index].viability_reason
                    break
        out.append(
            Individual(
                genome_id=chain_individual.genome_id,
                genome=chain_individual.genome,
                fish_id=chain_individual.fish_id if viable else None,
                fitness=float(fitness[index]),
                viable=viable,
                failure_reason=reason,
            )
        )
    return tuple(out)


def _selection_score(
    components: Mapping[str, np.ndarray],
    *,
    viable: np.ndarray,
    weights: Mapping[str, float],
    mode: str,
    floor: float,
    drift_seed: int | None,
) -> np.ndarray:
    """选择用 `F` 的三种口径（仅实验用；默认 `minmax` 即 `evolution §6` 现状）。

    - ``minmax``：逐分量代内 min-max 后加权（`evolution/fitness.py::composite_fitness`，现状）。
    - ``drop_degenerate``：同上，但**剔除代内跨度 < ``floor`` 的退化分量**，权重按剩余分量重分。
      动机（2026-09-26 seed 1103 实测）：分量是原始量、量纲差极大（存活步数 0--600 / 捕获计数 /
      逃逸计数 / ``energy_efficiency`` 约 1e-3），min-max 的**意图**是拉齐量纲，但它无法区分
      「有意义的变异」与「噪声级变异」——两者都映射到满 ``[0,1]``。实测 ``energy_efficiency``
      代内跨度仅 7.1e-04（噪声级）却被放大并保留 0.20 权重，即约 1/5 选择压力是噪声；
      默认口径下 20 代无适应度上升、``prey_capture`` 反降 48%。
    - ``drift``：**漂变对照**——用与适应度无关的确定性伪随机分数（本臂专用的本地 rng，
      不占用 `core §3` 的命名空间），使同一套选择机制退化为随机抽样；用于排除
      「上升来自环境漂移」这一竞争解释。
    """
    if mode == "minmax":
        return composite_fitness(components, viable=viable, weights=weights)
    if mode == "drift":
        rng = np.random.default_rng(0 if drift_seed is None else drift_seed)
        score = rng.random(len(viable)).astype(np.float32)
        score[~viable] = np.float32(0.0)
        return score
    if mode == "drop_degenerate":
        spans = {
            name: (
                float(
                    np.max(np.asarray(components[name], dtype=np.float32)[viable])
                    - np.min(np.asarray(components[name], dtype=np.float32)[viable])
                )
                if bool(viable.any())
                else 0.0
            )
            for name in weights
        }
        kept = {name: weight for name, weight in weights.items() if spans[name] >= floor}
        if not kept:
            raise ValueError(f"全部分量跨度都 < floor={floor}；spans={spans}")
        total = sum(kept.values())
        renorm = {name: weight / total for name, weight in kept.items()}
        return composite_fitness(
            {name: components[name] for name in kept}, viable=viable, weights=renorm
        )
    raise ValueError(f"未知 fitness_mode: {mode!r}")


def _mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def dashboard_aggregates(
    chain_individuals: tuple[ChainIndividual, ...],
    evaluation: PopulationEvaluation,
    *,
    theta_N: float,
    theta_H: float,
    motifs: tuple[str, ...],
) -> dict:
    """Evolution Dashboard 聚合（`交互与可视化.md` §8；`代循环编排.md` §5）。

    **这里算的是"期望表型"（基因型读出）**：`architecture(E_A, E_B, θ_N, θ_H)`，其中
    ``E_A/E_B`` 由基因组与 motif 亲和直接读出（`genome §3`，**不进入发育**）。之所以不用观测档
    （`N=|M|`、`H=CV_τ`）：实测观测档在演化中几乎不变（选的是行为适应度），当比例曲线是直线；
    观测档与外显率的差距属 `experiment/penetrance.py`（"基因型→表型"研究点），不在本面板。

    `p_A` = `P(high_N)`、`p_B` = `P(high_H)`；连接组均值为 `evaluation.phenotypes` 上的
    活跃神经元 / 非零边 / `tau` 均值。
    """
    classes = [
        architecture(
            expression_A(ci.genome, motifs),
            expression_B(ci.genome, motifs),
            theta_N,
            theta_H,
        ).class_label
        for ci in chain_individuals
    ]
    n = len(classes) or 1
    freq = {label: classes.count(label) / n for label in _PHENOTYPE_CLASSES}
    phenotypes = evaluation.phenotypes
    neurons = [int(p.active_mask.sum()) for p in phenotypes]
    edges = [int((p.adjacency != 0).sum()) for p in phenotypes]
    taus = [
        float(p.tau.float()[p.active_mask.bool()].mean())
        for p in phenotypes
        if bool(p.active_mask.any())
    ]
    return {
        "p_A": freq["A_B_"] + freq["A_bb"],
        "p_B": freq["A_B_"] + freq["aaB_"],
        "phenotype_freq": freq,
        "mean_neuron": _mean([float(v) for v in neurons]),
        "mean_edge": _mean([float(v) for v in edges]),
        "mean_tau": _mean(taus),
    }


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
    if episode is not None:
        spawn_seed, _ = arena_seeds_for(seed, generation)
        write_episode_log(
            gen_dir / "events.jsonl",
            experiment_id=experiment_id,
            environment_id=environment_id,
            generation=generation,
            episode_seed=spawn_seed,
            events=episode.events,
        )
        rows = individual_metric_rows(
            episode.per_fish,
            seed=seed,
            episode_steps=steps,
            e_max=arena_config.energy.e_max,
            capture_success_prob=arena_config.growth.capture_success_prob,
            weights=weights,
        )
        write_seed_artifacts(
            gen_dir,
            rows=rows,
            seed=seed,
            per_fish=episode.per_fish,
            events=episode.events,
            steps=steps,
            elapsed=elapsed,
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


@dataclass
class EvolutionState:
    """跨代可变的演化状态（`代循环编排.md` §3）：正式 run 与会话内演化共用同一份。

    `run_dir=None` ⇒ **纯内存**（会话内逐代演化）：不写 `g<gen>/`、不写 `evolution.jsonl`，
    只把 `summaries` 留在内存。`generation` = 下一个待评估代的序号（= 已产出代数）。
    """

    experiment_id: str
    master_seed: int
    chain: ModelChainConfig
    arena_config: ArenaConfig
    evolution_config: EvolutionConfig
    steps: int
    weights: dict
    seed_manager: SeedManager
    individuals: tuple[Individual, ...]
    motifs: tuple[str, ...]
    environment_id: str
    device: str
    fitness_mode: str
    fitness_floor: float
    episodes_per_generation: int = 1
    forced_by_generation: Mapping[int, tuple[str, str]] | None = None
    run_dir: Path | None = None
    generation: int = 0
    summaries: list[GenerationSummary] = field(default_factory=list)
    bottleneck: bool = False


def setup_evolution(
    *,
    experiment_id: str,
    master_seed: int,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    evolution_config: EvolutionConfig,
    individuals: tuple[Individual, ...] | None = None,
    run_dir: Path | None = None,
    environment_id: str = "default",
    steps: int | None = None,
    device: str = "cpu",
    forced_by_generation: Mapping[int, tuple[str, str]] | None = None,
    fitness_mode: str = "minmax",
    fitness_floor: float = 1e-3,
    episodes_per_generation: int = 1,
) -> EvolutionState:
    """建立代循环的初始状态（generation 0）；`run_dir` 已建好时置 `status="running"`。

    `individuals` 缺省时由 `initial_population` 生成（正式 run）；**会话内演化**显式传入会话
    自身的基因组种群（于是 Arena 种群 ≡ 演化种群）。`run_dir=None` ⇒ 纯内存、不写盘。
    """
    if steps is None:
        steps = arena_config.world.episode_steps
    if individuals is None:
        population = initial_population(
            master_seed=master_seed,
            experiment_id=experiment_id,
            n=evolution_config.population_size,
            layout=chain.layout,
        )
        individuals = tuple(
            Individual(genome_id=c.genome_id, genome=c.genome, fish_id=c.fish_id)
            for c in population
        )
    state = EvolutionState(
        experiment_id=experiment_id,
        master_seed=master_seed,
        chain=chain,
        arena_config=arena_config,
        evolution_config=evolution_config,
        steps=steps,
        weights=evolution_config.fitness_weights.model_dump(),
        seed_manager=SeedManager(master_seed),
        individuals=individuals,
        motifs=motif_catalog(master_seed, chain.layout),
        environment_id=environment_id,
        device=device,
        fitness_mode=fitness_mode,
        fitness_floor=fitness_floor,
        episodes_per_generation=episodes_per_generation,
        forced_by_generation=forced_by_generation,
        run_dir=run_dir,
    )
    if run_dir is not None:
        runlayout.update_run_status(run_dir, "running")
    return state


def one_generation(
    state: EvolutionState, *, on_step: Callable[[int, int], None] | None = None
) -> GenerationSummary:
    """推进**一代**（原地更新 `state`）：评估 → 折算 `F` → 落产物 → `advance_generation`。

    返回该代 `GenerationSummary`；`state.generation` 自增 1（= 已产出代数）。出现 bottleneck
    时不更换 `state.individuals`（"子代为空的语义"由该代 `summary` 承载，与 `run_evolution` 一致）。
    """
    generation = state.generation
    chain_individuals = to_chain_individuals(state.individuals, experiment_id=state.experiment_id)
    t0 = time.perf_counter()
    # K 次独立 episode（`experiment §2.4`；K=1 时与旧行为逐字节一致）
    episode_indices = generation_episode_indices(generation, state.episodes_per_generation)
    evaluations = tuple(
        evaluate_population(
            chain_individuals,
            master_seed=state.master_seed,
            chain=state.chain,
            arena_config=state.arena_config,
            steps=state.steps,
            generation=episode_index,
            device=state.device,
            on_step=on_step,
        )
        for episode_index in episode_indices
    )
    elapsed = time.perf_counter() - t0
    evaluation = evaluations[0]  # 落地件取 k=0 的实现
    if len(evaluations) == 1:
        individuals = assemble_individuals(
            chain_individuals,
            evaluation,
            arena_config=state.arena_config,
            weights=state.weights,
            fitness_mode=state.fitness_mode,
            fitness_floor=state.fitness_floor,
            drift_seed=state.master_seed * 1_000_003 + generation,
        )
    else:
        individuals = assemble_individuals_averaged(
            chain_individuals,
            evaluations,
            arena_config=state.arena_config,
            weights=state.weights,
            fitness_mode=state.fitness_mode,
            fitness_floor=state.fitness_floor,
            drift_seed=state.master_seed * 1_000_003 + generation,
        )
    if state.run_dir is not None:
        _write_generation_artifacts(
            state.run_dir,
            experiment_id=state.experiment_id,
            environment_id=state.environment_id,
            generation=generation,
            seed=state.master_seed,
            individuals=individuals,
            evaluation=evaluation,
            arena_config=state.arena_config,
            weights=state.weights,
            steps=state.steps,
            elapsed=elapsed,
        )
    viable_fitness = [i.fitness for i in individuals if i.viable]
    aggregates = dashboard_aggregates(
        chain_individuals,
        evaluation,
        theta_N=state.chain.phenotype.theta_N,
        theta_H=state.chain.phenotype.theta_H,
        motifs=state.motifs,
    )
    summary = GenerationSummary(
        generation=generation,
        n_individuals=len(individuals),
        n_viable=len(viable_fitness),
        fitness_mean=(float(np.mean(viable_fitness)) if viable_fitness else None),
        fitness_std=(float(np.std(viable_fitness, ddof=1)) if len(viable_fitness) > 1 else None),
        bottleneck=False,
        event=None,
        **aggregates,
    )
    state.generation = generation + 1
    state.summaries.append(summary)

    result = advance_generation(
        individuals,
        experiment_id=state.experiment_id,
        generation=generation + 1,
        seed_manager=state.seed_manager,
        config=state.evolution_config,
        layout=state.chain.layout,
        forced_pair=(
            state.forced_by_generation.get(generation) if state.forced_by_generation else None
        ),
    )
    if not result.success:
        state.bottleneck = True
        state.summaries[-1] = replace(summary, bottleneck=True, event=result.event)
        return state.summaries[-1]
    state.individuals = result.offspring
    return summary


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
    forced_by_generation: Mapping[int, tuple[str, str]] | None = None,
    fitness_mode: str = "minmax",
    fitness_floor: float = 1e-3,
    episodes_per_generation: int = 1,
    on_seed_progress: Callable[[float], None] | None = None,
) -> EvolutionRunResult:
    """跑 `generations` 代；`run_dir` 须已由 `runlayout.create_run_dir` 建好。

    逐代写 `<run>/generations/g<gen:04d>/` 与 `<run>/evolution.jsonl`；`metadata.json.status`
    依 `created → running → completed | bottleneck` 更新。**循环体即 `one_generation(state)`**
    （`代循环编排.md` §3）。

    `episodes_per_generation`（默认 1）> 1 时，每代的 `F` 由 K 次**独立** episode 实现
    的分量均值折算（见 `assemble_individuals_averaged`）：第 `g` 代用下标
    `g*K + k, k=0..K-1`，因此 `K=1` 时与旧行为**逐字节一致**。落地件（事件日志、
    dashboard 聚合）取 `k=0` 的实现。诊断依据：单次实现的排序可靠性实测 `rho_1 = 0.069`。
    """
    state = setup_evolution(
        experiment_id=experiment_id,
        master_seed=master_seed,
        chain=chain,
        arena_config=arena_config,
        evolution_config=evolution_config,
        run_dir=run_dir,
        environment_id=environment_id,
        steps=steps,
        device=device,
        forced_by_generation=forced_by_generation,
        fitness_mode=fitness_mode,
        fitness_floor=fitness_floor,
        episodes_per_generation=episodes_per_generation,
    )
    generations_run = 0
    for generation_index in range(generations):

        def _step_cb(done: int, total: int, g: int = generation_index) -> None:
            """把"本代第几步"映射成**种子内单调**进度（跨代不回退），供作业进度条用。"""
            if on_seed_progress is not None:
                frac = (done / total) if total else 1.0
                on_seed_progress((g + max(0.0, min(1.0, frac))) / generations)

        one_generation(state, on_step=_step_cb if on_seed_progress is not None else None)
        generations_run += 1
        if state.bottleneck:
            break

    write_jsonl(run_dir / "evolution.jsonl", [asdict(s) for s in state.summaries])
    runlayout.update_run_status(run_dir, "bottleneck" if state.bottleneck else "completed")
    return EvolutionRunResult(
        generations_run=generations_run,
        bottleneck=state.bottleneck,
        summaries=tuple(state.summaries),
        final_population=state.individuals,
    )


__all__ = [
    "EVENT_POPULATION_BOTTLENECK",
    "EvolutionRunResult",
    "EvolutionState",
    "GenerationSummary",
    "assemble_individuals",
    "one_generation",
    "run_evolution",
    "setup_evolution",
    "to_chain_individuals",
]
