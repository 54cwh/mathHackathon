"""`experiment/arena_rollout.py` 驱动契约测试。

守两件事：
1. `track_ids` 中的鱼（即使已死）每步给出**步前**观测（与手写「先 observe 再 step」逐值一致）；
2. `actions` 只覆盖存活鱼（死鱼不产动作）。
"""

from __future__ import annotations

import numpy as np

from evogenesis.arena.config import load_arena_config
from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import ExpertPolicy
from evogenesis.core.ids import mint_id
from evogenesis.core.seed import SeedManager
from evogenesis.experiment.arena_rollout import expert_rollout

EXPERIMENT_ID = "exp-roll"
MASTER_SEED = 1103
STEPS = 5
N_FISH = 4


def _make_arena() -> tuple[DanioArena, list[str]]:
    config = load_arena_config(
        "configs/default_arena.yaml",
        overrides={"world": {"episode_steps": STEPS}, "population": {"n_fish": N_FISH}},
    )
    fish_ids = [mint_id(EXPERIMENT_ID, "fish", 0, i) for i in range(N_FISH)]
    genome_ids = [mint_id(EXPERIMENT_ID, "genome", 0, i) for i in range(N_FISH)]
    manager = SeedManager(MASTER_SEED)
    arena = DanioArena(
        config,
        spawn_seed=manager.seed("arena_spawn", 0),
        dynamics_seed=manager.seed("arena_dynamics", 0),
        fish_ids=fish_ids,
        genome_ids=genome_ids,
    )
    arena.reset()
    return arena, fish_ids


def test_track_ids_yields_dead_fish_pre_step_observation():
    dead = mint_id(EXPERIMENT_ID, "fish", 0, 0)

    # 参照：手写「先 observe 再 step」循环
    reference: list[np.ndarray] = []
    arena_ref, _ = _make_arena()
    arena_ref.fish[dead].alive = False
    policy = ExpertPolicy()
    for _ in range(STEPS):
        reference.append(arena_ref.observe(dead))
        actions = {
            fid: policy(arena_ref.observe(fid))
            for fid, f in arena_ref.fish.items()
            if f.alive
        }
        arena_ref.step(actions)

    # 被测：expert_rollout(track_ids=...) 每步的观测
    arena_new, _ = _make_arena()
    arena_new.fish[dead].alive = False
    recorded: list[np.ndarray] = []
    for rollout in expert_rollout(
        arena_new, steps=STEPS, expert=ExpertPolicy(), track_ids=(dead,)
    ):
        assert dead in rollout.observations  # 死鱼也在（被跟踪）
        assert dead not in rollout.actions  # 但不产动作
        recorded.append(rollout.observations[dead])

    assert len(recorded) == STEPS
    for got, want in zip(recorded, reference, strict=True):
        assert np.array_equal(got, want)
