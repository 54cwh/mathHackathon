"""Stage-1 专家轨迹采集测试（learning §2；core §4.2/§4.5；schemas/trajectory.schema.json）。

单元测试直接打 `evogenesis.experiment.collect`（业务逻辑 owner）；另保留一条对薄 CLI
`scripts/collect_trajectories.py` 的冒烟测试（小 episode、2 条 episode）。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from evogenesis.arena.config import load_arena_config
from evogenesis.core.ids import mint_id
from evogenesis.core.io import read_jsonl
from evogenesis.core.seed import SeedManager
from evogenesis.experiment import collect

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "collect_trajectories.py"
EPISODE_STEPS = 12
CLI_EPISODE_STEPS = 6
N_EPISODES = 2
EXPERIMENT_ID = "exp-test"
ENVIRONMENT_ID = "test-env"
SCHEMA_VERSION = "1.0.0"
SEED = 1103
HEADER_REQUIRED = {
    "record_type",
    "schema_version",
    "experiment_id",
    "episode_id",
    "environment_id",
    "generation",
    "episode_seed",
    "total_steps",
    "terminated",
    "truncated",
}
STEP_REQUIRED = {
    "record_type",
    "fish_id",
    "genome_id",
    "step",
    "observation",
    "expert_action",
}


def small_config(steps: int = EPISODE_STEPS):
    """用 override 把 episode_steps 调小，保持其余 Arena 契约为默认。"""
    return load_arena_config(
        ROOT / "configs" / "default_arena.yaml",
        overrides={"world": {"episode_steps": steps}},
    )


def run(tmp_path: Path, seed: int = SEED) -> list[Path]:
    return collect.collect_trajectories(
        small_config(),
        experiment_id=EXPERIMENT_ID,
        environment_id=ENVIRONMENT_ID,
        generation=0,
        schema_version=SCHEMA_VERSION,
        seed=seed,
        trajectories=N_EPISODES,
        out_dir=tmp_path,
    )


def test_writes_one_jsonl_per_episode(tmp_path):
    written = run(tmp_path)
    names = [p.name for p in written]
    assert names == ["episode_ep0001.jsonl", "episode_ep0002.jsonl"]
    assert all(p.is_file() for p in written)


def test_header_required_fields_and_values(tmp_path):
    written = run(tmp_path)
    header, *steps = read_jsonl(written[0])
    assert header["record_type"] == "header"
    assert HEADER_REQUIRED <= set(header)
    assert header["schema_version"] == SCHEMA_VERSION
    assert header["experiment_id"] == EXPERIMENT_ID
    assert header["episode_id"] == "ep0001"
    assert header["environment_id"] == ENVIRONMENT_ID
    assert header["generation"] == 0
    assert isinstance(header["episode_seed"], int)
    assert header["total_steps"] == len(steps) == EPISODE_STEPS
    assert header["terminated"] is False
    assert header["truncated"] is True


def test_step_records_shape_and_ids(tmp_path):
    written = run(tmp_path)
    _, *steps = read_jsonl(written[0])
    expected_fish = mint_id(EXPERIMENT_ID, "fish", 0, 0)
    expected_genome = mint_id(EXPERIMENT_ID, "genome", 0, 0)
    assert {s["fish_id"] for s in steps} == {expected_fish}
    for i, record in enumerate(steps):
        assert record["record_type"] == "step"
        assert STEP_REQUIRED <= set(record)
        assert record["fish_id"] == expected_fish
        assert record["genome_id"] == expected_genome
        assert record["step"] == i
        assert len(record["observation"]) == 12
        assert all(0.0 <= value <= 1.0 for value in record["observation"])
        assert len(record["expert_action"]) == 2
        assert all(isinstance(value, float) for value in record["expert_action"])


def test_only_one_controlled_fish_recorded(tmp_path):
    written = run(tmp_path)
    for path in written:
        _, *steps = read_jsonl(path)
        assert len({s["fish_id"] for s in steps}) == 1


def test_same_seed_reproduces_file_contents(tmp_path):
    first = run(tmp_path / "a")
    second = run(tmp_path / "b")
    assert len(first) == len(second)
    for a, b in zip(first, second, strict=True):
        assert a.read_bytes() == b.read_bytes()


def test_episode_seed_uses_seed_manager_namespace(tmp_path):
    written = run(tmp_path)
    first, second = read_jsonl(written[0]), read_jsonl(written[1])
    assert first[0]["episode_id"] != second[0]["episode_id"]
    assert first[0]["episode_seed"] == SeedManager(SEED).seed("arena_spawn", 0)
    assert second[0]["episode_seed"] == SeedManager(SEED).seed("arena_spawn", 1)
    assert collect.episode_seed(SEED, 0) == SeedManager(SEED).seed("arena_spawn", 0)


def test_different_seed_changes_episode_seed():
    assert collect.episode_seed(SEED, 0) != collect.episode_seed(SEED + 1, 0)


@pytest.mark.parametrize("bad_index", [-1])
def test_episode_id_rejects_negative_index(bad_index):
    with pytest.raises(ValueError):
        collect.episode_id(bad_index)


def test_collect_rejects_nonpositive_episode_steps(tmp_path):
    with pytest.raises(ValueError, match="episode_steps"):
        collect.collect_trajectories(
            small_config(steps=0),
            experiment_id=EXPERIMENT_ID,
            environment_id=ENVIRONMENT_ID,
            generation=0,
            schema_version=SCHEMA_VERSION,
            seed=SEED,
            trajectories=1,
            out_dir=tmp_path,
        )


def test_cli_smoke_writes_two_episodes(tmp_path):
    arena_yaml = yaml.safe_load((ROOT / "configs" / "default_arena.yaml").read_text("utf-8"))
    arena_yaml["world"]["episode_steps"] = CLI_EPISODE_STEPS
    small_arena = tmp_path / "arena_small.yaml"
    small_arena.write_text(yaml.safe_dump(arena_yaml), encoding="utf-8")
    out_dir = tmp_path / "trajectories"

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--experiment-id",
            "cli-smoke",
            "--seed",
            str(SEED),
            "--environment-id",
            ENVIRONMENT_ID,
            "--schema-version",
            SCHEMA_VERSION,
            "--generation",
            "0",
            "--trajectories",
            str(N_EPISODES),
            "--arena-config",
            str(small_arena),
            "--out-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    written = sorted(out_dir.glob("episode_*.jsonl"))
    assert [p.name for p in written] == ["episode_ep0001.jsonl", "episode_ep0002.jsonl"]
    for path in written:
        header, *steps = read_jsonl(path)
        assert header["record_type"] == "header"
        assert header["total_steps"] == len(steps) == CLI_EPISODE_STEPS
