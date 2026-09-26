"""Arena smoke + unit tests (Danio_Arena设计与实现说明.md + acceptance checklist Arena section)."""

import dataclasses

import numpy as np
import pytest

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.entities import Entity, Fish, Prey
from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import PredatorPolicy

KNOWN_EVENTS = {
    "arena.spawn",
    "arena.prey_captured",
    "arena.capture_attempt",
    "arena.escape",
    "arena.energy_depleted",
    "arena.episode_end",
    "arena.fish_captured",
    "arena.collision",
}


def make_arena(seed: int = 7, **overrides) -> DanioArena:
    cfg = ArenaConfig()
    if overrides:
        cfg = ArenaConfig(**overrides)
    return DanioArena(cfg, master_seed=seed)


def test_reset_deterministic_same_seed():
    a1, a2 = make_arena(7), make_arena(7)
    a1.reset(), a2.reset()
    for fid in a1.fish:
        assert np.allclose(a1.fish[fid].pos, a2.fish[fid].pos)
        assert a1.fish[fid].heading == a2.fish[fid].heading
    for pid in a1.prey:
        assert np.allclose(a1.prey[pid].pos, a2.prey[pid].pos)
        assert a1.prey[pid].size == a2.prey[pid].size


def test_reset_different_seed_differs():
    a1, a2 = make_arena(7), make_arena(8)
    a1.reset(), a2.reset()
    assert not np.allclose(a1.fish["fish_00"].pos, a2.fish["fish_00"].pos)


def test_obs_shape_and_ranges():
    arena = make_arena()
    arena.reset()
    for fid in list(arena.fish)[:3]:
        obs = arena.observe(fid)
        assert obs.shape == (12,)
        assert np.all(np.isfinite(obs))
        assert np.all(obs >= 0.0) and np.all(obs <= 1.0)


def test_population_counts_match_frozen_defaults():
    arena = make_arena()
    arena.reset()
    assert len(arena.fish) == 12
    assert len(arena.prey) == 24
    assert len(arena.predators) == 3
    assert len(arena.obstacles) == 6


def test_capture_grants_food_reward():
    arena = make_arena()
    arena.reset()
    fish = arena.fish["fish_00"]
    fish.energy = 0.5
    fish.heading = 0.0  # prey below is dead ahead: inside the forward cone
    prey = arena.prey["prey_00"]
    fish.pos = np.array([50.0, 30.0])
    prey.pos = np.array([50.5, 30.0])
    size = prey.size
    result = arena.step({"fish_00": (0.0, 0.0)})
    types = {e.type for e in result.events}
    assert "arena.prey_captured" in types
    assert not prey.alive
    assert fish.captures == 1
    # section 12: the reward scales with prey size, normalised by the prey size
    # range midpoint (0.45) so the mean reward stays energy.food_reward = 0.12
    reward = round(0.12 * size / 0.45, 6)  # same rounding as _prey_reward
    captured = next(e for e in result.events if e.type == "arena.prey_captured")
    assert captured.payload["food_reward"] == pytest.approx(reward, abs=1e-6)
    assert fish.energy == pytest.approx(0.5 - 0.0008 + reward, abs=1e-9)


def test_too_small_to_eat_attempt_logged():
    arena = make_arena()
    arena.reset()
    fish = arena.fish["fish_00"]
    fish.heading = 0.0  # keep the prey inside the forward cone
    prey = arena.prey["prey_00"]
    prey.size = 1.5  # 1.0 / 1.5 = 0.667 < kappa 1.25 -> not eatable
    fish.pos = np.array([50.0, 30.0])
    prey.pos = np.array([50.5, 30.0])
    result = arena.step({"fish_00": (0.0, 0.0)})
    attempts = [e for e in result.events if e.type == "arena.capture_attempt"]
    assert attempts, "expected a capture_attempt event"
    assert attempts[0].payload["result"] == "too_small_to_eat"
    assert prey.alive


def test_starvation_death_event():
    arena = make_arena()
    arena.reset()
    fish = arena.fish["fish_00"]
    fish.energy = 0.0005  # below base cost -> dies this step
    result = arena.step({})
    assert not fish.alive
    depleted = [e for e in result.events if e.type == "arena.energy_depleted"]
    assert depleted and depleted[0].payload["fish_id"] == "fish_00"


