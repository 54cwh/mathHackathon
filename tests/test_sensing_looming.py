"""looming_rate（12 维第 9 维）携带信息且不可见时归零（`arena §4.1` / A1 / M13 修复回归）。"""

from __future__ import annotations

import numpy as np

from evogenesis.arena.config import load_arena_config
from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import ExpertPolicy
from evogenesis.core.seed import SeedManager

MASTER_SEED = 1103
STEPS = 40


def _arena(overrides: dict | None = None):
    config = load_arena_config("configs/default_arena.yaml", overrides=overrides)
    manager = SeedManager(MASTER_SEED)
    arena = DanioArena(
        config,
        spawn_seed=manager.seed("arena_spawn", 0),
        dynamics_seed=manager.seed("arena_dynamics", 0),
    )
    arena.reset()
    return arena


def _looming_series(arena) -> list[float]:
    expert = ExpertPolicy()
    values: list[float] = []
    for _ in range(STEPS):
        obs = {fid: arena.observe(fid) for fid, f in arena.fish.items() if f.alive}
        values.extend(float(o[8]) for o in obs.values())
        arena.step({fid: expert(o) for fid, o in obs.items()})
    return values


def test_looming_carries_information():
    """修复后 looming 不再恒 0（默认环境天敌会逼近）。"""
    values = np.array(_looming_series(_arena()))
    assert values.size > 0
    assert 0.0 <= values.min() and values.max() <= 1.0
    assert (values > 0.0).any(), "looming 仍恒 0：差分相位未修复"


def test_looming_zero_when_no_predator_visible():
    values = np.array(_looming_series(_arena({"population": {"n_predators": 0}})))
    assert values.size > 0
    assert (values == 0.0).all()


def test_looming_norm_scales_channel():
    """`sensing.looming_norm`（R_loom）为分母：越大输出越小。"""
    small = np.max(_looming_series(_arena({"sensing": {"looming_norm": 1.0}})))
    large = np.max(_looming_series(_arena({"sensing": {"looming_norm": 7.0}})))
    assert small > large > 0.0


def test_looming_zero_when_predator_out_of_sight():
    """天敌在感知半径外（不可见）→ looming 记 0。"""
    arena = _arena()
    far = np.array([arena.cfg.world.width, arena.cfg.world.height])
    for predator in arena.predators.values():
        predator.pos = far
        predator.target_fish_id = None
    values = np.array(_looming_series(arena))
    assert (values == 0.0).all()
