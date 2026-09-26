"""Arena smoke + unit tests (arena/Danio_Arena设计与实现说明.md + acceptance checklist Arena section)."""

import numpy as np
import pytest

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.entities import Fish
from evogenesis.arena.env import DanioArena

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
    prey_id = next(iter(arena.prey))
    prey = arena.prey[prey_id]
    prey.pos = fish.pos + np.array([0.5, 0.0])  # well inside capture radius 1.2
    fish.pos = np.array([50.0, 30.0])
    prey.pos = np.array([50.5, 30.0])
    result = arena.step({"fish_00": (0.0, 0.0)})
    types = {e.type for e in result.events}
    assert "arena.prey_captured" in types
    assert not prey.alive
    assert fish.captures == 1
    # 0.5 - 0.0008 (base) + 0.12 (food) = 0.6192
    assert fish.energy == pytest.approx(0.6192, abs=1e-9)


def test_too_small_to_eat_attempt_logged():
    arena = make_arena()
    arena.reset()
    fish = arena.fish["fish_00"]
    prey_id = next(iter(arena.prey))
    prey = arena.prey[prey_id]
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
