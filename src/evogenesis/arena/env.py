"""Danio Arena: continuous 2-D ecology env (Danio_Arena设计与实现说明.md).

Deterministic given (config, spawn_seed, dynamics_seed). Emits the frozen event
vocabulary v1 (arena §18.4.2, machine-readable authority tests::KNOWN_EVENTS) in
dot form (arena.*); see Danio_Arena设计与实现说明.md §18.4.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.entities import Entity, Fish, Obstacle, Predator, Prey
from evogenesis.arena.policies import PredatorPolicy, PreyPolicy
from evogenesis.arena.sensing import (
    max_predator_angular_size,
    nearest_visible_prey,
    observe,
)

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

    def __init__(
        self,
        config: ArenaConfig | None = None,
        *,
        spawn_seed: int,
        dynamics_seed: int,
        fish_ids: Sequence[str] | None = None,
        genome_ids: Sequence[str] | None = None,
        generation: int = 0,
    ):
        self.cfg = config or ArenaConfig()
        self.spawn_seed = int(spawn_seed)
        self.dynamics_seed = int(dynamics_seed)
        if fish_ids is None:
            self._fish_ids: tuple[str, ...] | None = None
        else:
            ids = tuple(fish_ids)
            if len(ids) != self.cfg.population.n_fish:
                raise ValueError(
                    f"fish_ids 数量 {len(ids)} 与 population.n_fish "
                    f"{self.cfg.population.n_fish} 不一致"
                )
            if len(set(ids)) != len(ids):
                raise ValueError("fish_ids 必须互异（core §3.1 稳定 ID）")
            self._fish_ids = ids
        if genome_ids is None:
            self._genome_ids: tuple[str, ...] | None = None
        else:
            gids = tuple(genome_ids)
            if len(gids) != self.cfg.population.n_fish:
                raise ValueError(
                    f"genome_ids 数量 {len(gids)} 与 population.n_fish "
                    f"{self.cfg.population.n_fish} 不一致"
                )
            # 允许重复的 `"unknown"`：无基因的鱼（ExpertPolicy / 默认种群）都用它，
            # 与本类 `fish_ids is None` 时的内部默认一致；**真实 genome_id 仍须互异**。
            known = [g for g in gids if g != "unknown"]
            if len(set(known)) != len(known):
                raise ValueError("genome_ids 必须互异（core §3.1 稳定 ID）")
            self._genome_ids = gids
        self._generation = int(generation)
        self.events: list[Event] = []
        self.fish: dict[str, Fish] = {}
        self.prey: dict[str, Prey] = {}
        self.predators: dict[str, Predator] = {}
        self.obstacles: list[Obstacle] = []
        self.step_idx = 0
        self._seq = 0
        self._episode_ended = False
        self._spawn_rng = np.random.default_rng(self.spawn_seed)
        self._dynamics_rng = np.random.default_rng(self.dynamics_seed)
        self._prey_policy = PreyPolicy(
            speed=self.cfg.actors.prey_speed,
            turn_std=self.cfg.actors.wander_turn_std,
            turn_clip=self.cfg.actors.prey_turn_clip,
        )
        self._pred_policy = PredatorPolicy(
            cruise_speed=self.cfg.actors.predator_cruise_speed,
            chase_speed=self.cfg.actors.predator_chase_speed,
            detection_radius=self.cfg.actors.predator_detection_radius,
            release_radius=self.cfg.actors.predator_release_radius,
            # 必须注入：否则 config 里改这个值不影响行为（P1 审计 A7）
            max_chase_steps=self.cfg.actors.predator_max_chase_steps,
        )

    def reset(self) -> None:
        self._spawn_rng = np.random.default_rng(self.spawn_seed)
        self._dynamics_rng = np.random.default_rng(self.dynamics_seed)
        self.events.clear()
        self.step_idx = 0
        self._seq = 0
        self._episode_ended = False
        self.obstacles = []
        self._next_prey_id = self.cfg.population.n_prey
        self._spawn_obstacles()
        ids = (
            self._fish_ids
            if self._fish_ids is not None
            else tuple(f"fish_{i:02d}" for i in range(self.cfg.population.n_fish))
        )
        gids = (
            self._genome_ids
            if self._genome_ids is not None
            else tuple("unknown" for _ in range(self.cfg.population.n_fish))
        )
        self.fish = {}
        for fid, gid in zip(ids, gids, strict=True):
            self.fish[fid] = Fish(
                fid,
                self._free_spot(2.0),
                float(self._spawn_rng.uniform(0, 2 * np.pi)),
                size=self.cfg.growth.initial_size,
                energy=self.cfg.energy.e_max,
                genome_id=gid,
                generation=self._generation,
            )
        self.prey = {
            f"prey_{i:02d}": Prey(
                f"prey_{i:02d}",
                self._free_spot(1.0),
                float(self._spawn_rng.uniform(0, 2 * np.pi)),
                size=float(
                    self._spawn_rng.uniform(
                        self.cfg.actors.prey_size_min, self.cfg.actors.prey_size_max
                    )
                ),
            )
            for i in range(self.cfg.population.n_prey)
        }
        # 捕食者：彼此至少相距一个**检测半径**（`env §2.2`）——否则三条会挤在一起、
        # 检测圈互相重叠，画面与实际捕食行为都看不出"三只分别在不同位置巡逻"。
        self.predators = {}
        for i in range(self.cfg.population.n_predators):
            pid = f"predator_{i:02d}"
            pos = self._free_spot(
                3.0,
                avoid=[p.pos for p in self.predators.values()],
                min_dist=self.cfg.actors.predator_detection_radius,
            )
            self.predators[pid] = Predator(
                pid,
                pos,
                float(self._spawn_rng.uniform(0, 2 * np.pi)),
                size=self.cfg.actors.predator_size,
            )
        for eid in (*self.fish, *self.prey, *self.predators):
            self._emit("arena.spawn", {"entity_id": eid})

    def spawn_fish(
        self,
        fish_id: str,
        *,
        genome_id: str,
        position: np.ndarray | None = None,
        heading: float | None = None,
        size: float | None = None,
        energy: float | None = None,
        generation: int | None = None,
    ) -> Fish:
        """运行期**追加**一条鱼（`api/API接口.md` §1.11：把发育好的个体送进 Arena）。

        语义与边界：

        - 只追加、不改既有鱼；返回新建的 `Fish`。
        - `position=None` 时用 `_free_spot` 找空位 —— 这会消耗 `spawn_seed` 的**生成随机流**，
          但该流只在生成期使用，**不影响**已有实体与 `dynamics_seed` 的动力学流；
          显式传入 `position` 则完全不消耗随机数（调用方若要严格可复现，传固定坐标）。
        - **会话期实体**：`reset()` 会按构造时的 `fish_ids` 重建种群，故追加的个体会被清掉。
          这是刻意的——追加是交互行为，不属于实验配置。
        - `fish_id` 必须非空且未占用（`core §3.1`：稳定 ID，禁数组下标当 identity）。
        """
        if not fish_id:
            raise ValueError("fish_id 必须非空（core §3.1）")
        if fish_id in self.fish:
            raise ValueError(f"fish_id {fish_id!r} 已存在")
        pos = self._free_spot(2.0) if position is None else np.asarray(position, dtype=float)
        fish = Fish(
            fish_id,
            pos,
            float(self._spawn_rng.uniform(0, 2 * np.pi)) if heading is None else float(heading),
            size=self.cfg.growth.initial_size if size is None else float(size),
            energy=self.cfg.energy.e_max if energy is None else float(energy),
            genome_id=genome_id,
            generation=self._generation if generation is None else int(generation),
        )
        self.fish[fish_id] = fish
        self._emit("arena.spawn", {"entity_id": fish_id, "genome_id": genome_id, "added": True})
        return fish

    def _spawn_obstacles(self) -> None:
        """Place obstacles one by one into ``self.obstacles`` (which must start
        empty) so later obstacles avoid earlier ones; keeps ``reset`` idempotent."""
        lo = self.cfg.actors.obstacle_radius_min
        hi = self.cfg.actors.obstacle_radius_max
        for i in range(self.cfg.population.n_obstacles):
            r = float(self._spawn_rng.uniform(lo, hi))
            pos = self._free_spot(r + 1.0)
            self.obstacles.append(Obstacle(f"obstacle_{i:02d}", pos, r))

    def _free_spot(
        self,
        clearance: float,
        *,
        avoid: Sequence[np.ndarray] = (),
        min_dist: float = 0.0,
    ) -> np.ndarray:
        """Rejection-sample a position inside the world, outside obstacles.

        `min_dist > 0` 时还要求与 `avoid` 中任意点距离 ≥ `min_dist`（`env §2.2 初始布局`）。
        默认不启用该约束（保持既有对象的布局不变）。
        """
        w = self.cfg.world.width
        h = self.cfg.world.height
        for _ in range(200):
            pos = np.array([self._spawn_rng.uniform(0, w), self._spawn_rng.uniform(0, h)])
            if any(o.contains(pos, clearance) for o in self.obstacles):
                continue
            if min_dist > 0.0 and any(
                float(np.linalg.norm(pos - np.asarray(other))) < min_dist for other in avoid
            ):
                continue
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
            looming_rate=fish._looming_rate,
            predator_size_ref=self.cfg.sensing.predator_size_ref,
        )

    def step(self, actions: dict[str, tuple[float, float]] | None = None) -> StepResult:
        actions = actions or {}
        if self._episode_ended:
            return StepResult(self.step_idx, True, [])
        dt = self.cfg.world.dt
        new_events: list[Event] = []

        # --- looming (arena §4.1 / A1)：步首采样「可见天敌最大角尺寸」
        #     步尾（全部实体移动后）再采样 θ_after，得本步相对扩张率
        #     `(θ_after-θ_before)/(θ_after·Δt)`（分母 θ_t=θ_after，同所引依据），按
        #     R_loom=sensing.looming_norm 归一到 [0,1] 缓存给 `observe()`。
        #     任一端不可见（θ=0）即记 0，避免"看不见却仍在 loom"。
        predator_list = list(self.predators.values())
        theta_before = {
            fid: max_predator_angular_size(
                fish, predator_list, self.cfg.sensing.radius, self.cfg.sensing.fov_degrees
            )
            for fid, fish in self.fish.items()
            if fish.alive
        }

        # --- fish: turn, move, eat, pay energy (Danio_Arena设计与实现说明.md sections 5-8)
        for fid, fish in self.fish.items():
            if not fish.alive:
                continue
            omega, v = actions.get(fid, (0.0, 0.0))
            omega = float(np.clip(omega, -1.0, 1.0))
            # 演示可配：先缩放再裁剪（默认 1.0/1.0 ⇒ 与 `[0,1]` 既有口径逐位一致）。
            v = float(
                np.clip(v * self.cfg.actors.fish_speed_scale, 0.0, self.cfg.actors.fish_speed_cap)
            )
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
                    prob = self.cfg.growth.capture_success_prob
                    if prob < 1.0 and self._dynamics_rng.random() >= prob:
                        # 尺寸门通过但扑击失败：猎物存活，记「missed」（arena §8 新版）
                        fish.capture_attempts += 1
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
                                    "result": "missed",
                                },
                            )
                        )
                        break
                    prey.alive = False
                    fish.capture_attempts += 1
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
                fish.capture_attempts += 1
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
            self._steer_away_from_obstacles(pred, gain=self.cfg.actors.predator_obstacle_avoid_gain)
            pred.advance(dt, self.cfg.world.width, self.cfg.world.height, self.cfg.world.boundary)

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
            omega, v = self._prey_policy.act(self._dynamics_rng)
            prey.heading += omega * dt
            prey.speed = v
            self._steer_away_from_obstacles(prey, gain=self.cfg.actors.prey_obstacle_avoid_gain)
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
                    float(self._spawn_rng.uniform(0, 2 * np.pi)),
                    size=float(
                        self._spawn_rng.uniform(
                            self.cfg.actors.prey_size_min, self.cfg.actors.prey_size_max
                        )
                    ),
                )
                new_events.append(self._emit("arena.spawn", {"entity_id": pid}))

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

        # --- looming 结算（步尾）：用移动后的 θ_after 与步首 θ_before 作差（见步首注释）。
        for fid, before in theta_before.items():
            fish = self.fish[fid]
            after = max_predator_angular_size(
                fish, predator_list, self.cfg.sensing.radius, self.cfg.sensing.fov_degrees
            )
            if fish.alive and before > 0.0 and after > 0.0:
                rate = ((after - before) / dt) / after
                fish._looming_rate = min(max(rate / self.cfg.sensing.looming_norm, 0.0), 1.0)
            else:
                fish._looming_rate = 0.0

        if self.cfg.probe.enabled:
            self._update_probe()

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

    def h3_probe_report(self) -> dict:
        """H3 历史依赖探针汇总（`arena §14`；`probe.enabled=false` 时 `trials=0`）。"""
        trials = sum(f.probe_trials for f in self.fish.values())
        successes = sum(f.probe_successes for f in self.fish.values())
        return {
            "delay_steps": self.cfg.probe.delay_steps,
            "return_radius": self.cfg.probe.return_radius,
            "window_steps": self.cfg.probe.window_steps,
            "shuffle_history": self.cfg.probe.shuffle_history,
            "trials": trials,
            "successes": successes,
            "P": (successes / trials) if trials else None,
        }

    def _update_probe(self) -> None:
        """H3 探针状态机（`arena §14`）：最近可见猎物 → last_seen → 延迟 D → 回归判定 r_H。"""
        width, height = self.cfg.world.width, self.cfg.world.height
        prey_list = list(self.prey.values())
        for fish in self.fish.values():
            if not fish.alive:
                continue
            hit = nearest_visible_prey(
                fish, prey_list, self.cfg.sensing.radius, self.cfg.sensing.fov_degrees
            )
            if hit is not None:
                fish._last_seen_prey_pos = hit[1]
                fish._steps_since_prey_seen = 0
                fish._probe_remaining = 0  # 猎物重新可见 → 本次 trial 失败
                continue
            fish._steps_since_prey_seen += 1
            if fish._probe_remaining > 0:
                expectation = fish._probe_expectation
                if (
                    expectation is not None
                    and float(np.linalg.norm(fish.pos - expectation))
                    <= self.cfg.probe.return_radius
                ):
                    fish.probe_successes += 1
                    fish._probe_remaining = 0
                else:
                    fish._probe_remaining -= 1
            elif (
                fish._steps_since_prey_seen >= self.cfg.probe.delay_steps
                and fish._last_seen_prey_pos is not None
            ):
                base = fish._last_seen_prey_pos
                if self.cfg.probe.shuffle_history:
                    fish._probe_expectation = np.array([width - base[0], height - base[1]])
                else:
                    fish._probe_expectation = np.array(base, dtype=float)
                fish._probe_remaining = self.cfg.probe.window_steps
                fish.probe_trials += 1

    def per_fish_log(self) -> dict[str, dict]:
        """Danio_Arena设计与实现说明.md section 13 per-fish record."""
        return {
            fid: {
                "generation": f.generation,
                "encounters": f.encounters,
                "captures": f.captures,
                "capture_attempts": f.capture_attempts,
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
