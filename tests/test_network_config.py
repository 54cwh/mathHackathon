"""DanioNet 读出配置的漂移守护与加载测试。

契约：取值 owner 为 ``configs/default_model.yaml``（``network`` 节 + ``development`` 节的
``max_neurons``/``domains``）。
"""

from pathlib import Path

import yaml

from evogenesis.connectome.config import (
    DEFAULT_MODEL_CONFIG_PATH,
    DEFAULT_NETWORK_CONFIG,
    NetworkReadoutConfig,
    load_network_config,
)

NETWORK_FIELDS = (
    "sensory_dim",
    "action_dim",
    "activation",
    "input_weight_std",
    "hunger_gain_std",
    "neuron_bias_std",
    "motor_pool_split",
    "action_pooling",
    "input_weight_scope",
)

DEVELOPMENT_FIELDS = ("zero_input_steps", "saturation_ratio_max", "saturation_eps")


def _sections() -> tuple[dict, dict]:
    assert DEFAULT_MODEL_CONFIG_PATH.is_file(), DEFAULT_MODEL_CONFIG_PATH
    data = yaml.safe_load(Path(DEFAULT_MODEL_CONFIG_PATH).read_text(encoding="utf-8"))
    return data["network"], data["development"]


def test_default_config_mirrors_frozen_config():
    network, development = _sections()
    for name in NETWORK_FIELDS:
        assert getattr(DEFAULT_NETWORK_CONFIG, name) == network[name], name
    for name in DEVELOPMENT_FIELDS:
        assert getattr(DEFAULT_NETWORK_CONFIG, name) == development[name], name
    assert DEFAULT_NETWORK_CONFIG.max_nodes == development["max_neurons"]
    assert list(DEFAULT_NETWORK_CONFIG.domains) == development["domains"]


def test_load_network_config_reads_default_path():
    assert load_network_config() == DEFAULT_NETWORK_CONFIG


def test_load_network_config_applies_overrides():
    cfg = load_network_config(overrides={"network": {"hunger_gain_std": 0.25}})
    assert cfg.hunger_gain_std == 0.25
    assert cfg.sensory_dim == DEFAULT_NETWORK_CONFIG.sensory_dim


def test_load_network_config_none_returns_mirror():
    assert load_network_config(None) == NetworkReadoutConfig()


def test_unsupported_split_and_pooling_rejected():
    import pytest

    with pytest.raises(NotImplementedError):
        NetworkReadoutConfig(motor_pool_split="x_quantile")
    with pytest.raises(NotImplementedError):
        NetworkReadoutConfig(action_pooling="max")
    with pytest.raises(NotImplementedError):
        NetworkReadoutConfig(action_dim=3)
    with pytest.raises(NotImplementedError):
        NetworkReadoutConfig(input_weight_scope="global")
