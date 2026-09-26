"""模型链装配（`pipeline/模型链装配.md`）：config → 种群 → q(G) → 发育 → DanioNet 动作。"""

from dataclasses import replace

import numpy as np
import pytest

from evogenesis.arena.config import load_arena_config
from evogenesis.arena.env import DanioArena
from evogenesis.core.ids import mint_id
from evogenesis.core.seed import SeedManager
from evogenesis.pipeline.arena_episode import run_arena_episode
from evogenesis.pipeline.model_chain import (
    danionet_of,
    initial_population,
    load_model_chain_config,
    motif_catalog,
    phenotype_of,
)

MASTER_SEED = 250927
EXPERIMENT_ID = "exp-pipeline"


def test_load_model_chain_config_matches_frozen_yaml():
    chain = load_model_chain_config()
    assert chain.layout.chromosome_pairs == 2
    assert chain.layout.bp_per_haplotype_chromosome == 128
    assert chain.rgcd.grn_dim == 8
    assert chain.network.sensory_dim == 12


def test_initial_population_is_deterministic_and_minted():
    population = initial_population(master_seed=MASTER_SEED, experiment_id=EXPERIMENT_ID, n=3)
    assert [ind.genome_id for ind in population] == [
        mint_id(EXPERIMENT_ID, "genome", 0, index) for index in range(3)
    ]
    assert population[0].genome.haploid_bp == 256
    assert [ind.fish_id for ind in population] == [
        mint_id(EXPERIMENT_ID, "fish", 0, index) for index in range(3)
    ]
    again = initial_population(master_seed=MASTER_SEED, experiment_id=EXPERIMENT_ID, n=3)
    assert [ind.genome.maternal_haplotype for ind in population] == [
        ind.genome.maternal_haplotype for ind in again
    ]


def test_motif_catalog_shape():
    motifs = motif_catalog(MASTER_SEED)
    assert len(motifs) == 8
    assert all(len(motif) == 6 for motif in motifs)


def test_chain_to_danionet_actions():
    chain = load_model_chain_config()
    motifs = motif_catalog(MASTER_SEED)
    population = initial_population(master_seed=MASTER_SEED, experiment_id=EXPERIMENT_ID, n=60)
    phenotypes = [
        phenotype_of(ind.genome, motifs, master_seed=MASTER_SEED, index=index, config=chain.rgcd)
        for index, ind in enumerate(population)
    ]
    viable = [phenotype for phenotype in phenotypes if phenotype.viable]
    assert viable, "60 次抽样内未出现 viable 发育产物（模型层面问题）"
    net = danionet_of(viable[:1], master_seed=MASTER_SEED, config=chain.network)
    observation = np.zeros((1, chain.network.sensory_dim), dtype=np.float32)
    omega, v = net.step(observation)
    assert -1.0 <= float(omega.detach()) <= 1.0
    assert 0.0 <= float(v.detach()) <= 1.0


def test_run_arena_episode_is_deterministic():
    chain = load_model_chain_config()
    arena_config = load_arena_config(None)
    population = initial_population(master_seed=MASTER_SEED, experiment_id=EXPERIMENT_ID, n=160)
    first = run_arena_episode(
        population, master_seed=MASTER_SEED, chain=chain, arena_config=arena_config, steps=40
    )
    second = run_arena_episode(
        population, master_seed=MASTER_SEED, chain=chain, arena_config=arena_config, steps=40
    )
    assert first.steps == 40
    assert first.evaluated_individuals == len(first.per_fish)
    stable_fish_ids = {ind.fish_id for ind in population}
    assert set(first.per_fish) <= stable_fish_ids
    assert first.per_fish == second.per_fish


def test_arena_accepts_stable_fish_and_genome_ids():
    base = load_arena_config(None)
    config = replace(base, population=replace(base.population, n_fish=2))
    fish_ids = ["exp:g0:fish0000", "exp:g0:fish0001"]
    genome_ids = ["exp:g0:genome0000", "exp:g0:genome0001"]
    arena = DanioArena(
        config, spawn_seed=7, dynamics_seed=7, fish_ids=fish_ids, genome_ids=genome_ids
    )
    arena.reset()
    assert set(arena.fish) == set(fish_ids)
    assert [arena.fish[fid].genome_id for fid in fish_ids] == genome_ids
    with pytest.raises(ValueError):
        DanioArena(
            config, spawn_seed=7, dynamics_seed=7, fish_ids=fish_ids, genome_ids=["only-one"]
        )


def test_arena_injects_generation_into_live_fish():
    base = load_arena_config(None)
    config = replace(base, population=replace(base.population, n_fish=1))
    arena = DanioArena(config, spawn_seed=7, dynamics_seed=7, generation=3)
    arena.reset()
    assert next(iter(arena.fish.values())).generation == 3


def test_run_arena_episode_propagates_generation():
    chain = load_model_chain_config()
    arena_config = load_arena_config(None)
    population = initial_population(master_seed=MASTER_SEED, experiment_id=EXPERIMENT_ID, n=60)
    result = run_arena_episode(
        population,
        master_seed=MASTER_SEED,
        chain=chain,
        arena_config=arena_config,
        steps=2,
        generation=3,
    )
    assert result.per_fish
    assert all(rec["generation"] == 3 for rec in result.per_fish.values())


def test_arena_seeds_are_namespaced():
    from evogenesis.pipeline.arena_episode import arena_seeds_for

    spawn_seed, dynamics_seed = arena_seeds_for(MASTER_SEED)
    manager = SeedManager(MASTER_SEED)
    assert spawn_seed == manager.seed("arena_spawn", 0)
    assert dynamics_seed == manager.seed("arena_dynamics", 0)
    assert spawn_seed != dynamics_seed != MASTER_SEED
