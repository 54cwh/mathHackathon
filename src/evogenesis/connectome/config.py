"""DanioNet 读出配置：取值 owner 为 ``configs/default_model.yaml`` 的 ``network`` 节。

``max_nodes``（padding 宽度）与 ``domains``（六类神经元顺序）取自 ``development`` 节
（前者是 RGCD ``max_neurons``，见 `DanioNet设计规范.md` §3 定稿段）。
本模块不新造数值：``NetworkReadoutConfig`` 的默认值是冻结配置的镜像，由
``tests/test_network_config.py`` 的漂移守护测试断言一致。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evogenesis.core.config import ModelConfig, load_config

DEFAULT_MODEL_CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "default_model.yaml"

DOMAIN_ORDER: tuple[str, ...] = (
    "sensory",
    "prey",
    "threat",
    "integrator_memory",
    "inhibitory",
    "motor",
)


@dataclass(frozen=True)
class NetworkReadoutConfig:
    """DanioNet 读出参数（镜像 ``configs/default_model.yaml``）。"""

    sensory_dim: int = 12
    action_dim: int = 2
    activation: str = "tanh"
    input_weight_std: float = 0.289
    hunger_gain_std: float = 0.1
    neuron_bias_std: float = 0.1
    motor_pool_split: str = "median_x"
    action_pooling: str = "mean"
    input_weight_scope: str = "per_cell_type"
    # §7 viability 判据（与 development 同一组）
    zero_input_steps: int = 50
    saturation_ratio_max: float = 0.9
    saturation_eps: float = 0.001
    max_nodes: int = 48
    domains: tuple[str, ...] = DOMAIN_ORDER

    def __post_init__(self) -> None:
        if self.action_dim != 2:
            raise NotImplementedError(f"未实现 action_dim={self.action_dim}（§4 输出 (ω, v)）")
        if self.input_weight_scope != "per_cell_type":
            raise NotImplementedError(
                f"未实现 input_weight_scope={self.input_weight_scope!r}（§3 U_i=U_{{type_i}}）"
            )
        if self.motor_pool_split != "median_x":
            raise NotImplementedError(f"未实现 motor_pool_split={self.motor_pool_split!r}（§5）")
        if self.action_pooling != "mean":
            raise NotImplementedError(f"未实现 action_pooling={self.action_pooling!r}（§4）")

    @property
    def n_cell_types(self) -> int:
        return len(self.domains)


DEFAULT_NETWORK_CONFIG = NetworkReadoutConfig()


def load_network_config(
    path: str | os.PathLike[str] | None = DEFAULT_MODEL_CONFIG_PATH,
    *,
    overrides: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> NetworkReadoutConfig:
    """按 ``CLI > env > file > default`` 读取 ``network``/``development`` 节。

    ``path=None`` 时只用 ``NetworkReadoutConfig`` 默认值（冻结配置的镜像）。
    """
    if path is None:
        return NetworkReadoutConfig()
    cfg: ModelConfig = load_config(path, overrides=overrides, environ=environ)
    return NetworkReadoutConfig(
        sensory_dim=cfg.network.sensory_dim,
        action_dim=cfg.network.action_dim,
        activation=cfg.network.activation,
        input_weight_std=cfg.network.input_weight_std,
        hunger_gain_std=cfg.network.hunger_gain_std,
        neuron_bias_std=cfg.network.neuron_bias_std,
        motor_pool_split=cfg.network.motor_pool_split,
        action_pooling=cfg.network.action_pooling,
        input_weight_scope=cfg.network.input_weight_scope,
        zero_input_steps=cfg.development.zero_input_steps,
        saturation_ratio_max=cfg.development.saturation_ratio_max,
        saturation_eps=cfg.development.saturation_eps,
        max_nodes=cfg.development.max_neurons,
        domains=tuple(cfg.development.domains),
    )
