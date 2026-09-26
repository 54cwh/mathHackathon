"""ExpertPolicy 驱动的 Arena 单局编排（owner：`experiment/实验与评价体系.md` §5.1）。

基线 / 环境 pre-check 用 `ExpertPolicy` 驱动一局；业务逻辑（稳定 ID 铸造、A14 双子种子、
`expert_rollout` 驱动、整群 trace 收集）在本模块，`scripts/run_arena.py` 只做参数解析与落盘。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from evogenesis.arena.config import load_arena_config
from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import expert_policy_from_config
from evogenesis.core.ids import mint_id
from evogenesis.core.seed import SeedManager
from evogenesis.experiment.arena_rollout import expert_rollout
from evogenesis.experiment.behavior_trace import TraceCollector


@dataclass(frozen=True)
class ArenaRunResult:
    """一局 ExpertPolicy run 的产物（供入口脚本落盘）。"""

    per_fish: dict[str, dict]
    events: list
    elapsed: float
    trace: list[dict]
    done: bool
    steps_run: int
    fish_ids: list[str]
    spawn_seed: int
    dynamics_seed: int


def run_episode(
    cfg_path: str | Path,
    seed: int,
    steps: int,
    overrides: dict | None = None,
    emit_behavior_trace: bool = False,
    experiment_id: str = "run",
    generation: int = 0,
) -> ArenaRunResult:
    """跑一局，返回逐鱼记录/事件/墙钟/整群 trace。

    驱动循环走 `experiment/arena_rollout.py::expert_rollout`（与 BC 采集共用）。
    整群 trace 只在 `emit_behavior_trace=True` 时收集；死鱼止步（无观测即无记录）。
    """
    cfg = load_arena_config(cfg_path, overrides=overrides)
    fish_ids = [mint_id(experiment_id, "fish", generation, i) for i in range(cfg.population.n_fish)]
    genome_ids = [
        mint_id(experiment_id, "genome", generation, i) for i in range(cfg.population.n_fish)
    ]
    manager = SeedManager(seed)
    spawn_seed = manager.seed("arena_spawn", generation)
    dynamics_seed = manager.seed("arena_dynamics", generation)
    arena = DanioArena(
        cfg,
        spawn_seed=spawn_seed,
        dynamics_seed=dynamics_seed,
        fish_ids=fish_ids,
        genome_ids=genome_ids,
        generation=generation,
    )
    arena.reset()
    expert = expert_policy_from_config(cfg)
    collector = TraceCollector(arena) if emit_behavior_trace else None
    done = False
    steps_run = 0
    t0 = time.perf_counter()
    for rollout in expert_rollout(arena, steps=steps, expert=expert):
        if collector is not None:
            collector.add(rollout)
        done = rollout.done
        steps_run = rollout.step + 1
    trace = collector.records() if collector is not None else []
    elapsed = time.perf_counter() - t0
    return ArenaRunResult(
        per_fish=arena.per_fish_log(),
        events=list(arena.events),
        elapsed=elapsed,
        trace=trace,
        done=done,
        steps_run=steps_run,
        fish_ids=fish_ids,
        spawn_seed=spawn_seed,
        dynamics_seed=dynamics_seed,
    )


__all__ = ["ArenaRunResult", "run_episode"]
