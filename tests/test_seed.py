import numpy as np
import pytest
import torch

from evogenesis.core.seed import NAMESPACES, SeedManager, set_global_seed


def test_same_master_and_namespace_reproducible():
    a = SeedManager(7).rng("mutation").uniform(size=5)
    b = SeedManager(7).rng("mutation").uniform(size=5)
    assert np.array_equal(a, b)


def test_different_namespace_differs():
    a = SeedManager(7).rng("mutation").uniform(size=5)
    b = SeedManager(7).rng("crossover").uniform(size=5)
    assert not np.array_equal(a, b)


def test_different_master_differs():
    a = SeedManager(7).rng("development").uniform(size=5)
    b = SeedManager(8).rng("development").uniform(size=5)
    assert not np.array_equal(a, b)


def test_spawn_rng_reproducible_and_distinct():
    a0 = SeedManager(11).spawn_rng("arena_spawn", 0).uniform(size=4)
    a1 = SeedManager(11).spawn_rng("arena_spawn", 1).uniform(size=4)
    b0 = SeedManager(11).spawn_rng("arena_spawn", 0).uniform(size=4)
    assert np.array_equal(a0, b0)
    assert not np.array_equal(a0, a1)


def test_spawn_grows_without_order_dependence():
    grown = SeedManager(1)._spawn("mutation", 4)
    first = SeedManager(1)._spawn("mutation", 1)[0]
    assert grown[0].spawn_key == first.spawn_key

    high_first = SeedManager(1).spawn_rng("development", 3).uniform(size=3)
    manager = SeedManager(1)
    manager.spawn_rng("development", 0)
    low_then_high = manager.spawn_rng("development", 3).uniform(size=3)
    assert np.array_equal(high_first, low_then_high)


def test_python_rng_reproducible():
    a = [SeedManager(3).python_rng("mutation").random() for _ in range(3)]
    b = [SeedManager(3).python_rng("mutation").random() for _ in range(3)]
    assert a == b


def test_torch_generator_reproducible():
    def draw():
        gen = SeedManager(5).torch_generator("development")
        return torch.rand(4, generator=gen)

    assert torch.equal(draw(), draw())


def test_unknown_namespace_raises():
    with pytest.raises(ValueError):
        SeedManager(1).rng("nope")


def test_negative_index_raises():
    with pytest.raises(ValueError):
        SeedManager(1).spawn_rng("mutation", -1)


def test_namespaces_frozen():
    assert NAMESPACES == {
        "mutation": 0,
        "crossover": 1,
        "development": 2,
        "arena_spawn": 3,
        "motif_catalog": 4,
        "network_init": 5,
        "selection": 6,
        "initial_population": 7,
        "bc": 8,
        "arena_dynamics": 9,
        "baseline_init": 10,
        "penetrance_calibration": 11,
        "penetrance_report": 12,
        "baseline_support": 13,
        "robustness": 14,
        "arena_eval_spawn": 15,
        "arena_eval_dynamics": 16,
        # 发育参数集 Θ_D（RGCD §1/§13 定稿：由 seed 确定性初始化、**每 seed 一套**）。
        # 与 `development`=2 刻意分离：后者是 ξ（位置 / 分裂 Bernoulli / ε_p / ε_g）的
        # **逐个体**随机流；把 Θ_D 也挂在它上面会让每个个体拿到一套不同的发育参数
        # （实测把 N 的类内 sd 由纯二项 2.26 抬到 3.3–4.0，并令 penetrance 观测轴不可辨识）。
        # `t` 恒 0（同 `network_init` 先例）：该命名空间下只有一个实体。
        "development_params": 17,
    }


def test_set_global_seed_reproducible():
    set_global_seed(42)
    first = np.random.random(3).tolist()
    set_global_seed(42)
    assert np.random.random(3).tolist() == first


def test_master_seed_range_enforced():
    with pytest.raises(ValueError):
        SeedManager(-1)
    with pytest.raises(ValueError):
        SeedManager(2**32)
    assert SeedManager(0).master_seed == 0


def test_torch_generator_cross_process_deterministic():
    """core §3：NumPy 子种子 → torch 种子属项目选定，须跨进程最小复现验证。"""
    import subprocess
    import sys

    snippet = (
        "import torch; from evogenesis.core.seed import SeedManager; "
        "g = SeedManager(5).torch_generator('development'); "
        "print(torch.rand(4, generator=g).tolist())"
    )

    def run():
        out = subprocess.run(
            [sys.executable, "-c", snippet], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()

    assert run() == run()


def test_entity_integer_seed_reproducible_and_distinct():
    a = SeedManager(11).seed("arena_spawn", 0)
    assert a == SeedManager(11).seed("arena_spawn", 0)
    assert 0 <= a < 2**32
    assert a != SeedManager(11).seed("arena_spawn", 1)
    with pytest.raises(ValueError):
        SeedManager(11).seed("arena_spawn", -1)
