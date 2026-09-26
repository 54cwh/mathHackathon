"""世代推进测试（``evolution §5/§7``）：出生数、世代不重叠、ID、复现、瓶颈。"""

import numpy as np

from evogenesis.core.ids import mint_id
from evogenesis.core.seed import SeedManager
from evogenesis.evolution.config import load_evolution_config
from evogenesis.evolution.population import (
    EVENT_POPULATION_BOTTLENECK,
    Individual,
    advance_generation,
)
from evogenesis.evolution.selection import random_pairs
from evogenesis.genome.config import DEFAULT_LAYOUT
from evogenesis.genome.genome import ChromosomePair, DiploidGenome


def _genome(genome_id: str, chain: str = "A") -> DiploidGenome:
    pair = ChromosomePair(chain * 128, chain * 128, layout=DEFAULT_LAYOUT)
    return DiploidGenome((pair, pair), genome_id=genome_id, layout=DEFAULT_LAYOUT)


def _individual(
    genome_id: str, fitness: float = 0.0, viable: bool = True, reason=None
) -> Individual:
    return Individual(
        genome_id=genome_id,
        genome=_genome(genome_id),
        fitness=fitness,
        viable=viable,
        failure_reason=reason,
    )


def _parents(n: int = 3) -> list[Individual]:
    return [
        _individual(f"exp-0001:g0:genome{i:04d}", fitness=float(i), viable=True) for i in range(n)
    ]


def test_birth_count_is_population_size():
    config = load_evolution_config()
    result = advance_generation(
        _parents(),
        experiment_id="exp-0001",
        generation=1,
        seed_manager=SeedManager(1),
        config=config,
    )
    assert result.success is True
    assert result.event is None
    assert len(result.offspring) == 48 == config.population_size


def test_birth_count_follows_config_override():
    config = load_evolution_config(overrides={"population_size": 4})
    result = advance_generation(
        _parents(),
        experiment_id="exp-0001",
        generation=1,
        seed_manager=SeedManager(2),
        config=config,
    )
    assert len(result.offspring) == 4


def test_generations_do_not_overlap():
    parents = _parents()
    parent_ids = {parent.genome_id for parent in parents}
    result = advance_generation(
        parents,
        experiment_id="exp-0001",
        generation=1,
        seed_manager=SeedManager(3),
        config=load_evolution_config(),
    )
    offspring_ids = {child.genome_id for child in result.offspring}
    assert parent_ids.isdisjoint(offspring_ids)


def test_offspring_ids_match_mint_id_and_are_sequential():
    result = advance_generation(
        _parents(),
        experiment_id="exp-0001",
        generation=2,
        seed_manager=SeedManager(4),
        config=load_evolution_config(),
    )
    expected = [mint_id("exp-0001", "genome", 2, i) for i in range(48)]
    assert [child.genome_id for child in result.offspring] == expected
    assert len(set(expected)) == 48


def test_newborns_marked_unevaluated():
    result = advance_generation(
        _parents(),
        experiment_id="exp-0001",
        generation=1,
        seed_manager=SeedManager(5),
        config=load_evolution_config(),
    )
    for child in result.offspring:
        assert child.viable is False
        assert child.fitness == 0.0
        assert child.failure_reason is None
        assert child.fish_id is None
        assert child.genome.genome_id == child.genome_id


def test_same_seed_reproducible():
    config = load_evolution_config()

    def run():
        return advance_generation(
            _parents(),
            experiment_id="exp-0001",
            generation=1,
            seed_manager=SeedManager(42),
            config=config,
        )

    first, second = run(), run()
    assert first.offspring == second.offspring
    assert first.selected_parent_ids == second.selected_parent_ids


def test_different_seed_changes_offspring():
    config = load_evolution_config()

    def run(seed):
        return advance_generation(
            _parents(),
            experiment_id="exp-0001",
            generation=1,
            seed_manager=SeedManager(seed),
            config=config,
        )

    assert run(1).offspring != run(2).offspring


def test_empty_cohort_is_bottleneck_failure():
    result = advance_generation(
        [],
        experiment_id="exp-0001",
        generation=1,
        seed_manager=SeedManager(11),
        config=load_evolution_config(),
    )
    assert result.success is False
    assert result.event == EVENT_POPULATION_BOTTLENECK
    assert result.offspring == ()
    assert result.selected_parent_ids == ()


def test_fewer_than_two_viable_is_bottleneck_failure():
    parents = [
        _individual("exp-0001:g0:genome0000", fitness=1.0, viable=True),
        _individual("exp-0001:g0:genome0001", fitness=99.0, viable=False),
    ]
    result = advance_generation(
        parents,
        experiment_id="exp-0001",
        generation=1,
        seed_manager=SeedManager(6),
        config=load_evolution_config(),
    )
    assert result.success is False
    assert result.event == EVENT_POPULATION_BOTTLENECK
    assert result.offspring == ()
    assert result.selected_parent_ids == ()


