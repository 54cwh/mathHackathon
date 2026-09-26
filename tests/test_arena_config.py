"""Arena config loader tests (arena/Danio_Arena设计与实现说明.md section 18.2)."""

from dataclasses import asdict, fields, replace
from pathlib import Path

import pytest
import yaml

from evogenesis.arena.config import (
    ARENA_SECTIONS,
    DERIVED_READONLY_KEYS,
    ActorDefaults,
    ArenaConfig,
    arena_config_snapshot,
    load_arena_config,
)
from evogenesis.arena.env import DanioArena

REPO = Path(__file__).resolve().parents[1]
ARENA_YAML = REPO / "configs" / "default_arena.yaml"
LF = chr(10)


def test_sections_cover_every_arena_config_field():
    assert set(ARENA_SECTIONS) == {f.name for f in fields(ArenaConfig)}


def test_yaml_matches_dataclass_defaults():
    """Drift guard: the YAML and the Python defaults must agree field by field."""
    assert load_arena_config(ARENA_YAML) == ArenaConfig()


def test_episode_seconds_is_derived_and_consistent():
    cfg = load_arena_config(ARENA_YAML)
    raw = yaml.safe_load(ARENA_YAML.read_text(encoding="utf-8"))
    assert ("world", "episode_seconds") in DERIVED_READONLY_KEYS
    assert raw["world"]["episode_seconds"] * cfg.world.hz == cfg.world.episode_steps
    assert not hasattr(cfg.world, "episode_seconds")


def test_precedence_is_cli_over_env_over_file():
    env = {"EVOGENESIS_WORLD__HZ": "7"}
    assert load_arena_config(ARENA_YAML, environ=env).world.hz == 7
    got = load_arena_config(ARENA_YAML, overrides={"world": {"hz": 3}}, environ=env)
    assert got.world.hz == 3


def test_env_overrides_nested_actors_field():
    env = {"EVOGENESIS_ACTORS__PREDATOR_SIZE": "9.5"}
    assert load_arena_config(ARENA_YAML, environ=env).actors.predator_size == 9.5


def test_unknown_key_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        LF.join(["actors:", "  predator_size: 3.125", "  predator_sizes: 1.0", ""]),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="predator_sizes"):
        load_arena_config(bad)


def test_unknown_section_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        LF.join(["world:", "  hz: 20", "not_a_section:", "  x: 1", ""]), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="not_a_section"):
        load_arena_config(bad)


def test_snapshot_is_run_ready():
    cfg = load_arena_config(ARENA_YAML)
    snapshot = arena_config_snapshot(cfg)
    assert list(snapshot) == list(ARENA_SECTIONS)
    assert snapshot == asdict(cfg)


def test_env_section_and_field_names_are_case_insensitive():
    """core 的 env 层按 Pydantic 字段名大小写不敏感匹配；Arena 的镜像表由 dataclass 生成。"""
    env = {"EVOGENESIS_Growth__Capture_Radius": "5.5"}
    assert load_arena_config(ARENA_YAML, environ=env).growth.capture_radius == 5.5


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_arena_config(REPO / "configs" / "does_not_exist.yaml")


DERIVED_ONLY: dict[str, str] = {
    "world.hz": "经 `WorldConfig.dt`（= 1/hz）消费；因此源码里出现的是 `cfg.world.dt`。",
}


def test_every_arena_config_field_is_actually_consumed():
    """死旋钮守卫：每个字段都必须有消费点，否则改 config 不影响行为（审计 A7）。"""
    src_dir = REPO / "src" / "evogenesis" / "arena"
    src = ""
    for f in sorted(src_dir.glob("*.py")):
        src += f.read_text(encoding="utf-8")
    dead = []
    for section in fields(ArenaConfig):
        for field in fields(section.type):
            key = f"{section.name}.{field.name}"
            if key in DERIVED_ONLY:
                continue
            if f"cfg.{key}" not in src:
                dead.append(key)
    assert not dead, f"未被代码消费的 Arena 配置字段（死旋钮）: {dead}"


def test_predator_policy_gets_max_chase_steps_from_config():
    """A7 回归：`actors.predator_max_chase_steps` 必须真的注入策略，而不是用策略自带的默认值。"""
    # 冻结 dataclass：用 replace 造一个与 policies.py 默认值 80 不同的 cfg，未注入即会暴露
    cfg = replace(ArenaConfig(), actors=replace(ActorDefaults(), predator_max_chase_steps=7))
    arena = DanioArena(cfg, master_seed=1)
    assert arena._pred_policy.max_chase_steps == 7
