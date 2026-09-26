"""Stage-1 专家轨迹落盘（BC 训练数据；`core §4.2` 语义、`core §4.5` 路径）。

owner 归属（2026-09-26 用户裁定，见 `research/notes/契约决策记录.md`）：
**采集器归 `experiment`/`scripts`**（原无产出方）；字段/格式 owner 仍为
`schemas/trajectory.schema.json`（冻结），`arena` 不负责落盘。

本模块只做**写入**，不定义任何字段语义；字段名一律照抄 schema。
"""

from __future__ import annotations

from pathlib import Path

from evogenesis.core.io import write_jsonl

# schema 版本（SemVer）。加可选字段=MINOR，改必填=MAJOR（schema 的兼容规则）。
SCHEMA_VERSION = "1.1.0"

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
    dynamics_seed: int | None = None,
    terminated: bool = False,
    truncated: bool = False,
    environment_config: dict | None = None,
) -> dict:
    """episode 级 header（schema `$defs/header` 的字段）。

    `terminated` 默认 `False`（A9：无任务终止信号）；`truncated` 由调用方按
    `StepResult.done` 传入。`dynamics_seed` 为 `arena_dynamics` 子种子（`core §3`），
    写入后 episode 可自包含重放（与 `episode_seed` 一起）。
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
        "terminated": bool(terminated),
        "truncated": bool(truncated),
        "obs_dim_names": list(OBS_DIM_NAMES),
    }
    if dynamics_seed is not None:
        head["dynamics_seed"] = int(dynamics_seed)
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
    is_first: bool | None = None,
    is_last: bool | None = None,
) -> dict:
    """一条 step 样本（schema `$defs/step` 的全部必填字段）。

    `reward` 不写：schema 标为可选，Arena 侧没有与 BC 对齐的回报定义，
    不得凭空造一个（避免 AI 填空）。`is_first` / `is_last` 仅在显式给定时写入
    （BC 单鱼口径默认不落盘，见 `learning §2`）。
    """
    record = {
        "record_type": "step",
        "fish_id": str(fish_id),
        "genome_id": str(genome_id),
        "step": int(step),
        "observation": [float(x) for x in observation],
        "expert_action": [float(x) for x in expert_action],
    }
    if is_first is not None:
        record["is_first"] = bool(is_first)
    if is_last is not None:
        record["is_last"] = bool(is_last)
    return record


def write_episode(path: Path, header: dict, steps: list[dict]) -> Path:
    """写一个 episode 的 JSONL：首行 header，其后逐 step（`core §4.5` 布局）。"""
    write_jsonl(path, [header, *steps])
    return path


__all__ = [
    "OBS_DIM_NAMES",
    "SCHEMA_VERSION",
    "episode_header",
    "step_record",
    "write_episode",
]
