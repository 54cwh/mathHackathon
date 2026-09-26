"""Experiment metrics tests (实验与评价体系.md section 4; experiment/metrics.py)."""

from __future__ import annotations

import pytest

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.env import DanioArena
from evogenesis.experiment.metrics import (
    BLOCKED_METRICS,
    COMPOSITE_WEIGHTS,
    aggregate_by_seed,
    capture_rate,
    composite_fitness,
    energy_efficiency,
    episode_metrics,
    escape_success_rate,
    prey_capture_rate,
    summarise_over_seeds,
    survival_rate,
)


def _record(**over: object) -> dict:
    """per_fish_log() 形状的最小记录。"""
    rec = {
        "survival_steps": 600,
        "captures": 3,
        "capture_attempts": 5,
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


def test_capture_rate_is_absolute_rate():
    """§2.1 主口径：`captures / episode_steps`（单位时间捕食数）。"""
    assert capture_rate(6, 600) == pytest.approx(0.01)
    assert capture_rate(0, 600) == 0.0
    with pytest.raises(ValueError):
        capture_rate(1, 0)


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


def test_prey_capture_rate_denominator_is_encounters_with_one_as_floor():
    """2026-09-26 裁决：分母 = `encounters`（尺寸门之前的距离口径）。"""
    assert prey_capture_rate(3, 40) == 0.075
    assert prey_capture_rate(0, 0) == 0.0  # max(0, 1) = 1
    assert prey_capture_rate(4, 4) == 1.0  # 追近的都吃到了


def test_episode_metrics_computes_four_metrics_plus_fitness():
    row = episode_metrics(_record(), episode_steps=600, e_max=1.0)
    assert row["survival"] == 1.0
    assert row["escape_success"] == 0.5
    assert row["energy_efficiency"] == pytest.approx((0.25 - 1.0) / 600)
    assert row["energy_final"] == 0.25
    assert row["captures"] == 3 and row["encounters"] == 40
    assert row["capture_attempts"] == 5  # 保留为**诊断列**（= captures + 吃不下）
    assert row["capture_rate"] == pytest.approx(3 / 600)  # §2.1 主口径
    assert row["prey_capture"] == pytest.approx(3 / 40)  # 分母 = encounters
    # 四项齐备后 composite fitness 真的算出来，且等于文档权重的加权和
    expected = (
        COMPOSITE_WEIGHTS["survival"] * row["survival"]
        + COMPOSITE_WEIGHTS["prey_capture"] * row["prey_capture"]
        + COMPOSITE_WEIGHTS["escape_success"] * row["escape_success"]
        + COMPOSITE_WEIGHTS["energy_efficiency"] * row["energy_efficiency"]
    )
    assert row["composite_fitness"] == pytest.approx(expected)
    assert not BLOCKED_METRICS, "prey_capture 已实现，阻断表应为空"


def test_episode_metrics_reads_only_keys_that_per_fish_log_provides():
    """漂移守护：`episode_metrics` 用到的键必须真的出现在 `per_fish_log()` 里。"""
    arena = DanioArena(ArenaConfig(), spawn_seed=7, dynamics_seed=7)
    arena.reset()
    for _ in range(3):
        arena.step(None)
    rec = next(iter(arena.per_fish_log().values()))
    for key in (
        "survival_steps",
        "captures",
        "capture_attempts",
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
