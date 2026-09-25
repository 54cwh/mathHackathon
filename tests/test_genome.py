import random

from evogenesis.design.genome import ChromosomePair, DiploidGenome, make_gamete


def test_diploid_length():
    s = "A" * 128
    g = DiploidGenome((ChromosomePair(s, s), ChromosomePair(s, s)))
    assert g.diploid_bp == 512


def test_gamete_length():
    s = "A" * 128
    g = DiploidGenome((ChromosomePair(s, s), ChromosomePair(s, s)))
    gamete = make_gamete(g, 0.001, 0.5, random.Random(1))
    assert len(gamete) == 2
    assert all(len(x) == 128 for x in gamete)
