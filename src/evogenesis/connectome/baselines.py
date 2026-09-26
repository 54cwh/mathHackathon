"""§8 对照基线：MLP / GRU / Fixed Sparse RNN（owner：`DanioNet设计规范.md` §8）。

与 `DanioNet` **同构接口**，以便同一套 BC 训练与 §2.4 测量直接可用：
``n_neurons`` / ``active_counts`` / ``theta``（唯一 ``nn.Parameter``）/ ``sign_constrained=False`` /
``reset()`` / ``step(observations) -> (ω, v)`` / ``complexity()``。

连接数（仅权重，不含 bias）按 §8 反解：MLP \\(H=14\\)→196；GRU \\(H=4\\)→200；
Fixed Sparse RNN \\(H=12\\), 递归密度 \\(\\rho=0.15\\) → ≈190（以实际 mask 计）。
初始化尺度用 Glorot 均匀、bias 置 0，属 §8 标明的**设计选择（D）**。
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
import torch
from torch import nn

from evogenesis.core.seed import SeedManager
from evogenesis.core.tensors import to_float32_tensor

N_OURS = 190
SPARSE_DENSITY = 0.15
DEFAULT_SENSORY_DIM = 12
ACTION_DIM = 2


class _BaselineConfig:
    """供测量模块读取的最小 config 面（`max_nodes` = 隐层宽）。"""

    __slots__ = ("max_nodes", "sensory_dim")

    def __init__(self, max_nodes: int, sensory_dim: int) -> None:
        self.max_nodes = max_nodes
        self.sensory_dim = sensory_dim


class BaselinePolicy(nn.Module):
    """基线公共骨架：单一扁平 ``theta``、确定性 Glorot 初始化、状态 ``h``。"""

    sign_constrained = False

    def __init__(
        self,
        *,
        master_seed: int,
        index: int,
        hidden: int,
        sensory_dim: int = DEFAULT_SENSORY_DIM,
        device: str = "cpu",
    ) -> None:
        super().__init__()
        if hidden < 1:
            raise ValueError(f"hidden 必须 ≥ 1，实际 {hidden}")
        self.device = device
        self.hidden = hidden
        self.sensory_dim = sensory_dim
        self.config = _BaselineConfig(max_nodes=hidden, sensory_dim=sensory_dim)
        self._n_neurons = [hidden]
        self.register_buffer("h", torch.zeros((1, hidden), dtype=torch.float32, device=device))
        shapes = self._init_shapes()
        self._sizes = [int(np.prod(shape)) for shape in shapes]
        generator = SeedManager(master_seed).spawn_rng("baseline_init", index)
        flat = np.zeros(sum(self._sizes), dtype=np.float32)
        offset = 0
        for size, (fan_in, fan_out), zero in zip(
            self._sizes, self._fans(), self._zero_blocks(), strict=True
        ):
            if not zero:
                limit = math.sqrt(6.0 / (fan_in + fan_out))
                flat[offset : offset + size] = generator.uniform(-limit, limit, size=size)
            offset += size
        self.theta = nn.Parameter(to_float32_tensor(flat, device=device))

    def _init_shapes(self) -> list[tuple[int, ...]]:
        raise NotImplementedError

    def _fans(self) -> list[tuple[int, int]]:
        raise NotImplementedError

    def _zero_blocks(self) -> list[bool]:
        raise NotImplementedError

    @property
    def n_neurons(self) -> list[int]:
        return list(self._n_neurons)

    @property
    def active_counts(self) -> list[int]:
        return list(self._n_neurons)

    def _take(self, shape: tuple[int, ...], offset: int) -> torch.Tensor:
        size = 1
        for dim in shape:
            size *= dim
        return self.theta[offset : offset + size].view(shape)

    def _block_offsets(self) -> list[int]:
        offsets: list[int] = []
        offset = 0
        for size in self._sizes:
            offsets.append(offset)
            offset += size
        return offsets

    def reset(self) -> None:
        self.h = torch.zeros_like(self.h)

    def _obs(self, observations: np.ndarray | torch.Tensor) -> torch.Tensor:
        x = (
            observations
            if isinstance(observations, torch.Tensor)
            else to_float32_tensor(observations)
        )
        x = x.to(dtype=torch.float32, device=self.device)
        if x.dim() == 1:
            x = x.unsqueeze(0)
        if x.dim() != 2 or x.shape[-1] != self.sensory_dim:
            raise ValueError(
                f"observation 形状须为 (batch, {self.sensory_dim})，实际 {tuple(x.shape)}"
            )
        return x

    def step(self, observations: np.ndarray | torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        raise NotImplementedError

    def complexity(self) -> dict[str, int]:
        """§8 口径：`macs_impl` 按稠密权重数、`macs_theo` 按实际连接数。"""
        raise NotImplementedError


class MLPPolicy(BaselinePolicy):
    """单隐层 MLP（§8；\\(H = 14\\) ⇒ 196 连接）。"""

    HIDDEN = 14

    def __init__(
        self,
        *,
        master_seed: int,
        index: int,
        sensory_dim: int = DEFAULT_SENSORY_DIM,
        device: str = "cpu",
    ):
        super().__init__(
            master_seed=master_seed,
            index=index,
            hidden=self.HIDDEN,
            sensory_dim=sensory_dim,
            device=device,
        )

    def _init_shapes(self) -> list[tuple[int, ...]]:
        return [
            (self.hidden, self.sensory_dim),
            (self.hidden,),
            (ACTION_DIM, self.hidden),
            (ACTION_DIM,),
        ]

    def _fans(self) -> list[tuple[int, int]]:
        return [
            (self.sensory_dim, self.hidden),
            (self.sensory_dim, self.hidden),
            (self.hidden, ACTION_DIM),
            (self.hidden, ACTION_DIM),
        ]

    def _zero_blocks(self) -> list[bool]:
        return [False, True, False, True]

    def step(self, observations):
        x = self._obs(observations)
        o = self._block_offsets()
        w1 = self._take((self.hidden, self.sensory_dim), o[0])
        b1 = self._take((self.hidden,), o[1])
        w2 = self._take((ACTION_DIM, self.hidden), o[2])
        b2 = self._take((ACTION_DIM,), o[3])
        self.h = torch.tanh(x @ w1.t() + b1)
        y = torch.tanh(self.h @ w2.t() + b2)
        return y[:, 0], y[:, 1]

    def complexity(self) -> dict[str, int]:
        weights = self.sensory_dim * self.hidden + self.hidden * ACTION_DIM
        return {
            "parameter_count": weights,
            "active_edges": weights,
            "macs_implemented": weights,
            "macs_theoretical": weights,
            "flops_implemented": 2 * weights,
            "flops_theoretical": 2 * weights,
        }


class FixedSparseRNNPolicy(BaselinePolicy):
    """固定稀疏递归网络（§8；\\(H = 12\\)、递归密度 \\(\\rho = 0.15\\) ⇒ ≈190 连接）。"""

    HIDDEN = 12

    def __init__(
        self,
        *,
        master_seed: int,
        index: int,
        sensory_dim: int = DEFAULT_SENSORY_DIM,
        device: str = "cpu",
    ):
        super().__init__(
            master_seed=master_seed,
            index=index,
            hidden=self.HIDDEN,
            sensory_dim=sensory_dim,
            device=device,
        )
        generator = SeedManager(master_seed).spawn_rng("baseline_init", index)
        mask = generator.random((self.hidden, self.hidden)) < SPARSE_DENSITY
        self.register_buffer("support", torch.as_tensor(mask, dtype=torch.bool, device=device))

    def _init_shapes(self) -> list[tuple[int, ...]]:
        return [
            (self.hidden, self.hidden),
            (self.hidden, self.sensory_dim),
            (self.hidden,),
            (ACTION_DIM, self.hidden),
            (ACTION_DIM,),
        ]

    def _fans(self) -> list[tuple[int, int]]:
        return [
            (self.hidden, self.hidden),
            (self.sensory_dim, self.hidden),
            (self.sensory_dim, self.hidden),
            (self.hidden, ACTION_DIM),
            (self.hidden, ACTION_DIM),
        ]

    def _zero_blocks(self) -> list[bool]:
        return [False, False, True, False, True]

    def step(self, observations):
        x = self._obs(observations)
        o = self._block_offsets()
        w_rec = self._take((self.hidden, self.hidden), o[0]) * self.support
        w_in = self._take((self.hidden, self.sensory_dim), o[1])
        b = self._take((self.hidden,), o[2])
        w_out = self._take((ACTION_DIM, self.hidden), o[3])
        b_out = self._take((ACTION_DIM,), o[4])
        pre = self.h @ w_rec.t() + x @ w_in.t() + b
        self.h = torch.tanh(pre)
        y = torch.tanh(self.h @ w_out.t() + b_out)
        return y[:, 0], y[:, 1]

    def complexity(self) -> dict[str, int]:
        dense = (
            self.hidden * self.hidden + self.sensory_dim * self.hidden + self.hidden * ACTION_DIM
        )
        sparse_rec = int(self.support.sum().item())
        sparse = sparse_rec + self.sensory_dim * self.hidden + self.hidden * ACTION_DIM
        return {
            "parameter_count": sparse,
            "active_edges": sparse,
            "macs_implemented": dense,
            "macs_theoretical": sparse,
            "flops_implemented": 2 * dense,
            "flops_theoretical": 2 * sparse,
        }


class GRUPolicy(BaselinePolicy):
    """单层 GRU（§8；\\(H = 4\\) ⇒ 200 连接）。"""

    HIDDEN = 4

    def __init__(
        self,
        *,
        master_seed: int,
        index: int,
        sensory_dim: int = DEFAULT_SENSORY_DIM,
        device: str = "cpu",
    ):
        super().__init__(
            master_seed=master_seed,
            index=index,
            hidden=self.HIDDEN,
            sensory_dim=sensory_dim,
            device=device,
        )

    def _init_shapes(self) -> list[tuple[int, ...]]:
        h, d = self.hidden, self.sensory_dim
        return [
            (h, d),
            (h, h),
            (h,),
            (h, d),
            (h, h),
            (h,),
            (h, d),
            (h, h),
            (h,),
            (ACTION_DIM, h),
            (ACTION_DIM,),
        ]

    def _fans(self) -> list[tuple[int, int]]:
        h, d = self.hidden, self.sensory_dim
        return [
            (d, h),
            (h, h),
            (d + h, h),
            (d, h),
            (h, h),
            (d + h, h),
            (d, h),
            (h, h),
            (d + h, h),
            (h, ACTION_DIM),
            (h, ACTION_DIM),
        ]

    def _zero_blocks(self) -> list[bool]:
        return [False, False, True, False, False, True, False, False, True, False, True]

    def step(self, observations):
        x = self._obs(observations)
        o = self._block_offsets()
        h, d = self.hidden, self.sensory_dim
        wx_z = self._take((h, d), o[0])
        wh_z = self._take((h, h), o[1])
        b_z = self._take((h,), o[2])
        wx_r = self._take((h, d), o[3])
        wh_r = self._take((h, h), o[4])
        b_r = self._take((h,), o[5])
        wx_n = self._take((h, d), o[6])
        wh_n = self._take((h, h), o[7])
        b_n = self._take((h,), o[8])
        w_out = self._take((ACTION_DIM, h), o[9])
        b_out = self._take((ACTION_DIM,), o[10])
        z = torch.sigmoid(x @ wx_z.t() + self.h @ wh_z.t() + b_z)
        r = torch.sigmoid(x @ wx_r.t() + self.h @ wh_r.t() + b_r)
        n = torch.tanh(x @ wx_n.t() + (r * self.h) @ wh_n.t() + b_n)
        self.h = (1.0 - z) * n + z * self.h
        y = torch.tanh(self.h @ w_out.t() + b_out)
        return y[:, 0], y[:, 1]

    def complexity(self) -> dict[str, int]:
        h, d = self.hidden, self.sensory_dim
        weights = 3 * (h * d + h * h) + h * ACTION_DIM
        return {
            "parameter_count": weights,
            "active_edges": weights,
            "macs_implemented": weights,
            "macs_theoretical": weights,
            "flops_implemented": 2 * weights,
            "flops_theoretical": 2 * weights,
        }


BASELINES: dict[str, Callable[..., BaselinePolicy]] = {
    "mlp": MLPPolicy,
    "gru": GRUPolicy,
    "fixed_sparse_rnn": FixedSparseRNNPolicy,
}


def build_baselines(
    master_seed: int,
    *,
    index: int = 0,
    sensory_dim: int = DEFAULT_SENSORY_DIM,
    device: str = "cpu",
) -> dict[str, BaselinePolicy]:
    """构造三个基线（同一 `baseline_init` 命名空间、按各自 H 反解，§8）。"""
    return {
        name: cls(master_seed=master_seed, index=index, sensory_dim=sensory_dim, device=device)
        for name, cls in BASELINES.items()
    }


__all__ = [
    "BASELINES",
    "BaselinePolicy",
    "FixedSparseRNNPolicy",
    "GRUPolicy",
    "MLPPolicy",
    "N_OURS",
    "SPARSE_DENSITY",
    "build_baselines",
]