def test_episode_terminates_at_max_steps():
    arena = make_arena()
    arena.reset()
    result = None
    for _ in range(600):
        result = arena.step({})
    assert result is not None and result.done
    end = [e for e in arena.events if e.type == "arena.episode_end"]
    assert end and end[0].payload["steps"] == 600


def test_turn_inertia_reduces_bigger_fish_turning():
    arena = make_arena()
    arena.reset()
    small = Fish("small", np.zeros(2), 0.0, size=1.0)
    big = Fish("big", np.zeros(2), 0.0, size=2.0)
    assert arena._omega_eff(small, 1.0) > arena._omega_eff(big, 1.0)


def test_all_events_in_known_vocabulary():
    arena = make_arena()
    arena.reset()
    for _ in range(120):
        arena.step({})
    for ev in arena.events:
        assert ev.type.startswith("arena.")
        assert ev.type in KNOWN_EVENTS


def test_per_fish_log_completeness():
    arena = make_arena()
    arena.reset()
    for _ in range(10):
        arena.step({})
    log = arena.per_fish_log()
    required = {
        "generation",
        "encounters",
        "captures",
        "predator_encounters",
        "escape_successes",
        "collisions",
        "energy_trajectory",
        "size_trajectory",
        "survival_steps",
        "motor_commands",
    }
    for fid, rec in log.items():
        assert required.issubset(rec.keys()), fid
        assert len(rec["energy_trajectory"]) == rec["survival_steps"]


def test_reset_idempotent_on_same_instance():
    arena = make_arena(7)
    arena.reset()
    fish = {fid: f.pos.copy() for fid, f in arena.fish.items()}
    obstacles = [(o.pos.copy(), o.radius) for o in arena.obstacles]
    arena.reset()
    for fid, pos in fish.items():
        assert np.allclose(arena.fish[fid].pos, pos), fid
    for obstacle, (pos, radius) in zip(arena.obstacles, obstacles, strict=True):
        assert np.allclose(obstacle.pos, pos)
        assert obstacle.radius == radius


def test_step_after_episode_end_is_inert():
    arena = make_arena()
    arena.reset()
    result = None
    for _ in range(600):
        result = arena.step({})
    assert result is not None and result.done
    assert arena.step_idx == 600
    end_count = sum(1 for e in arena.events if e.type == "arena.episode_end")
    result = arena.step({})
    assert result.done
    assert arena.step_idx == 600
    assert sum(1 for e in arena.events if e.type == "arena.episode_end") == end_count


def test_dead_fish_not_credited_escape():
    arena = make_arena(3)
    arena.reset()
    pred = next(iter(arena.predators.values()))
    pred.target_fish_id = "fish_00"
    arena.fish["fish_00"].alive = False
    result = arena.step({})
    assert arena.fish["fish_00"].escape_successes == 0
    assert not [e for e in result.events if e.type == "arena.escape"]


def test_predator_encounter_recorded_on_acquisition():
    arena = make_arena()
    arena.reset()
    pred = arena.predators["predator_00"]
    pred.pos = np.array([50.0, 30.0])
    pred.target_fish_id = None
    for f in arena.fish.values():
        f.pos = np.array([5.0, 5.0])
    arena.fish["fish_00"].pos = np.array([52.0, 30.0])
    arena.step({})
    assert arena.fish["fish_00"].predator_encounters >= 1


def _cfg(
    pred_size: float | None = None, kappa: float | None = None, cap_r: float | None = None
) -> ArenaConfig:
    """Default config with selected growth/actor fields overridden."""
    cfg = ArenaConfig()
    return dataclasses.replace(
        cfg,
        growth=dataclasses.replace(
            cfg.growth,
            capture_radius=cfg.growth.capture_radius if cap_r is None else cap_r,
            capture_size_ratio=cfg.growth.capture_size_ratio if kappa is None else kappa,
        ),
        actors=dataclasses.replace(
            cfg.actors,
            predator_size=cfg.actors.predator_size if pred_size is None else pred_size,
        ),
    )


def _fish_captured(cfg: ArenaConfig, size: float) -> bool:
    """Put one predator next to one fish of the given size; was it eaten?"""
    arena = DanioArena(cfg, master_seed=7)
    arena.reset()
    for pid in list(arena.predators)[1:]:
        arena.predators[pid].pos = np.array([0.0, 0.0])
        arena.predators[pid].target_fish_id = None
    victim, hunter = arena.fish["fish_00"], arena.predators["predator_00"]
    victim.size = size
    victim.pos = np.array([50.0, 30.0])
    hunter.pos = np.array([50.05, 30.0])
    hunter.heading = float(np.pi)  # victim is at -x: face it (forward cone)
    hunter.target_fish_id = "fish_00"
    res = arena.step({})
    return any(
        e.type == "arena.fish_captured" and e.payload["fish_id"] == "fish_00" for e in res.events
    )


