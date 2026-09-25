from dataclasses import dataclass


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


class PredatorPolicy:
    pass


class PreyPolicy:
    pass
