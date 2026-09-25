import random

from evogenesis.genome.genome import mutate_sequence


def test_mutation_reproducibility():
    seq = "A" * 128
    assert mutate_sequence(seq, 0.1, random.Random(123)) == mutate_sequence(
        seq, 0.1, random.Random(123)
    )
