"""配置加载与校验（core §0 / §10 #5，已定稿）。

覆盖优先级 **CLI > env > file > default**（core §0）。分层 API 以公开函数
``read_yaml`` / ``env_overrides`` / ``deep_update`` 提供，供各模块封装自己的加载器
（如 ``genome/config.py``、``arena/config.py``）；本文件的 ``load_config`` 是它们的通用组合。
- file 层：``configs/*.yaml``（运行期取值的唯一来源，core §7）。
- env 层：前缀 ``EVOGENESIS_``，嵌套用双下划线 ``__``（沿用 pydantic-settings 的命名约定）；
  段名对 Pydantic 字段名大小写不敏感匹配；值按 YAML 标量解析（契约见 core §0）。
- CLI 层：点分键（如 ``learning.lr``）或嵌套 dict。
- default 层：Pydantic 字段默认值；**数值参数一律必填**，此处不发明取值（core §7 禁止）。

各模块用 ``load_config(path, model=...)`` 传入自己的 Pydantic 模型，即可加载对应
``configs/*.yaml``（core §0「加载并校验 configs/*.yaml」）。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

ENV_PREFIX = "EVOGENESIS_"
ENV_NESTED_DELIMITER = "__"


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenomeConfig(_Section):
    chromosome_pairs: int
    bp_per_haplotype_chromosome: int
    alphabet: list[str]
    motif_count: int
    motif_length: int
    motif_topk: int
    motif_subset_A: int
    motif_subset_B: int


class PhenotypeConfig(_Section):
    theta_N: float
    theta_H: float

    @model_validator(mode="after")
    def _check_theta_range(self) -> PhenotypeConfig:
        for name, value in (("theta_N", self.theta_N), ("theta_H", self.theta_H)):
            if not 0.0 < value < 0.5:
                raise ValueError(
                    f"{name} 须落在 (0, 0.5)（genome §3 完全显性必要条件），实际 {value}"
                )
        return self


class GRNConfig(_Section):
    dim: int
    development_steps: int
    rho: float
    activation: str
    weight_init: str
    spectral_radius: float
    init_b_std: float


class DevelopmentConfig(_Section):
    initial_precursors: int
    domains: list[str]
    precursors_per_domain: int
    max_divisions_per_precursor: int
    max_neurons: int
    placement: str
    position_space: str
    split_noise: float
    gene_noise: float
    c_domain_bonus: float
    zero_input_steps: int
    saturation_ratio_max: float
    saturation_eps: float


class ConnectomeConfig(_Section):
    target_density: float
    allow_self_loops: bool
    distance_lambda: float
    distance_space: str
    regulatory_gamma: float
    w_bar_initial: float
    ablation_random_density: float
    ablation_w_grn: bool = False
    tau_min: float
    tau_max: float


class NetworkConfig(_Section):
    sensory_dim: int
    action_dim: int
    activation: str
    input_weight_scope: str
    input_weight_std: float
    hunger_gain_std: float
    neuron_bias_std: float
    motor_pool_split: str
    action_pooling: str


class LearningConfig(_Section):
    method: str
    optimizer: str
    lr: float
    mini_batch_updates: int
    batch_size: int
    trajectories: int
    optional_rl: bool
    loss_weight_normalization: str
    loss_variance_floor_ratio: float
    loss_weight_fallback_omega: float
    loss_weight_fallback_v: float


class ModelConfig(_Section):
    genome: GenomeConfig
    phenotype: PhenotypeConfig
    grn: GRNConfig
    development: DevelopmentConfig
    connectome: ConnectomeConfig
    network: NetworkConfig
    learning: LearningConfig


def deep_update(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base


def _nested(overrides: Mapping[str, Any]) -> dict[str, Any]:
    """点分键（``learning.lr``）展开为嵌套 dict；嵌套 dict 原样保留。"""
    out: dict[str, Any] = {}
    for key, value in overrides.items():
        if isinstance(value, Mapping):
            deep_update(out, {key: _nested(value)})
            continue
        parts = key.split(".")
        cursor = out
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = value
    return out


def _match_field(segment: str, model: type[BaseModel]) -> tuple[str, type[BaseModel] | None]:
    """把 env 段名大小写不敏感地匹配到模型字段；返回 (字段名, 子模型类型)。"""
    for name, field in model.model_fields.items():
        if name.casefold() == segment.casefold():
            annotation = field.annotation
            nested = (
                annotation
                if isinstance(annotation, type) and issubclass(annotation, BaseModel)
                else None
            )
            return name, nested
    return segment, None


def _canonical_path(segments: list[str], model: type[BaseModel]) -> list[str]:
    canonical: list[str] = []
    current: type[BaseModel] | None = model
    for segment in segments:
        if current is None:
            canonical.append(segment)
            continue
        name, current = _match_field(segment, current)
        canonical.append(name)
    return canonical


def env_overrides(environ: Mapping[str, str], model: type[BaseModel]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for raw_key, raw_value in environ.items():
        if not raw_key.startswith(ENV_PREFIX):
            continue
        segments = raw_key[len(ENV_PREFIX) :].split(ENV_NESTED_DELIMITER)
        if not all(segments):
            continue
        path = _canonical_path(segments, model)
        try:
            value: Any = yaml.safe_load(raw_value)
        except yaml.YAMLError:
            value = raw_value
        cursor = out
        for part in path[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[path[-1]] = value
    return out


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"config 文件不存在：{path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(f"config 顶层必须是映射：{path}")
    return loaded


def load_config[ConfigModel: BaseModel](
    path: str | os.PathLike[str] | None = None,
    *,
    model: type[ConfigModel] = ModelConfig,  # type: ignore[assignment]
    overrides: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> ConfigModel:
    """按 ``CLI > env > file > default`` 合成并校验配置。

    ``model`` 为对应 ``configs/*.yaml`` 的 Pydantic 模型；默认 ``ModelConfig``。
    """
    data: dict[str, Any] = {}
    if path is not None:
        deep_update(data, read_yaml(Path(path)))
    deep_update(data, env_overrides(os.environ if environ is None else environ, model))
    if overrides:
        deep_update(data, _nested(overrides))
    return model.model_validate(data)


def config_snapshot(config: BaseModel) -> dict[str, Any]:
    """供 run 目录落盘的已解析配置快照（core §7）。"""
    return config.model_dump()
