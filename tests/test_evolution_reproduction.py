"""繁殖：gamete/fertilization 复用与突变/交叉率透传（``evolution §3/§5/§8``）。"""

import numpy as np
import pytest

from evogenesis.core.ids import mint_id
from evogenesis.evolution.reproduction import (
    gamete_seed_index,
    offspring_genome,
    with_genome_id,
)
from evogenesis.genome.config import DEFAULT_LAYOUT, GenomeLayout
from evogenesis.genome.genome import ChromosomePair, DiploidGenome, hamming_distance

SHORT = GenomeLayout(
    bp_per_haplotype_chromosome=8,
    chromosome_pairs=2,
    motif_count=2,
    motif_length=2,
    motif_topk=1,
    motif_subset_A=0,
    motif_subset_B=1,
)


def _genome(pair_chains, *, genome_id="g-0001", layout=DEFAULT_LAYOUT):
    pairs = tuple(ChromosomePair(m, p, layout=layout) for m, p in pair_chains)
    return DiploidGenome(pairs, genome_id=genome_id, layout=layout)


def _homozygous(chain_per_pair, *, genome_id="g-0001", layout=DEFAULT_LAYOUT):
    return _genome([(chain, chain) for chain in chain_per_pair], genome_id=genome_id, layout=layout)


def test_offspring_without_crossover_copies_parental_chains():
    parent_a = _genome([("A" * 8, "C" * 8), ("A" * 8, "C" * 8)], layout=SHORT)
    parent_b = _genome([("G" * 8, "T" * 8), ("G" * 8, "T" * 8)], layout=SHORT)
    child = offspring_genome(
        parent_a,
        parent_b,
        mu=0.0,
        crossover_probability=0.0,
        crossover_rng=np.random.default_rng(0),
        mutation_rng=np.random.default_rng(1),
        layout=SHORT,
    )
    for i in range(2):
        assert child.pairs[i].maternal in {parent_a.pairs[i].maternal, parent_a.pairs[i].paternal}
        assert child.pairs[i].paternal in {parent_b.pairs[i].maternal, parent_b.pairs[i].paternal}


def test_crossover_probability_is_transmitted():
    parent_a = _genome([("A" * 8, "C" * 8), ("A" * 8, "C" * 8)], layout=SHORT)
    parent_b = _genome([("G" * 8, "T" * 8), ("G" * 8, "T" * 8)], layout=SHORT)
    child = offspring_genome(
        parent_a,
        parent_b,
        mu=0.0,
        crossover_probability=1.0,
        crossover_rng=np.random.default_rng(0),
        mutation_rng=np.random.default_rng(1),
        layout=SHORT,
    )
    # p_c=1 时每条染色体必为重组体，严格不等于亲本任一同源链。
    for i in range(2):
        assert child.pairs[i].maternal not in {"A" * 8, "C" * 8}
        assert child.pairs[i].paternal not in {"G" * 8, "T" * 8}


def test_mutation_rate_is_transmitted_matches_binomial_expectation():
    # 亲本各对同源链相同，故子代两链相对亲本链的 Hamming 距离=该 gamete 的突变数。
    parent_a = _homozygous(["A" * 128, "C" * 128])
    parent_b = _homozygous(["G" * 128, "T" * 128])
    mu = 0.001
    crossover_rng = np.random.default_rng(2024)
    mutation_rng = np.random.default_rng(42)
    n_children = 3000
    total = 0
    for _ in range(n_children):
        child = offspring_genome(
            parent_a,
            parent_b,
            mu=mu,
            crossover_probability=0.0,
            crossover_rng=crossover_rng,
            mutation_rng=mutation_rng,
        )
        for i in range(2):
            total += hamming_distance(child.pairs[i].maternal, parent_a.pairs[i].maternal)
            total += hamming_distance(child.pairs[i].paternal, parent_b.pairs[i].maternal)
    observed = total / n_children
    expected = 2 * 2 * 128 * mu  # 2 gamete × 2 chromosome × 128 bp × mu
    # 每子代计数 ~ Binomial(512, 0.001)：σ_child=0.715；n=3000 → σ_mean=0.0131，
    # abs=0.06 约 4.6σ（并计入极小概率的回突变重合）。
    assert observed == pytest.approx(expected, abs=0.06)


def test_with_genome_id_matches_mint_id_format():
    genome = _genome([("A" * 128, "C" * 128), ("A" * 128, "C" * 128)])
    stamped = with_genome_id(genome, experiment_id="exp-0001", generation=2, index=7)
    assert stamped.genome_id == mint_id("exp-0001", "genome", 2, 7)
    assert stamped.genome_id == "exp-0001:g2:genome0007"
    assert stamped.pairs == genome.pairs


def test_gamete_seed_index_is_globally_unique():
    # core §3 配子级 t = generation * N + index：跨代同 index 不复用随机流。
    n = 48
    assert gamete_seed_index(mint_id("exp-0001", "genome", 0, 0), population_size=n) == 0
    assert gamete_seed_index(mint_id("exp-0001", "genome", 3, 11), population_size=n) == 3 * n + 11
    assert gamete_seed_index("exp-0001:g3:genome0042", population_size=n) == 3 * n + 42
    same_slot_next_gen = gamete_seed_index("exp-0001:g4:genome0042", population_size=n)
    assert same_slot_next_gen != gamete_seed_index("exp-0001:g3:genome0042", population_size=n)


@pytest.mark.parametrize("bad", ["", "exp-0001:g3:fish0001", "exp-0001:g3:genomeXX", "nope"])
def test_gamete_seed_index_rejects_malformed(bad):
    with pytest.raises(ValueError):
        gamete_seed_index(bad, population_size=48)


def test_gamete_seed_index_rejects_nonpositive_population_size():
    with pytest.raises(ValueError):
        gamete_seed_index(mint_id("exp-0001", "genome", 1, 0), population_size=0)


def test_same_seed_reproducible():
    parent_a = _genome([("A" * 8, "C" * 8), ("G" * 8, "T" * 8)], layout=SHORT)
    parent_b = _genome([("C" * 8, "A" * 8), ("T" * 8, "G" * 8)], layout=SHORT)

    def draw():
        return offspring_genome(
            parent_a,
            parent_b,
            mu=0.05,
            crossover_probability=0.5,
            crossover_rng=np.random.default_rng(11),
            mutation_rng=np.random.default_rng(12),
            layout=SHORT,
        )

    assert draw() == draw()


def test_different_seed_changes_offspring():
    parent_a = _genome([("A" * 8, "C" * 8), ("G" * 8, "T" * 8)], layout=SHORT)
    parent_b = _genome([("C" * 8, "A" * 8), ("T" * 8, "G" * 8)], layout=SHORT)
    first = offspring_genome(
        parent_a,
        parent_b,
        mu=0.05,
        crossover_probability=0.5,
        crossover_rng=np.random.default_rng(1),
        mutation_rng=np.random.default_rng(2),
        layout=SHORT,
    )
    second = offspring_genome(
        parent_a,
        parent_b,
        mu=0.05,
        crossover_probability=0.5,
        crossover_rng=np.random.default_rng(3),
        mutation_rng=np.random.default_rng(4),
        layout=SHORT,
    )
    assert first != second
