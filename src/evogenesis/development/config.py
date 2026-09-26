"""RGCD 发育参数：取值 owner 为 ``configs/default_model.yaml`` 的 ``grn`` /
``development`` / ``connectome`` / ``network`` 节（RGCD §13、`core §7`）。

本模块**不新造数值**：``RGCDConfig`` 的默认值是冻结配置的镜像，由
``tests/test_development_config.py`` 的漂移守护测试断言与配置文件逐字段一致；
运行期用 ``load_development_config()`` 经 ``core`` 的 ``load_config`` 读取真实配置注入。
参数依据与状态见 ``docs/参数总表.json``（``group`` ∈ {grn, development, connectome, network}）。

读取时只用本模块自带的 section 模型（顶层 ``extra="ignore"``），因此不依赖
``core.ModelConfig`` 的其它节，避免跨 lane 编辑相互干扰。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from evogenesis.core.config import load_config

# 仓库根 = 本文件 ``src/evogenesis/development/config.py`` 的上溯第 3 级。
DEFAULT_MODEL_CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "default_model.yaml"

# 六类神经元谱系顺序（``configs/default_model.yaml → development.domains``，RGCD §3）。
DOMAIN_ORDER: tuple[str, ...] = (
    "sensory",
    "prey",
    "threat",
    "integrator_memory",
    "inhibitory",
    "motor",
)


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _GRNSection(_Section):
    dim: int
    development_steps: int
    rho: float
    activation: str
    weight_init: str
    spectral_radius: float
    init_b_std: float


class _DevelopmentSection(_Section):
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


class _ConnectomeSection(_Section):
    target_density: float
    allow_self_loops: bool
    distance_lambda: float
    distance_space: str
    regulatory_gamma: float
    w_bar_initial: float
    ablation_random_density: float
    tau_min: float
    tau_max: float


class _NetworkSection(_Section):
    sensory_dim: int
    action_dim: int
    activation: str
    input_weight_scope: str
    input_weight_std: float
    hunger_gain_std: float
    neuron_bias_std: float
    motor_pool_split: str
    action_pooling: str


class _RGCDModelConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    grn: _GRNSection
    development: _DevelopmentSection
    connectome: _ConnectomeSection
    network: _NetworkSection


@dataclass(frozen=True)
class RGCDConfig:
    """RGCD 参数镜像（``configs/default_model.yaml`` 的相关节）。"""

    # grn（RGCD §4，`configs → grn`）
    grn_dim: int = 8
    development_steps: int = 12
    grn_rho: float = 0.35
    grn_activation: str = "sigmoid"
    grn_weight_init: str = "xavier"
    grn_spectral_radius: float = 0.9
    init_b_std: float = 0.1

    # development（RGCD §3/§5/§7/§8，`configs → development`）
    initial_precursors: int = 24
    domains: tuple[str, ...] = DOMAIN_ORDER
    precursors_per_domain: int = 4
    max_divisions_per_precursor: int = 1
    max_neurons: int = 48
    placement: str = "domain_blocked"
    position_space: str = "unit_square"
    split_noise: float = 0.05
    gene_noise: float = 0.1
    c_domain_bonus: float = 1.5
    zero_input_steps: int = 50
    saturation_ratio_max: float = 0.9
    saturation_eps: float = 0.001

    # connectome（RGCD §8/§10/§11，`configs → connectome`）
    target_density: float = 0.15
    allow_self_loops: bool = False
    distance_lambda: float = 2.0
    distance_space: str = "unit_square"
    regulatory_gamma: float = 1.0
    w_bar_initial: float = 0.5
    tau_min: float = 1.0
    tau_max: float = 10.0

    # network（RGCD §7 dynamical viability 的 φ，`configs → network`）
    network_activation: str = "tanh"

    @property
    def n_domains(self) -> int:
        return len(self.domains)

    @property
    def weight_feature_dim(self) -> int:
        r"""``[\mathbf g_i;\mathbf g_j;\mathbf z_i;\mathbf z_j]`` 的维数（RGCD §10）。"""
        return 2 * self.grn_dim + 2 * self.n_domains

    @classmethod
    def from_config(cls, cfg: _RGCDModelConfig) -> RGCDConfig:
        return cls(
            grn_dim=cfg.grn.dim,
            development_steps=cfg.grn.development_steps,
            grn_rho=cfg.grn.rho,
            grn_activation=cfg.grn.activation,
            grn_weight_init=cfg.grn.weight_init,
            grn_spectral_radius=cfg.grn.spectral_radius,
            init_b_std=cfg.grn.init_b_std,
            initial_precursors=cfg.development.initial_precursors,
            domains=tuple(cfg.development.domains),
            precursors_per_domain=cfg.development.precursors_per_domain,
            max_divisions_per_precursor=cfg.development.max_divisions_per_precursor,
            max_neurons=cfg.development.max_neurons,
            placement=cfg.development.placement,
            position_space=cfg.development.position_space,
            split_noise=cfg.development.split_noise,
            gene_noise=cfg.development.gene_noise,
            c_domain_bonus=cfg.development.c_domain_bonus,
            zero_input_steps=cfg.development.zero_input_steps,
            saturation_ratio_max=cfg.development.saturation_ratio_max,
            saturation_eps=cfg.development.saturation_eps,
            target_density=cfg.connectome.target_density,
            allow_self_loops=cfg.connectome.allow_self_loops,
            distance_lambda=cfg.connectome.distance_lambda,
            distance_space=cfg.connectome.distance_space,
            regulatory_gamma=cfg.connectome.regulatory_gamma,
            w_bar_initial=cfg.connectome.w_bar_initial,
            tau_min=cfg.connectome.tau_min,
            tau_max=cfg.connectome.tau_max,
            network_activation=cfg.network.activation,
        )


DEFAULT_CONFIG = RGCDConfig()


def load_development_config(
    path: str | os.PathLike[str] | None = DEFAULT_MODEL_CONFIG_PATH,
    *,
    overrides: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> RGCDConfig:
    """按 ``CLI > env > file > default`` 读取相关节并转为 ``RGCDConfig``。

    默认读 ``configs/default_model.yaml``；``path=None`` 时只用 ``RGCDConfig`` 的
    默认值（冻结配置的镜像），便于离线与单测。
    """
    if path is None:
        return RGCDConfig()
    cfg = load_config(path, model=_RGCDModelConfig, overrides=overrides, environ=environ)
    return RGCDConfig.from_config(cfg)
