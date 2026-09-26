"""环境对照三组（E-F）的守护测试。

对应 `experiment/实验与评价体系.md` §7 的**单因子对照**设计：
每个环境相对基线只改变一个驱动，否则环境效应不可归因。
"""

import pytest

from evogenesis.arena.config import ArenaConfig, load_arena_config
from evogenesis.experiment.environments import (
    BASELINE,
    environment_env_vars,
    load_environment,
    load_environments,
)

EXPECTED_IDS = {"food_rich", "predator_rich", "resource_scarce"}
# 每个环境**允许**触碰的 population 键（单因子）；其余键出现即为设计漂移
ALLOWED_KEYS = {
    "food_rich": {"n_prey", "prey_regrowth_steps"},
    "predator_rich": {"n_predators"},
    "resource_scarce": {"n_prey", "prey_regrowth_steps"},
}


def test_three_environments_exist():
    assert set(load_environments()) == EXPECTED_IDS
    assert BASELINE == "default"  # 基线不是三组之一


@pytest.mark.parametrize("env_id", sorted(EXPECTED_IDS))
def test_single_factor_contrast_holds(env_id: str):
    """§7 的核心不变量：每个环境只在 population 段内动**被声明的**旋钮。"""
    overrides = load_environment(env_id)
    assert set(overrides) == {"population"}, f"{env_id} 引入了非 population 段覆盖"
    assert set(overrides["population"]) <= ALLOWED_KEYS[env_id], (
        f"{env_id} 触碰了未声明的旋钮：{set(overrides['population']) - ALLOWED_KEYS[env_id]}"
    )
    assert overrides["population"], f"{env_id} 没有任何覆盖（等于基线，无对照意义）"


@pytest.mark.parametrize("env_id", ["food_rich", "resource_scarce"])
def test_regrowth_follows_its_documented_rule(env_id: str):
    """`prey_regrowth_steps` 是**派生量**：`ceil(600 / n_prey)`（非 `round`，避平局歧义）。"""
    pop = load_environment(env_id)["population"]
    expected = -(-600 // pop["n_prey"])  # 整数向上取整，避免浮点
    assert pop["prey_regrowth_steps"] == expected
    # 显式记录平局语义：food_rich 的 600/48 = 12.5 必须取 13 而非 round 的 12
    if pop["n_prey"] == 48:
        assert pop["prey_regrowth_steps"] == 13


def test_unknown_environment_raises():
    with pytest.raises(KeyError):
        load_environment("no_such_env")


@pytest.mark.parametrize("env_id", sorted(EXPECTED_IDS))
def test_overrides_reach_arena_config_and_differ_from_baseline(env_id: str):
    """覆盖必须真的落到 ArenaConfig，且与默认值有差（否则该环境是空壳）。"""
    base = load_arena_config()
    cfg = load_arena_config(overrides=load_environment(env_id))
    assert isinstance(cfg, ArenaConfig)
    assert cfg != base, f"{env_id} 覆盖后与基线完全相同"
    # 未声明的段必须与基线一致（守护「不暗改契约值」）
    for section in ("world", "sensing", "energy", "growth", "actors"):
        assert getattr(cfg, section) == getattr(base, section), f"{env_id} 暗改了 {section}"
    assert cfg.population.n_fish == base.population.n_fish
    assert cfg.population.n_obstacles == base.population.n_obstacles


def test_env_vars_match_nested_overrides():
    """子进程分层用的环境变量须与嵌套 overrides 一一对应（快照才如实）。"""
    overrides = load_environment("food_rich")
    assert environment_env_vars(overrides) == {
        "EVOGENESIS_POPULATION__N_PREY": "48",
        "EVOGENESIS_POPULATION__PREY_REGROWTH_STEPS": "13",
    }
    # 环境变量路径必须真的生效（与 overrides 等价）
    via_env = load_arena_config(environ=environment_env_vars(overrides))
    assert via_env == load_arena_config(overrides=overrides)
