"""Transparent rule policies for the Arena (Danio_Arena设计与实现说明.md sections 9-11).

ExpertPolicy is used for imitation data only -- it never takes part in
DanioNet scoring. Predator/Prey policies are the transparent ecology rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from evogenesis.arena.config import ArenaConfig


@dataclass
class ExpertPolicy:
    prey_weight: float = 1.0
    threat_weight: float = 1.8
    obstacle_weight: float = 1.2
    hunger_gain: float = 0.8
    speed_base: float = 0.45
    speed_hunger_gain: float = 0.35
    speed_threat_gain: float = 0.30

    def __call__(self, obs):
        prey_l, prey_r = obs[0], obs[1]
        threat_l, threat_r = obs[2], obs[3]
        obstacle_l, obstacle_r = obs[4], obs[5]
        hunger = obs[11]
        turn = (
            (prey_r - prey_l) * (self.prey_weight + self.hunger_gain * hunger)
            - (threat_r - threat_l) * self.threat_weight
            - (obstacle_r - obstacle_l) * self.obstacle_weight
        )
        omega = max(-1.0, min(1.0, turn))
        speed = max(
            0.0,
            min(
                1.0,
                self.speed_base
                + self.speed_hunger_gain * hunger
                + self.speed_threat_gain * max(threat_l, threat_r),
            ),
        )
        return omega, speed


@dataclass
class PreyPolicy:
    """Danio_Arena设计与实现说明.md section 10: stochastic wander（无主动逃跑；MVP）。

    避障由 env 的 `_steer_away_from_obstacles(prey, gain=2.0)` 统一处理，故本策略不含
    避障/`obstacle_rel_bearing` 逻辑。
    """

    speed: float = 0.35
    turn_std: float = 0.8
    turn_clip: float = 3.0  # rad/s, 游走转向裁剪（§10，config actors.prey_turn_clip）

    def act(self, rng: np.random.Generator) -> tuple[float, float]:
        omega = float(rng.normal(0.0, self.turn_std))
        return float(np.clip(omega, -self.turn_clip, self.turn_clip)), self.speed


@dataclass
class PredatorPolicy:
    """Danio_Arena设计与实现说明.md section 9: cruise -> chase legal target -> avoid obstacles ->
    resume cruise. Pure planning only: returns the desired heading and speed;
    turn-rate limiting and geometry live in the env."""

    cruise_speed: float = 0.40
    chase_speed: float = 0.65
    detection_radius: float = 15.0
    release_radius: float = 22.0
    max_chase_steps: int = 80  # give up after N consecutive steps; 设计选择（D）（arena §15）

    def plan(
        self,
        pos: np.ndarray,
        heading: float,
        current_target: str | None,
        fish_pos: dict[str, np.ndarray],
        current_chase_steps: int = 0,
        banned_fish_id: str | None = None,
    ) -> tuple[str | None, float, float]:
        """Return (target_fish_id | None, desired_heading, speed).

        Hysteresis: keep the current target until it is beyond
        ``release_radius``; otherwise pick the nearest fish within
        ``detection_radius``.

        Limited chase (Danio_Arena设计与实现说明.md section 9 / A8): after
        ``max_chase_steps`` consecutive steps on one fish the predator gives up and
        cruises; that fish is then ignored while it stays inside
        ``detection_radius``, so the predator cannot instantly re-lock it.
        """
        # The ban lives in env-owned state: the caller clears it once the fish is dead
        # or outside the detection radius. Here we only honour it.
        if current_target in fish_pos and current_target != banned_fish_id:
            d = float(np.linalg.norm(fish_pos[current_target] - pos))
            if d <= self.release_radius:
                if current_chase_steps >= self.max_chase_steps:
                    return None, heading, self.cruise_speed  # give up and cruise
                return current_target, self._toward(pos, fish_pos[current_target]), self.chase_speed

        best_id, best_d = None, float("inf")
        for fid, fpos in fish_pos.items():
            if fid == banned_fish_id:
                continue
            d = float(np.linalg.norm(fpos - pos))
            if d < self.detection_radius and d < best_d:
                best_id, best_d = fid, d

        if best_id is not None:
            return best_id, self._toward(pos, fish_pos[best_id]), self.chase_speed
        return None, heading, self.cruise_speed

    @staticmethod
    def _toward(pos: np.ndarray, target: np.ndarray) -> float:
        return float(np.arctan2(target[1] - pos[1], target[0] - pos[0]))


def expert_policy_from_config(cfg: ArenaConfig) -> ExpertPolicy:
    """由 `cfg.expert` 构造 `ExpertPolicy`（§11，数值唯一来源 = config）。"""
    return ExpertPolicy(
        prey_weight=cfg.expert.prey_weight,
        threat_weight=cfg.expert.threat_weight,
        obstacle_weight=cfg.expert.obstacle_weight,
        hunger_gain=cfg.expert.hunger_gain,
        speed_base=cfg.expert.speed_base,
        speed_hunger_gain=cfg.expert.speed_hunger_gain,
        speed_threat_gain=cfg.expert.speed_threat_gain,
    )
