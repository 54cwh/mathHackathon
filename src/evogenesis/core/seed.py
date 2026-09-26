"""核心种子派生（core §3，已定稿）。

master seed → 命名空间子种子，四路随机源统一派生：
Python ``random`` / NumPy / PyTorch CPU / PyTorch CUDA。

派生式（core §3 定稿）：命名空间序列 ``SeedSequence([namespace_id, master_seed])``
（**变化 ID 前置**）；实体级子种子取该序列的 ``spawn`` 树第 ``index`` 项——
``spawn`` 结果按命名空间缓存，取更高索引时按更大的 ``k`` 重新 ``spawn``
（前缀与更小 ``k`` 一致，故与调用顺序无关）。四路随机源由同一子序列派生。
"""

from __future__ import annotations

import random

import numpy as np
import torch

# 命名空间 id（core §3 定稿）。未知名字显式报错，不静默发明新 id。
NAMESPACES: dict[str, int] = {
    "mutation": 0,
    "crossover": 1,
    "development": 2,
    "arena_spawn": 3,
    "motif_catalog": 4,
    "network_init": 5,
    "selection": 6,
    "initial_population": 7,
    "bc": 8,
    "arena_dynamics": 9,
    "baseline_init": 10,
    "penetrance_calibration": 11,
    "penetrance_report": 12,
    "baseline_support": 13,
    "robustness": 14,
}


def _namespace_id(name: str) -> int:
    try:
        return NAMESPACES[name]
    except KeyError as exc:
        known = ", ".join(sorted(NAMESPACES))
        raise ValueError(f"未注册的种子命名空间 {name!r}；已注册：{known}") from exc


def set_global_seed(seed: int) -> None:
    """程序入口的全局随机源初始化（四路）。子种子请改用 :class:`SeedManager`。"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class SeedManager:
    """由 master seed 派生各随机过程的子种子。"""

    def __init__(self, master_seed: int) -> None:
        if not 0 <= int(master_seed) < 2**32:
            raise ValueError("master_seed 必须落在 [0, 2**32)")
        self._master_seed = int(master_seed)
        self._spawn_cache: dict[str, list[np.random.SeedSequence]] = {}

    @property
    def master_seed(self) -> int:
        return self._master_seed

    def _namespace_sequence(self, name: str) -> np.random.SeedSequence:
        # 变化 ID 前置（core §3 定稿）：官方并行 RNG 建议，且实体子序列由此序列 spawn，
        # 前置可避免列表熵与 spawn 路径碰撞。
        return np.random.SeedSequence([_namespace_id(name), self._master_seed])

    def _spawn(self, name: str, count: int) -> list[np.random.SeedSequence]:
        cached = self._spawn_cache.get(name)
        if cached is None or count > len(cached):
            cached = list(self._namespace_sequence(name).spawn(count))
            self._spawn_cache[name] = cached
        return cached[:count]

    def rng(self, name: str) -> np.random.Generator:
        """命名空间级 NumPy 生成器（非实体级）。"""
        return np.random.default_rng(self._namespace_sequence(name))

    def seed(self, name: str, index: int) -> int:
        """实体级整数子种子 ``g``（``core §3``）：``C.generate_state(1, uint32)[0]``。

        供只接受整数种子的下游（如 ``DanioArena(spawn_seed=..., dynamics_seed=...)``）使用；同一
        ``(master_seed, name, index)`` 恒得同一 ``g``。
        """
        if index < 0:
            raise ValueError("index 必须非负")
        state = self._spawn(name, index + 1)[index].generate_state(1, dtype=np.uint32)
        return int(state[0])

    def spawn_rng(self, name: str, index: int) -> np.random.Generator:
        """实体级 NumPy 生成器：命名空间序列的第 ``index`` 个 spawn 子序列。"""
        if index < 0:
            raise ValueError("index 必须非负")
        return np.random.default_rng(self._spawn(name, index + 1)[index])

    def python_rng(self, name: str, index: int = 0) -> random.Random:
        """实体级 Python ``random.Random``，种子由同一子序列派生。"""
        if index < 0:
            raise ValueError("index 必须非负")
        state = self._spawn(name, index + 1)[index].generate_state(1, dtype=np.uint32)
        return random.Random(int(state[0]))

    def torch_generator(self, name: str, index: int = 0, device: str = "cpu") -> torch.Generator:
        """实体级 ``torch.Generator``，种子由同一子序列派生。"""
        if index < 0:
            raise ValueError("index 必须非负")
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("请求 CUDA 生成器但当前环境无可用 CUDA")
        state = self._spawn(name, index + 1)[index].generate_state(1, dtype=np.uint32)
        return torch.Generator(device=device).manual_seed(int(state[0]))
