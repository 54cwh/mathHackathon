"""BC 专家轨迹加载（`learning/行为克隆学习.md` §2；`core/核心机制与数据流.md` §4.2/§4.5）。

只读消费 `scripts/collect_trajectories.py` 落盘的 episode JSONL（header + step 两级），
按 `schemas/trajectory.schema.json` 的必填字段与维度校验，再把多 episode 拼成训练张量
（``float32``，`core §7`）。轨迹格式 owner 为 `schemas/trajectory.schema.json`；本模块
不改写、不重命名任何字段。

契约要点（`learning §2`）：每条 episode 只记录 1 条受控鱼的 `(observation, expert_action)`；
`observation` 为 12 维、`expert_action` 为 2 维 `(ω*, v*)`。因此样本数 = 各 episode 步数之和。
"""

from __future__ import annotations

import math
import os
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from evogenesis.core.io import read_jsonl

#: `DanioNet设计规范.md` §2 / `core §4.2`：observation 维度（顺序冻结）
SENSORY_DIM = 12
#: `DanioNet设计规范.md` §2 / `core §4.2`：expert_action 维度 ``(ω*, v*)``
ACTION_DIM = 2

_HEADER_REQUIRED = frozenset(
    {
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
)
_HEADER_OPTIONAL = frozenset({"environment_config", "obs_dim_names", "dynamics_seed"})
_STEP_REQUIRED = frozenset(
    {"record_type", "fish_id", "genome_id", "step", "observation", "expert_action"}
)
_STEP_OPTIONAL = frozenset({"reward", "is_first", "is_last"})

PathLike = str | os.PathLike[str]


class TrajectoryFormatError(ValueError):
    """轨迹 JSONL 违反 `schemas/trajectory.schema.json` 的必填/维度约束。"""


def _require_keys(
    record: dict[str, Any], required: frozenset[str], allowed: frozenset[str], ctx: str
) -> None:
    missing = required - set(record)
    if missing:
        raise TrajectoryFormatError(f"{ctx} 缺少必填字段：{sorted(missing)}")
    unknown = set(record) - allowed
    if unknown:
        raise TrajectoryFormatError(f"{ctx} 含 schema 未定义字段：{sorted(unknown)}")


def _require_str(value: Any, name: str, ctx: str) -> str:
    if not isinstance(value, str) or not value:
        raise TrajectoryFormatError(f"{ctx} 字段 {name} 必须为非空字符串，实际 {value!r}")
    return value


def _require_int(value: Any, name: str, ctx: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TrajectoryFormatError(f"{ctx} 字段 {name} 必须为整数，实际 {value!r}")
    return value


def _require_bool(value: Any, name: str, ctx: str) -> bool:
    if not isinstance(value, bool):
        raise TrajectoryFormatError(f"{ctx} 字段 {name} 必须为布尔，实际 {value!r}")
    return value


def _require_float(value: Any, name: str, ctx: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrajectoryFormatError(f"{ctx} 字段 {name} 必须为数值，实际 {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise TrajectoryFormatError(f"{ctx} 字段 {name} 必须有限，实际 {value!r}")
    return number


def _parse_observation(value: Any, ctx: str) -> list[float]:
    if not isinstance(value, list) or len(value) != SENSORY_DIM:
        raise TrajectoryFormatError(
            f"{ctx} observation 必须为长度 {SENSORY_DIM} 的数组，实际 {value!r}"
        )
    obs: list[float] = []
    for index, item in enumerate(value):
        number = _require_float(item, f"observation[{index}]", ctx)
        if not 0.0 <= number <= 1.0:
            raise TrajectoryFormatError(
                f"{ctx} observation[{index}]={number} 越界（§2 值域 [0,1]）"
            )
        obs.append(number)
    return obs


def _parse_action(value: Any, ctx: str) -> list[float]:
    if not isinstance(value, list) or len(value) != ACTION_DIM:
        raise TrajectoryFormatError(
            f"{ctx} expert_action 必须为长度 {ACTION_DIM} 的数组，实际 {value!r}"
        )
    return [
        _require_float(item, f"expert_action[{index}]", ctx) for index, item in enumerate(value)
    ]


@dataclass(frozen=True)
class Episode:
    """单条 episode 的解析结果（header + 逐步样本）。"""

    path: Path
    header: dict[str, Any]
    observations: np.ndarray  # (n_steps, SENSORY_DIM) float32
    expert_actions: np.ndarray  # (n_steps, ACTION_DIM) float32

    @property
    def n_steps(self) -> int:
        return int(self.observations.shape[0])


@dataclass(frozen=True)
class TrajectoryDataset:
    """多 episode 拼接后的 BC 训练集。

    同时提供**扁平视图**（``observations`` / ``expert_actions``，供 σ/λ 统计）与
    **按 episode 的序列视图**（``episode_slice`` / ``iter_episodes`` / ``uniform_episode_steps``，
    供 `learning §3` 的整段 BPTT）。`learning §3` 的采样单位是 episode；每批 64 条。
    """

    observations: np.ndarray  # (N, SENSORY_DIM) float32
    expert_actions: np.ndarray  # (N, ACTION_DIM) float32
    headers: tuple[dict[str, Any], ...]  # 每个 episode 的 header（元数据）
    episode_paths: tuple[Path, ...]
    episode_lengths: tuple[int, ...]

    @property
    def n_samples(self) -> int:
        return int(self.observations.shape[0])

    @property
    def n_episodes(self) -> int:
        return len(self.headers)

    @property
    def sensory_dim(self) -> int:
        return int(self.observations.shape[1])

    @property
    def action_dim(self) -> int:
        return int(self.expert_actions.shape[1])

    def __post_init__(self) -> None:
        if len(self.headers) != len(self.episode_lengths):
            raise ValueError("headers 与 episode_lengths 长度不一致")
        if sum(self.episode_lengths) != self.n_samples:
            raise ValueError(
                f"episode_lengths 之和 {sum(self.episode_lengths)} 与样本数 {self.n_samples} 不一致"
            )

    @property
    def episode_offsets(self) -> tuple[int, ...]:
        """各 episode 在扁平数组中的起始下标，``len = n_episodes + 1``。"""
        offsets = [0]
        for length in self.episode_lengths:
            offsets.append(offsets[-1] + length)
        return tuple(offsets)

    @property
    def uniform_episode_steps(self) -> int:
        """全部 episode 等长时的公共步数（`learning §2`：记录满 ``episode_steps``）。

        不等长时无法满足 §3「前向满 ``episode_steps`` 步」的单一预算口径，显式报错。
        """
        if self.n_episodes == 0:
            raise ValueError("数据集没有 episode")
        if len(set(self.episode_lengths)) != 1:
            raise ValueError(
                f"episode 步数不等长 {sorted(set(self.episode_lengths))}；"
                "§3 要求按统一 episode_steps 展开"
            )
        return int(self.episode_lengths[0])

    def episode_slice(self, index: int) -> tuple[np.ndarray, np.ndarray]:
        """第 ``index`` 条 episode 的有序 ``(observations, expert_actions)`` 视图。"""
        if not 0 <= index < self.n_episodes:
            raise IndexError(f"episode 下标 {index} 越界（共 {self.n_episodes} 条）")
        offsets = self.episode_offsets
        start, stop = offsets[index], offsets[index + 1]
        return self.observations[start:stop], self.expert_actions[start:stop]

    def iter_episodes(self) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        """按落盘顺序逐条产出 ``(observations, expert_actions)``（`learning §3` BPTT 用）。"""
        for index in range(self.n_episodes):
            yield self.episode_slice(index)


def _validate_header(header: dict[str, Any], ctx: str) -> None:
    _require_keys(header, _HEADER_REQUIRED, _HEADER_REQUIRED | _HEADER_OPTIONAL, ctx)
    if header["record_type"] != "header":
        raise TrajectoryFormatError(
            f"{ctx} 首行 record_type 必须为 'header'，实际 {header['record_type']!r}"
        )
    _require_str(header["schema_version"], "schema_version", ctx)
    _require_str(header["experiment_id"], "experiment_id", ctx)
    _require_str(header["episode_id"], "episode_id", ctx)
    _require_str(header["environment_id"], "environment_id", ctx)
    _require_int(header["generation"], "generation", ctx)
    _require_int(header["episode_seed"], "episode_seed", ctx)
    if "dynamics_seed" in header:
        _require_int(header["dynamics_seed"], "dynamics_seed", ctx)
    total_steps = _require_int(header["total_steps"], "total_steps", ctx)
    if total_steps < 1:
        raise TrajectoryFormatError(f"{ctx} total_steps 必须 ≥ 1，实际 {total_steps}")
    _require_bool(header["terminated"], "terminated", ctx)
    _require_bool(header["truncated"], "truncated", ctx)
    if "environment_config" in header and not isinstance(header["environment_config"], dict):
        raise TrajectoryFormatError(f"{ctx} environment_config 必须为映射")
    if "obs_dim_names" in header:
        names = header["obs_dim_names"]
        if not isinstance(names, list) or len(names) != SENSORY_DIM:
            raise TrajectoryFormatError(
                f"{ctx} obs_dim_names 必须为长度 {SENSORY_DIM} 的字符串数组"
            )
        for name in names:
            _require_str(name, "obs_dim_names[]", ctx)


def _parse_step(record: dict[str, Any], index: int, ctx: str) -> tuple[list[float], list[float]]:
    """校验一条 step 并返回 ``(observation, expert_action)``。"""
    step_ctx = f"{ctx} 第 {index} 条 step"
    _require_keys(record, _STEP_REQUIRED, _STEP_REQUIRED | _STEP_OPTIONAL, step_ctx)
    if record["record_type"] != "step":
        raise TrajectoryFormatError(
            f"{step_ctx} record_type 必须为 'step'，实际 {record['record_type']!r}"
        )
    _require_str(record["fish_id"], "fish_id", step_ctx)
    _require_str(record["genome_id"], "genome_id", step_ctx)
    step = _require_int(record["step"], "step", step_ctx)
    if step < 0:
        raise TrajectoryFormatError(f"{step_ctx} step 必须 ≥ 0，实际 {step}")
    observation = _parse_observation(record["observation"], step_ctx)
    expert_action = _parse_action(record["expert_action"], step_ctx)
    if "reward" in record:
        _require_float(record["reward"], "reward", step_ctx)
    if "is_first" in record:
        _require_bool(record["is_first"], "is_first", step_ctx)
    if "is_last" in record:
        _require_bool(record["is_last"], "is_last", step_ctx)
    return observation, expert_action


def load_episode(path: PathLike) -> Episode:
    """读取单个 episode JSONL（首行 header + 逐步 step），返回校验后的样本。"""
    target = Path(path)
    ctx = f"轨迹 {target.name}"
    records = read_jsonl(target)
    if not records:
        raise TrajectoryFormatError(f"{ctx} 为空文件")
    header = records[0]
    if not isinstance(header, dict):
        raise TrajectoryFormatError(f"{ctx} 首行必须为对象")
    _validate_header(header, ctx)

    steps = records[1:]
    if len(steps) != header["total_steps"]:
        raise TrajectoryFormatError(
            f"{ctx} 实际 step 行数 {len(steps)} 与 header total_steps "
            f"{header['total_steps']} 不一致"
        )

    observations = np.empty((len(steps), SENSORY_DIM), dtype=np.float32)
    expert_actions = np.empty((len(steps), ACTION_DIM), dtype=np.float32)
    for index, record in enumerate(steps):
        if not isinstance(record, dict):
            raise TrajectoryFormatError(f"{ctx} 第 {index} 条 step 必须为对象")
        observation, expert_action = _parse_step(record, index, ctx)
        observations[index] = observation
        expert_actions[index] = expert_action
    return Episode(
        path=target, header=header, observations=observations, expert_actions=expert_actions
    )


def load_trajectories(paths: Iterable[PathLike]) -> TrajectoryDataset:
    """顺序读取多个 episode 并拼接；空集合报错（`core §4.5` 期望至少一条）。"""
    resolved = [Path(path) for path in paths]
    episodes = [load_episode(path) for path in resolved]
    if not episodes:
        raise TrajectoryFormatError("未提供任何 episode 文件")
    observations = np.concatenate([episode.observations for episode in episodes], axis=0)
    expert_actions = np.concatenate([episode.expert_actions for episode in episodes], axis=0)
    return TrajectoryDataset(
        observations=observations,
        expert_actions=expert_actions,
        headers=tuple(episode.header for episode in episodes),
        episode_paths=tuple(episode.path for episode in episodes),
        episode_lengths=tuple(episode.n_steps for episode in episodes),
    )


def load_trajectory_dir(directory: PathLike) -> TrajectoryDataset:
    """读取目录下全部 ``episode_*.jsonl``（按文件名排序，`core §4.5` 命名）。"""
    root = Path(directory)
    paths: Sequence[Path] = sorted(root.glob("episode_*.jsonl"))
    if not paths:
        raise TrajectoryFormatError(f"目录 {root} 下没有 episode_*.jsonl")
    return load_trajectories(paths)


__all__ = [
    "ACTION_DIM",
    "SENSORY_DIM",
    "Episode",
    "TrajectoryDataset",
    "TrajectoryFormatError",
    "load_episode",
    "load_trajectories",
    "load_trajectory_dir",
]
