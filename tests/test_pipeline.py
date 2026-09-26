"""模型链装配（`pipeline/模型链装配.md`）：config → 种群 → q(G) → 发育 → DanioNet 动作。"""

import numpy as np

from evogenesis.arena.config import load_arena_config
from evogenesis.core.ids import mint_id
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
