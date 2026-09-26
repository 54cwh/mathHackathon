"""Arena configuration.

Defaults mirror ``configs/default_arena.yaml`` (frozen values, docs/参数总表.json).
All numbers MUST stay in sync with that file; the config object exists so
experiments can override knobs without touching the frozen defaults.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorldConfig:
    width: float = 100.0
    height: float = 60.0
    hz: int = 20
    episode_steps: int = 600  # 30 s at 20 Hz

    @property
    def dt(self) -> float:
        return 1.0 / self.hz


@dataclass(frozen=True)
class PopulationConfig:
    n_fish: int = 12
    n_prey: int = 24
    n_predators: int = 3
    n_obstacles: int = 6


@dataclass(frozen=True)
class SensingConfig:
    radius: float = 18.0
    fov_degrees: float = 220.0


@dataclass(frozen=True)
class EnergyConfig:
    e_max: float = 1.0
    base_cost_per_step: float = 0.0008
    movement_cost_scale: float = 0.0015
    food_reward: float = 0.12


@dataclass(frozen=True)
class GrowthConfig:
    initial_size: float = 1.0
    max_size: float = 2.5
    capture_size_ratio: float = 1.25  # kappa (Danio_Arena设计与实现说明.md section 8)
    capture_radius: float = 1.2
    turn_inertia_scale: float = 0.35  # k_turn (Danio_Arena设计与实现说明.md section 5)
    biomass_to_size_gain: float = 0.02  # MVP calibration knob (play-test later)


@dataclass(frozen=True)
class ActorDefaults:
    """MVP calibration knobs -- Danio_Arena设计与实现说明.md: values from play-testing."""

    prey_speed: float = 0.35
    prey_size_min: float = 0.30
    prey_size_max: float = 0.60
    predator_size: float = 2.0
    predator_cruise_speed: float = 0.40
    predator_chase_speed: float = 0.65
    predator_detection_radius: float = 15.0
    predator_release_radius: float = 22.0  # hysteresis: target lost beyond this
    predator_turn_rate: float = 5.0  # rad/s, same unit convention as fish omega
    obstacle_radius_min: float = 1.5
    obstacle_radius_max: float = 3.5
    wander_turn_std: float = 0.8  # rad/s, std of the prey turning-rate jitter


@dataclass(frozen=True)
class ArenaConfig:
    world: WorldConfig = field(default_factory=WorldConfig)
    population: PopulationConfig = field(default_factory=PopulationConfig)
    sensing: SensingConfig = field(default_factory=SensingConfig)
    energy: EnergyConfig = field(default_factory=EnergyConfig)
    growth: GrowthConfig = field(default_factory=GrowthConfig)
    actors: ActorDefaults = field(default_factory=ActorDefaults)
