"""evolution 模块参数：取值 owner 为 ``configs/evolution.yaml``。

本模块**不新造数值**：``EvolutionConfig`` 只做 ``configs/evolution.yaml`` 的类型化镜像，
经 ``core.config.load_config`` 读取并校验（覆盖优先级 ``CLI > env > file > default``）。
``fitness_weights``（``0.35/0.25/0.20/0.20``）由本模型注入选择用的 ``F``，不在代码里硬编码；
参数依据与状态见 ``docs/参数总表.json``。

重组算子（单点交叉）由 ``genome/生物学与进化遗传学基础.md`` §4 定义，本模块只透传交叉概率、
不携带交叉次数上限。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from evogenesis.core.config import load_config


def _resolve_default_config() -> Path:
    """自本文件向上查找 ``configs/evolution.yaml``（源码 / editable 检出）。"""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "configs" / "evolution.yaml"
        if candidate.is_file():
            return candidate
    return Path(__file__).resolve().parents[3] / "configs" / "evolution.yaml"


DEFAULT_EVOLUTION_CONFIG_PATH = _resolve_default_config()


class FitnessWeights(BaseModel):
    """选择用 ``F`` 的四项权重（``evolution §6``）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    survival: float
    prey_capture: float
    escape_success: float
    energy_efficiency: float


class EvolutionConfig(BaseModel):
    """``configs/evolution.yaml`` 的完整类型化镜像。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    population_size: int
    tournament_size: int
    fitness_normalization: Literal["within_generation_minmax"]
    mutation_rate_per_base_per_gamete: float
    crossover_probability_per_chromosome: float
    fitness_weights: FitnessWeights
    generation_buttons: list[int]
    mendel_display_offspring: int


def load_evolution_config(
    path: str | os.PathLike[str] | None = DEFAULT_EVOLUTION_CONFIG_PATH,
    *,
    overrides: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> EvolutionConfig:
    """读取 ``configs/evolution.yaml`` 并校验为 ``EvolutionConfig``。

    参数一律来自 config（``core §7`` 禁止在代码处发明取值），故 ``path=None`` 显式报错，
    不提供内置默认值。``overrides`` 形状同 YAML（如 ``{"population_size": 8}`` 或
    ``{"fitness_weights": {"survival": 1.0}}``）。
    """
    if path is None:
        raise ValueError("evolution 参数无内置默认值，必须提供 config 文件（core §7）")
    return load_config(path, model=EvolutionConfig, overrides=overrides, environ=environ)
