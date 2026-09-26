"""H3 历史依赖探针测试（`arena §14`）。

构造场景：鱼正前方放一只猎物（可见）→ 移走后连续不可见达 `D` 步触发 trial → 回到期望位置判 success。
另测：默认关闭、reset 清零。
"""

from __future__ import annotations

import numpy as np

from evogenesis.arena.config import ArenaConfig, ProbeConfig
from evogenesis.arena.entities import Prey
from evogenesis.arena.env import DanioArena


def _arena(**probe) -> DanioArena:
    cfg = ArenaConfig(probe=ProbeConfig(enabled=True, **probe))
    arena = DanioArena(cfg, spawn_seed=1, dynamics_seed=1)
    arena.reset()
    return arena


def _isolate(arena: DanioArena, fid: str) -> tuple:
    """清掉其它实体，只留一只正前方猎物；返回 (fish, prey)。"""
    fish = arena.fish[fid]
    prey = Prey("prey_00", np.array([55.0, 30.0]), 0.0, size=0.4)
    arena.prey = {"prey_00": prey}
    arena.predators = {}
    arena.obstacles = []
    fish.pos = np.array([50.0, 30.0])
    fish.heading = 0.0
    fish.alive = True
    return fish, prey


def test_probe_trial_then_success() -> None:
    arena = _arena(delay_steps=2, return_radius=1.0, window_steps=5)
    fid = next(iter(arena.fish))
    fish, prey = _isolate(arena, fid)

    arena.step({})  # 猎物可见 → 记 last_seen
    assert fish._last_seen_prey_pos is not None

    prey.pos = np.array([5.0, 5.0])  # 远离 → 不可见
    arena.step({})
    arena.step({})  # 连续 2 步不可见 → 触发 trial
    assert fish.probe_trials == 1

    fish.pos = np.array([55.0, 30.0])  # 回到期望位置
    arena.step({})
    assert fish.probe_successes == 1

    report = arena.h3_probe_report()
    assert report["trials"] >= 1
    assert report["successes"] >= 1
    assert report["P"] is not None


def test_probe_disabled_by_default() -> None:
    assert ArenaConfig().probe.enabled is False
    arena = DanioArena(ArenaConfig(), spawn_seed=1, dynamics_seed=1)
    arena.reset()
    arena.step({})
    assert arena.h3_probe_report()["trials"] == 0


def test_probe_window_expiry_counts_no_success() -> None:
    arena = _arena(delay_steps=1, return_radius=0.5, window_steps=2)
    fid = next(iter(arena.fish))
    fish, prey = _isolate(arena, fid)
    arena.step({})  # 看见
    prey.pos = np.array([5.0, 5.0])
    arena.step({})  # 不可见 1 步 → trial（window=2）
    assert fish.probe_trials == 1
    fish.pos = np.array([10.0, 10.0])  # 远离期望位置
    arena.step({})
    arena.step({})  # 窗口耗尽
    assert fish.probe_successes == 0


def test_probe_reset_clears_state() -> None:
    arena = _arena(delay_steps=1, return_radius=1.0, window_steps=3)
    fid = next(iter(arena.fish))
    _isolate(arena, fid)
    arena.step({})
    arena.reset()
    assert all(f.probe_trials == 0 and f.probe_successes == 0 for f in arena.fish.values())