def test_no_viable_is_bottleneck_failure():
    parents = [
        _individual("exp-0001:g0:genome0000", fitness=1.0, viable=False),
        _individual("exp-0001:g0:genome0001", fitness=2.0, viable=False),
    ]
    result = advance_generation(
        parents,
        experiment_id="exp-0001",
        generation=1,
        seed_manager=SeedManager(7),
        config=load_evolution_config(),
    )
    assert result.success is False
    assert result.event == EVENT_POPULATION_BOTTLENECK


def test_selected_parents_are_viable_only():
    parents = [
        _individual("exp-0001:g0:genome0000", fitness=0.0, viable=True),
        _individual("exp-0001:g0:genome0001", fitness=1.0, viable=True),
        _individual("exp-0001:g0:genome0002", fitness=1000.0, viable=False),
    ]
    viable_ids = {parents[0].genome_id, parents[1].genome_id}
    result = advance_generation(
        parents,
        experiment_id="exp-0001",
        generation=1,
        seed_manager=SeedManager(8),
        config=load_evolution_config(overrides={"population_size": 20}),
    )
    assert set(result.selected_parent_ids) <= viable_ids


def test_viable_parents_with_zero_fitness_are_still_eligible():
    # §5 定稿：viable 但 F=0 者仍可入选，不得因 F=0 被当作 non-viable 排除。
    parents = [
        _individual("exp-0001:g0:genome0000", fitness=0.0, viable=True),
        _individual("exp-0001:g0:genome0001", fitness=0.0, viable=True),
    ]
    viable_ids = {parents[0].genome_id, parents[1].genome_id}
    result = advance_generation(
        parents,
        experiment_id="exp-0001",
        generation=1,
        seed_manager=SeedManager(12),
        config=load_evolution_config(overrides={"population_size": 8}),
    )
    assert result.success is True
    assert set(result.selected_parent_ids) <= viable_ids


def test_selected_pairs_never_self_pair():
    # §5 禁自体配对：可行时配对不得出现同一亲本两次。此处直接检查 ``random_pairs``，
    # 避免从 ``selected_parent_ids``（抽中顺序、未经配对置换）误判。
    selected = [0, 1, 2, 0, 1, 2, 0, 1]  # max multiplicity 3 ≤ n/2=4，可行
    pairs = random_pairs(selected, np.random.default_rng(0))
    for a, b in pairs:
        assert a != b


def test_fish_id_is_carried_through():
    parents = [
        Individual(
            genome_id="exp-0001:g0:genome0000",
            genome=_genome("exp-0001:g0:genome0000"),
            fish_id="exp-0001:g0:fish0000",
            fitness=1.0,
            viable=True,
        ),
        Individual(
            genome_id="exp-0001:g0:genome0001",
            genome=_genome("exp-0001:g0:genome0001"),
            fish_id="exp-0001:g0:fish0001",
            fitness=0.0,
            viable=True,
        ),
    ]
    result = advance_generation(
        parents,
        experiment_id="exp-0001",
        generation=1,
        seed_manager=SeedManager(13),
        config=load_evolution_config(overrides={"population_size": 4}),
    )
    assert parents[0].fish_id == "exp-0001:g0:fish0000"
    assert set(result.selected_parent_ids) <= {p.genome_id for p in parents}


def test_higher_fitness_parent_selected_more_often():
    parents = [
        _individual("exp-0001:g0:genome0000", fitness=1.0, viable=True),
        _individual("exp-0001:g0:genome0001", fitness=0.0, viable=True),
    ]
    counts = {0: 0, 1: 0}
    for seed in range(30):
        result = advance_generation(
            parents,
            experiment_id="exp-0001",
            generation=1,
            seed_manager=SeedManager(seed),
            config=load_evolution_config(overrides={"population_size": 40}),
        )
        for parent_id in result.selected_parent_ids:
            counts[0 if parent_id.endswith("0000") else 1] += 1
    assert counts[0] > counts[1]
    assert counts[0] / (counts[0] + counts[1]) > 0.5


def test_tournament_size_exceeding_viable_count_raises_in_advance():
    """S4：3 个 viable、config.tournament_size=4 → advance_generation 抛错（不静默退化）。"""
    import pytest

    config = load_evolution_config(overrides={"tournament_size": 4})
    with pytest.raises(ValueError):
        advance_generation(
            _parents(3),
            experiment_id="exp-0001",
            generation=1,
            seed_manager=SeedManager(1),
            config=config,
        )
