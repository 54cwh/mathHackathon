"""Danio Arena: continuous 2-D ecology env (Danio_Arena设计与实现说明.md).

Deterministic given (config, master_seed). Emits the draft event vocabulary
from core/核心机制与数据流.md section 5.1 in dot form (arena.*, R11) plus
arena.fish_captured / arena.collision (vocabulary still DRAFT pending
joint freeze).
"""

from dataclasses import dataclass, field

import numpy as np

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.entities import Entity, Fish, Obstacle, Predator, Prey
from evogenesis.arena.policies import PredatorPolicy, PreyPolicy
from evogenesis.arena.sensing import nearest_predator_relative_size, observe

# Collision margin already used by the pre-existing obstacle test
# (o.contains(fish.pos, 0.1)); reused as the fish effective radius in the
# penetration-depth formula (section 18.7 A7), not invented anew.
FISH_RADIUS = 0.1


@dataclass(frozen=True)
class Event:
    seq: int
    step: int
    type: str
    payload: dict

    def to_dict(self) -> dict:
        return {"seq": self.seq, "type": self.type, "step": self.step, "payload": self.payload}


@dataclass
class StepResult:
    step: int
    done: bool
    events: list[Event] = field(default_factory=list)


class DanioArena:
    """Minimal runnable Arena: physics + sensing + energy + predation + events."""

    def __init__(self, config: ArenaConfig | None = None, master_seed: int = 0):
        self.cfg = config or ArenaConfig()
        self.master_seed = master_seed
        self.events: list[Event] = []
        self.fish: dict[str, Fish] = {}
        self.prey: dict[str, Prey] = {}
        self.predators: dict[str, Predator] = {}
        self.obstacles: list[Obstacle] = []
        self.step_idx = 0
        self._seq = 0
        self._episode_ended = False
        self._rng = np.random.default_rng(master_seed)
        self._prey_policy = PreyPolicy(
            speed=self.cfg.actors.prey_speed, turn_std=self.cfg.actors.wander_turn_std
        )
        self._pred_policy = PredatorPolicy(
            cruise_speed=self.cfg.actors.predator_cruise_speed,
            chase_speed=self.cfg.actors.predator_chase_speed,
            detection_radius=self.cfg.actors.predator_detection_radius,
            release_radius=self.cfg.actors.predator_release_radius,
        )

    def reset(self) -> None:
        self._rng = np.random.default_rng(self.master_seed)
        self.events.clear()
        self.step_idx = 0
        self._seq = 0
        self._episode_ended = False
        self.obstacles = []
        self._next_prey_id = self.cfg.population.n_prey
        self._spawn_obstacles()
        self.fish = {
            f"fish_{i:02d}": Fish(
                f"fish_{i:02d}",
                self._free_spot(2.0),
                float(self._rng.uniform(0, 2 * np.pi)),
                size=self.cfg.growth.initial_size,
                energy=self.cfg.energy.e_max,
            )
            for i in range(self.cfg.population.n_fish)
        }
        self.prey = {
            f"prey_{i:02d}": Prey(
                f"prey_{i:02d}",
                self._free_spot(1.0),
                float(self._rng.uniform(0, 2 * np.pi)),
                size=float(
                    self._rng.uniform(self.cfg.actors.prey_size_min, self.cfg.actors.prey_size_max)
                ),
            )
            for i in range(self.cfg.population.n_prey)
        }
        self.predators = {
            f"predator_{i:02d}": Predator(
                f"predator_{i:02d}",
                self._free_spot(3.0),
                float(self._rng.uniform(0, 2 * np.pi)),
                size=self.cfg.actors.predator_size,
            )
            for i in range(self.cfg.population.n_predators)
        }
        for eid in (*self.fish, *self.prey, *self.predators):
            self._emit("arena.spawn", {"entity_id": eid})

    def _spawn_obstacles(self) -> None:
        """Place obstacles one by one into ``self.obstacles`` (which must start
        empty) so later obstacles avoid earlier ones; keeps ``reset`` idempotent."""
        lo = self.cfg.actors.obstacle_radius_min
        hi = self.cfg.actors.obstacle_radius_max
        for i in range(self.cfg.population.n_obstacles):
            r = float(self._rng.uniform(lo, hi))
            pos = self._free_spot(r + 1.0)
            self.obstacles.append(Obstacle(f"obstacle_{i:02d}", pos, r))

    def _free_spot(self, clearance: float) -> np.ndarray:
        """Rejection-sample a position inside the world, outside obstacles."""
        w = self.cfg.world.width
        h = self.cfg.world.height
        for _ in range(200):
            pos = np.array([self._rng.uniform(0, w), self._rng.uniform(0, h)])
            if not any(o.contains(pos, clearance) for o in self.obstacles):
                return pos
        return np.array([w / 2, h / 2])

    def _emit(self, etype: str, payload: dict) -> Event:
        self._seq += 1
        ev = Event(self._seq, self.step_idx, etype, payload)
        self.events.append(ev)
        return ev

    def _omega_eff(self, fish: Fish, omega: float) -> float:
        """Danio_Arena设计与实现说明.md section 5: turning flexibility drops as size grows."""
        k = self.cfg.growth.turn_inertia_scale
        return omega / (1.0 + k * (fish.size - 1.0))

    # Reward for one prey (section 6/12): scales with prey size, normalised by the
    # midpoint of the prey size range so the MEAN reward equals energy.food_reward,
    # keeping the A3 energy budget (and its must-eat conclusion) intact.
    def _prey_reward(self, prey: Prey) -> float:
        s_bar = 0.5 * (self.cfg.actors.prey_size_min + self.cfg.actors.prey_size_max)
        return round(self.cfg.energy.food_reward * prey.size / s_bar, 6)

    # Section 8: the target must lie inside the HUNTER forward cone.
    # capture_cone_degrees is the TOTAL cone angle (half each side), applied
    # symmetrically to both predation directions.
    def _in_forward_cone(self, hunter: Entity, target_pos: np.ndarray, d: float) -> bool:
        if d <= 0.0:
            return True
        bearing = float(np.arctan2(target_pos[1] - hunter.pos[1], target_pos[0] - hunter.pos[0]))
        rel = float(np.arctan2(np.sin(bearing - hunter.heading), np.cos(bearing - hunter.heading)))
        half = float(np.deg2rad(self.cfg.growth.capture_cone_degrees) / 2.0)
        return abs(rel) <= half

    def _steer_away_from_obstacles(self, entity: Entity, gain: float = 0.5) -> None:
        """Rotate heading away from an obstacle we are about to hit."""
        look = (
            entity.pos
            + entity.speed * np.array([np.cos(entity.heading), np.sin(entity.heading)]) * 3.0
        )
        for o in self.obstacles:
            if o.contains(look):
                away = np.arctan2(entity.pos[1] - o.pos[1], entity.pos[0] - o.pos[0])
                diff = float(
                    np.arctan2(np.sin(away - entity.heading), np.cos(away - entity.heading))
                )
                entity.heading += float(np.sign(diff)) * gain
                return

    def observe(self, fish_id: str) -> np.ndarray:
        fish = self.fish[fish_id]
        return observe(
            fish,
            list(self.prey.values()),
            list(self.predators.values()),
            self.obstacles,
            radius=self.cfg.sensing.radius,
            fov_degrees=self.cfg.sensing.fov_degrees,
            current_speed=fish.speed,
            e_max=self.cfg.energy.e_max,
            prev_predator_rel=fish._prev_predator_rel,
        )

    def step(self, actions: dict[str, tuple[float, float]] | None = None) -> StepResult:
        actions = actions or {}
        if self._episode_ended:
            return StepResult(self.step_idx, True, [])
        dt = self.cfg.world.dt
        new_events: list[Event] = []

        # --- fish: turn, move, eat, pay energy (Danio_Arena设计与实现说明.md sections 5-8)
        for fid, fish in self.fish.items():
            if not fish.alive:
                continue
            omega, v = actions.get(fid, (0.0, 0.0))
            omega = float(np.clip(omega, -1.0, 1.0))
            v = float(np.clip(v, 0.0, 1.0))
            fish.motor_log.append((omega, v))

            fish.heading = fish.heading + self._omega_eff(fish, omega) * dt
            fish.speed = v
            fish.advance(dt, self.cfg.world.width, self.cfg.world.height, self.cfg.world.boundary)

            # obstacle contact: hard non-penetration (project back onto the surface, zero
            # bounce) + soft energy penalty by penetration depth (section 18.7 A7). The event
            # payload is left unchanged on purpose: the penalty is visible via energy_trace.
            penetration = 0.0
            for o in self.obstacles:
                gap = float(np.linalg.norm(fish.pos - o.pos))
                reaches = o.radius + FISH_RADIUS
                if gap <= reaches:
                    penetration = max(penetration, reaches - gap)
                    fish.collisions += 1
                    if gap > 0.0:
                        fish.pos = o.pos + (fish.pos - o.pos) * (reaches / gap)
                    else:
                        fish.pos = o.pos + np.array([reaches, 0.0])
                    new_events.append(
                        self._emit(
                            "arena.collision", {"fish_id": fid, "obstacle_id": o.obstacle_id}
                        )
                    )
                    break

            # predation on prey (Danio_Arena设计与实现说明.md section 8):
            # d < r_capture AND size >= kappa * prey_size AND target in the hunter
            # forward cone. encounters stays distance-only (S6).
            for prey in self.prey.values():
                if not prey.alive:
                    continue
                d = float(np.linalg.norm(prey.pos - fish.pos))
                if d >= self.cfg.growth.capture_radius:
                    continue
                fish.encounters += 1
                if not self._in_forward_cone(fish, prey.pos, d):
                    break  # in-radius prey is behind us: no attempt this step
                size_ratio = fish.size / prey.size
                if size_ratio >= self.cfg.growth.capture_size_ratio:
                    prey.alive = False
                    fish.captures += 1
                    fish.size = min(
                        self.cfg.growth.max_size,
                        float(
                            np.sqrt(fish.size**2 + self.cfg.growth.prey_area_gain * prey.size**2)
                        ),
                    )
                    new_events.append(
                        self._emit(
                            "arena.prey_captured",
                            {
                                "fish_id": fid,
                                "prey_id": prey.entity_id,
                                "distance": round(d, 3),
                                "size_ratio": round(size_ratio, 3),
                                "food_reward": self._prey_reward(prey),
                            },
                        )
                    )
                    break
                new_events.append(
                    self._emit(
                        "arena.capture_attempt",
                        {
                            "fish_id": fid,
                            "prey_id": prey.entity_id,
                            "distance": round(d, 3),
                            "size_ratio": round(size_ratio, 3),
                            "threshold": self.cfg.growth.capture_size_ratio,
                            "capture_radius": self.cfg.growth.capture_radius,
                            "result": "too_small_to_eat",
                        },
                    )
                )
                break  # one attempt per fish per step

            # energy (Danio_Arena设计与实现说明.md section 6):
            # E = clip(E - C_base - C_move*v^2 - C_pen*p + R_food*f(prey), 0, E_max)
            e = (
                fish.energy
                - self.cfg.energy.base_cost_per_step
                - self.cfg.energy.movement_cost_scale * v * v
                - self.cfg.energy.collision_penalty * penetration
            )
            for ev in new_events:
                if ev.type == "arena.prey_captured" and ev.payload["fish_id"] == fid:
                    e += ev.payload["food_reward"]
            fish.energy = min(max(e, 0.0), self.cfg.energy.e_max)
            fish.hunger = 1.0 - fish.energy / self.cfg.energy.e_max
            fish.energy_trace.append(fish.energy)
            fish.size_trace.append(fish.size)

            if fish.energy <= 0.0:
                fish.alive = False
                new_events.append(
                    self._emit(
                        "arena.energy_depleted",
                        {"fish_id": fid, "survival_steps": fish.survival_steps},
                    )
                )
                continue
            fish.survival_steps += 1

        # --- predator capture of fish (Danio_Arena设计与实现说明.md section 8 applies both ways)
        for pred in self.predators.values():
            if not pred.alive:
                continue
            fish_pos = {fid: f.pos for fid, f in self.fish.items() if f.alive}
            prev_target = pred.target_fish_id
            # a limited-chase ban expires once the fish is dead or out of detect range
            if pred.banned_fish_id is not None:
                banned_pos = fish_pos.get(pred.banned_fish_id)
                if (
                    banned_pos is None
                    or float(np.linalg.norm(banned_pos - pred.pos))
                    >= self.cfg.actors.predator_detection_radius
                ):
                    pred.banned_fish_id = None
            target, desired, speed = self._pred_policy.plan(
                pred.pos,
                pred.heading,
                prev_target,
                fish_pos,
                current_chase_steps=pred.chase_steps,
                banned_fish_id=pred.banned_fish_id,
            )
            # A8 limited chase: consecutive steps spent on the same fish
            pred.chase_steps = pred.chase_steps + 1 if target and target == prev_target else 0
            if target is None and prev_target is not None and prev_target in fish_pos:
                pred.banned_fish_id = prev_target  # gave up: do not instantly re-lock
            # A8 threat outcome: releasing a lock opens a survival window for that fish
            if prev_target is not None and target != prev_target and prev_target in self.fish:
                lost_fish = self.fish[prev_target]
                if lost_fish.alive:
                    lost_fish._threat_step = self.step_idx
                    lost_fish._threat_source = pred.entity_id
            if target is not None:
                locked = self.fish[target]
                locked._threat_step = None  # re-locked: the earlier window is void
                locked._threat_source = None
                if target != prev_target:
                    locked.predator_encounters += 1
            pred.target_fish_id = target
            diff = float(np.arctan2(np.sin(desired - pred.heading), np.cos(desired - pred.heading)))
            max_turn = self.cfg.actors.predator_turn_rate * dt
            pred.heading += float(np.clip(diff, -max_turn, max_turn))
            pred.speed = speed
            self._steer_away_from_obstacles(pred)
            pred.advance(dt, self.cfg.world.width, self.cfg.world.height)

            if target is None:
                continue
            fish = self.fish[target]
            d = float(np.linalg.norm(fish.pos - pred.pos))
            if (
                d < self.cfg.growth.capture_radius
                and pred.size >= self.cfg.growth.capture_size_ratio * fish.size
                and self._in_forward_cone(pred, fish.pos, d)
            ):
                fish.alive = False
                pred.target_fish_id = None
                new_events.append(
                    self._emit(
                        "arena.fish_captured",
                        {
                            "fish_id": target,
                            "predator_id": pred.entity_id,
                            "survival_steps": fish.survival_steps,
                        },
                    )
                )

        # --- prey wander (Danio_Arena设计与实现说明.md section 10)
        for prey in self.prey.values():
            if not prey.alive:
                continue
            omega, v = self._prey_policy.act(self._rng)
            prey.heading += omega * dt
            prey.speed = v
            self._steer_away_from_obstacles(prey, gain=2.0)
            prey.advance(dt, self.cfg.world.width, self.cfg.world.height, self.cfg.world.boundary)

        # --- prey regrowth (section 12, R2 open replenishment): deterministic timing
        regrow = self.cfg.population.prey_regrowth_steps
        if regrow > 0 and self.step_idx % regrow == 0:
            alive_prey = sum(1 for p in self.prey.values() if p.alive)
            if alive_prey < self.cfg.population.n_prey:
                pid = f"prey_{self._next_prey_id:02d}"
                self._next_prey_id += 1
                self.prey[pid] = Prey(
                    pid,
                    self._free_spot(1.0),
                    float(self._rng.uniform(0, 2 * np.pi)),
                    size=float(
                        self._rng.uniform(
                            self.cfg.actors.prey_size_min, self.cfg.actors.prey_size_max
                        )
                    ),
                )
                new_events.append(self._emit("arena.spawn", {"entity_id": pid}))

        # --- looming bookkeeping: reuse the encoder's own definition (nearest
        #     visible predator), so the differential is a genuine rate of change
        #     rather than a nearest-vs-largest aggregation artifact.
        predators = list(self.predators.values())
        for fish in self.fish.values():
            if not fish.alive:
                continue
            fish._prev_predator_rel = nearest_predator_relative_size(
                fish, predators, self.cfg.sensing.radius, self.cfg.sensing.fov_degrees
            )

        # --- A8 resolution: a released lock counts as an escape only once the fish
        #     has survived escape_hold_steps beyond the release (section 15).
        hold = self.cfg.actors.escape_hold_steps
        for fid, fish in self.fish.items():
            if fish._threat_step is None:
                continue
            if not fish.alive:
                fish._threat_step = None
                fish._threat_source = None
                continue
            if self.step_idx - fish._threat_step >= hold:
                new_events.append(
                    self._emit(
                        "arena.escape",
                        {"fish_id": fid, "threat_source": fish._threat_source},
                    )
                )
                fish.escape_successes += 1
                fish._threat_step = None
                fish._threat_source = None

        self.step_idx += 1
        # A9: always run the full episode; individual death only freezes that fish
        done = self.step_idx >= self.cfg.world.episode_steps
        if done:
            self._episode_ended = True
            new_events.append(
                self._emit(
                    "arena.episode_end",
                    {
                        "steps": self.step_idx,
                        "fish_alive": sum(1 for f in self.fish.values() if f.alive),
                        "prey_remaining": sum(1 for p in self.prey.values() if p.alive),
                    },
                )
            )

        new_events.sort(key=lambda e: e.seq)
        return StepResult(self.step_idx, done, new_events)

    def per_fish_log(self) -> dict[str, dict]:
        """Danio_Arena设计与实现说明.md section 13 per-fish record."""
        return {
            fid: {
                "generation": f.generation,
                "encounters": f.encounters,
                "captures": f.captures,
                "predator_encounters": f.predator_encounters,
                "escape_successes": f.escape_successes,
                "collisions": f.collisions,
                "energy_trajectory": f.energy_trace,
                "size_trajectory": f.size_trace,
                "survival_steps": f.survival_steps,
                "motor_commands": f.motor_log,
            }
            for fid, f in self.fish.items()
        }
