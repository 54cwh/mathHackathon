"""`--override` 解析与消融臂配置测试（`experiment §3.4`；`connectome §9`）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from evogenesis.arena.config import load_arena_config
from evogenesis.development.config import load_development_config
from evogenesis.experiment.environments import load_environment
from evogenesis.experiment.overrides import parse_overrides
from evogenesis.pipeline import (
    initial_population,
    load_model_chain_config,
    motif_catalog,
    phenotype_of,
    phenotypes_of,
)


def test_parse_overrides_types_and_merge():
    parsed = parse_overrides(
        [
            "connectome.tau_min=5.5",
            "connectome.tau_max=5.5",
            "connectome.distance_lambda=0",
            "genome.motif_length=6",
        ]
    )
    assert parsed["connectome"] == {"tau_min": 5.5, "tau_max": 5.5, "distance_lambda": 0}
    assert isinstance(parsed["connectome"]["tau_min"], float)
    assert isinstance(parsed["connectome"]["distance_lambda"], int)
    assert parsed["genome"]["motif_length"] == 6


@pytest.mark.parametrize(
    "bad", ["connectome_tau_min=1", "connectome=1", "connectome.tau.min=1", "x"]
)
def test_parse_overrides_rejects_malformed(bad):
    with pytest.raises(ValueError):
        parse_overrides([bad])


def test_model_chain_config_plumbs_overrides_to_rgcd_and_network():
    overrides = {"connectome": {"tau_min": 5.5, "tau_max": 5.5, "distance_lambda": 0.0}}
    model_config = Path(__file__).resolve().parents[1] / "configs" / "default_model.yaml"
    chain = load_model_chain_config(model_config, overrides=overrides)
    assert chain.rgcd.tau_min == 5.5 and chain.rgcd.tau_max == 5.5
    assert chain.rgcd.distance_lambda == 0.0
    assert chain.network.tau_min == 5.5  # DanioNet 侧同源


def test_homogeneous_tau_override_yields_constant_tau():
    overrides = {"connectome": {"tau_min": 5.5, "tau_max": 5.5}}
    rgcd = load_development_config(overrides=overrides)
    population = initial_population(master_seed=23, experiment_id="probe", n=6)
    motifs = motif_catalog(23)
    phenotype = phenotype_of(population[0].genome, motifs, master_seed=23, index=0, config=rgcd)
    assert bool((phenotype.tau == phenotype.tau[0]).all())
    assert float(phenotype.tau[0]) == pytest.approx(5.5, abs=1e-6)


def test_no_wiring_cost_override_is_accepted():
    rgcd = load_development_config(overrides={"connectome": {"distance_lambda": 0.0}})
    assert rgcd.distance_lambda == 0.0
    population = initial_population(master_seed=23, experiment_id="probe", n=6)
    phenotypes = phenotypes_of(population, motif_catalog(23), master_seed=23, config=rgcd)
    assert len(phenotypes) == 6  # 仍可发育（λ=0 不破坏管线）


def test_environment_overrides_are_arena_scoped():
    """`--environment` 的覆盖只作用于 Arena 配置（population/...），与 model chain 正交。"""
    arena = load_arena_config(overrides=load_environment("food_rich"))
    assert arena.population.n_prey == 48
    assert arena.population.prey_regrowth_steps == 13
