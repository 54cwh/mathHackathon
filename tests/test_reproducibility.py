from evogenesis.core.seed import SeedManager
from evogenesis.genome.genome import mutate_sequence


def test_mutation_reproducibility():
    seq = "A" * 128
    first = mutate_sequence(seq, 0.1, SeedManager(123).rng("mutation"))
    second = mutate_sequence(seq, 0.1, SeedManager(123).rng("mutation"))
    assert first == second
    assert first != seq
