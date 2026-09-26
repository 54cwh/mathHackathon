"""Arena configuration.

Defaults mirror ``configs/default_arena.yaml`` (frozen values, docs/参数总表.json).
All numbers MUST stay in sync with that file; the config object exists so
experiments can override knobs without touching the frozen defaults.
"""

import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from pydantic import BaseModel, create_model

# 分层语义（CLI > env > file > default）的 owner 是 ``core §config``。此处**直接复用**
# `core.config` 的 helper，不在本模块另写一版（AGENTS「不得在两处各写一版」）。
# 若 core 把分层上提为公开 API，这里应改为公开导入。
from evogenesis.core.config import _deep_update, _env_overrides, _read_yaml


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
    capture_radius: float = 4.61
    turn_inertia_scale: float = 0.35  # k_turn (Danio_Arena设计与实现说明.md section 5)
    biomass_to_size_gain: float = 0.02  # MVP calibration knob (play-test later)


@dataclass(frozen=True)
class ActorDefaults:
    """MVP calibration knobs -- Danio_Arena设计与实现说明.md: values from play-testing."""

    prey_speed: float = 0.35
    prey_size_min: float = 0.30
    prey_size_max: float = 0.60
    predator_size: float = 3.125
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


# --- 装配与分层加载 ---------------------------------------------------------

ARENA_DEFAULT_CONFIG = Path("configs/default_arena.yaml")

# section 名 → dataclass（同 ``core/config.py`` 的「section 名 = dataclass 名」约定）
ARENA_SECTIONS: dict[str, type] = {
    "world": WorldConfig,
    "population": PopulationConfig,
    "sensing": SensingConfig,
    "energy": EnergyConfig,
    "growth": GrowthConfig,
    "actors": ActorDefaults,
}

# 允许出现在 YAML、但不参与构造的**派生只读键**（§18.2.1：episode_seconds = episode_steps / hz）
DERIVED_READONLY_KEYS: frozenset[tuple[str, str]] = frozenset({("world", "episode_seconds")})


def _build_env_schema() -> type[BaseModel]:
    """按 ``ARENA_SECTIONS`` **运行时生成** Pydantic 镜像，仅供 ``core`` 的 env 层做段名
    大小写规范化（``_env_overrides(environ, model)``）。字段名的唯一 owner 仍是上面的
    dataclass —— 本表不手写第二份，故不构成 AGENTS 所禁的「两处各写一版」。
    """
    sections = {
        name: create_model(f"{cls.__name__}Env", **{f.name: (Any, None) for f in fields(cls)})
        for name, cls in ARENA_SECTIONS.items()
    }
    return create_model(
        "ArenaEnvSchema", **{name: (model, None) for name, model in sections.items()}
    )


_ENV_SCHEMA = _build_env_schema()


def _build_arena_config(data: Mapping[str, Any]) -> ArenaConfig:
    """把已分层的嵌套 dict 严格构造成 ``ArenaConfig``（未知 section/键即报错）。"""
    unknown_sections = set(data) - set(ARENA_SECTIONS)
    if unknown_sections:
        raise ValueError(f"default_arena.yaml 出现未知 section：{sorted(unknown_sections)}")
    kwargs: dict[str, Any] = {}
    for name, section_type in ARENA_SECTIONS.items():
        section = dict(data.get(name) or {})
        allowed = {f.name for f in fields(section_type)}
        for key in list(section):
            if (name, key) in DERIVED_READONLY_KEYS:
                del section[key]
                continue
            if key not in allowed:
                raise ValueError(
                    f"default_arena.yaml 的 {name}.{key} 不是 {section_type.__name__} 的字段"
                )
        kwargs[name] = section_type(**section)
    return ArenaConfig(**kwargs)


def load_arena_config(
    path: str | os.PathLike[str] | None = None,
    *,
    overrides: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> ArenaConfig:
    """按 ``CLI > env > file > default`` 合成 Arena 配置。

    ``path=None`` 时只取 env / overrides（纯默认值 + 覆盖）。
    ``overrides`` 为**嵌套**映射（形状同 YAML），优先级最高。
    """
    data: dict[str, Any] = {}
    if path is not None:
        _deep_update(data, _read_yaml(Path(path)))
    _deep_update(data, _env_overrides(os.environ if environ is None else environ, _ENV_SCHEMA))
    if overrides:
        _deep_update(data, overrides)
    return _build_arena_config(data)


def arena_config_snapshot(config: ArenaConfig) -> dict[str, Any]:
    """供 run 目录落盘的已解析配置快照（同 ``core.config::config_snapshot`` 用法）。"""
    return asdict(config)
