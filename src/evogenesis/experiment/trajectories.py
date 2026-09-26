"""Stage-1 专家轨迹落盘（BC 训练数据；`core §4.2` 语义、`core §4.5` 路径）。

owner 归属（2026-09-26 用户裁定，见 `research/notes/契约决策记录.md`）：
**采集器归 `experiment`/`scripts`**（原无产出方）；字段/格式 owner 仍为
`schemas/trajectory.schema.json`（冻结），`arena` 不负责落盘。

本模块只做**写入**，不定义任何字段语义；字段名一律照抄 schema。
"""

from __future__ import annotations

import json
from pathlib import Path

# schema 版本（SemVer）。加可选字段=MINOR，改必填=MAJOR（schema 的兼容规则）。
SCHEMA_VERSION = "1.0.0"

# 12 维 observation 分量名，顺序与 `DanioNet设计规范.md` §2 冻结表逐字一致。
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


def episode_header(
    *,
    experiment_id: str,
    episode_id: str,
    environment_id: str,
    generation: int,
    episode_seed: int,
    total_steps: int,
    environment_config: dict | None = None,
) -> dict:
    """episode 级 header（schema `$defs/header` 的全部必填字段）。

    `terminated` / `truncated` 均记 `False`：按 A9 裁决**一律跑满 600 步**，
    既无任务终止信号，也未因步数/时限被截断。
    """
    head = {
        "record_type": "header",
        "schema_version": SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "episode_id": episode_id,
        "environment_id": environment_id,
        "generation": generation,
        "episode_seed": episode_seed,
        "total_steps": total_steps,
        "terminated": False,
        "truncated": False,
        "obs_dim_names": list(OBS_DIM_NAMES),
    }
    if environment_config is not None:
        head["environment_config"] = environment_config
    return head


def step_record(
    *,
    fish_id: str,
    genome_id: str,
    step: int,
    observation,
    expert_action,
    is_first: bool,
    is_last: bool,
) -> dict:
    """一条 step 样本（schema `$defs/step` 的全部必填字段）。

    `reward` 不写：schema 标为可选，Arena 侧没有与 BC 对齐的回报定义，
    不得凭空造一个（避免 AI 填空）。
    """
    return {
        "record_type": "step",
        "fish_id": str(fish_id),
        "genome_id": str(genome_id),
        "step": int(step),
        "observation": [float(x) for x in observation],
        "expert_action": [float(x) for x in expert_action],
        "is_first": bool(is_first),
        "is_last": bool(is_last),
    }


def write_episode(path: Path, header: dict, steps: list[dict]) -> Path:
    """写一个 episode 的 JSONL：首行 header，其后逐 step（`core §4.5` 布局）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(header, ensure_ascii=False) + chr(10))
        for rec in steps:
            fh.write(json.dumps(rec, ensure_ascii=False) + chr(10))
    return path


__all__ = [
    "OBS_DIM_NAMES",
    "SCHEMA_VERSION",
    "episode_header",
    "step_record",
    "write_episode",
]
