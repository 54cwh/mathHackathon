"""learning/data.py 测试：JSONL 读取、schema 必填/维度校验、多 episode 拼接。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from evogenesis.core.io import write_jsonl
from evogenesis.learning.data import (
    ACTION_DIM,
    SENSORY_DIM,
    TrajectoryDataset,
    TrajectoryFormatError,
    load_episode,
    load_trajectories,
    load_trajectory_dir,
)

EPISODE_ID = "ep0001"
SCHEMA_VERSION = "1.0.0"


def _header(*, total_steps: int, episode_id: str = EPISODE_ID) -> dict[str, Any]:
    return {
        "record_type": "header",
        "schema_version": SCHEMA_VERSION,
        "experiment_id": "exp-test",
        "episode_id": episode_id,
        "environment_id": "env-test",
        "generation": 0,
        "episode_seed": 12345,
        "total_steps": total_steps,
        "terminated": False,
        "truncated": True,
    }


def _step(step: int) -> dict[str, Any]:
    rng = np.random.default_rng(step)
    obs = rng.uniform(0.0, 1.0, size=SENSORY_DIM)
    action = np.array([rng.uniform(-1.0, 1.0), rng.uniform(0.0, 1.0)])
    return {
        "record_type": "step",
        "fish_id": "exp-test:g0:fish0000",
        "genome_id": "exp-test:g0:genome0000",
        "step": step,
        "observation": [float(x) for x in obs],
        "expert_action": [float(action[0]), float(action[1])],
    }


def _records(n_steps: int, *, episode_id: str = EPISODE_ID) -> list[dict[str, Any]]:
    return [
        _header(total_steps=n_steps, episode_id=episode_id),
        *(_step(i) for i in range(n_steps)),
    ]


def _write(path: Path, records: list[dict[str, Any]]) -> Path:
    write_jsonl(path, records)
    return path


def test_load_episode_shapes_dtype_and_metadata(tmp_path: Path):
    path = _write(tmp_path / "episode_ep0001.jsonl", _records(3))
    episode = load_episode(path)
    assert episode.n_steps == 3
    assert episode.observations.shape == (3, SENSORY_DIM)
    assert episode.expert_actions.shape == (3, ACTION_DIM)
    assert episode.observations.dtype == np.float32
    assert episode.expert_actions.dtype == np.float32
    assert episode.header["episode_id"] == EPISODE_ID


def test_load_trajectory_dir_concatenates_and_reports_metadata(tmp_path: Path):
    _write(tmp_path / "episode_ep0001.jsonl", _records(3, episode_id="ep0001"))
    _write(tmp_path / "episode_ep0002.jsonl", _records(2, episode_id="ep0002"))
    dataset = load_trajectory_dir(tmp_path)
    assert dataset.n_samples == 5
    assert dataset.n_episodes == 2
    assert dataset.episode_lengths == (3, 2)
    assert dataset.sensory_dim == SENSORY_DIM
    assert dataset.action_dim == ACTION_DIM
    assert [header["episode_id"] for header in dataset.headers] == ["ep0001", "ep0002"]


def test_load_trajectories_preserves_given_order(tmp_path: Path):
    first = _write(tmp_path / "a.jsonl", _records(1, episode_id="epA"))
    second = _write(tmp_path / "b.jsonl", _records(2, episode_id="epB"))
    dataset = load_trajectories([second, first])
    assert [header["episode_id"] for header in dataset.headers] == ["epB", "epA"]


def test_missing_required_step_field_raises(tmp_path: Path):
    records = _records(1)
    del records[1]["observation"]
    path = _write(tmp_path / "episode.jsonl", records)
    with pytest.raises(TrajectoryFormatError, match="observation"):
        load_episode(path)


def test_missing_header_field_raises(tmp_path: Path):
    records = _records(1)
    del records[0]["environment_id"]
    path = _write(tmp_path / "episode.jsonl", records)
    with pytest.raises(TrajectoryFormatError, match="environment_id"):
        load_episode(path)


def test_observation_wrong_dimension_raises(tmp_path: Path):
    records = _records(1)
    records[1]["observation"] = records[1]["observation"][:-1]
    path = _write(tmp_path / "episode.jsonl", records)
    with pytest.raises(TrajectoryFormatError, match="observation"):
        load_episode(path)


def test_action_wrong_dimension_raises(tmp_path: Path):
    records = _records(1)
    records[1]["expert_action"] = [0.1]
    path = _write(tmp_path / "episode.jsonl", records)
    with pytest.raises(TrajectoryFormatError, match="expert_action"):
        load_episode(path)


def test_observation_out_of_range_raises(tmp_path: Path):
    records = _records(1)
    records[1]["observation"][0] = 1.5
    path = _write(tmp_path / "episode.jsonl", records)
    with pytest.raises(TrajectoryFormatError, match="越界"):
        load_episode(path)


def test_non_finite_action_raises(tmp_path: Path):
    records = _records(1)
    records[1]["expert_action"] = [float("nan"), 0.2]
    path = _write(tmp_path / "episode.jsonl", records)
    with pytest.raises(TrajectoryFormatError, match="有限"):
        load_episode(path)


def test_first_record_must_be_header(tmp_path: Path):
    records = _records(1)
    records[0]["record_type"] = "step"
    path = _write(tmp_path / "episode.jsonl", records)
    with pytest.raises(TrajectoryFormatError, match="header"):
        load_episode(path)


def test_total_steps_mismatch_raises(tmp_path: Path):
    records = _records(2)
    records[0]["total_steps"] = 5
    path = _write(tmp_path / "episode.jsonl", records)
    with pytest.raises(TrajectoryFormatError, match="total_steps"):
        load_episode(path)


def test_unknown_field_raises(tmp_path: Path):
    records = _records(1)
    records[1]["unexpected"] = 1
    path = _write(tmp_path / "episode.jsonl", records)
    with pytest.raises(TrajectoryFormatError, match="未定义字段"):
        load_episode(path)


def test_empty_file_raises(tmp_path: Path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    with pytest.raises(TrajectoryFormatError, match="空文件"):
        load_episode(path)


def test_load_trajectories_empty_raises():
    with pytest.raises(TrajectoryFormatError, match="未提供"):
        load_trajectories([])


def test_load_trajectory_dir_without_files_raises(tmp_path: Path):
    with pytest.raises(TrajectoryFormatError, match="episode_"):
        load_trajectory_dir(tmp_path)


def test_episode_views_preserve_order_and_offsets(tmp_path: Path):
    _write(tmp_path / "episode_ep0001.jsonl", _records(3, episode_id="ep0001"))
    _write(tmp_path / "episode_ep0002.jsonl", _records(2, episode_id="ep0002"))
    dataset = load_trajectory_dir(tmp_path)
    assert dataset.episode_offsets == (0, 3, 5)
    first_obs, first_act = dataset.episode_slice(0)
    assert first_obs.shape == (3, SENSORY_DIM)
    assert first_act.shape == (3, ACTION_DIM)
    assert np.array_equal(first_obs, dataset.observations[:3])
    slices = list(dataset.iter_episodes())
    assert len(slices) == 2
    assert np.array_equal(slices[1][0], dataset.observations[3:5])


def test_uniform_episode_steps_returns_common_length(tmp_path: Path):
    _write(tmp_path / "episode_ep0001.jsonl", _records(3, episode_id="ep0001"))
    _write(tmp_path / "episode_ep0002.jsonl", _records(3, episode_id="ep0002"))
    dataset = load_trajectory_dir(tmp_path)
    assert dataset.uniform_episode_steps == 3


def test_uniform_episode_steps_rejects_non_uniform():
    dataset = TrajectoryDataset(
        observations=np.zeros((5, SENSORY_DIM), dtype=np.float32),
        expert_actions=np.zeros((5, ACTION_DIM), dtype=np.float32),
        headers=({"episode_id": "a"}, {"episode_id": "b"}),
        episode_paths=(),
        episode_lengths=(2, 3),
    )
    with pytest.raises(ValueError, match="不等长"):
        _ = dataset.uniform_episode_steps


def test_dataset_rejects_inconsistent_lengths():
    with pytest.raises(ValueError, match="不一致"):
        TrajectoryDataset(
            observations=np.zeros((4, SENSORY_DIM), dtype=np.float32),
            expert_actions=np.zeros((4, ACTION_DIM), dtype=np.float32),
            headers=({"episode_id": "a"},),
            episode_paths=(),
            episode_lengths=(3,),
        )
