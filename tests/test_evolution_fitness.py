"""代内 fitness 合成测试（``evolution §6``）。"""

import numpy as np
import pytest

from evogenesis.evolution.fitness import composite_fitness, minmax_normalize

WEIGHTS = {
    "survival": 0.35,
    "prey_capture": 0.25,
    "escape_success": 0.20,
    "energy_efficiency": 0.20,
}


def _components(s, p, e, q):
    return {
        "survival": np.array(s, dtype=np.float32),
        "prey_capture": np.array(p, dtype=np.float32),
        "escape_success": np.array(e, dtype=np.float32),
        "energy_efficiency": np.array(q, dtype=np.float32),
    }


def test_minmax_normalize_maps_to_unit_interval():
    normalized = minmax_normalize([1.0, 2.0, 3.0], cohort_mask=[True, True, True])
    assert normalized.dtype == np.float32
    assert normalized.tolist() == pytest.approx([0.0, 0.5, 1.0])


def test_minmax_normalize_max_equals_min_sets_zero():
    normalized = minmax_normalize([3.0, 3.0, 3.0], cohort_mask=[True, True, True])
    assert normalized.tolist() == [0.0, 0.0, 0.0]


def test_minmax_normalize_uses_viable_cohort_only():
    # 非 viable 的极端值不得进入 min/max；viable 子集为 [1, 2]。
    normalized = minmax_normalize([1.0, 2.0, 100.0], cohort_mask=[True, True, False])
    assert normalized.tolist() == pytest.approx([0.0, 1.0, 0.0])


def test_normalization_is_within_viable_cohort():
    components = _components(
        [1.0, 2.0, 100.0], [1.0, 2.0, 100.0], [1.0, 2.0, 100.0], [1.0, 2.0, 100.0]
    )
    f = composite_fitness(components, viable=[True, True, False], weights=WEIGHTS)
    # viable [1,2] -> 归一到 0/1，四项权重和为 1.0；非 viable 置 0。
    assert f.tolist() == pytest.approx([0.0, 1.0, 0.0])


def test_non_viable_gets_zero_even_with_extreme_components():
    components = _components([100.0, 1.0], [100.0, 1.0], [100.0, 1.0], [100.0, 1.0])
    f = composite_fitness(components, viable=[False, True], weights=WEIGHTS)
    assert f.tolist() == pytest.approx([0.0, 0.0])


def test_component_max_equals_min_yields_zero_contribution():
    # survival 全相等 -> 该分量置 0；其余三分量贡献。
    components = _components([5.0, 5.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0])
    f = composite_fitness(components, viable=[True, True], weights=WEIGHTS)
    assert f.tolist() == pytest.approx([0.0, 0.25 + 0.20 + 0.20])


def test_weights_are_injected_not_hardcoded():
    components = _components([0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0])
    only_survival = {
        "survival": 1.0,
        "prey_capture": 0.0,
        "escape_success": 0.0,
        "energy_efficiency": 0.0,
    }
    f = composite_fitness(components, viable=[True, True], weights=only_survival)
    assert f.tolist() == pytest.approx([0.0, 1.0])


def test_all_components_equal_across_generation_yields_zero_fitness():
    components = _components([1.0, 1.0], [2.0, 2.0], [3.0, 3.0], [4.0, 4.0])
    f = composite_fitness(components, viable=[True, True], weights=WEIGHTS)
    assert f.tolist() == [0.0, 0.0]


def test_mismatched_keys_rejected():
    components = _components([0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0])
    del components["energy_efficiency"]
    with pytest.raises(ValueError):
        composite_fitness(components, viable=[True, True], weights=WEIGHTS)


def test_mismatched_viable_length_rejected():
    components = _components([0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0])
    with pytest.raises(ValueError):
        composite_fitness(components, viable=[True], weights=WEIGHTS)