def test_predator_size_coupling_invariant():
    """section 8: predator_size >= kappa * max_size, else the biggest fish is immune.

    size is clamped at max_size, so an immune max-size fish stays immune.
    """
    cfg = ArenaConfig()
    assert cfg.actors.predator_size >= cfg.growth.capture_size_ratio * cfg.growth.max_size


def test_capture_boundary_is_inclusive_at_max_size():
    """section 8: the judgement includes its boundary (regression guard).

    The hunter is pointed at the victim so the forward-cone gate passes.
    """
    cfg = _cfg(pred_size=3.125, kappa=1.25, cap_r=4.61)
    assert cfg.actors.predator_size == cfg.growth.capture_size_ratio * cfg.growth.max_size
    assert _fish_captured(cfg, cfg.growth.max_size - 1e-6) is True
    assert _fish_captured(cfg, cfg.growth.max_size) is True
    assert _fish_captured(cfg, cfg.growth.max_size + 1e-6) is False


def test_prey_capture_boundary_is_inclusive():
    """section 8, fish-eats-prey side: size_ratio == kappa still eats (cone aligned)."""
    cfg = _cfg(cap_r=10.0)
    for size, expect_alive in ((1.0, False), (1.0 * (1 + 1e-6), True)):
        arena = DanioArena(cfg, master_seed=7)
        arena.reset()
        for pid in list(arena.prey)[1:]:
            arena.prey[pid].pos = np.array([0.0, 0.0])
        fish = arena.fish["fish_00"]
        fish.heading = 0.0  # prey at +x is dead ahead (forward cone)
        fish.size = 1.25
        prey = arena.prey["prey_00"]
        prey.size = size
        fish.pos = np.array([50.0, 30.0])
        prey.pos = np.array([50.5, 30.0])
        arena.step({})
        assert prey.alive is expect_alive, f"prey.size={size}"


def test_forward_cone_blocks_capture_from_behind():
    """section 8: a prey inside r_capture but behind the hunter is not eatable,
    while encounters keeps its distance-only meaning (S6)."""
    arena = make_arena()
    arena.reset()
    fish = arena.fish["fish_00"]
    fish.heading = 0.0  # facing +x
    prey = arena.prey["prey_00"]
    fish.pos = np.array([50.0, 30.0])
    prey.pos = np.array([49.5, 30.0])  # 0.5 behind the hunter, inside r_capture
    before = fish.encounters
    result = arena.step({"fish_00": (0.0, 0.0)})
    types = {e.type for e in result.events}
    assert "arena.prey_captured" not in types
    assert "arena.capture_attempt" not in types
    assert prey.alive
    assert fish.encounters == before + 1  # contact still counted (S6)


def test_boundary_reflect_is_deterministic_and_inbounds():
    """section 2.1: reflect is specular, draws no RNG, and keeps entities inside."""
    ent = Entity("e", np.array([0.01, 30.0]), float(np.pi), speed=1.0)
    ent.advance(0.05, 100.0, 60.0, "reflect")  # moves to x = -0.04
    assert 0.0 <= ent.pos[0] <= 100.0
    assert ent.pos[0] == pytest.approx(0.04, abs=1e-12)
    assert ent.heading == pytest.approx(0.0, abs=1e-12)  # theta -> pi - theta


def test_boundary_clamp_is_still_available():
    ent = Entity("e", np.array([0.01, 30.0]), float(np.pi), speed=1.0)
    ent.advance(0.05, 100.0, 60.0, "clamp")
    assert ent.pos[0] == 0.0


def test_boundary_config_default_and_validation():
    assert ArenaConfig().world.boundary == "reflect"
    with pytest.raises(ValueError, match="boundary"):
        Entity("e", np.zeros(2), 0.0).advance(0.05, 100.0, 60.0, "wrap")


