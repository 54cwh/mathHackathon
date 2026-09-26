"""共享的 ExpertPolicy 逐步驱动（`experiment §5.1`）。

`scripts/run_arena.py`（基线 / 环境 pre-check）与 `experiment/collect.py`（Stage-1 BC 采集）
都用 `ExpertPolicy` 驱动 Arena。本模块是该驱动循环的**唯一实现**：每步「观测全部存活鱼 →
`ExpertPolicy` 出动作 → `arena.step`」。记录哪些鱼、写成哪类文件（BC `trajectories/` 或
整群 `behavior_trace/`）由调用方决定，本模块不落盘。
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import expert_policy_from_config

if TYPE_CHECKING:
    from evogenesis.arena.policies import ExpertPolicy


@dataclass(frozen=True)
class RolloutStep:
    """一步驱动结果。

    - `alive_ids`：当步存活鱼（稳定 `fish_id`），`actions` 只覆盖它们；
    - `observations`：覆盖 `alive_ids` **加上** `track_ids` 中非存活的被跟踪鱼——均为
      **步前**观测（`arena.step` 之前），故「某鱼记录的最后一步」与旧口径一致。
    """

    step: int
    alive_ids: tuple[str, ...]
    observations: dict[str, np.ndarray]
    actions: dict[str, tuple[float, float]]
    done: bool


def expert_rollout(
    arena: DanioArena,
    *,
    steps: int,
    expert: ExpertPolicy | None = None,
    track_ids: tuple[str, ...] = (),
) -> Iterator[RolloutStep]:
    """逐步驱动 `arena`，产出每步的观测/动作；`done` 为真时提前停止。

    调用方须先 `arena.reset()`。`actions` 只含存活鱼（`arena.step` 跳过死鱼）；
    `track_ids` 用于「即使该鱼已死也要它的**步前**观测」（如 BC 受控鱼逐步记录）。
    """
    policy = expert_policy_from_config(arena.cfg) if expert is None else expert
    tracked = tuple(track_ids)
    for step in range(steps):
        alive_ids = tuple(fid for fid, fish in arena.fish.items() if fish.alive)
        observed_ids = alive_ids + tuple(fid for fid in tracked if fid not in alive_ids)
        observations = {fid: arena.observe(fid) for fid in observed_ids}
        actions = {fid: policy(observations[fid]) for fid in alive_ids}
        done = arena.step(actions).done
        yield RolloutStep(
            step=step,
            alive_ids=alive_ids,
            observations=observations,
            actions=actions,
            done=done,
        )
        if done:
            return


__all__ = ["RolloutStep", "expert_rollout"]
