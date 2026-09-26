"""行为克隆学习（`learning/行为克隆学习.md` v1.3）。

对外接口：轨迹加载（:mod:`~evogenesis.learning.data`）、损失权重（:mod:`~evogenesis.learning.stats`）、
加权 MSE（:mod:`~evogenesis.learning.loss`）、训练循环（:mod:`~evogenesis.learning.train`）与
训练报告（:mod:`~evogenesis.learning.report`）。
"""

from evogenesis.learning.data import (
    ACTION_DIM,
    SENSORY_DIM,
    Episode,
    TrajectoryDataset,
    TrajectoryFormatError,
    load_episode,
    load_trajectories,
    load_trajectory_dir,
)
from evogenesis.learning.loss import per_dim_mse, weighted_action_mse
from evogenesis.learning.report import (
    TrainingReport,
    active_support,
    build_report,
    delta_w_identity_error,
    sign_flip_rate,
    spectral_radius,
)
from evogenesis.learning.stats import (
    DEFAULT_ACTION_RANGES,
    LossWeights,
    compute_loss_weights,
    population_std,
)
from evogenesis.learning.train import (
    SUPPORTED_WEIGHT_NORMALIZATION,
    CoverageStats,
    TrainResult,
    compute_coverage_stats,
    train_bc,
)

__all__ = [
    "ACTION_DIM",
    "DEFAULT_ACTION_RANGES",
    "SENSORY_DIM",
    "SUPPORTED_WEIGHT_NORMALIZATION",
    "CoverageStats",
    "Episode",
    "LossWeights",
    "TrainResult",
    "TrainingReport",
    "TrajectoryDataset",
    "TrajectoryFormatError",
    "active_support",
    "build_report",
    "compute_coverage_stats",
    "compute_loss_weights",
    "delta_w_identity_error",
    "load_episode",
    "load_trajectories",
    "load_trajectory_dir",
    "per_dim_mse",
    "population_std",
    "sign_flip_rate",
    "spectral_radius",
    "train_bc",
    "weighted_action_mse",
]
