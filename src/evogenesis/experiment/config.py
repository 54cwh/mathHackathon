"""experiment 协议参数：取值 owner 为 ``configs/experiment.yaml``（`实验与评价体系.md` §3.6）。

本模块**不新造数值**：``ExperimentConfig`` 只做 ``configs/experiment.yaml`` 的类型化镜像，
经 ``core.config.load_config`` 读取并校验（覆盖优先级 ``CLI > env > file > default``）。
参数依据与状态见 ``docs/参数总表.json``。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from evogenesis.core.config import load_config


def _resolve_config(name: str) -> Path:
    """自本文件向上查找 ``configs/<name>``（源码 / editable 检出）。"""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "configs" / name
        if candidate.is_file():
            return candidate
    return Path(__file__).resolve().parents[3] / "configs" / name


DEFAULT_EXPERIMENT_CONFIG_PATH = _resolve_config("experiment.yaml")
DEFAULT_SEEDS_CONFIG_PATH = _resolve_config("experiment_seeds.yaml")
DEFAULT_DEMO_SEED_CONFIG_PATH = _resolve_config("demo_seed.yaml")


class ExperimentConfig(BaseModel):
    """``configs/experiment.yaml`` 的完整类型化镜像。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    generations: int


class SeedsConfig(BaseModel):
    """``configs/experiment_seeds.yaml`` 的镜像（正式 seed 轴，`core §3`）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    seeds: list[int]
    minimum_formal_replicates: int


def load_experiment_config(
    path: str | os.PathLike[str] | None = DEFAULT_EXPERIMENT_CONFIG_PATH,
    *,
    overrides: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> ExperimentConfig:
    """读取 ``configs/experiment.yaml`` 并校验为 ``ExperimentConfig``。

    参数一律来自 config（``core §7`` 禁止在代码处发明取值），故 ``path=None`` 显式报错，
    不提供内置默认值。``overrides`` 形状同 YAML（如 ``{"generations": 5}``）。
    """
    if path is None:
        raise ValueError("experiment 参数无内置默认值，必须提供 config 文件（core §7）")
    return load_config(path, model=ExperimentConfig, overrides=overrides, environ=environ)


def load_formal_seeds(
    path: str | os.PathLike[str] | None = DEFAULT_SEEDS_CONFIG_PATH,
) -> SeedsConfig:
    """读取 ``configs/experiment_seeds.yaml``（正式 seed 轴的唯一来源）。"""
    if path is None:
        raise ValueError("experiment seeds 无内置默认值，必须提供 config 文件（core §7）")
    return load_config(path, model=SeedsConfig)


__all__ = [
    "DEFAULT_DEMO_SEED_CONFIG_PATH",
    "DEFAULT_EXPERIMENT_CONFIG_PATH",
    "DEFAULT_SEEDS_CONFIG_PATH",
    "ExperimentConfig",
    "SeedsConfig",
    "load_experiment_config",
    "load_formal_seeds",
]
