"""`experiment/expert_run.py` 单局 ExpertPolicy 编排（`实验与评价体系.md` §5.1）。"""

from __future__ import annotations

from pathlib import Path

from evogenesis.experiment.expert_run import run_episode

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "configs" / "default_arena.yaml"


def test_run_episode_deterministic_and_ids():
    a = run_episode(CFG, seed=1103, steps=6, experiment_id="exp-x")
    b = run_episode(CFG, seed=1103, steps=6, experiment_id="exp-x")
    assert a.steps_run == 6
    assert a.per_fish == b.per_fish
    assert all(fid.startswith("exp-x:g0:fish") for fid in a.fish_ids)
    assert a.spawn_seed != a.dynamics_seed


def test_run_episode_behavior_trace_only_when_enabled():
    off = run_episode(CFG, seed=1103, steps=4, experiment_id="exp-x")
    on = run_episode(CFG, seed=1103, steps=4, experiment_id="exp-x", emit_behavior_trace=True)
    assert off.trace == []
    assert on.trace and {r["fish_id"] for r in on.trace} <= set(on.fish_ids)


def test_run_episode_arena_seeds_follow_generation():
    """arena 子种子实体序号取 `generation`，跨代不复用同一随机流（`代循环编排 §4`）。"""
    from evogenesis.core.seed import SeedManager

    gen0 = run_episode(CFG, seed=1103, steps=2, experiment_id="exp-x", generation=0)
    gen3 = run_episode(CFG, seed=1103, steps=2, experiment_id="exp-x", generation=3)
    manager = SeedManager(1103)
    assert gen3.spawn_seed == manager.seed("arena_spawn", 3)
    assert gen3.dynamics_seed == manager.seed("arena_dynamics", 3)
    assert gen3.spawn_seed != gen0.spawn_seed
