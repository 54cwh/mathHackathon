"""binary tournament 选择测试（``evolution §5``）。"""

import numpy as np
import pytest

from evogenesis.evolution.selection import (
    binary_tournament,
    is_population_bottleneck,
    random_pairs,
)


def test_bottleneck_detection():
    assert is_population_bottleneck([]) is True
    assert is_population_bottleneck([0]) is True
    assert is_population_bottleneck([0, 1]) is False


def test_tournament_never_selects_non_viable_candidate():
    # 下标 2 的 F 极大但不是 viable，绝不进候选。
    fitness = [0.1, 0.2, 100.0]
    rng = np.random.default_rng(0)
    selected = binary_tournament(fitness, [0, 1], tournament_size=2, rng=rng, n_selections=2000)
    assert set(selected.tolist()) <= {0, 1}


def test_tournament_candidates_are_viable_only_all_the_time():
    fitness = [0.0, 0.0, 0.0, 0.0]
    rng = np.random.default_rng(7)
    selected = binary_tournament(fitness, [1, 3], tournament_size=2, rng=rng, n_selections=500)
    assert set(selected.tolist()) <= {1, 3}


def test_high_fitness_selected_significantly_more_often():
    # 两个候选：有放回抽样下最优者胜率 = 1 - (1/2)^2 = 0.75。
    fitness = [1.0, 0.0]
    rng = np.random.default_rng(12345)
    selected = binary_tournament(fitness, [0, 1], tournament_size=2, rng=rng, n_selections=20000)
    best_freq = float((selected == 0).mean())
    assert best_freq == pytest.approx(0.75, abs=0.02)  # 约 6.5 sigma
    assert best_freq > 0.5


def test_high_fitness_wins_head_to_head_more_than_half():
    fitness = [0.0, 1.0, 2.0]
    rng = np.random.default_rng(99)
    selected = binary_tournament(fitness, [0, 1, 2], tournament_size=2, rng=rng, n_selections=20000)
    counts = np.bincount(selected, minlength=3)
    # 期望胜率：最优 5/9≈0.556 > 中 1/3≈0.333 > 最差 1/9≈0.111
    assert counts[2] > counts[1] > counts[0]
    assert counts[2] / counts.sum() == pytest.approx(5 / 9, abs=0.03)


def test_random_pairs_uses_even_selection():
    selected = [0, 1, 2, 3]
    pairs = random_pairs(selected, np.random.default_rng(0))
    assert pairs.shape == (2, 2)
    assert sorted(pairs.reshape(-1).tolist()) == [0, 1, 2, 3]


def test_random_pairs_preserves_multiset():
    selected = [0, 0, 1, 2, 2, 3]
    pairs = random_pairs(selected, np.random.default_rng(5))
    assert sorted(pairs.reshape(-1).tolist()) == sorted(selected)


def test_random_pairs_never_self_pairs_when_feasible():
    # 抽中顺序里大量相邻重复（有放回抽样的典型情形）；max multiplicity 3 ≤ n/2=6 → 可行。
    selected = [0, 0, 1, 0, 1, 1, 2, 2, 0, 0, 2, 1]
    for seed in range(50):
        pairs = random_pairs(selected, np.random.default_rng(seed))
        assert all(a != b for a, b in pairs.tolist())


def test_random_pairs_rejects_odd_count():
    with pytest.raises(ValueError):
        random_pairs([0, 1, 2], np.random.default_rng(0))


def test_random_pairs_infeasible_keeps_minimal_self_pairs():
    # §2 可行性边界：max multiplicity m=3 > N=2 → 至少 m-N=1 个自体配对，且不多于 1 个。
    selected = [0, 0, 0, 1]
    pairs = random_pairs(selected, np.random.default_rng(0))
    self_pairs = sum(1 for a, b in pairs.tolist() if a == b)
    assert self_pairs == 1


def test_random_pairs_single_distinct_parent_is_all_self_pairs():
    # 全池只有一种下标：自体配对不可避免，返回全部自体配对而非报错。
    pairs = random_pairs([3, 3, 3, 3], np.random.default_rng(7))
    assert pairs.shape == (2, 2)
    assert all(a == b == 3 for a, b in pairs.tolist())


def test_tournament_size_exceeding_candidates_rejected():
    with pytest.raises(ValueError):
        binary_tournament(
            [0.1, 0.2, 0.3],
            [0, 1],
            tournament_size=3,
            rng=np.random.default_rng(0),
            n_selections=1,
        )


class _FixedDraws:
    """最小 rng 替身：返回预设的候选内下标，用于验证并列取先抽中者。"""

    def __init__(self, draws):
        self._draws = np.asarray(draws, dtype=np.intp)

    def integers(self, low, high, size):
        return self._draws.reshape(size)


def test_ties_prefer_first_drawn_candidate():
    # candidates [5, 7] 的 F 相等；一次锦标赛抽中顺序为 7 后 5，胜者应为先抽中的 7。
    fitness = [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0]
    rng = _FixedDraws([[1, 0]])
    selected = binary_tournament(fitness, [5, 7], tournament_size=2, rng=rng, n_selections=1)
    assert selected.tolist() == [7]


def test_tournament_rejects_empty_pool():
    with pytest.raises(ValueError):
        binary_tournament(
            [0.0], [], tournament_size=2, rng=np.random.default_rng(0), n_selections=1
        )


def test_tournament_rejects_nonfinite_fitness():
    """候选 fitness 含 NaN/Inf 时 argmax 行为不定，须显式报错。"""
    with pytest.raises(ValueError, match="非有限"):
        binary_tournament(
            [1.0, float("nan")],
            [0, 1],
            tournament_size=2,
            rng=np.random.default_rng(0),
            n_selections=1,
        )
