"""Arena entities: fish, prey, predators, obstacles."""

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Entity:
    """Base moving entity in continuous 2-D space."""

    entity_id: str
    pos: np.ndarray  # [x, y]
    heading: float  # theta, radians
    speed: float = 0.0
    size: float = 1.0

    def advance(self, dt: float, world_w: float, world_h: float) -> None:
        """Danio_Arena设计规范.md section 5: theta_{t+1} = theta_t + omega*dt was applied by caller;
        position uses the NEW heading."""
        self.pos = (
            self.pos + self.speed * np.array([np.cos(self.heading), np.sin(self.heading)]) * dt
        )
        self.pos[0] = min(max(self.pos[0], 0.0), world_w)
        self.pos[1] = min(max(self.pos[1], 0.0), world_h)


@dataclass
class Fish(Entity):
    """A Danio individual driven by DanioNet (or ExpertPolicy for imitation)."""

    generation: int = 0
    genome_id: str = "unknown"
    energy: float = 1.0  # will be reset to e_max on spawn
    hunger: float = 0.0
    biomass: float = 0.0
    alive: bool = True
    # per-fish log buffers (Danio_Arena设计规范.md section 13)
    energy_trace: list[float] = field(default_factory=list)
    size_trace: list[float] = field(default_factory=list)
    motor_log: list[tuple[float, float]] = field(default_factory=list)
    survival_steps: int = 0
    captures: int = 0
    encounters: int = 0
    predator_encounters: int = 0
    escape_successes: int = 0
    collisions: int = 0
    _prev_predator_rel: float = 0.0  # for looming rate


@dataclass
class Prey(Entity):
    alive: bool = True


@dataclass
class Predator(Entity):
    target_fish_id: str | None = None
    alive: bool = True


@dataclass
class Obstacle:
    obstacle_id: str
    pos: np.ndarray
    radius: float

    def contains(self, pos: np.ndarray, margin: float = 0.0) -> bool:
        return bool(np.linalg.norm(pos - self.pos) <= self.radius + margin)
