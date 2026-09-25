"""Danio Arena: continuous 2-D ecology env (doc 07).

Deterministic given (config, master_seed). Emits the draft event vocabulary
from docs/data-pipeline.md section 5.1 in dot form (arena.*, R11) plus
arena.fish_captured / arena.collision (vocabulary still DRAFT pending
joint freeze).
"""

from dataclasses import dataclass, field

import numpy as np

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.entities import Entity, Fish, Obstacle, Predator, Prey
from evogenesis.arena.policies import PredatorPolicy, PreyPolicy
from evogenesis.arena.sensing import nearest_predator_relative_size, observe


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
        """Doc 07 section 5: turning flexibility drops as size grows."""
        k = self.cfg.growth.turn_inertia_scale
        return omega / (1.0 + k * (fish.size - 1.0))

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

        # --- fish: turn, move, eat, pay energy (doc 07 sections 5-8)
        for fid, fish in self.fish.items():
            if not fish.alive:
                continue
            omega, v = actions.get(fid, (0.0, 0.0))
            omega = float(np.clip(omega, -1.0, 1.0))
            v = float(np.clip(v, 0.0, 1.0))
            fish.motor_log.append((omega, v))

            fish.heading = fish.heading + self._omega_eff(fish, omega) * dt
            fish.speed = v
            fish.advance(dt, self.cfg.world.width, self.cfg.world.height)

            for o in self.obstacles:
                if o.contains(fish.pos, 0.1):
                    fish.collisions += 1
                    new_events.append(
                        self._emit(
                            "arena.collision", {"fish_id": fid, "obstacle_id": o.obstacle_id}
                        )
                    )
                    break

            # predation on prey (doc 07 section 8):
            # d < r_capture AND size > kappa * prey_size
            for prey in self.prey.values():
                if not prey.alive:
                    continue
                d = float(np.linalg.norm(prey.pos - fish.pos))
                if d >= self.cfg.growth.capture_radius:
                    continue
                fish.encounters += 1
                size_ratio = fish.size / prey.size
                if size_ratio > self.cfg.growth.capture_size_ratio:
                    prey.alive = False
                    fish.captures += 1
                    fish.biomass += prey.size
                    fish.size = min(
                        self.cfg.growth.max_size,
                        fish.size + self.cfg.growth.biomass_to_size_gain * prey.size,
                    )
                    new_events.append(
                        self._emit(
                            "arena.prey_captured",
                            {
                                "fish_id": fid,
                                "prey_id": prey.entity_id,
                                "distance": round(d, 3),
                                "size_ratio": round(size_ratio, 3),
                                "food_reward": self.cfg.energy.food_reward,
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

            # energy (doc 07 section 6):
            # E = clip(E - C_base - C_move*v^2 + R_food, 0, E_max)
            e = (
                fish.energy
                - self.cfg.energy.base_cost_per_step
                - self.cfg.energy.movement_cost_scale * v * v
            )
            for ev in new_events:
                if ev.type == "arena.prey_captured" and ev.payload["fish_id"] == fid:
                    e += self.cfg.energy.food_reward
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

        # --- predator capture of fish (doc 07 section 8 applies both ways)
        for pred in self.predators.values():
            if not pred.alive:
                continue
            fish_pos = {fid: f.pos for fid, f in self.fish.items() if f.alive}
            target, desired, speed = self._pred_policy.plan(
                pred.pos, pred.heading, pred.target_fish_id, fish_pos
            )
            prev_target = pred.target_fish_id
            if prev_target is not None and target != prev_target:
                lost_fish = self.fish.get(prev_target)
                if lost_fish is not None and lost_fish.alive:
                    new_events.append(
                        self._emit(
                            "arena.escape",
                            {"fish_id": prev_target, "threat_source": pred.entity_id},
                        )
                    )
                    lost_fish.escape_successes += 1
            if target is not None and target != prev_target:
                self.fish[target].predator_encounters += 1
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
                and pred.size > self.cfg.growth.capture_size_ratio * fish.size
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

        # --- prey wander (doc 07 section 10)
        for prey in self.prey.values():
            if not prey.alive:
                continue
            omega, v = self._prey_policy.act(self._rng)
            prey.heading += omega * dt
            prey.speed = v
            self._steer_away_from_obstacles(prey, gain=2.0)
            prey.advance(dt, self.cfg.world.width, self.cfg.world.height)

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

        self.step_idx += 1
        extinct = bool(self.fish) and all(not f.alive for f in self.fish.values())
        done = self.step_idx >= self.cfg.world.episode_steps or extinct
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
        """Doc 07 section 13 per-fish record."""
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
