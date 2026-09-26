"""RGCD 发育参数：取值 owner 为 ``configs/default_model.yaml`` 的 ``grn`` /
``development`` / ``connectome`` / ``network`` 节（RGCD §13、`core §7`）。

本模块**不新造数值**：``RGCDConfig`` 的默认值是冻结配置的镜像，由
``tests/test_development_config.py`` 的漂移守护测试断言与配置文件逐字段一致。
``load_development_config()`` 经 ``core`` 的 ``load_config`` 读取真实配置注入；生产调用方为
``pipeline/model_chain.py::load_model_chain_config``（入口 ``scripts/run_chain.py``）。
``connectome.ablation_w_grn`` / ``ablation_random_density`` 为 w/o GRN 消融的开关与密度
（`connectome §9`、`RGCD §8` 消融段），已在 ``develop`` 接线。
参数依据与状态见 ``docs/参数总表.json``（``group`` ∈ {grn, development, connectome, network}）。

字段 schema（`configs/default_model.yaml` 各节）归 ``core/config.py`` **唯一拥有**；
本模块只保留运行期镜像 dataclass ``RGCDConfig`` 与 ``from_config`` 映射，不另写 Pydantic section。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evogenesis.core.config import ModelConfig, load_config


def _resolve_default_model_config() -> Path:
    """自本文件向上查找 ``configs/default_model.yaml``（源码 / editable 检出）。"""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "configs" / "default_model.yaml"
        if candidate.is_file():
            return candidate
    return Path(__file__).resolve().parents[3] / "configs" / "default_model.yaml"


DEFAULT_MODEL_CONFIG_PATH = _resolve_default_model_config()

# 六类神经元谱系顺序（``configs/default_model.yaml → development.domains``，RGCD §3）。
DOMAIN_ORDER: tuple[str, ...] = (
    "sensory",
    "prey",
    "threat",
    "integrator_memory",
    "inhibitory",
    "motor",
)


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
    domain_identity_spread_scale: float = 1.0
    #: §5 的两个设计增益（α/β）与基因组通道的 motif 索引。
    #: 索引**单一来源**：`genome.motif_subset_A`（不在此另写一版）。
    division_drive_gain: float = 1.0
    division_locus_gain: float = 0.0
    division_locus_indices: tuple[int, ...] = (0,)
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
    #: §7(iv) 的 ρ(W⁰) 重定目标（仿 §4 对 `W_g` 的 `grn_spectral_radius=0.9`）。
    rho_w0_target: float = 0.9
    tau_min: float = 1.0
    tau_max: float = 10.0
    #: `connectome §9` 的 w/o GRN 消融开关与独立随机布线密度（默认关；见 RGCD §8 消融）
    ablation_w_grn: bool = False
    ablation_random_density: float = 0.15

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
    def from_config(cls, cfg: ModelConfig) -> RGCDConfig:
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
            domain_identity_spread_scale=cfg.development.domain_identity_spread_scale,
            division_drive_gain=cfg.development.division_drive_gain,
            division_locus_gain=cfg.development.division_locus_gain,
            division_locus_indices=(cfg.genome.motif_subset_A,),
            zero_input_steps=cfg.development.zero_input_steps,
            saturation_ratio_max=cfg.development.saturation_ratio_max,
            saturation_eps=cfg.development.saturation_eps,
            target_density=cfg.connectome.target_density,
            allow_self_loops=cfg.connectome.allow_self_loops,
            distance_lambda=cfg.connectome.distance_lambda,
            distance_space=cfg.connectome.distance_space,
            regulatory_gamma=cfg.connectome.regulatory_gamma,
            w_bar_initial=cfg.connectome.w_bar_initial,
            rho_w0_target=cfg.connectome.rho_w0_target,
            ablation_w_grn=cfg.connectome.ablation_w_grn,
            ablation_random_density=cfg.connectome.ablation_random_density,
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
    cfg = load_config(path, overrides=overrides, environ=environ)
    return RGCDConfig.from_config(cfg)
