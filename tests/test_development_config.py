from pathlib import Path

import yaml

from evogenesis.development.config import (
    DEFAULT_CONFIG,
    DEFAULT_MODEL_CONFIG_PATH,
    load_development_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

FIELD_SOURCES = {
    # RGCDConfig 字段 -> (yaml 节, yaml 键)
    "grn_dim": ("grn", "dim"),
    "development_steps": ("grn", "development_steps"),
    "grn_rho": ("grn", "rho"),
    "grn_activation": ("grn", "activation"),
    "grn_weight_init": ("grn", "weight_init"),
    "grn_spectral_radius": ("grn", "spectral_radius"),
    "init_b_std": ("grn", "init_b_std"),
    "initial_precursors": ("development", "initial_precursors"),
    "domains": ("development", "domains"),
    "precursors_per_domain": ("development", "precursors_per_domain"),
    "max_divisions_per_precursor": ("development", "max_divisions_per_precursor"),
    "max_neurons": ("development", "max_neurons"),
    "placement": ("development", "placement"),
    "position_space": ("development", "position_space"),
    "split_noise": ("development", "split_noise"),
    "gene_noise": ("development", "gene_noise"),
    "division_drive_gain": ("development", "division_drive_gain"),
    "division_locus_gain": ("development", "division_locus_gain"),
    "c_domain_bonus": ("development", "c_domain_bonus"),
    "zero_input_steps": ("development", "zero_input_steps"),
    "saturation_ratio_max": ("development", "saturation_ratio_max"),
    "saturation_eps": ("development", "saturation_eps"),
    "target_density": ("connectome", "target_density"),
    "allow_self_loops": ("connectome", "allow_self_loops"),
    "distance_lambda": ("connectome", "distance_lambda"),
    "distance_space": ("connectome", "distance_space"),
    "regulatory_gamma": ("connectome", "regulatory_gamma"),
    "w_bar_initial": ("connectome", "w_bar_initial"),
    "tau_min": ("connectome", "tau_min"),
    "tau_max": ("connectome", "tau_max"),
    "network_activation": ("network", "activation"),
}


def _yaml_model() -> dict:
    assert DEFAULT_MODEL_CONFIG_PATH.is_file(), DEFAULT_MODEL_CONFIG_PATH
    return yaml.safe_load(Path(DEFAULT_MODEL_CONFIG_PATH).read_text(encoding="utf-8"))


def test_default_config_mirrors_frozen_config():
    model = _yaml_model()
    for field, (section, key) in FIELD_SOURCES.items():
        expected = model[section][key]
        if field == "domains":
            expected = tuple(expected)
        assert getattr(DEFAULT_CONFIG, field) == expected, field


def test_load_development_config_reads_default_path():
    assert load_development_config() == DEFAULT_CONFIG


def test_load_development_config_none_returns_mirror():
    assert load_development_config(None) == DEFAULT_CONFIG


def test_load_development_config_applies_overrides():
    cfg = load_development_config(overrides={"connectome": {"target_density": 0.2}})
    assert cfg.target_density == 0.2
    assert cfg.grn_dim == DEFAULT_CONFIG.grn_dim


def test_weight_feature_dim_matches_section_10():
    # [g_i; g_j; z_i; z_j] = 8 + 8 + 6 + 6 = 28（RGCD §10）
    assert DEFAULT_CONFIG.weight_feature_dim == 28
