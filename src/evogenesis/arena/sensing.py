"""12-dim sensory encoder (doc 05 section 2, doc 07 section 4).

Dimension order is FROZEN (acceptance checklist: "12 维输入顺序固定"):

    0 prey_left_signal      6 prey_relative_size
    1 prey_right_signal     7 predator_relative_size
    2 threat_left_signal    8 looming_rate
    3 threat_right_signal   9 current_speed
    4 obstacle_left_signal 10 energy
    5 obstacle_right_signal11 hunger

All values are in [0, 1]. Left/right split is by the sign of the entity's
bearing sine in the fish's heading frame; only entities inside the sensory
radius AND the FOV cone contribute (doc 07 section 4: no full-map knowledge).
"""

import numpy as np

from evogenesis.arena.entities import Fish, Obstacle, Predator, Prey

SENSORY_DIM = 12

#: human-readable names, index-aligned with the encoder output (schema ref)
DIM_NAMES = (
    "prey_left_signal", "prey_right_signal",
    "threat_left_signal", "threat_right_signal",
    "obstacle_left_signal", "obstacle_right_signal",
    "prey_relative_size", "predator_relative_size",
    "looming_rate", "current_speed", "energy", "hunger",
)


def _bearing(pos: np.ndarray, fish: Fish) -> tuple[float, float] | None:
    """Return (distance, relative bearing angle) of ``pos`` in fish frame,
    or None if outside radius or outside the FOV cone."""
    delta = np.asarray(pos, dtype=float) - fish.pos
    dist = float(np.linalg.norm(delta))
    if dist == 0.0:
        return 0.0, 0.0
    rel = float(np.arctan2(delta[1], delta[0]) - fish.heading)
    rel = np.arctan2(np.sin(rel), np.cos(rel))  # wrap to (-pi, pi]
    return dist, float(rel)


def _split_channels(
    fish: Fish,
    candidates: list[tuple[np.ndarray, float]],
    radius: float, half_fov: float,
) -> tuple[float, float]:
    """Sum linear-falloff intensities into (left, right) channels in [0, 1]."""
    left = right = 0.0
    for pos, _size in candidates:
        res = _bearing(pos, fish)
        if res is None:
            continue
        dist, rel = res
        if dist > radius or abs(rel) > half_fov:
            continue
        intensity = 1.0 - dist / radius
        if np.sin(rel) < 0.0:
            left += intensity
        else:
            right += intensity
    return min(left, 1.0), min(right, 1.0)


def _nearest_visible(
    fish: Fish,
    candidates: list[tuple[np.ndarray, float]],
    radius: float, half_fov: float,
) -> tuple[float, float] | None:
    """(distance, size) of the nearest visible candidate, or None."""
    best: tuple[float, float] | None = None
    for pos, size in candidates:
        res = _bearing(pos, fish)
        if res is None:
            continue
        dist, rel = res
        if dist > radius or abs(rel) > half_fov:
            continue
        if best is None or dist < best[0]:
            best = (dist, size)
    return best


def observe(
    fish: Fish,
    prey: list[Prey],
    predators: list[Predator],
    obstacles: list[Obstacle],
    radius: float,
    fov_degrees: float,
    current_speed: float,
    e_max: float,
    prev_predator_rel: float,
) -> np.ndarray:
    """Encode the frozen 12-dim observation for one fish."""
    half_fov = np.deg2rad(fov_degrees) / 2.0

    prey_c = [(p.pos, p.size) for p in prey if p.alive]
    pred_c = [(d.pos, d.size) for d in predators if d.alive]
    obst_c = [(o.pos, o.radius) for o in obstacles]

    prey_l, prey_r = _split_channels(fish, prey_c, radius, half_fov)
    threat_l, threat_r = _split_channels(fish, pred_c, radius, half_fov)
    obst_l, obst_r = _split_channels(fish, obst_c, radius, half_fov)

    nearest_prey = _nearest_visible(fish, prey_c, radius, half_fov)
    prey_rel = min(nearest_prey[1] / fish.size, 1.0) if nearest_prey else 0.0

    nearest_pred = _nearest_visible(fish, pred_c, radius, half_fov)
    pred_rel = min(nearest_pred[1] / fish.size / 2.5, 1.0) if nearest_pred else 0.0

    # looming: positive rate of change of nearest predator relative size,
    # scaled so that closing-in within ~1 s saturates the channel (MVP approx).
    looming = max(0.0, pred_rel - prev_predator_rel) * 10.0
    looming = min(looming, 1.0)

    energy_norm = min(max(fish.energy / e_max, 0.0), 1.0)

    obs = np.array([
        prey_l, prey_r,
        threat_l, threat_r,
        obst_l, obst_r,
        prey_rel, pred_rel,
        looming,
        min(max(current_speed, 0.0), 1.0),
        energy_norm,
        1.0 - energy_norm,  # hunger (doc 07 section 6: H = 1 - E/Emax)
    ], dtype=float)
    assert obs.shape == (SENSORY_DIM,)
    return obs
