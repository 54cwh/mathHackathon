"""整群行为 trace（行为回放 / 诊断资产；**非** BC 训练数据）。

owner：`experiment`；schema `schemas/behavior_trace.schema.json`。用途与 BC `trajectory` 区分：

- `trajectory`（`schemas/trajectory.schema.json`）：每条 episode **1 条受控鱼**，供 `learning` BC；
- `behavior_trace`（本模块）：**全群**逐 step 观测/动作，逐 episode 一文件，供行为回放、
  分布诊断与出图（`population.jsonl` / `episodes.jsonl` 的逐群视角）。死鱼止步 ⇒ 同文件
  step 稀疏（不同 `fish_id` 步数不同），`header.total_steps` 记 **episode 长度**（非文件行数）。

本模块只负责写入与 header/step 组装，不定义字段语义（字段与 `trajectory` 的 step 同形）。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from evogenesis.arena.env import DanioArena
from evogenesis.experiment.arena_rollout import RolloutStep

#: 12 维 observation 分量名，顺序与 `DanioNet设计规范.md` §2 冻结表逐字一致。
OBS_DIM_NAMES = (
    "prey_left_signal",
    "prey_right_signal",
    "threat_left_signal",
    "threat_right_signal",
    "obstacle_left_signal",
    "obstacle_right_signal",
    "prey_relative_size",
    "predator_relative_size",
    "looming_rate",
    "current_speed",
    "energy",
    "hunger",
)

SCHEMA_VERSION = "1.0.0"


def trace_header(
    *,
    experiment_id: str,
    episode_id: str,
    environment_id: str,
    generation: int,
    episode_seed: int,
    dynamics_seed: int,
    total_steps: int,
    terminated: bool,
    truncated: bool,
    fish_ids: list[str],
    environment_config: dict | None = None,
) -> dict:
    """整群 trace 的 header（`behavior_trace.schema.json` `$defs/header` 必填字段）。

    `total_steps` 为 **episode 长度**（不是文件行数；同文件多鱼、死鱼止步故稀疏）。
    `terminated=False`（A9：无任务终止信号）、`truncated=StepResult.done`。
    """
    head = {
        "record_type": "header",
        "schema_version": SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "episode_id": episode_id,
        "environment_id": environment_id,
        "generation": generation,
        "episode_seed": episode_seed,
        "dynamics_seed": dynamics_seed,
        "total_steps": total_steps,
        "terminated": bool(terminated),
        "truncated": bool(truncated),
        "fish_ids": list(fish_ids),
        "obs_dim_names": list(OBS_DIM_NAMES),
    }
    if environment_config is not None:
        head["environment_config"] = environment_config
    return head


def trace_step(
    *,
    fish_id: str,
    genome_id: str,
    step: int,
    observation: np.ndarray,
    expert_action: tuple[float, float],
    is_first: bool,
    is_last: bool,
) -> dict:
    """一条整群 trace step（与 `trajectory` step 同形）。"""
    return {
        "record_type": "step",
        "fish_id": str(fish_id),
        "genome_id": str(genome_id),
        "step": int(step),
        "observation": [float(x) for x in observation],
        "expert_action": [float(expert_action[0]), float(expert_action[1])],
        "is_first": bool(is_first),
        "is_last": bool(is_last),
    }


def write_trace(path: Path, header: dict, steps: list[dict]) -> Path:
    """写一个整群 trace 的 JSONL：首行 header，其后逐 step。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(header, ensure_ascii=False) + chr(10))
        for rec in steps:
            fh.write(json.dumps(rec, ensure_ascii=False) + chr(10))
    return path


class TraceCollector:
    """把 `expert_rollout` 的逐步结果累积为整群 trace（含 `is_first` / `is_last`）。

    唯一实现：`run_arena` 与测试共用，避免在调用方重复组装/标记逻辑。
    """

    def __init__(self, arena: DanioArena) -> None:
        self._arena = arena
        self._records: list[dict] = []
        self._seen: set[str] = set()

    def add(self, rollout: RolloutStep) -> None:
        """记录该步全部存活鱼；死鱼不记录（其步数因此短于 episode 长度）。"""
        for fid in rollout.alive_ids:
            self._records.append(
                trace_step(
                    fish_id=fid,
                    genome_id=self._arena.fish[fid].genome_id,
                    step=rollout.step,
                    observation=rollout.observations[fid],
                    expert_action=rollout.actions[fid],
                    is_first=fid not in self._seen,
                    is_last=False,
                )
            )
            self._seen.add(fid)

    def records(self) -> list[dict]:
        """返回记录列表；每条鱼在本 episode 的**末条**记录被置 `is_last=True`。"""
        last_index: dict[str, int] = {}
        for idx, rec in enumerate(self._records):
            last_index[rec["fish_id"]] = idx
        for idx in last_index.values():
            self._records[idx]["is_last"] = True
        return self._records


__all__ = [
    "OBS_DIM_NAMES",
    "SCHEMA_VERSION",
    "TraceCollector",
    "trace_header",
    "trace_step",
    "write_trace",
]
