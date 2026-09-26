"""Experiment C baseline 对照的守护（`实验与评价体系.md` §3.3）。

用合成的小轨迹 + 默认模型/竞技场配置跑通「构造 → BC 训练 → Arena → 指标/复杂度 → 跨模型
汇总 → 对照表 schema」，避免真实 600 步数据。`MODELS` 被临时收窄为两个基线以提速。

重点守护（对应本次 12 agent × 3 episode 改造中修掉的缺陷）：

- **两段式汇总**：payload 里每个指标的 `n` 是 **seed 数**，不是观测数（旧实现跳过
  `aggregate_by_seed`，把观测池化，`std` 退化为混合总方差、`n` 被放大）。
- **CSV 行定位**：`fish_id` 非空，且 `(agent, episode)` 能唯一定位一行（`fish_id` 跨 episode
  重复，缺 `episode` 无法区分）。
- **agent 互不同源**：同模型 `n_agents` 个 agent 的 `baseline_init` / `bc` 序号两两不同
  （旧实现固定取模型槽位，12 个 agent 完全同源，实验无效）。
- **批量复杂度**：batch > 1 的 DanioNet 不再抛形状错误；结构量为逐个体等权均值。
- **评估种子解耦**：`arena_eval_seeds_for` 与采集侧 `episode_seed` 逐字不等。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import fmean

import jsonschema
import numpy as np
import pytest
import torch

from evogenesis.arena.config import ArenaConfig
from evogenesis.connectome.baselines import MLPPolicy
from evogenesis.connectome.danionet import DanioNet
from evogenesis.core.config import LearningConfig, read_yaml
from evogenesis.core.io import write_jsonl
from evogenesis.core.seed import SeedManager
from evogenesis.development import develop
from evogenesis.evolution.config import load_evolution_config
from evogenesis.evolution.reproduction import gamete_seed_index
from evogenesis.experiment import baseline_run
from evogenesis.experiment.baseline_run import (
    BASELINE_INDEX_BASE,
    BaselineAgentBatch,
    BaselineComparisonResult,
    _baseline_t,
    _complexity,
    comparison_payload,
    run_baseline_comparison,
)
from evogenesis.experiment.collect import episode_dynamics_seed, episode_seed
from evogenesis.experiment.config import load_experiment_config
from evogenesis.experiment.learning_run import load_learning_config
from evogenesis.experiment.measure import network_complexity
from evogenesis.experiment.metrics import SCALAR_METRICS
from evogenesis.pipeline import (
    ModelChainConfig,
    arena_eval_seeds_for,
    drive_arena_with_ids,
    load_model_chain_config,
)

ROOT = Path(__file__).resolve().parents[1]
MODEL_CONFIG = ROOT / "configs" / "default_model.yaml"
EVOLUTION_CONFIG = ROOT / "configs" / "evolution.yaml"

#: `test_danionet.py` / `test_measure.py` 同款 viable 夹具（RGCD `develop` 的确定性产物）。
MASTER_SEED = 250927
VIABLE_Q = np.array(
    [
        0.5077722072601318,
        0.8713393807411194,
        0.36126405000686646,
        0.5981840491294861,
        0.05925164371728897,
        0.3876318037509918,
        0.3230363428592682,
        0.15019972622394562,
    ],
    dtype=np.float32,
)
#: `master_seed=250927` 下经实测确认 viable 的两个 index（供 ≥2 个体的批量夹具）。
VIABLE_INDICES = (6, 11)

#: `experiment §2.1` 裁决下**可**为 `None` 的标量指标：`encounters == 0` ⇒ 「无出手机会」
#: ⇒ 未定义，汇总时被跳过，故其 `n` 可小于 seed 数。其余指标恒有定义。
_NONE_ABLE_METRICS = ("prey_capture",)


def _write_trajectory(
    directory: Path, name: str, *, steps: int, experiment_id: str = "expC"
) -> None:
    header = {
        "record_type": "header",
        "schema_version": "1.1.0",
        "experiment_id": experiment_id,
        "episode_id": name.removesuffix(".jsonl").removeprefix("episode_"),
        "environment_id": "default",
        "generation": 0,
        "episode_seed": 1,
        "total_steps": steps,
        "terminated": False,
        "truncated": True,
    }
    rows = [
        {
            "record_type": "step",
            "fish_id": f"{experiment_id}:g0:fish0000",
            "genome_id": f"{experiment_id}:g0:genome0000",
            "step": step,
            "observation": [0.0] * 12,
            "expert_action": [0.0, 0.5],
        }
        for step in range(steps)
    ]
    write_jsonl(directory / name, [header, *rows])


def _prepare(tmp_path: Path) -> tuple[Path, ModelChainConfig, LearningConfig]:
    trajectories = tmp_path / "trajectories"
    trajectories.mkdir(parents=True, exist_ok=True)
    _write_trajectory(trajectories, "episode_ep0001.jsonl", steps=3)
    _write_trajectory(trajectories, "episode_ep0002.jsonl", steps=3)
    return trajectories, load_model_chain_config(MODEL_CONFIG), load_learning_config(MODEL_CONFIG)


def _run_small(
    tmp_path: Path,
    monkeypatch,
    *,
    seeds: tuple[int, ...],
    n_agents: int,
    n_episodes: int,
    workers: int = 1,
):
    """小规模跑通 Experiment C（MODELS 收窄为两个基线），返回 (result, run_dirs)。"""
    trajectories, chain, learning_config = _prepare(tmp_path)
    monkeypatch.setattr(baseline_run, "MODELS", ("mlp", "gru"))
    run_dirs = {seed: tmp_path / f"run_{seed}" for seed in seeds}
    for run_dir in run_dirs.values():
        run_dir.mkdir()
    result = run_baseline_comparison(
        experiment_id="expC",
        seeds=seeds,
        chain=chain,
        arena_config=ArenaConfig(),
        learning_config=learning_config,
        evolution_config=load_evolution_config(EVOLUTION_CONFIG),
        trajectories_dir=trajectories,
        n_agents=n_agents,
        n_episodes=n_episodes,
        n_danio=2,
        steps=5,
        run_dir_of=lambda seed: run_dirs[seed],
        workers=workers,
    )
    return result, run_dirs


def _read_metrics_csv(run_dir: Path) -> list[dict[str, str]]:
    with (run_dir / "metrics.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_baseline_comparison_runs_and_matches_schema(tmp_path: Path, monkeypatch) -> None:
    """端到端：2 seed × 2 模型 × 2 agent × 2 episode，落 CSV 与跨 seed 表并过 schema。"""
    seeds = (1103, 2207)
    n_agents, n_episodes = 2, 2
    result, run_dirs = _run_small(
        tmp_path, monkeypatch, seeds=seeds, n_agents=n_agents, n_episodes=n_episodes
    )

    assert [m["model"] for m in result.models] == ["mlp", "gru"]
    for model in result.models:
        assert model["metrics"] is not None
        for metric in SCALAR_METRICS:
            assert set(model["metrics"][metric]) == {"mean", "std", "n"}
            # D1 回归闸：n = **seed 数**，不是观测数 n_agents × n_episodes × seeds = 8
            n_observed = model["metrics"][metric]["n"]
            assert 1 <= n_observed <= len(seeds)
            if metric not in _NONE_ABLE_METRICS:
                assert n_observed == len(seeds), (
                    f"{model['model']} / {metric} 的 n 应为 seed 数 {len(seeds)}；"
                    "若为 8 说明跳过了 aggregate_by_seed（观测被池化）"
                )
        assert model["complexity"]["parameter_count"] > 0
        assert model["n_agents"] == n_agents          # 逐模型 = 实际评估数

    payload = comparison_payload(result)
    assert payload["n_agents"] == n_agents            # 顶层 = 签字规模
    assert payload["n_episodes"] == n_episodes
    schema = json.loads((ROOT / "schemas" / "baseline_comparison.schema.json").read_text("utf-8"))
    jsonschema.validate(payload, schema)

    # 每个 seed 一份 metrics.csv，且按 (seed, model) 恰 n_agents × n_episodes 行
    for seed in seeds:
        rows = _read_metrics_csv(run_dirs[seed])
        assert len(rows) == len(result.models) * n_agents * n_episodes
        assert {r["seed"] for r in rows} == {str(seed)}
        assert {r["model"] for r in rows} == {"mlp", "gru"}


def test_metrics_csv_locates_rows_by_agent_and_episode(tmp_path: Path, monkeypatch) -> None:
    """D6 闸：`fish_id` 非空，且 `(agent, episode)` 能唯一定位一行。

    `fish_id` 在 `n_episodes` 个 episode 间**重复**，故缺 `episode` 无法区分行来源。
    """
    n_agents, n_episodes = 2, 3
    _result, run_dirs = _run_small(
        tmp_path, monkeypatch, seeds=(1103,), n_agents=n_agents, n_episodes=n_episodes
    )
    rows = _read_metrics_csv(run_dirs[1103])

    assert all(r["fish_id"].strip() for r in rows), "fish_id 不得为空（旧实现恒空）"
    for column in ("agent", "episode", "model"):
        assert column in rows[0], f"metrics.csv 缺列 {column}"
    for model in ("mlp", "gru"):
        model_rows = [r for r in rows if r["model"] == model]
        assert len(model_rows) == n_agents * n_episodes
        assert {int(r["agent"]) for r in model_rows} == set(range(n_agents))
        assert {int(r["episode"]) for r in model_rows} == set(range(n_episodes))
        # 同一 fish_id 恰出现 n_episodes 次；每个 (agent, episode) 组合恰一行
        for agent in range(n_agents):
            agent_rows = [r for r in model_rows if int(r["agent"]) == agent]
            assert len({r["fish_id"] for r in agent_rows}) == 1
            assert len(agent_rows) == n_episodes
        assert len({(r["fish_id"], r["episode"]) for r in model_rows}) == len(model_rows)


def test_agent_seeds_distinct_across_agents() -> None:
    """D3 闸：同模型 `n_agents` 个 agent 的 `baseline_init` / `bc` 流必须两两不同。"""
    n_agents = 4
    ts = [_baseline_t(0, agent, n_agents=n_agents) for agent in range(n_agents)]
    assert ts == [BASELINE_INDEX_BASE + a for a in range(n_agents)]
    assert len(set(ts)) == n_agents

    init_firsts = {
        float(SeedManager(1103).spawn_rng("baseline_init", t).uniform(-1.0, 1.0)) for t in ts
    }
    assert len(init_firsts) == n_agents, "12 个 agent 不得共享同一条 baseline_init 初值流"
    bc_firsts = {float(SeedManager(1103).spawn_rng("bc", t).uniform(-1.0, 1.0)) for t in ts}
    assert len(bc_firsts) == n_agents, "12 个 agent 不得共享同一个 bc 采样序号"


def test_baseline_and_danionet_index_partitions_disjoint() -> None:
    """`core §3.1` 唯一性域：基线 `t ∈ [1000, ...)` 与 DanioNet `t ∈ [0, n_danio)` 不得相交。"""
    n_agents, n_danio = 12, 400
    baseline_ts = {
        _baseline_t(slot, agent, n_agents=n_agents)
        for slot in range(len(baseline_run.MODELS) - 1)  # 仅基线槽位
        for agent in range(n_agents)
    }
    danio_ts = {
        gamete_seed_index(f"expC:g0:genome{i:04d}", population_size=n_danio)
        for i in range(n_danio)
    }
    assert not (baseline_ts & danio_ts)
    assert min(baseline_ts) >= BASELINE_INDEX_BASE
    assert max(danio_ts) < n_danio       # generation=0 ⇒ t = index


def test_danionet_batch_theta_injection_matches_single_nets() -> None:
    """C1 闸：`train_bc` 拒 batch>1，故逐个体训练后注入；注入后批量网须与单个体网逐元素一致。"""
    phenotypes = [develop(VIABLE_Q, master_seed=MASTER_SEED, index=i) for i in VIABLE_INDICES]
    for phenotype in phenotypes:
        assert phenotype.viable, phenotype.viability_reason

    singles = [DanioNet([phenotype], master_seed=MASTER_SEED) for phenotype in phenotypes]
    batch = DanioNet(phenotypes, master_seed=MASTER_SEED)
    assert len(batch.n_neurons) == len(phenotypes)

    with torch.no_grad():
        for slot, single in enumerate(singles):
            batch.theta.data[slot].copy_(single.theta.data[0])

    observations = np.zeros((len(phenotypes), 12), dtype=np.float32)
    batch.reset()
    with torch.no_grad():
        omega_batch, v_batch = batch.step(observations)
    for slot, single in enumerate(singles):
        single.reset()
        with torch.no_grad():
            omega_one, v_one = single.step(observations[slot : slot + 1])
        # 先验/支撑一致 + θ 注入正确 ⇒ 批量第 slot 行与单个体逐元素相同
        assert torch.allclose(omega_batch[slot], omega_one[0], atol=1e-6)
        assert torch.allclose(v_batch[slot], v_one[0], atol=1e-6)


def test_complexity_at_batch_gt_one_reports_per_agent_mean() -> None:
    """D2 闸：batch>1 的 DanioNet 不再抛形状错误；结构量报逐个体等权均值。"""
    phenotypes = [develop(VIABLE_Q, master_seed=MASTER_SEED, index=i) for i in VIABLE_INDICES]
    net = DanioNet(phenotypes, master_seed=MASTER_SEED)
    n_agents = len(phenotypes)

    complexity, note = _complexity(net, sensory_dim=12, n_agents=n_agents)  # 旧实现此处 ValueError
    expected_keys = {
        "parameter_count",
        "active_edges",
        "macs_implemented",
        "macs_theoretical",
        "flops_implemented",
        "flops_theoretical",
        "latency_p50_ms",
        "latency_p95_ms",
    }
    assert set(complexity) == expected_keys
    per_agent = [network_complexity(net, individual=b) for b in range(n_agents)]
    assert complexity["parameter_count"] == pytest.approx(
        fmean(entry["parameter_count"] for entry in per_agent)
    )
    assert complexity["latency_p50_ms"] >= 0.0
    if note is not None:                      # 个体结构有差异时才记极差
        assert "极差" in note


def test_complexity_for_baseline_batch_has_no_spread_note() -> None:
    """基线三模型逐 agent 结构恒等（`connectome §8`）⇒ 无极差 note。"""
    batch = BaselineAgentBatch(
        [MLPPolicy(master_seed=1103, index=0), MLPPolicy(master_seed=1103, index=1)]
    )
    complexity, note = _complexity(batch, sensory_dim=12, n_agents=2)
    assert note is None
    assert complexity["parameter_count"] > 0


def test_eval_episode_seeds_disjoint_from_collection() -> None:
    """混叠修复闸：`arena_eval_seeds_for` 与采集侧 `episode_seed` 系列逐字不等。

    改前实测 `arena_seeds_for(master, i)` 与 `episode_seed(master, i)` **逐字相等** —— 复用它
    会使评估局落在训练数据的环境实例上，并令评估的 episode 轴不携带独立环境变异。
    """
    for master in (1103, 250927):
        for i in range(4):
            spawn, dynamics = arena_eval_seeds_for(master, i)
            assert spawn != dynamics, (
                "spawn 与 dynamics 不得同流（出生布局与猎物游走会共用同一条序列）"
            )
            for j in range(4):
                assert spawn != episode_seed(master, j)
                assert spawn != episode_dynamics_seed(master, j)
                assert dynamics != episode_seed(master, j)
                assert dynamics != episode_dynamics_seed(master, j)
        assert arena_eval_seeds_for(master, 0) == arena_eval_seeds_for(master, 0)   # 确定性


def test_eval_seeds_shared_across_models_and_agents(tmp_path: Path) -> None:
    """`core §4.2` 红线：同一 `index` 下所有模型与个体面对同一份出生布局、同一条猎物游走。"""
    seed, episode = 1103, 1
    first = arena_eval_seeds_for(seed, episode)
    second = arena_eval_seeds_for(seed, episode)
    assert first == second
    assert first != arena_eval_seeds_for(seed, episode + 1)   # episode 轴确实生效


def test_payload_derives_n_agents_from_result_not_hardcoded() -> None:
    """D5 闸（行为断言）：`n_agents` / `n_episodes` 必须随结果变化，不得硬编码为 1。"""
    for n_agents, n_episodes in ((1, 1), (2, 3), (12, 3)):
        result = BaselineComparisonResult(
            experiment_id="expC",
            seeds=(1103, 2207),
            steps=600,
            n_agents=n_agents,
            n_episodes=n_episodes,
            models=(),
        )
        payload = comparison_payload(result)
        assert payload["n_agents"] == n_agents
        assert payload["n_episodes"] == n_episodes
        assert payload["seeds"] == [1103, 2207]


def test_baseline_agent_batch_isolates_recursion_between_agents() -> None:
    """适配器：`n_neurons` 长度 = agent 数；各 agent 的递归状态互不串扰；batch 不符即报错。"""
    nets = [MLPPolicy(master_seed=1103, index=i) for i in range(2)]
    batch = BaselineAgentBatch(nets)
    assert batch.n_neurons == [nets[0].n_neurons[0]] * 2

    observations = np.zeros((2, 12), dtype=np.float32)
    observations[0, 0] = 1.0                      # 只刺激 agent 0
    batch.reset()
    with torch.no_grad():
        omega, v = batch.step(observations)
    assert omega.shape == (2,) and v.shape == (2,)
    assert not torch.equal(nets[0].h, nets[1].h), "两 agent 的 h 必须彼此隔离（不得串扰）"

    with pytest.raises(ValueError, match="不一致"):
        batch.step(np.zeros((3, 12), dtype=np.float32))


def test_drive_arena_with_ids_rejects_batch_mismatch(tmp_path: Path) -> None:
    """单个 `MLPPolicy` 的 `n_neurons` 长度为 1 —— 这正是 `BaselineAgentBatch` 必须存在的原因。"""
    _trajectories, chain, _learning_config = _prepare(tmp_path)
    net = MLPPolicy(master_seed=1103, index=0)
    with pytest.raises(ValueError, match="不一致"):
        drive_arena_with_ids(
            fish_ids=["expC:g0:fish0000", "expC:g0:fish0001"],
            genome_ids=["expC:g0:genome0000", "expC:g0:genome0001"],
            net=net,
            master_seed=1103,
            chain=chain,
            arena_config=ArenaConfig(),
            steps=1,
        )


def test_param_configs_loadable_for_experiment_c() -> None:
    # 冒烟：Experiment C 依赖的配置可解析（字段漂移由各模块守护测试负责）。
    assert read_yaml(MODEL_CONFIG)["network"]["sensory_dim"] == 12
    assert load_learning_config(MODEL_CONFIG).batch_size >= 1
    config = load_experiment_config()
    assert config.n_agents >= 1
    assert config.n_episodes >= 1
    assert config.n_danio >= config.n_agents, "候选池须不小于目标 agent 数（否则必然降级）"


def test_workers_parallel_matches_serial_bit_for_bit(tmp_path: Path, monkeypatch) -> None:
    """`workers > 1` **只提速、不改语义**：与串行结果逐位一致。

    48 个训练作业彼此独立，种子由 `(master_seed, t)` 派生、与调用顺序无关（`core §3` 正是为此
    设计）。故进程并行不改变任何 `theta`、任何指标。**唯一允许不同的是 latency**（wall-clock
    测量，属环境量而非计算结果），故比较时排除 `latency_*`。
    """
    kwargs = {"seeds": (1103,), "n_agents": 2, "n_episodes": 2}
    serial, _ = _run_small(tmp_path / "serial", monkeypatch, workers=1, **kwargs)
    parallel, _ = _run_small(tmp_path / "parallel", monkeypatch, workers=2, **kwargs)

    assert [m["model"] for m in serial.models] == [m["model"] for m in parallel.models]
    structure_keys = (
        "parameter_count",
        "active_edges",
        "macs_implemented",
        "macs_theoretical",
        "flops_implemented",
        "flops_theoretical",
    )
    for a, b in zip(serial.models, parallel.models, strict=True):
        assert a["n_agents"] == b["n_agents"]
        assert a["note"] == b["note"]
        # 指标必须逐位一致（含 mean / std / n）
        assert a["metrics"] == b["metrics"], f"{a['model']} 的指标随并行度变化了"
        for key in structure_keys:
            assert a["complexity"][key] == b["complexity"][key], f"{key} 随并行度变化了"
        # latency 是 wall-clock 量，允许不同，但必须仍是数值
        for key in ("latency_p50_ms", "latency_p95_ms"):
            assert isinstance(a["complexity"][key], float)
            assert isinstance(b["complexity"][key], float)


def test_workers_gt_one_actually_uses_the_pool(tmp_path: Path, monkeypatch) -> None:
    """`workers > 1` 必须**真的走进程池**（否则上一条等价性测试会因两条路径都串行而空过）。

    判据：并行跑完后，**主进程**的 `baseline_run._WORKER_CTX` 仍为空 —— 数据集只在子进程里加载；
    而串行路径会把它填满。
    """
    kwargs = {"seeds": (1103,), "n_agents": 2, "n_episodes": 2}
    baseline_run._WORKER_CTX.clear()
    _run_small(tmp_path / "serial", monkeypatch, workers=1, **kwargs)
    assert baseline_run._WORKER_CTX, "串行路径应在主进程内预热 _WORKER_CTX"

    baseline_run._WORKER_CTX.clear()
    _run_small(tmp_path / "parallel", monkeypatch, workers=2, **kwargs)
    assert baseline_run._WORKER_CTX == {}, (
        "并行路径下主进程不得加载数据集/持有训练上下文；"
        "若非空说明 executor 未真正传到 _evaluate_*（子进程池被绕过）"
    )
