"""Stage-1 专家轨迹采集（`learning/行为克隆学习.md` §2；`core/核心机制与数据流.md` §4.2/§4.5）。

owner 依据：`core §4.5` 定「产出方 = `experiment`/`scripts` 编排」，`experiment/实验与评价体系.md`
§5.1 定义 run 目录布局与 `trajectories/`。本模块承载采集业务逻辑——跑 Arena episode、按
`core §3` 派生 episode 子种子、组 header/step 记录并落盘；`scripts/collect_trajectories.py`
只是薄 CLI（AGENTS：`scripts/` 不放业务逻辑）。

字段与文件形态 owner 是 `schemas/trajectory.schema.json`（已冻结）；本模块不新增字段语义、
不发明数值。采集粒度（定稿，`learning §2`）：每条 episode **只记录 1 条受控鱼**的
`(observation, expert_action)`；环境中其余个体照常存在，由 `ExpertPolicy` 驱动（`learning §5`
Stage-1 driver）以提供真实感知上下文，但**不入轨迹**。逐步驱动循环与 `run_arena` 共用
`experiment/arena_rollout.py::expert_rollout`。
"""

from __future__ import annotations

from pathlib import Path

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import ExpertPolicy
from evogenesis.core.config import read_yaml
from evogenesis.core.ids import mint_id
from evogenesis.core.io import write_jsonl
from evogenesis.core.seed import SeedManager
from evogenesis.experiment.arena_rollout import expert_rollout
from evogenesis.experiment.trajectories import (
    SCHEMA_VERSION,
    episode_header,
    step_record,
)

#: `core §3` 定稿的 Arena 命名空间（出生 / 逐步动力学）
ARENA_SPAWN_NAMESPACE = "arena_spawn"
ARENA_DYNAMICS_NAMESPACE = "arena_dynamics"


def episode_id(index: int) -> str:
    """稳定 episode ID，形如 ``ep0001``（`core §4.2`；index 从 0 起）。"""
    if index < 0:
        raise ValueError("episode index 必须非负")
    return f"ep{index + 1:04d}"


def episode_seed(master_seed: int, index: int) -> int:
    """本 episode 的整数子种子（`core §3`）：``SeedManager.seed("arena_spawn", index)``。

    同一 ``(master_seed, index)`` 恒得同一子种子；直接交给
    ``DanioArena(spawn_seed=..., dynamics_seed=...)``（后者只接受整数种子）。
    """
    return SeedManager(master_seed).seed(ARENA_SPAWN_NAMESPACE, index)


def episode_dynamics_seed(master_seed: int, index: int) -> int:
    """本 episode 的逐步动力学子种子（`core §3`）

    ``SeedManager.seed("arena_dynamics", index)``。
    """
    return SeedManager(master_seed).seed(ARENA_DYNAMICS_NAMESPACE, index)


def default_trajectories(model_config: Path) -> int:
    """从 model config 读 `learning.trajectories`（规模取值 owner = `configs/`）。"""
    learning = read_yaml(model_config).get("learning") or {}
    if "trajectories" not in learning:
        raise ValueError(f"{model_config} 缺少 learning.trajectories")
    return int(learning["trajectories"])


def collect_episode(
    config: ArenaConfig,
    *,
    experiment_id: str,
    environment_id: str,
    generation: int,
    episode_index: int,
    seed: int,
    dynamics_seed: int,
    controlled_index: int = 0,
) -> tuple[dict, list[dict]]:
    """跑一条 episode，返回 (header, step 记录列表)；只记录受控鱼。

    受控鱼默认取 ``controlled_index=0``，其稳定身份由 ``core §3.1`` 铸造
    （``mint_id(..., "fish", generation, index)``）并**注入 Arena**（``fish_ids`` /
    ``genome_ids`` / ``generation``），故轨迹声明的身份与 Arena 实体身份一致。
    其余存活个体同由 `ExpertPolicy` 驱动但不入轨迹。``seed`` / ``dynamics_seed`` 为
    `core §3` 的 ``arena_spawn`` / ``arena_dynamics`` 整数子种子（调用方派生）。
    ``terminated=False``（A9：无任务终止信号）、``truncated=StepResult.done``（跑满即时限截断）。
    受控鱼一旦死亡仍逐 step 记录其**步前**观测（`expert_rollout(track_ids=...)`）。
    """
    n_fish = config.population.n_fish
    if config.world.episode_steps < 1:
        raise ValueError(
            f"episode_steps 须 ≥1（schema minimum:1），得到 {config.world.episode_steps}"
        )
    if not 0 <= controlled_index < n_fish:
        raise ValueError(f"controlled_index 须在 [0, {n_fish})，得到 {controlled_index}")
    fish_ids = [mint_id(experiment_id, "fish", generation, i) for i in range(n_fish)]
    genome_ids = [mint_id(experiment_id, "genome", generation, i) for i in range(n_fish)]
    arena = DanioArena(
        config,
        spawn_seed=seed,
        dynamics_seed=dynamics_seed,
        fish_ids=fish_ids,
        genome_ids=genome_ids,
        generation=generation,
    )
    arena.reset()
    controlled_fish = fish_ids[controlled_index]
    fish_id = controlled_fish
    genome_id = genome_ids[controlled_index]
    expert = ExpertPolicy()

    steps: list[dict] = []
    done = False
    for rollout in expert_rollout(
        arena,
        steps=config.world.episode_steps,
        expert=expert,
        track_ids=(controlled_fish,),
    ):
        controlled_obs = rollout.observations[controlled_fish]
        controlled_action = rollout.actions.get(controlled_fish) or expert(controlled_obs)
        done = rollout.done
        steps.append(
            step_record(
                fish_id=fish_id,
                genome_id=genome_id,
                step=rollout.step,
                observation=controlled_obs,
                expert_action=controlled_action,
            )
        )

    header = episode_header(
        experiment_id=experiment_id,
        episode_id=episode_id(episode_index),
        environment_id=environment_id,
        generation=generation,
        episode_seed=seed,
        dynamics_seed=dynamics_seed,
        total_steps=len(steps),
        terminated=False,
        truncated=bool(done),
    )
    return header, steps


def collect_trajectories(
    config: ArenaConfig,
    *,
    experiment_id: str,
    environment_id: str,
    generation: int,
    seed: int,
    trajectories: int,
    out_dir: str | Path,
    controlled_index: int = 0,
) -> list[Path]:
    """采集 ``trajectories`` 条 episode 并逐条落盘，返回写入的文件路径列表。

    路径布局：``<out_dir>/episode_<episode_id>.jsonl``（`core §4.5`）；schema 版本取
    `trajectories.SCHEMA_VERSION`（唯一来源，不再由 CLI 传入）。
    """
    out = Path(out_dir)
    written: list[Path] = []
    for index in range(trajectories):
        header, steps = collect_episode(
            config,
            experiment_id=experiment_id,
            environment_id=environment_id,
            generation=generation,
            episode_index=index,
            seed=episode_seed(seed, index),
            dynamics_seed=episode_dynamics_seed(seed, index),
            controlled_index=controlled_index,
        )
        path = out / f"episode_{header['episode_id']}.jsonl"
        write_jsonl(path, [header, *steps])
        written.append(path)
    return written


__all__ = [
    "ARENA_DYNAMICS_NAMESPACE",
    "ARENA_SPAWN_NAMESPACE",
    "SCHEMA_VERSION",
    "collect_episode",
    "collect_trajectories",
    "default_trajectories",
    "episode_dynamics_seed",
    "episode_id",
    "episode_seed",
]
