import random
from dataclasses import dataclass

BASES = "ACGT"


@dataclass(frozen=True)
class ChromosomePair:
    maternal: str
    paternal: str

    def __post_init__(self):
        if len(self.maternal) != 128 or len(self.paternal) != 128:
            raise ValueError("Each haplotype chromosome must be 128 bp.")
        if set(self.maternal + self.paternal) - set(BASES):
            raise ValueError("Genome contains non-ACGT symbols.")


@dataclass(frozen=True)
class DiploidGenome:
    pairs: tuple[ChromosomePair, ChromosomePair]

    @property
    def diploid_bp(self) -> int:
        return sum(len(p.maternal) + len(p.paternal) for p in self.pairs)


def mutate_sequence(seq: str, mu: float, rng: random.Random) -> str:
    out = []
    for b in seq:
        if rng.random() < mu:
            out.append(rng.choice([x for x in BASES if x != b]))
        else:
            out.append(b)
    return "".join(out)


def crossover(a: str, b: str, probability: float, rng: random.Random):
    if rng.random() >= probability:
        return a, b
    point = rng.randint(1, len(a) - 1)
    return a[:point] + b[point:], b[:point] + a[point:]


def make_gamete(genome: DiploidGenome, mu: float, crossover_probability: float, rng: random.Random):
    gamete = []
    for pair in genome.pairs:
        x, y = crossover(pair.maternal, pair.paternal, crossover_probability, rng)
        gamete.append(mutate_sequence(rng.choice([x, y]), mu, rng))
    return tuple(gamete)


def fertilize(gamete_a, gamete_b) -> DiploidGenome:
    return DiploidGenome(
        (
            ChromosomePair(gamete_a[0], gamete_b[0]),
            ChromosomePair(gamete_a[1], gamete_b[1]),
        )
    )
