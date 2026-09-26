"""evolution 配置加载与漂移守护（owner：``configs/evolution.yaml``）。"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from evogenesis.evolution.config import (
    DEFAULT_EVOLUTION_CONFIG_PATH,
    EvolutionConfig,
    FitnessWeights,
    load_evolution_config,
)
from evogenesis.experiment.metrics import COMPOSITE_WEIGHTS


def _yaml_data() -> dict:
    assert DEFAULT_EVOLUTION_CONFIG_PATH.is_file(), DEFAULT_EVOLUTION_CONFIG_PATH
    return yaml.safe_load(Path(DEFAULT_EVOLUTION_CONFIG_PATH).read_text(encoding="utf-8"))


def test_load_evolution_config_mirrors_frozen_config():
    config = load_evolution_config()
    data = _yaml_data()
    assert config.population_size == data["population_size"] == 48
    assert config.tournament_size == data["tournament_size"] == 2
    assert (
        config.fitness_normalization
        == data["fitness_normalization"]
        == ("within_generation_minmax")
    )
    assert (
        config.mutation_rate_per_base_per_gamete
        == data["mutation_rate_per_base_per_gamete"]
        == 0.001
    )
    assert (
        config.crossover_probability_per_chromosome
        == data["crossover_probability_per_chromosome"]
        == 0.5
    )
    assert "max_crossovers_per_chromosome" not in data
    assert config.generation_buttons == data["generation_buttons"]
    assert config.mendel_display_offspring == data["mendel_display_offspring"] == 160


def test_fitness_normalization_is_constrained_literal():
    # §6 定稿：唯一允许的归一化口径是代内 min-max。
    assert load_evolution_config().fitness_normalization == "within_generation_minmax"
    with pytest.raises(ValidationError):
        load_evolution_config(overrides={"fitness_normalization": "global_zscore"})


def test_fitness_weights_match_experiment_composite_weights():
    # 漂移守护（§6 边界）：选择用 F 的权重与 experiment/metrics.py 的显示分权重必须一致。
    assert load_evolution_config().fitness_weights.model_dump() == COMPOSITE_WEIGHTS


def test_fitness_weights_read_from_config_not_hardcoded():
    config = load_evolution_config()
    assert config.fitness_weights == FitnessWeights(
        survival=0.35, prey_capture=0.25, escape_success=0.20, energy_efficiency=0.20
    )
    assert config.fitness_weights.model_dump() == _yaml_data()["fitness_weights"]


def test_overrides_apply_and_partial_weight_merges():
    config = load_evolution_config(
        overrides={"population_size": 8, "fitness_weights": {"survival": 1.0}}
    )
    assert config.population_size == 8
    assert config.fitness_weights.survival == 1.0
    assert config.fitness_weights.prey_capture == 0.25
    assert config.mutation_rate_per_base_per_gamete == 0.001


def test_env_overrides_apply():
    config = load_evolution_config(environ={"EVOGENESIS_POPULATION_SIZE": "7"})
    assert config.population_size == 7


def test_missing_keys_rejected():
    with pytest.raises(ValidationError):
        EvolutionConfig(population_size=1)


def test_none_path_rejected():
    with pytest.raises(ValueError):
        load_evolution_config(None)
