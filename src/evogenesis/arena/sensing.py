"""12-dim sensory encoder (connectome/DanioNet设计规范.md section 2,
Danio_Arena设计与实现说明.md section 4).

Dimension order is FROZEN (acceptance checklist: "12 维输入顺序固定"):

    0 prey_left_signal      6 prey_relative_size
    1 prey_right_signal     7 predator_relative_size
    2 threat_left_signal    8 looming_rate
    3 threat_right_signal   9 current_speed
    4 obstacle_left_signal 10 energy
    5 obstacle_right_signal11 hunger

All values are in [0, 1]. Left/right split is by the sign of the entity's
bearing sine in the fish's heading frame; only entities inside the sensory
radius AND the FOV cone contribute (Danio_Arena设计与实现说明.md section 4: no full-map knowledge).
"""

import numpy as np

from evogenesis.arena.entities import Fish, Obstacle, Predator, Prey

SENSORY_DIM = 12

#: human-readable names, index-aligned with the encoder output (schema ref)
DIM_NAMES = (
    "prey_left_signal",
    "prey_right_signal",
    "threat_left_signal",
    "threat_right_signal",
    "obstacle_left_signal",
    "obstacle_right_signal",
    "prey_relative_size",
    "predator_relative_size",
    "looming_rate",
    "current_speed",
    "energy",
    "hunger",
)


def _bearing(pos: np.ndarray, fish: Fish) -> tuple[float, float]:
    """Return (distance, relative bearing angle) of ``pos`` in the fish frame.

    Always returns a pair; radius / FOV filtering is the caller's job (see
    ``_split_channels`` / ``_nearest_visible`` / ``max_predator_angular_size``).
    """
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
    radius: float,
    half_fov: float,
) -> tuple[float, float]:
    """Sum linear-falloff intensities into (left, right) channels in [0, 1]."""
    left = right = 0.0
    for pos, _size in candidates:
        dist, rel = _bearing(pos, fish)
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
    radius: float,
    half_fov: float,
) -> tuple[float, float] | None:
    """(distance, size) of the nearest visible candidate, or None."""
    best: tuple[float, float] | None = None
    for pos, size in candidates:
        dist, rel = _bearing(pos, fish)
        if dist > radius or abs(rel) > half_fov:
            continue
        if best is None or dist < best[0]:
            best = (dist, size)
    return best


def nearest_predator_relative_size(
    fish: Fish,
    predators: list[Predator],
    radius: float,
    fov_degrees: float,
    *,
    size_ref: float = 2.5,
) -> float:
    """Relative size of the nearest visible predator, in [0, 1].

    Single source of truth for the encoder's ``predator_relative_size``.
    ``size_ref`` 为归一参考（`arena §4.1`，config `sensing.predator_size_ref`）。
    """
    half_fov = np.deg2rad(fov_degrees) / 2.0
    cand = [(d.pos, d.size) for d in predators]
    nearest = _nearest_visible(fish, cand, radius, half_fov)
    return min(nearest[1] / fish.size / size_ref, 1.0) if nearest else 0.0


def max_predator_angular_size(
    fish: Fish,
    predators: list[Predator],
    radius: float,
    fov_degrees: float,
) -> float:
    """Max angular size θ (rad) over visible predators, or 0.0 if none.

    编码口径（`arena §4.1` / `A1` / `research/reference/looming-and-growth.md`）：
    \\(\\theta = 2\\arctan((size/2)/r)\\)，对「视野半径 + FOV 内」的**所有**天敌取 **max**
    （多头天敌以最具威胁者为准，与所引依据一致）。
    """
    half_fov = np.deg2rad(fov_degrees) / 2.0
    best = 0.0
    for predator in predators:
        dist, rel = _bearing(predator.pos, fish)
        if dist > radius or abs(rel) > half_fov or dist <= 0.0:
            continue
        theta = float(2.0 * np.arctan((predator.size / 2.0) / dist))
        best = max(best, theta)
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
    looming_rate: float,
    predator_size_ref: float = 2.5,
) -> np.ndarray:
    """Encode the frozen 12-dim observation for one fish."""
    half_fov = np.deg2rad(fov_degrees) / 2.0

    prey_c = [(p.pos, p.size) for p in prey if p.alive]
    pred_c = [(d.pos, d.size) for d in predators]
    obst_c = [(o.pos, o.radius) for o in obstacles]

    prey_l, prey_r = _split_channels(fish, prey_c, radius, half_fov)
    threat_l, threat_r = _split_channels(fish, pred_c, radius, half_fov)
    obst_l, obst_r = _split_channels(fish, obst_c, radius, half_fov)

    nearest_prey = _nearest_visible(fish, prey_c, radius, half_fov)
    prey_rel = min(nearest_prey[1] / fish.size, 1.0) if nearest_prey else 0.0

    pred_rel = nearest_predator_relative_size(
        fish, predators, radius, fov_degrees, size_ref=predator_size_ref
    )

    # looming：由 env 在步首按角尺寸扩张率 `(Δθ/θ)/Δt / R_loom` 算好并缓存（`arena §4.1`），
    # 编码器只做截断（不在此差分，避免"prev 刷新时序"再次退化为常数）。
    looming = min(max(looming_rate, 0.0), 1.0)

    energy_norm = min(max(fish.energy / e_max, 0.0), 1.0)

    obs = np.array(
        [
            prey_l,
            prey_r,
            threat_l,
            threat_r,
            obst_l,
            obst_r,
            prey_rel,
            pred_rel,
            looming,
            min(max(current_speed, 0.0), 1.0),
            energy_norm,
            1.0 - energy_norm,  # hunger (Danio_Arena设计与实现说明.md section 6: H = 1 - E/Emax)
        ],
        dtype=float,
    )
    assert obs.shape == (SENSORY_DIM,)
    return obs
