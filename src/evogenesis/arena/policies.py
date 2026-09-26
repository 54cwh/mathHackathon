"""Transparent rule policies for the Arena (Danio_Arena设计与实现说明.md sections 9-11).

ExpertPolicy is used for imitation data only -- it never takes part in
DanioNet scoring. Predator/Prey policies are the transparent ecology rules.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class ExpertPolicy:
    prey_weight: float = 1.0
    threat_weight: float = 1.8
    obstacle_weight: float = 1.2
    hunger_gain: float = 0.8

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
        speed = max(0.0, min(1.0, 0.45 + 0.35 * hunger + 0.30 * max(threat_l, threat_r)))
        return omega, speed


@dataclass
class PreyPolicy:
    """Danio_Arena设计与实现说明.md section 10: stochastic wander + obstacle avoidance +
    proximity avoidance. Prey do not see fish (no active fleeing in MVP);
    proximity avoidance is handled by the env separation pass."""

    speed: float = 0.35
    turn_std: float = 0.8
    avoid_gain: float = 2.5

    def act(
        self, rng: np.random.Generator, obstacle_rel_bearing: float | None = None
    ) -> tuple[float, float]:
        omega = float(rng.normal(0.0, self.turn_std))
        if obstacle_rel_bearing is not None:
            # steer away: obstacle on the right (rel > 0) -> turn left (omega < 0)
            omega -= float(np.sign(obstacle_rel_bearing)) * self.avoid_gain
        return float(np.clip(omega, -3.0, 3.0)), self.speed


@dataclass
class PredatorPolicy:
    """Danio_Arena设计与实现说明.md section 9: cruise -> chase legal target -> avoid obstacles ->
    resume cruise. Pure planning only: returns the desired heading and speed;
    turn-rate limiting and geometry live in the env."""

    cruise_speed: float = 0.40
    chase_speed: float = 0.65
    detection_radius: float = 15.0
    release_radius: float = 22.0

    def plan(
        self,
        pos: np.ndarray,
        heading: float,
        current_target: str | None,
        fish_pos: dict[str, np.ndarray],
    ) -> tuple[str | None, float, float]:
        """Return (target_fish_id | None, desired_heading, speed).

        Hysteresis: keep the current target until it is beyond
        ``release_radius``; otherwise pick the nearest fish within
        ``detection_radius``.
        """
        if current_target in fish_pos:
            d = float(np.linalg.norm(fish_pos[current_target] - pos))
            if d <= self.release_radius:
                return current_target, self._toward(pos, fish_pos[current_target]), self.chase_speed

        best_id, best_d = None, float("inf")
        for fid, fpos in fish_pos.items():
            d = float(np.linalg.norm(fpos - pos))
            if d < self.detection_radius and d < best_d:
                best_id, best_d = fid, d

        if best_id is not None:
            return best_id, self._toward(pos, fish_pos[best_id]), self.chase_speed
        return None, heading, self.cruise_speed

    @staticmethod
    def _toward(pos: np.ndarray, target: np.ndarray) -> float:
        return float(np.arctan2(target[1] - pos[1], target[0] - pos[0]))
