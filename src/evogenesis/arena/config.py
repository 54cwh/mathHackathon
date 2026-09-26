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
from evogenesis.core.config import deep_update, env_overrides, read_yaml


@dataclass(frozen=True)
class WorldConfig:
    width: float = 100.0
    height: float = 60.0
    hz: int = 20
    episode_steps: int = 600  # 30 s at 20 Hz
    boundary: str = "reflect"  # "reflect" (default) | "clamp" (section 2.1)

    def __post_init__(self) -> None:
        if self.boundary not in ("reflect", "clamp"):
            raise ValueError(f"world.boundary 取值非法：{self.boundary!r}（仅 reflect / clamp）")

    @property
    def dt(self) -> float:
        return 1.0 / self.hz


@dataclass(frozen=True)
class PopulationConfig:
    n_fish: int = 12
    n_prey: int = 24
    n_predators: int = 3
    n_obstacles: int = 6
    prey_regrowth_steps: int = 25  # 设计选择（D）：600 / n_prey（arena §16，dossier T3 s3.1）


@dataclass(frozen=True)
class SensingConfig:
    radius: float = 18.0
    fov_degrees: float = 220.0
    predator_size_ref: float = 2.5  # 相对尺寸归一参考（§4.1）
    looming_norm: float = 3.5  # R_loom（s^-1），标定占位 [2,5]（§4.1/A1）

    def __post_init__(self) -> None:
        if self.predator_size_ref <= 0.0:
            raise ValueError("predator_size_ref 必须 > 0")
        if self.looming_norm <= 0.0:
            raise ValueError("looming_norm 必须 > 0")


@dataclass(frozen=True)
class EnergyConfig:
    e_max: float = 1.0
    base_cost_per_step: float = 0.0008
    movement_cost_scale: float = 0.0015
    food_reward: float = 0.12
    collision_penalty: float = 0.001  # c_pen，设计选择（D）（arena §6 / §18.7 A7）


@dataclass(frozen=True)
class GrowthConfig:
    initial_size: float = 1.0
    max_size: float = 2.5
    capture_size_ratio: float = 1.25  # kappa (Danio_Arena设计与实现说明.md section 8)
    capture_radius: float = 4.61
    capture_cone_degrees: float = 120.0  # total cone, hunter-forward (section 8)
    turn_inertia_scale: float = 0.35  # k_turn (Danio_Arena设计与实现说明.md section 5)
    prey_area_gain: float = (
        0.2  # g in size = sqrt(size^2 + g*prey_size^2); 设计选择（D）（arena §7）
    )
    # 鱼的捕食成功率（arena §8）：1.0=确定性（默认，历史行为）；<1 时尺寸门通过后按概率判定，
    # 失败记 arena.capture_attempt(result="missed") 且猎物存活。
    capture_success_prob: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.capture_success_prob <= 1.0:
            raise ValueError(f"capture_success_prob 须在 [0, 1]，得到 {self.capture_success_prob}")


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
    prey_turn_clip: float = 3.0  # rad/s, PreyPolicy 游走转向裁剪（§10）
    prey_obstacle_avoid_gain: float = 2.0  # rad/step, 猎物避障转向增益（§10）
    predator_obstacle_avoid_gain: float = 0.5  # rad/step, 捕食者避障转向增益（§9）
    escape_hold_steps: int = 20  # A8 threat-outcome survival window; 设计选择（D）
    predator_max_chase_steps: int = 80  # A8 limited chase; 设计选择（D）


@dataclass(frozen=True)
class ExpertConfig:
    """ExpertPolicy 的透明规则权重与速度式常数（§11）。

    owner=本 dataclass；取值 `configs/default_arena.yaml::expert`。

    用于 BC 采集与现场 Demo 的**教师**策略；不参与 DanioNet scoring。
    """

    prey_weight: float = 1.0
    threat_weight: float = 1.8
    obstacle_weight: float = 1.2
    hunger_gain: float = 0.8
    speed_base: float = 0.45
    speed_hunger_gain: float = 0.35
    speed_threat_gain: float = 0.30


@dataclass(frozen=True)
class ProbeConfig:
    """H3 历史依赖探针（`arena §14`；**默认关闭**、测量层、不新增事件）。

    数值为 `草案待确认`（设计选择 D）：`delay_steps D=40`、`return_radius r_H=3.0`、
    `window_steps W=60`。owner=本 dataclass；取值 `configs/default_arena.yaml::probe`。
    """

    enabled: bool = False
    delay_steps: int = 40
    return_radius: float = 3.0
    window_steps: int = 60
    shuffle_history: bool = False


@dataclass(frozen=True)
class ArenaConfig:
    world: WorldConfig = field(default_factory=WorldConfig)
    population: PopulationConfig = field(default_factory=PopulationConfig)
    sensing: SensingConfig = field(default_factory=SensingConfig)
    energy: EnergyConfig = field(default_factory=EnergyConfig)
    growth: GrowthConfig = field(default_factory=GrowthConfig)
    actors: ActorDefaults = field(default_factory=ActorDefaults)
    expert: ExpertConfig = field(default_factory=ExpertConfig)
    probe: ProbeConfig = field(default_factory=ProbeConfig)


# --- 装配与分层加载 ---------------------------------------------------------

# section 名 → dataclass（同 ``core/config.py`` 的「section 名 = dataclass 名」约定）
ARENA_SECTIONS: dict[str, type] = {
    "world": WorldConfig,
    "population": PopulationConfig,
    "sensing": SensingConfig,
    "energy": EnergyConfig,
    "growth": GrowthConfig,
    "actors": ActorDefaults,
    "expert": ExpertConfig,
    "probe": ProbeConfig,
}

# 允许出现在 YAML、但不参与构造的**派生只读键**（§18.2.1：episode_seconds = episode_steps / hz）
DERIVED_READONLY_KEYS: frozenset[tuple[str, str]] = frozenset({("world", "episode_seconds")})


def _build_env_schema() -> type[BaseModel]:
    """按 ``ARENA_SECTIONS`` **运行时生成** Pydantic 镜像，仅供 ``core`` 的 env 层做段名
    大小写规范化（``env_overrides(environ, model)``）。字段名的唯一 owner 仍是上面的
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
        deep_update(data, read_yaml(Path(path)))
    deep_update(data, env_overrides(os.environ if environ is None else environ, _ENV_SCHEMA))
    if overrides:
        deep_update(data, overrides)
    return _build_arena_config(data)


def arena_config_snapshot(config: ArenaConfig) -> dict[str, Any]:
    """供 run 目录落盘的已解析配置快照（同 ``core.config::config_snapshot`` 用法）。"""
    return asdict(config)
