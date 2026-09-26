"""Experiment metrics tests (实验与评价体系.md section 4; experiment/metrics.py)."""

from __future__ import annotations

import pytest

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.env import DanioArena
from evogenesis.experiment.metrics import (
    BLOCKED_METRICS,
    COMPOSITE_WEIGHTS,
    aggregate_by_seed,
    composite_fitness,
    energy_efficiency,
    episode_metrics,
    escape_success_rate,
    summarise_over_seeds,
    survival_rate,
)


def _record(**over: object) -> dict:
    """per_fish_log() 形状的最小记录。"""
    rec = {
        "survival_steps": 600,
        "captures": 3,
        "encounters": 40,
        "predator_encounters": 2,
        "escape_successes": 1,
        "collisions": 0,
        "energy_trajectory": [1.0, 0.5, 0.25],
        "size_trajectory": [1.0, 1.1],
    }
    rec.update(over)
    return rec


def test_survival_rate_is_ratio_of_episode_steps():
    assert survival_rate(600, 600) == 1.0
    assert survival_rate(300, 600) == 0.5
    with pytest.raises(ValueError):
        survival_rate(1, 0)


def test_escape_success_rate_uses_one_as_floor():
    assert escape_success_rate(1, 2) == 0.5
    assert escape_success_rate(0, 0) == 0.0  # max(0, 1) = 1
    assert escape_success_rate(3, 0) == 3.0  # 文档原式，不做额外截断


def test_energy_efficiency_follows_documented_formula():
    # (E_i(T_i) - E_max) / T_i, E_max = 1.0
    assert energy_efficiency(1.0, 1.0, 600) == 0.0
    assert energy_efficiency(0.4, 1.0, 600) == pytest.approx(-0.001)
    assert energy_efficiency(0.4, 1.0, 600) <= 0.0  # 非正：这是「平均缺口」
    with pytest.raises(ValueError):
        energy_efficiency(0.4, 1.0, 0)


def test_composite_weights_are_the_documented_ones_and_sum_to_one():
    assert COMPOSITE_WEIGHTS == {
        "survival": 0.35,
        "prey_capture": 0.25,
        "escape_success": 0.20,
        "energy_efficiency": 0.20,
    }
    assert sum(COMPOSITE_WEIGHTS.values()) == pytest.approx(1.0)
    got = composite_fitness(1.0, 1.0, 1.0, 1.0)
    assert got == pytest.approx(1.0)
    assert composite_fitness(1.0, 0.0, 0.0, 0.0) == pytest.approx(0.35)


def test_episode_metrics_computes_defined_and_blocks_undefined():
    row = episode_metrics(_record(), episode_steps=600, e_max=1.0)
    assert row["survival"] == 1.0
    assert row["escape_success"] == 0.5
    assert row["energy_efficiency"] == pytest.approx((0.25 - 1.0) / 600)
    assert row["energy_final"] == 0.25
    assert row["captures"] == 3 and row["encounters"] == 40
    # 未定义量必须留空，且 BLOCKED_METRICS 给出原因
    assert row["prey_capture"] is None
    assert row["composite_fitness"] is None
    for key in ("prey_capture", "composite_fitness"):
        assert key in BLOCKED_METRICS
        assert BLOCKED_METRICS[key].strip()
    assert "capture_attempts" in BLOCKED_METRICS["prey_capture"]


def test_episode_metrics_reads_only_keys_that_per_fish_log_provides():
    """漂移守护：`episode_metrics` 用到的键必须真的出现在 `per_fish_log()` 里。"""
    arena = DanioArena(ArenaConfig(), master_seed=7)
    arena.reset()
    for _ in range(3):
        arena.step(None)
    rec = next(iter(arena.per_fish_log().values()))
    for key in (
        "survival_steps",
        "captures",
        "encounters",
        "predator_encounters",
        "escape_successes",
        "energy_trajectory",
    ):
        assert key in rec, key
    row = episode_metrics(rec, episode_steps=3, e_max=1.0)
    assert 0.0 <= row["survival"] <= 1.0
    assert row["energy_efficiency"] <= 0.0


def test_aggregate_by_seed_averages_individuals_then_summarise_uses_seed_axis():
    rows = [
        {"seed": 1103, "survival": 1.0},
        {"seed": 1103, "survival": 0.0},
        {"seed": 2207, "survival": 1.0},
        {"seed": 3301, "survival": 0.5},
    ]
    by_seed = aggregate_by_seed(rows)
    assert [r["seed"] for r in by_seed] == [1103, 2207, 3301]
    assert by_seed[0]["n_individuals"] == 2
    assert by_seed[0]["survival"] == pytest.approx(0.5)  # seed 内先取个体均值
    summary = summarise_over_seeds(by_seed)
    assert summary["survival"]["mean"] == pytest.approx((0.5 + 1.0 + 0.5) / 3)
    assert summary["survival"]["n"] == 3
    assert summary["survival"]["std"] is not None


def test_summarise_skips_blocked_columns_and_single_seed_has_no_std():
    blocked = [
        {"seed": 1103, "survival": 1.0, "composite_fitness": None},
        {"seed": 2207, "survival": 0.5, "composite_fitness": None},
    ]
    summary = summarise_over_seeds(blocked, metrics=("survival", "composite_fitness"))
    assert summary["composite_fitness"] == {"mean": None, "std": None, "n": 0}
    single = summarise_over_seeds([{"seed": 1, "survival": 1.0}], metrics=("survival",))
    assert single["survival"]["mean"] == 1.0
    assert single["survival"]["std"] is None  # n < 2
