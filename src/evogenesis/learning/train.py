"""BC 训练循环（`learning/行为克隆学习.md` v1.5 §3 已定稿；`DanioNet设计规范.md` §3/§4）。

训练粒度（`learning §1`）：每个当代个体各自训练**自己的** ``DanioNet``；本函数接受
单个个体的网络（``len(net.n_neurons) == 1``），只更新其 ``theta``。``ΔW = W − W⁰`` 为
导出量，不在此单独更新（`DanioNet §3`）。

前向与回传范围（`learning §3` 定稿）：因 ``h⁰=0`` 时 ``W·h⁰=0``，单步 ``∂L/∂Θ ≡ 0``，
故 BC **按 episode 顺序展开整段 BPTT**——每次更新抽 ``batch_size`` 条 episode（均匀随机
有放回，采样单位 = episode），每条自 ``h⁰=0`` 起前向满 ``episode_steps`` 步；先对该
episode 的逐步加权 MSE 取步均值，再对 batch 取均值，然后整段回传。

预算与优化器（§3）：``K = learning.mini_batch_updates`` 次更新、Adam、``learning.lr``，
只更新 ``net.theta``。采样随机源取自 ``core §3`` 的 ``bc`` 命名空间
（``seed_manager.spawn_rng("bc", seed_index)``），禁用 Python ``random``。

覆盖率口径（§3 定稿）：episode 级 ``K×batch / 总 episode 数``（= epoch 数），并给出
step 级可见样本 ``K×batch×episode_steps`` 及其对 ``总 episode 数×episode_steps`` 的倍数。

实现边界（§3 定稿）：训练集为空（0 episode）抛 ``ValueError``；权重对空集退回预注册
回退值（由 :mod:`evogenesis.learning.stats` 处理）；``loss_weight_normalization`` 仅支持
``per_dim_variance``，其他取值抛 ``NotImplementedError``。BC 采样实体序号 ``t`` 由调用方
以 ``seed_index`` 给定（与配子级 ``t`` 同规则），本模块不自行推导。
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

from evogenesis.connectome.danionet import DanioNet
from evogenesis.core.config import LearningConfig
from evogenesis.core.seed import SeedManager
from evogenesis.core.tensors import to_float32_tensor
from evogenesis.learning.data import TrajectoryDataset
from evogenesis.learning.loss import weighted_action_mse
from evogenesis.learning.stats import LossWeights, compute_loss_weights

#: `learning §3` 定稿的损失权重归一化口径（唯一已定义模式）
SUPPORTED_WEIGHT_NORMALIZATION = "per_dim_variance"


@dataclass(frozen=True)
class CoverageStats:
    """`learning §3` 定稿的覆盖率口径（episode 级 + step 级）。"""

    total_episodes: int
    episode_steps: int
    batch_size: int
    n_updates: int
    coverage_episodes: float  # K×batch / 总 episode 数（= epoch 数）
    coverage_steps: float  # 可见 step 样本 / 总 step 样本
    visible_steps: int  # K×batch×episode_steps
    total_steps: int  # 总 episode 数×episode_steps

    @property
    def epochs(self) -> float:
        """episode 级 ``K×batch/总 episode 数``（与 ``coverage_episodes`` 同值）。"""
        return self.coverage_episodes


def compute_coverage_stats(
    n_updates: int, batch_size: int, total_episodes: int, episode_steps: int
) -> CoverageStats:
    """按 `learning §3` 计算覆盖率；用于训练与独立测试。"""
    if total_episodes < 1 or episode_steps < 1 or batch_size < 1 or n_updates < 1:
        raise ValueError("覆盖率的四个输入均须 ≥ 1")
    visible_steps = n_updates * batch_size * episode_steps
    total_steps = total_episodes * episode_steps
    coverage_episodes = n_updates * batch_size / total_episodes
    return CoverageStats(
        total_episodes=total_episodes,
        episode_steps=episode_steps,
        batch_size=batch_size,
        n_updates=n_updates,
        coverage_episodes=coverage_episodes,
        coverage_steps=visible_steps / total_steps,
        visible_steps=visible_steps,
        total_steps=total_steps,
    )


@dataclass(frozen=True)
class TrainResult:
    """一次 BC 训练的产物（不落盘；报告见 :mod:`evogenesis.learning.report`）。"""

    loss_history: tuple[float, ...]
    update_batch_sizes: tuple[int, ...]
    loss_weights: LossWeights
    coverage_stats: CoverageStats
    sign_constrained: bool
    optimizer: str
    lr: float

    @property
    def n_updates(self) -> int:
        return len(self.loss_history)

    @property
    def batch_size(self) -> int:
        return self.update_batch_sizes[0] if self.update_batch_sizes else 0

    @property
    def final_loss(self) -> float:
        return self.loss_history[-1]

    @property
    def n_episodes(self) -> int:
        return self.coverage_stats.total_episodes

    @property
    def episode_steps(self) -> int:
        return self.coverage_stats.episode_steps

    @property
    def epochs(self) -> float:
        return self.coverage_stats.epochs

    @property
    def coverage_episodes(self) -> float:
        return self.coverage_stats.coverage_episodes

    @property
    def coverage_steps(self) -> float:
        return self.coverage_stats.coverage_steps

    @property
    def visible_steps(self) -> int:
        return self.coverage_stats.visible_steps

    @property
    def total_steps(self) -> int:
        return self.coverage_stats.total_steps


def _validate_config(cfg: LearningConfig) -> None:
    if cfg.optimizer != "adam":
        raise NotImplementedError(f"未实现 optimizer={cfg.optimizer!r}（§3 冻结为 adam）")
    if cfg.loss_weight_normalization != SUPPORTED_WEIGHT_NORMALIZATION:
        raise NotImplementedError(
            f"未实现 loss_weight_normalization={cfg.loss_weight_normalization!r}"
            f"（§3 仅定义 {SUPPORTED_WEIGHT_NORMALIZATION!r}）"
        )
    if cfg.mini_batch_updates < 1 or cfg.batch_size < 1:
        raise ValueError(
            f"mini_batch_updates / batch_size 必须 ≥ 1，实际 "
            f"({cfg.mini_batch_updates}, {cfg.batch_size})"
        )


def train_bc(
    net: DanioNet,
    dataset: TrajectoryDataset,
    cfg: LearningConfig,
    *,
    seed_manager: SeedManager,
    seed_index: int,
    device: str = "cpu",
    sign_constrained: bool = True,
) -> TrainResult:
    """在单个个体的 ``net`` 上执行 ``K`` 次 episode 级 BPTT 更新并返回 :class:`TrainResult`。

    参数
    ----
    net：单个体 ``DanioNet``（``len(net.n_neurons) == 1``），原地更新其 ``theta``。
    dataset：:class:`~evogenesis.learning.data.TrajectoryDataset`（按 episode 组织）。
    cfg：``configs/default_model.yaml::learning``
        （``load_config(..., model=ModelConfig).learning``）；``batch_size`` 为每批 episode 数。
    seed_manager：``core §3`` 种子管理器；episode 采样走 ``bc`` 命名空间。
    seed_index：该个体在 ``bc`` 命名空间内的稳定序号 ``t``（§3：由调用方按 ``genome_id`` 给定）。
    device：训练设备；``float32``。
    sign_constrained：`learning §4` 消融开关，**必须与传入 ``net`` 的构造设置一致**；
        无约束路径由 `DanioNet §3` 的 ``sign_constrained=False`` 提供（参数即有效权重）。
    """
    if net.sign_constrained != sign_constrained:
        raise ValueError(
            "sign_constrained 与 net 构造设置不一致："
            f"net.sign_constrained={net.sign_constrained}，调用传 {sign_constrained}。"
            "无约束消融须以 DanioNet(sign_constrained=False) 构造网络。"
        )
    _validate_config(cfg)
    if len(net.n_neurons) != 1:
        raise ValueError(
            f"train_bc 每次只训练一个个体（learning §1），实际 batch={len(net.n_neurons)}"
        )
    if dataset.n_episodes == 0:
        raise ValueError("训练集为空（0 episode），无法采样（§3 实现边界）")

    episode_steps = dataset.uniform_episode_steps
    weights = compute_loss_weights(
        dataset.expert_actions,
        floor_ratio=cfg.loss_variance_floor_ratio,
        fallback_omega=cfg.loss_weight_fallback_omega,
        fallback_v=cfg.loss_weight_fallback_v,
    )

    episodes = [
        (
            to_float32_tensor(observations, device=device),
            to_float32_tensor(actions, device=device),
        )
        for observations, actions in dataset.iter_episodes()
    ]

    optimizer = torch.optim.Adam([net.theta], lr=cfg.lr)
    rng = seed_manager.spawn_rng("bc", seed_index)
    n_episodes = dataset.n_episodes
    n_updates = cfg.mini_batch_updates
    batch_size = cfg.batch_size

    loss_history: list[float] = []
    batch_sizes: list[int] = []
    for _ in range(n_updates):
        sampled = rng.integers(0, n_episodes, size=batch_size)
        batch_sizes.append(int(sampled.size))

        optimizer.zero_grad()
        episode_losses = []
        for episode_index in sampled:
            observations, expert_actions = episodes[int(episode_index)]
            net.reset()
            step_losses = []
            for step in range(episode_steps):
                omega, v = net.step(observations[step])
                pred = torch.stack((omega[0], v[0])).unsqueeze(0)
                target = expert_actions[step].unsqueeze(0)
                step_losses.append(weighted_action_mse(pred, target, weights))
            episode_losses.append(torch.stack(step_losses).mean())
        loss = torch.stack(episode_losses).mean()
        loss.backward()
        optimizer.step()
        loss_history.append(float(loss.detach()))

    return TrainResult(
        loss_history=tuple(loss_history),
        update_batch_sizes=tuple(batch_sizes),
        loss_weights=weights,
        coverage_stats=compute_coverage_stats(n_updates, batch_size, n_episodes, episode_steps),
        sign_constrained=sign_constrained,
        optimizer=cfg.optimizer,
        lr=cfg.lr,
    )


__all__ = [
    "SUPPORTED_WEIGHT_NORMALIZATION",
    "CoverageStats",
    "TrainResult",
    "compute_coverage_stats",
    "train_bc",
]
