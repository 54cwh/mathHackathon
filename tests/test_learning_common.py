"""learning 测试共享夹具（无测试用例，供 test_learning_*.py 导入）。"""

from __future__ import annotations

import numpy as np
import torch

from evogenesis.connectome.danionet import DanioNet
from evogenesis.development import ConnectomePhenotype
from evogenesis.learning.data import TrajectoryDataset

MASTER_SEED = 424242
MOTOR_TYPE = 5
SENSORY_TYPE = 0


def make_phenotype(n_motor: int = 6) -> ConnectomePhenotype:
    """确定性合成个体：2 sensory + n_motor motor，含非空左右 motor 池与非零支撑。"""
    n = 2 + n_motor
    cell_type = torch.tensor(
        [SENSORY_TYPE, SENSORY_TYPE] + [MOTOR_TYPE] * n_motor, dtype=torch.long
    )
    rng = np.random.default_rng(0)
    adjacency = (rng.random((n, n)) < 0.3).astype(np.float32)
    np.fill_diagonal(adjacency, 0.0)
    weights0 = (rng.standard_normal((n, n)).astype(np.float32) * 0.5) * adjacency
    positions = torch.tensor([[(i + 0.5) / n, 0.5] for i in range(n)], dtype=torch.float32)
    return ConnectomePhenotype(
        adjacency=torch.from_numpy(adjacency),
        weights0=torch.from_numpy(weights0),
        tau=torch.ones(n, dtype=torch.float32),
        cell_type=cell_type,
        positions=positions,
        active_mask=torch.ones(n, dtype=torch.bool),
        viable=True,
        viability_reason="ok",
        z=torch.zeros((n, 6), dtype=torch.float32),
    )


def make_net(master_seed: int = MASTER_SEED) -> DanioNet:
    return DanioNet([make_phenotype()], master_seed=master_seed)


def make_actions(n: int, *, seed: int = 0) -> np.ndarray:
    """合成动作 ``(ω*, v*)``，值域落在 `DanioNet §4` 输出空间。"""
    rng = np.random.default_rng(seed)
    omega = rng.uniform(-1.0, 1.0, size=n).astype(np.float32)
    v = rng.uniform(0.0, 1.0, size=n).astype(np.float32)
    return np.stack([omega, v], axis=1).astype(np.float32)


def make_observations(n: int, *, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.uniform(0.0, 1.0, size=(n, 12)).astype(np.float32)


def make_dataset(n_episodes: int, episode_steps: int, *, seed: int = 0) -> TrajectoryDataset:
    """等长 episode 的合成训练集（按落盘顺序连续排布）。"""
    n = n_episodes * episode_steps
    rng = np.random.default_rng(seed)
    observations = rng.uniform(0.0, 1.0, size=(n, 12)).astype(np.float32)
    expert_actions = np.stack(
        [
            rng.uniform(-1.0, 1.0, size=n),
            rng.uniform(0.0, 1.0, size=n),
        ],
        axis=1,
    ).astype(np.float32)
    headers = tuple(
        {"episode_id": f"ep{i + 1:04d}", "total_steps": episode_steps} for i in range(n_episodes)
    )
    return TrajectoryDataset(
        observations=observations,
        expert_actions=expert_actions,
        headers=headers,
        episode_paths=(),
        episode_lengths=(episode_steps,) * n_episodes,
    )