def test_area_conservation_growth():
    """section 7: size <- min(max_size, sqrt(size^2 + g * prey_size^2))."""
    arena = make_arena()
    arena.reset()
    fish = arena.fish["fish_00"]
    fish.heading = 0.0
    prey = arena.prey["prey_00"]
    fish.pos, prey.pos = np.array([50.0, 30.0]), np.array([50.5, 30.0])
    size0, psize = fish.size, prey.size
    arena.step({"fish_00": (0.0, 0.0)})
    g = arena.cfg.growth.prey_area_gain
    expect = min(arena.cfg.growth.max_size, float(np.sqrt(size0**2 + g * psize**2)))
    assert fish.size == pytest.approx(expect, abs=1e-12)
    assert fish.size > size0  # visible in-episode growth


def test_prey_reward_is_mean_preserving():
    """section 6/12: at the prey size midpoint the reward equals energy.food_reward."""
    arena = make_arena()
    arena.reset()
    s_bar = 0.5 * (arena.cfg.actors.prey_size_min + arena.cfg.actors.prey_size_max)
    mid = Prey("p", np.zeros(2), 0.0, size=s_bar)
    assert arena._prey_reward(mid) == pytest.approx(arena.cfg.energy.food_reward, abs=1e-9)


def test_prey_regrowth_refills_toward_capacity():
    """section 12 (R2): deterministic regrowth tops the prey pool back up."""
    cfg = ArenaConfig()
    cfg = dataclasses.replace(
        cfg,
        population=dataclasses.replace(cfg.population, prey_regrowth_steps=1),
    )
    arena = DanioArena(cfg, master_seed=7)
    arena.reset()
    assert len(arena.prey) == 24
    for pid in ("prey_00", "prey_01", "prey_02"):
        arena.prey[pid].alive = False
    for _ in range(3):
        arena.step({})
    assert len(arena.prey) == 27  # one spawn per step while below capacity
    assert {"prey_24", "prey_25", "prey_26"} <= set(arena.prey)
    assert all(arena.prey[f"prey_{i}"].alive for i in (24, 25, 26))
    assert (
        sum(
            1
            for e in arena.events
            if e.type == "arena.spawn" and e.payload["entity_id"] == "prey_24"
        )
        == 1
    )


def test_escape_requires_survival_window():
    """section 15 (A8): a released lock counts as an escape only after T_hold steps."""
    cfg = ArenaConfig()
    cfg = dataclasses.replace(cfg, actors=dataclasses.replace(cfg.actors, escape_hold_steps=3))
    arena = DanioArena(cfg, master_seed=7)
    arena.reset()
    hunter = arena.predators["predator_00"]
    for pid in list(arena.predators)[1:]:
        arena.predators[pid].pos = np.array([0.0, 0.0])
        arena.predators[pid].target_fish_id = None
    arm = arena.fish["fish_00"]
    hunter.pos, hunter.target_fish_id = np.array([50.0, 30.0]), "fish_00"
    arm.pos = np.array([52.0, 30.0])
    arena.step({})  # lock held: no escape yet
    assert arm.escape_successes == 0
    arm.pos = np.array([5.0, 55.0])  # far beyond release/detect: the hunter gives up
    arena.step({})  # hunter releases -> the survival window opens
    assert arm._threat_step is not None
    for _ in range(3):  # hold = 3
        if arm.escape_successes:
            break
        arena.step({})
    assert arm.escape_successes == 1
    assert (
        sum(
            1
            for e in arena.events
            if e.type == "arena.escape" and e.payload["fish_id"] == "fish_00"
        )
        == 1
    )


def test_extinction_does_not_end_episode_early():
    """section 15 (A9): the episode always runs the full 600 steps."""
    arena = make_arena()
    arena.reset()
    for f in arena.fish.values():
        f.alive = False
    result = arena.step({})
    assert not result.done
    assert arena.step_idx == 1


def test_predator_gives_up_after_limited_chase():
    """section 9 (A8): max_chase_steps bounds a single pursuit."""
    pol = PredatorPolicy(max_chase_steps=3)
    pos = np.array([50.0, 30.0])
    fishes = {"fish_00": np.array([52.0, 30.0])}
    held = pol.plan(pos, 0.0, "fish_00", fishes, current_chase_steps=2)
    assert held[0] == "fish_00"
    gaveup = pol.plan(pos, 0.0, "fish_00", fishes, current_chase_steps=3)
    assert gaveup[0] is None and gaveup[2] == pol.cruise_speed
    banned = pol.plan(pos, 0.0, None, fishes, banned_fish_id="fish_00")
    assert banned[0] is None, "a banned fish is not re-acquired inside detect radius"
