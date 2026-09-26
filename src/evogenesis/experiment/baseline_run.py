"""Experiment C baseline 对照编排（owner：`实验与评价体系.md` §3.3）。

对照 MLP / GRU / Fixed Sparse RNN（`connectome/baselines.py`）与 DanioNet：**同数据、同 BC
预算、同 evaluation episode**，逐模型给出任务指标（mean ± std，沿 seed 轴）与复杂度
（参数量 / 活跃边 / FLOPs 双口径 / latency）。

本模块只编排：模型构造与尺寸反解归 `connectome §8`；BC 契约归 `learning §3`；Arena 驱动归
`pipeline §4`；指标口径归 `experiment §2`。

**评估规模（已定稿，2026-09-26 用户签署；`experiment §3.3`）**：每模型每 seed
**`n_agents` 个 agent × `n_episodes` 个 evaluation episode**。

- **evaluation episode 子种子**：`pipeline.arena_eval_seeds_for(seed, ep)`（`core §4.2` 的
  `arena_eval_spawn=15` / `arena_eval_dynamics=16`），`ep` = 0 起 episode 序号，
  **全模型、全 agent 共享** —— 各模型面对同一份出生布局与同一条猎物游走，唯一差异是网络动作
  （`§3.3` 的「相同 evaluation episodes」红线）。与采集侧 `arena_seeds_for` **刻意解耦**：
  后者与 `collect.episode_seed` 逐字等价，复用会使评估局落在训练数据的环境实例上。
- **基线（无 genome）**：身份自铸，`t = BASELINE_INDEX_BASE + slot * n_agents + agent`，
  同时用作 `baseline_init` 网络初值序号与 `bc` 采样序号 —— 同模型的 `n_agents` 个 agent 由此
  获得**互不相同**的初值与 BC 采样（旧实现固定取模型槽位，使 12 个 agent 完全同源，实验无效）。
  稳定 ID 由 `mint_id` 铸造后再解析回 `t`（`core §3` 合规）。
- **DanioNet（有 genome）**：取 `viable_pairs(...)[:n_agents]`（**保序 ⇒ 最低 index 的
  `n_agents` 个 viable**；与调用顺序无关，合规 `core §3` 稳定 ID 要求）；**ID 不动**（ID 是
  发育随机流的输入），`bc` 序号用配子级规则
  `gamete_seed_index(genome_id, population_size=n_danio)`。两家族的 `t` 区间不交
  （`[1000, ...)` vs `[0, n_danio)`，要求 `n_danio <= 1000`）。
- **训练粒度**：`train_bc` 硬性要求 batch=1（`learning §3`，不得改），故 DanioNet **逐个体**
  构造 `danionet_of([phenotype])` 训练，再把各自 `θ` 注入 `n_agents` 宽的评估网
  （范式同 `experiment/learning_run.py`，该路径已验证）。基线本就一对象一网络，无需注入。
- **降级语义**：DanioNet viable 数 < `n_agents` ⇒ **抛错**（信息带 seed / n_danio / 实际数）；
  `allow_partial=True` 显式开关改按 available 评估，并逐模型记**实际** `n_agents`。

**动作口径一致**：基线与 DanioNet 的 `(ω, v)` 同映射（`ω = tanh`、`v = σ`，`connectome §4/§8`），
`v ∈ [0,1]`；本模块不加任何按模型的读出修正。
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

import numpy as np
import torch

from evogenesis.arena.config import ArenaConfig
from evogenesis.connectome.baselines import BASELINES
from evogenesis.connectome.danionet import DanioNet
from evogenesis.core.config import LearningConfig
from evogenesis.core.ids import mint_id
from evogenesis.core.seed import SeedManager
from evogenesis.evolution.config import EvolutionConfig
from evogenesis.evolution.reproduction import gamete_seed_index
from evogenesis.experiment.measure import measure_latency, network_complexity
from evogenesis.experiment.metrics import (
    SCALAR_METRICS,
    aggregate_by_seed,
    episode_metrics,
    summarise_over_seeds,
)
from evogenesis.experiment.run_artifacts import write_metrics_csv
from evogenesis.learning.data import TrajectoryDataset, load_trajectory_dir
from evogenesis.learning.train import train_bc
from evogenesis.pipeline import (
    ModelChainConfig,
    arena_eval_seeds_for,
    danionet_of,
    drive_arena_with_ids,
    initial_population,
    motif_catalog,
    viable_pairs,
)

#: Experiment C 的模型集合与槽位（槽位用于基线的 `t` 分区）。
MODELS: tuple[str, ...] = (*BASELINES, "danionet")
DANIONET_MODEL = "danionet"

#: 基线 `t` 的分区基（`core §3.1` 的唯一性域 = 单个 experiment）。
#: DanioNet 的 `t = gamete_seed_index(...)` 落在 `[0, n_danio)`，故基 1000 时两家族不交。
BASELINE_INDEX_BASE = 1000

#: 结构量键（`experiment §2.4`，schema 固定 8 键中的 6 个；latency 另计）。
_STRUCTURE_KEYS: tuple[str, ...] = (
    "parameter_count",
    "active_edges",
    "macs_implemented",
    "macs_theoretical",
    "flops_implemented",
    "flops_theoretical",
)


#: 子进程（或串行路径下的主进程）训练上下文。由 `_worker_init` 填充一次。
#: **同一套 task 函数同时服务串行与并行两条路径** —— 故 `workers=1` 与 `workers>1` 的结果
#: 在构造上逐位一致（同一 RNG 流、同一数学、无归约顺序差异）。
_WORKER_CTX: dict[str, Any] = {}


def _worker_init(
    trajectories_dir: str,
    chain: ModelChainConfig,
    learning_config: LearningConfig,
    device: str,
) -> None:
    """每个工作进程各加载一次数据集（避免逐任务 pickle 数据集）。"""
    _WORKER_CTX["dataset"] = load_trajectory_dir(trajectories_dir)
    _WORKER_CTX["chain"] = chain
    _WORKER_CTX["learning_config"] = learning_config
    _WORKER_CTX["device"] = device


def _train_baseline_task(payload: tuple[str, int, int, int]) -> torch.Tensor:
    """训练一个基线个体，返回其训练后的 `theta`（`payload = (name, seed, t, sensory_dim)`）。

    只回传 `theta`：它由 `(master_seed, index, dataset, config)` 确定，故主进程把同一
    构造的未训练网络的 `theta` 覆盖为它，等价于在该进程内原地训练（`core §3` 无调用顺序依赖）。
    """
    name, seed, index, sensory_dim = payload
    ctx = _WORKER_CTX
    net = BASELINES[name](
        master_seed=seed, index=index, sensory_dim=sensory_dim, device=ctx["device"]
    )
    train_bc(
        net,
        ctx["dataset"],
        ctx["learning_config"],
        seed_manager=SeedManager(seed),
        seed_index=index,
        device=ctx["device"],
        sign_constrained=False,
    )
    return net.theta.detach().cpu().clone()


def _train_danionet_task(payload: tuple[Any, int, int]) -> torch.Tensor:
    """训练一个 DanioNet 个体，返回 `theta` 副本（`payload = (phenotype, seed, seed_index)`）。

    `train_bc` 硬性要求 batch=1（`learning §3`），故逐个体训练；`seed_index` 为配子级
    `gamete_seed_index(genome_id, population_size=n_danio)`。
    """
    phenotype, seed, seed_index = payload
    ctx = _WORKER_CTX
    single = danionet_of(
        [phenotype], master_seed=seed, config=ctx["chain"].network,
        device=ctx["device"], sign_constrained=True,
    )
    train_bc(
        single,
        ctx["dataset"],
        ctx["learning_config"],
        seed_manager=SeedManager(seed),
        seed_index=seed_index,
        device=ctx["device"],
        sign_constrained=True,
    )
    return single.theta.detach().cpu().clone()


@contextmanager
def _training_pool(
    workers: int,
    *,
    trajectories_dir: str | Path,
    chain: ModelChainConfig,
    learning_config: LearningConfig,
    device: str,
) -> Iterator[ProcessPoolExecutor | None]:
    """训练用进程池；`workers <= 1` 时 yield `None`（串行路径）。

    并行只提速、不改语义：48 个训练作业彼此独立，种子由 `(master_seed, t)` 派生、与调用
    顺序无关（`core §3` 正是为此设计）。**子进程各自持有自己那份 64×600 步计算图 ⇒ 主进程
    内存不随 `workers` 增长**；总内存 ≈ `workers × 单作业峰值`。
    """
    if workers <= 1:
        _worker_init(str(trajectories_dir), chain, learning_config, device)
        yield None
        return
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_worker_init,
        initargs=(str(trajectories_dir), chain, learning_config, device),
    ) as executor:
        yield executor


def _map_training(
    executor: ProcessPoolExecutor | None, task: Any, payloads: Sequence[Any]
) -> list[torch.Tensor]:
    """串行（`executor is None`）与并行共用的映射；两条路径调用**同一** `task`。"""
    if executor is None:
        return [task(payload) for payload in payloads]
    return list(executor.map(task, payloads))


class BaselineAgentBatch:
    """把 `n_agents` 个独立 baseline 对象适配成 `drive_arena_with_ids` 需要的批量接口。

    **只适配接口，不新增数值/语义**：不改各 agent 的 `θ` 与递归状态 `h`，不引入先验。
    各 agent 的递归状态彼此隔离 —— `step` 以 `observations[i:i+1]` 只喂第 i 个对象，
    故 `h` 不会跨 agent 串扰。
    """

    def __init__(self, nets: Sequence[Any]) -> None:
        if not nets:
            raise ValueError("至少需要一个 baseline 对象才能组装批量接口")
        self._nets = list(nets)

    @property
    def n_neurons(self) -> list[int]:
        """批量维长度 = agent 数（`drive_arena_with_ids` 的 batch 校验用）。"""
        return [net.n_neurons[0] for net in self._nets]

    def reset(self) -> None:
        for net in self._nets:
            net.reset()

    def step(self, observations: np.ndarray | torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        n = len(self._nets)
        if len(observations) != n:
            raise ValueError(f"observation batch {len(observations)} 与 agent 数 {n} 不一致")
        pairs = [net.step(observations[i : i + 1]) for i, net in enumerate(self._nets)]
        return torch.cat([p[0] for p in pairs]), torch.cat([p[1] for p in pairs])

    def complexity(self) -> dict[str, int]:
        """结构量取代表个体：基线三模型逐 agent 结构恒等（`connectome §8`）。纯接口适配。"""
        return self._nets[0].complexity()


@dataclass(frozen=True)
class ModelResult:
    """单模型在单 ``(seed, agent, episode)`` 下的评估结果。

    `(seed, model)` 下共 `n_agents` × `n_episodes` 条；`fish_id` 在 `n_episodes` 个 episode
    间**重复**，故必须同时记 `episode` 才能定位一条记录（`experiment §5.2`）。
    """

    seed: int
    model: str
    agent: int
    episode: int
    fish_id: str
    metrics: dict[str, Any]
    complexity: dict[str, float | int]
    complexity_note: str | None = None


@dataclass(frozen=True)
class BaselineComparisonResult:
    """Experiment C 对照结果（跨 seed 汇总）。"""

    experiment_id: str
    seeds: tuple[int, ...]
    steps: int
    n_agents: int
    n_episodes: int
    models: tuple[dict[str, Any], ...]  # 每模型：model / n_agents / metrics / complexity / note


def _complexity(
    net: Any, *, sensory_dim: int, n_agents: int
) -> tuple[dict[str, float | int], str | None]:
    """归一化复杂度：参数量 / 活跃边 / FLOPs 双口径 / latency（`experiment §2.4`）。

    - `latency`：**batch = `n_agents`** 的一次前向 wall-clock（`§2.4` 定稿口径）。调用方给出的
      `net` 须能一次吃下 `(n_agents, sensory_dim)`（DanioNet 批量网，或 `BaselineAgentBatch`）。
    - **结构量**是**单个体**量（`MACs_impl = N² + N·D`，**不含 batch 因子**）。DanioNet 报
      `n_agents` 个个体的**等权均值**，极差经第二个返回值写入该模型的 `note`（schema 对
      `complexity` 是 `additionalProperties: false` 的固定 8 键，容不下额外键）。
    """
    observation = np.zeros((n_agents, sensory_dim), dtype=np.float32)
    latency = measure_latency(net, observation)
    if isinstance(net, DanioNet):
        per_agent: list[dict[str, int]] = [
            network_complexity(net, individual=b) for b in range(n_agents)
        ]
    else:  # baseline：逐 agent 结构恒等（`connectome §8`），取一次即可
        per_agent = [net.complexity()]

    out: dict[str, float | int] = {}
    spreads: list[str] = []
    for key in _STRUCTURE_KEYS:
        vals = [float(entry[key]) for entry in per_agent]
        out[key] = fmean(vals)
        lo, hi = min(vals), max(vals)
        if hi > lo:
            spreads.append(f"{key} 极差 {hi - lo:g}")
    out["latency_p50_ms"] = float(latency["p50_ms"])
    out["latency_p95_ms"] = float(latency["p95_ms"])
    note = (
        f"复杂度 = {n_agents} 个体等权均值（" + "；".join(spreads) + "）" if spreads else None
    )
    return out, note


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


def _baseline_t(slot: int, agent: int, *, n_agents: int) -> int:
    """基线的稳定 ID index（`t`）：Experiment C 局部分区 `BASELINE_INDEX_BASE + slot*N + agent`。

    同一 `t` 同时喂给 `BASELINES[name](index=...)`（`baseline_init` 初值流）与
    `train_bc(seed_index=...)`（`bc` 采样流）—— 这是「同模型 `n_agents` 个 agent 互不同源」
    的实现点（旧实现两者都固定取模型槽位，12 个 agent 完全同源）。
    """
    return BASELINE_INDEX_BASE + slot * n_agents + agent


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
    n_agents: int,
    n_episodes: int,
    steps: int,
    generation: int,
    device: str,
    executor: ProcessPoolExecutor | None = None,
) -> list[ModelResult]:
    """建 `n_agents` 个基线对象、逐个 BC 训练，再让它们**同场**跑 `n_episodes` 局。

    每个 agent 一对象一网络（无 batch 维），故经 `BaselineAgentBatch` 适配后进同一 Arena
    （`drive_arena_with_ids` 要求 `len(fish_ids) == len(net.n_neurons)`）。
    """
    sensory_dim = chain.network.sensory_dim
    indices = [_baseline_t(slot, agent, n_agents=n_agents) for agent in range(n_agents)]
    nets = [
        BASELINES[name](master_seed=seed, index=t, sensory_dim=sensory_dim, device=device)
        for t in indices
    ]
    thetas = _map_training(
        executor, _train_baseline_task, [(name, seed, t, sensory_dim) for t in indices]
    )
    with torch.no_grad():
        for net, theta in zip(nets, thetas, strict=True):
            net.theta.data.copy_(theta)
    batch = BaselineAgentBatch(nets)
    fish_ids = [mint_id(experiment_id, "fish", generation, t) for t in indices]
    genome_ids = [mint_id(experiment_id, "genome", generation, t) for t in indices]
    complexity, cx_note = _complexity(batch, sensory_dim=sensory_dim, n_agents=n_agents)

    rows: list[ModelResult] = []
    for ep in range(n_episodes):
        episode = drive_arena_with_ids(
            fish_ids=fish_ids,
            genome_ids=genome_ids,
            net=batch,
            master_seed=seed,
            chain=chain,
            arena_config=arena_config,
            steps=steps,
            generation=generation,
            arena_seeds=arena_eval_seeds_for(seed, ep),
        )
        for agent, fish_id in enumerate(fish_ids):
            rows.append(
                ModelResult(
                    seed=seed,
                    model=name,
                    agent=agent,
                    episode=ep,
                    fish_id=fish_id,
                    metrics=_metrics_for(
                        episode.per_fish, fish_id, steps=steps,
                        arena_config=arena_config, weights=weights,
                    ),
                    complexity=complexity,
                    complexity_note=cx_note,
                )
            )
    return rows


def _evaluate_danionet(
    *,
    seed: int,
    dataset: TrajectoryDataset,
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    learning_config: LearningConfig,
    weights: dict[str, float],
    experiment_id: str,
    n_agents: int,
    n_episodes: int,
    n_danio: int,
    steps: int,
    generation: int,
    device: str,
    allow_partial: bool,
    executor: ProcessPoolExecutor | None = None,
) -> list[ModelResult]:
    """发育 `n_danio` 候选、取**最低 index 的 `n_agents` 个 viable**，逐个体训练后注入批量网。

    `train_bc` 硬性要求 batch=1（`learning §3`），故只能逐个体训练再注入 `θ`；评估网与
    `learning_run` 的范式一致（`W⁰`/支撑/先验是 `network_init` index=0 的确定性全局单表，
    故批量网与单个体网的先验逐元素相同，注入语义正确）。
    """
    if n_danio > BASELINE_INDEX_BASE:
        raise ValueError(
            f"n_danio={n_danio} 超过基线分区基 {BASELINE_INDEX_BASE}；"
            "两家族的稳定 ID 分区会重叠（见模块 docstring 的分区不变式）"
        )
    population = initial_population(
        master_seed=seed, experiment_id=experiment_id, n=n_danio, layout=chain.layout
    )
    motifs = motif_catalog(seed, chain.layout)
    pairs = viable_pairs(population, motifs, master_seed=seed, config=chain.rgcd, device=device)
    if len(pairs) < n_agents:
        if not allow_partial:
            raise ValueError(
                f"DanioNet 可用 viable 个体 {len(pairs)} < n_agents={n_agents}"
                f"（seed={seed}，n_danio={n_danio}）；§3.3 的降级语义要求显式 "
                "allow_partial=True 才按 available 评估"
            )
    else:
        pairs = pairs[:n_agents]
    if not pairs:
        raise ValueError(f"DanioNet 无 viable 个体（seed={seed}，n_danio={n_danio}），无法评估")

    sensory_dim = chain.network.sensory_dim
    thetas = _map_training(
        executor,
        _train_danionet_task,
        [
            (phenotype, seed, gamete_seed_index(individual.genome_id, population_size=n_danio))
            for individual, phenotype in pairs
        ],
    )

    eval_net = danionet_of(
        [phenotype for _, phenotype in pairs],
        master_seed=seed,
        config=chain.network,
        device=device,
        sign_constrained=True,
    )
    with torch.no_grad():
        for slot, theta in enumerate(thetas):
            eval_net.theta.data[slot].copy_(theta[0])

    n_eval = len(pairs)
    complexity, cx_note = _complexity(eval_net, sensory_dim=sensory_dim, n_agents=n_eval)
    fish_ids = [individual.fish_id for individual, _ in pairs]
    genome_ids = [individual.genome_id for individual, _ in pairs]

    rows: list[ModelResult] = []
    for ep in range(n_episodes):
        episode = drive_arena_with_ids(
            fish_ids=fish_ids,
            genome_ids=genome_ids,
            net=eval_net,
            master_seed=seed,
            chain=chain,
            arena_config=arena_config,
            steps=steps,
            generation=generation,
            arena_seeds=arena_eval_seeds_for(seed, ep),
        )
        for agent, fish_id in enumerate(fish_ids):
            rows.append(
                ModelResult(
                    seed=seed,
                    model=DANIONET_MODEL,
                    agent=agent,
                    episode=ep,
                    fish_id=fish_id,
                    metrics=_metrics_for(
                        episode.per_fish, fish_id, steps=steps,
                        arena_config=arena_config, weights=weights,
                    ),
                    complexity=complexity,
                    complexity_note=cx_note,
                )
            )
    return rows


def _summarise_models(results: list[ModelResult], *, n_agents: int) -> tuple[dict, ...]:
    """按模型分组并**两段式**汇总（`experiment §1.2`）。

    第一段先在该 seed 内对 `(agent × episode)` 取等权均值 → 每个 seed 一行
    （`aggregate_by_seed`）；第二段沿 seed 轴给 mean ± std（`summarise_over_seeds`）。
    故 payload 里每个指标的 `n` 是 **seed 数**，**不是**观测数（`n_agents × n_episodes × seeds`）
    —— 跳过第一段会把观测池化，`std` 退化为混合总方差、`n` 被放大（旧实现的缺陷）。

    `n_agents` 记**实际**评估数：`allow_partial` 降级路径下可小于顶层配置值。
    """
    out: list[dict] = []
    for name in MODELS:
        rows = [r for r in results if r.model == name]
        if not rows:
            out.append(
                {
                    "model": name,
                    "n_agents": 0,
                    "metrics": None,
                    "complexity": None,
                    "note": "无结果（DanioNet 在 n_danio 候选内无 viable 个体）"
                    if name == DANIONET_MODEL
                    else "无结果",
                }
            )
            continue
        seed_rows = aggregate_by_seed([{"seed": r.seed, **r.metrics} for r in rows])
        notes: list[str] = []
        actual = len({r.agent for r in rows})
        if actual != n_agents:
            notes.append(
                f"降级：实际评估 {actual} 个 agent（< 顶层 n_agents={n_agents}，allow_partial）"
            )
        if rows[0].complexity_note:
            notes.append(rows[0].complexity_note)
        out.append(
            {
                "model": name,
                "n_agents": actual,
                "metrics": summarise_over_seeds(seed_rows, metrics=SCALAR_METRICS),
                "complexity": rows[0].complexity,
                "note": "；".join(notes) if notes else None,
            }
        )
    return tuple(out)


def _evaluate_all_seeds(
    *,
    experiment_id: str,
    seeds: tuple[int, ...],
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    learning_config: LearningConfig,
    weights: dict[str, float],
    dataset: TrajectoryDataset,
    n_agents: int,
    n_episodes: int,
    n_danio: int,
    steps: int,
    generation: int,
    device: str,
    allow_partial: bool,
    run_dir_of: Any,
    executor: ProcessPoolExecutor | None,
) -> list[ModelResult]:
    """逐 seed × 逐模型评估，返回全部 `ModelResult`（`metrics.csv` 亦在此写入）。

    训练一律经 `_map_training(executor, ...)` —— **串行（`executor is None`）与并行调用同一批
    task**，故两条路径结果逐位一致；`executor` 只影响算得有多快。
    """
    results: list[ModelResult] = []
    for seed in seeds:
        rows_by_model: dict[str, list[ModelResult]] = {}
        for slot, name in enumerate(MODELS):
            if name == DANIONET_MODEL:
                rows = _evaluate_danionet(
                    seed=seed,
                    dataset=dataset,
                    chain=chain,
                    arena_config=arena_config,
                    learning_config=learning_config,
                    weights=weights,
                    experiment_id=experiment_id,
                    n_agents=n_agents,
                    n_episodes=n_episodes,
                    n_danio=n_danio,
                    steps=steps,
                    generation=generation,
                    device=device,
                    allow_partial=allow_partial,
                    executor=executor,
                )
            else:
                rows = _evaluate_baseline(
                    name,
                    slot=slot,
                    seed=seed,
                    dataset=dataset,
                    chain=chain,
                    arena_config=arena_config,
                    learning_config=learning_config,
                    weights=weights,
                    experiment_id=experiment_id,
                    n_agents=n_agents,
                    n_episodes=n_episodes,
                    steps=steps,
                    generation=generation,
                    device=device,
                    executor=executor,
                )
            results.extend(rows)
            rows_by_model[name] = rows

        if run_dir_of is not None:
            csv_rows = [
                {
                    "seed": r.seed,
                    "fish_id": r.fish_id,
                    "agent": r.agent,
                    "episode": r.episode,
                    "model": r.model,
                    **r.metrics,
                }
                for name in MODELS
                for r in rows_by_model.get(name, [])
            ]
            write_metrics_csv(run_dir_of(seed), csv_rows)
    return results


def run_baseline_comparison(
    *,
    experiment_id: str,
    seeds: tuple[int, ...],
    chain: ModelChainConfig,
    arena_config: ArenaConfig,
    learning_config: LearningConfig,
    evolution_config: EvolutionConfig,
    trajectories_dir: str | Path,
    n_agents: int,
    n_episodes: int,
    n_danio: int,
    run_dir_of: Any = None,
    steps: int | None = None,
    generation: int = 0,
    device: str = "cpu",
    allow_partial: bool = False,
    workers: int = 1,
) -> BaselineComparisonResult:
    """跑 Experiment C：每模型每 seed **`n_agents` agent × `n_episodes` episode**。

    `n_agents` / `n_episodes` / `n_danio` 为**必填**（值归 `configs/experiment.yaml`，本函数不
    设默认值以免与配置漂移）。``run_dir_of(seed) -> Path`` 为可选的 run 目录提供者（由 CLI 用
    `runlayout` 建）；给出时每 seed 写 ``<run>/metrics.csv``（`seed`/`fish_id` + 指标 +
    `agent`/`episode`/`model`）。跨 seed 汇总由本函数返回，落盘由 CLI 写
    `results/tables/<experiment_id>_baselines.json`。

    `steps=None` 取 `world.episode_steps`。`allow_partial` 见模块 docstring 的降级语义。
    `workers > 1` 时把每模型 `n_agents` 个**彼此独立**的 BC 训练交给进程池（只提速、不改
    语义：种子由 `(master_seed, t)` 派生、与调用顺序无关）；`workers=1` 为串行，与并行路径
    构造上逐位一致。并发上限由**内存**决定 —— 单作业峰值 ≈ 2–3 GB（64×600 步计算图）。
    """
    if n_agents < 1 or n_episodes < 1:
        raise ValueError(f"n_agents / n_episodes 必须 >= 1，实际 {n_agents} / {n_episodes}")
    steps = arena_config.world.episode_steps if steps is None else steps
    weights = evolution_config.fitness_weights.model_dump()
    dataset = load_trajectory_dir(trajectories_dir)

    with _training_pool(
        workers,
        trajectories_dir=trajectories_dir,
        chain=chain,
        learning_config=learning_config,
        device=device,
    ) as executor:
        results = _evaluate_all_seeds(
            experiment_id=experiment_id,
            seeds=seeds,
            chain=chain,
            arena_config=arena_config,
            learning_config=learning_config,
            weights=weights,
            dataset=dataset,
            n_agents=n_agents,
            n_episodes=n_episodes,
            n_danio=n_danio,
            steps=steps,
            generation=generation,
            device=device,
            allow_partial=allow_partial,
            run_dir_of=run_dir_of,
            executor=executor,
        )

    models = _summarise_models(results, n_agents=n_agents)
    return BaselineComparisonResult(
        experiment_id=experiment_id,
        seeds=seeds,
        steps=steps,
        n_agents=n_agents,
        n_episodes=n_episodes,
        models=models,
    )


def comparison_payload(result: BaselineComparisonResult) -> dict:
    """跨 seed 对照表的落盘 payload（schema = `schemas/baseline_comparison.schema.json`）。

    `n_agents` / `n_episodes` 由 `result` **自派生**（顶层 = 配置的签字规模；逐模型
    `n_agents` = 实际评估数）—— 不再由调用方传参，避免像旧实现那样硬编码成 1。
    """
    return {
        "experiment_id": result.experiment_id,
        "seeds": list(result.seeds),
        "steps": result.steps,
        "n_agents": result.n_agents,
        "n_episodes": result.n_episodes,
        "models": list(result.models),
    }


def table_path(experiment_id: str, root: str | Path) -> Path:
    """跨 seed 对照表路径 `results/tables/<experiment_id>_baselines.json`。"""
    return Path(root) / "tables" / f"{experiment_id}_baselines.json"


__all__ = [
    "BASELINE_INDEX_BASE",
    "DANIONET_MODEL",
    "MODELS",
    "BaselineAgentBatch",
    "BaselineComparisonResult",
    "ModelResult",
    "comparison_payload",
    "run_baseline_comparison",
    "table_path",
]
