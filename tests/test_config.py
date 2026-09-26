from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from evogenesis.core.config import config_snapshot, load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = REPO_ROOT / "configs" / "default_model.yaml"


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _minimal() -> dict:
    return {
        "genome": {
            "chromosome_pairs": 2,
            "bp_per_haplotype_chromosome": 128,
            "alphabet": ["A", "C", "G", "T"],
            "motif_count": 8,
            "motif_length": 6,
            "motif_window": 6,
            "motif_topk": 3,
            "motif_scan_scope": "per_chromosome",
            "motif_subset_A": 0,
            "motif_subset_B": 1,
        },
        "phenotype": {"theta_N": 0.25, "theta_H": 0.25},
        "grn": {
            "dim": 8,
            "development_steps": 12,
            "rho": 0.35,
            "activation": "sigmoid",
            "weight_init": "xavier",
            "spectral_radius": 0.9,
            "init_b_std": 0.1,
        },
        "development": {
            "initial_precursors": 24,
            "domains": ["sensory", "prey", "threat", "integrator_memory", "inhibitory", "motor"],
            "precursors_per_domain": 4,
            "max_divisions_per_precursor": 1,
            "max_neurons": 48,
            "placement": "domain_blocked",
            "position_space": "unit_square",
            "split_noise": 0.05,
            "gene_noise": 0.1,
            "c_domain_bonus": 1.5,
            "zero_input_steps": 50,
            "saturation_ratio_max": 0.9,
            "saturation_eps": 0.001,
        },
        "connectome": {
            "target_density": 0.15,
            "allow_self_loops": False,
            "distance_lambda": 2.0,
            "distance_space": "unit_square",
            "regulatory_gamma": 1.0,
            "w_bar_initial": 0.5,
            "ablation_random_density": 0.15,
            "tau_min": 1.0,
            "tau_max": 10.0,
        },
        "network": {
            "sensory_dim": 12,
            "action_dim": 2,
            "activation": "tanh",
            "input_weight_scope": "per_cell_type",
            "input_weight_std": 0.289,
            "hunger_gain_std": 0.1,
            "neuron_bias_std": 0.1,
            "motor_pool_split": "median_x",
            "action_pooling": "mean",
        },
        "learning": {
            "method": "behavior_cloning",
            "optimizer": "adam",
            "lr": 0.001,
            "mini_batch_updates": 20,
            "batch_size": 64,
            "trajectories": 200,
            "optional_rl": False,
            "loss_weight_omega": 0.4,
            "loss_weight_v": 1.6,
        },
    }


def test_loads_frozen_default_model():
    cfg = load_config(DEFAULT_MODEL, environ={})
    assert cfg.genome.chromosome_pairs == 2
    assert cfg.genome.bp_per_haplotype_chromosome == 128
    assert cfg.phenotype.theta_N == 0.25
    assert cfg.phenotype.theta_H == 0.25
    assert cfg.network.sensory_dim == 12
    assert cfg.learning.lr == 0.001
    assert cfg.learning.optimizer == "adam"


def test_precedence_cli_over_env_over_file(tmp_path):
    path = _write(tmp_path, _minimal())
    cfg = load_config(
        path,
        overrides={"learning.lr": 0.9},
        environ={"EVOGENESIS_LEARNING__LR": "0.5"},
    )
    assert cfg.learning.lr == 0.9


def test_env_overrides_file(tmp_path):
    path = _write(tmp_path, _minimal())
    cfg = load_config(path, environ={"EVOGENESIS_LEARNING__LR": "0.5"})
    assert cfg.learning.lr == 0.5
    assert cfg.learning.batch_size == 64


def test_file_only(tmp_path):
    path = _write(tmp_path, _minimal())
    cfg = load_config(path, environ={})
    assert cfg.learning.lr == 0.001


def test_cli_nested_dict_override(tmp_path):
    path = _write(tmp_path, _minimal())
    cfg = load_config(path, overrides={"learning": {"lr": 0.25}}, environ={})
    assert cfg.learning.lr == 0.25
    assert cfg.learning.optimizer == "adam"


def test_ignores_unrelated_env(tmp_path):
    path = _write(tmp_path, _minimal())
    cfg = load_config(path, environ={"PATH": "/usr/bin", "EVOGENESIS_LEARNING__LR": "0.2"})
    assert cfg.learning.lr == 0.2


def test_invalid_type_rejected(tmp_path):
    path = _write(tmp_path, _minimal())
    with pytest.raises(ValidationError):
        load_config(path, overrides={"learning.lr": "fast"}, environ={})


def test_unknown_key_rejected(tmp_path):
    data = _minimal()
    data["learning"]["nope"] = 1
    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, data), environ={})


def test_missing_section_rejected(tmp_path):
    data = _minimal()
    del data["network"]
    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, data), environ={})


def test_missing_file_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "absent.yaml", environ={})


def test_snapshot_roundtrip():
    cfg = load_config(DEFAULT_MODEL, environ={})
    snapshot = config_snapshot(cfg)
    assert snapshot["phenotype"]["theta_N"] == 0.25
    assert load_config(DEFAULT_MODEL, environ={}).model_dump() == snapshot
