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

    def advance(self, dt: float, world_w: float, world_h: float, boundary: str = "reflect") -> None:
        """Move by the NEW heading; boundary handling per that doc §2.1.

        ``reflect`` is a specular, fully deterministic bounce -- it draws no random
        numbers, so the per-step random stream is unaffected. ``clamp`` is kept only
        for contrast / historical reproduction.
        """
        self.pos = (
            self.pos + self.speed * np.array([np.cos(self.heading), np.sin(self.heading)]) * dt
        )
        if boundary == "clamp":
            self.pos[0] = min(max(self.pos[0], 0.0), world_w)
            self.pos[1] = min(max(self.pos[1], 0.0), world_h)
            return
        if boundary != "reflect":
            raise ValueError(f"world.boundary 取值非法：{boundary!r}（仅 reflect / clamp）")
        if self.pos[0] < 0.0:
            self.pos[0] = -self.pos[0]
            self.heading = float(np.pi) - self.heading
        elif self.pos[0] > world_w:
            self.pos[0] = 2.0 * world_w - self.pos[0]
            self.heading = float(np.pi) - self.heading
        if self.pos[1] < 0.0:
            self.pos[1] = -self.pos[1]
            self.heading = -self.heading
        elif self.pos[1] > world_h:
            self.pos[1] = 2.0 * world_h - self.pos[1]
            self.heading = -self.heading
        self.pos[0] = min(max(self.pos[0], 0.0), world_w)
        self.pos[1] = min(max(self.pos[1], 0.0), world_h)


@dataclass
class Fish(Entity):
    """A Danio individual driven by DanioNet (or ExpertPolicy for imitation)."""

    generation: int = 0
    genome_id: str = "unknown"
    energy: float = 1.0  # will be reset to e_max on spawn
    hunger: float = 0.0
    alive: bool = True
    # per-fish log buffers (Danio_Arena设计与实现说明.md section 13)
    energy_trace: list[float] = field(default_factory=list)
    size_trace: list[float] = field(default_factory=list)
    motor_log: list[tuple[float, float]] = field(default_factory=list)
    survival_steps: int = 0
    captures: int = 0
    # 每步至多 1 次：猎物进了（距离+前向锥）且判定了尺寸口径，不论吃到与否（§8）
    capture_attempts: int = 0
    encounters: int = 0
    predator_encounters: int = 0
    escape_successes: int = 0
    collisions: int = 0
    _prev_predator_rel: float = 0.0  # for looming rate
    # A8 threat-outcome escape window: set when a predator gives this fish up
    _threat_step: int | None = None
    _threat_source: str | None = None


@dataclass
class Prey(Entity):
    alive: bool = True


@dataclass
class Predator(Entity):
    target_fish_id: str | None = None
    alive: bool = True
    chase_steps: int = 0  # consecutive steps on this target (A8 limited chase)
    banned_fish_id: str | None = None  # gave up on it; ignored until it leaves detect


@dataclass
class Obstacle:
    obstacle_id: str
    pos: np.ndarray
    radius: float

    def contains(self, pos: np.ndarray, margin: float = 0.0) -> bool:
        return bool(np.linalg.norm(pos - self.pos) <= self.radius + margin)
