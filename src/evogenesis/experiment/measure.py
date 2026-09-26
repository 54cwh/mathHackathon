"""模型复杂度与推理开销测量（owner：`实验与评价体系.md` §2.4）。

本模块只做**测量与计数**，不定义模型、不复算结构：结构量（支撑边数、活跃神经元数、
padding 宽度）一律从 `DanioNet` 的既有 buffer / config 读出，与生产同源。

口径（符号定义见 §2.4）：

- ``MACs_impl = N² + N·D``（完整稠密矩阵，含 padding 与零边）；
- ``MACs_theo = E_A + N_act·D``（仅活跃部分，体现结构稀疏）；
- ``FLOPs = 2 × MACs``；两者均含输入投影、不含非线性。
- latency：单步前向（batch = 1，与生产同 device），warmup 后计时，报 p50 / p95（ms）；
  ``warmup`` / ``iters`` 的取值在 §2.4 标「草案待确认」，默认值即该处约定。
- peak memory：``tracemalloc`` 的 Python 分配峰值（B），范围由调用方给定（整 episode）。
"""

from __future__ import annotations

import statistics
import time
import tracemalloc
from collections.abc import Callable
from typing import Any, Protocol

import numpy as np

DEFAULT_WARMUP = 20
DEFAULT_ITERS = 200


class Steppable(Protocol):
    """只需具备 ``step(observations)`` 的最小接口（`DanioNet` 与 baseline 均满足）。"""

    def step(self, observations: Any) -> Any: ...


def count_flops(
    *, n_nodes: int, sensory_dim: int, support_edges: int, n_active: int
) -> dict[str, int]:
    """§2.4 双口径 MACs / FLOPs。

    参数：``n_nodes`` = padding 宽度 *N*；``sensory_dim`` = *D*；``support_edges`` = *E_A*；
    ``n_active`` = *N_act*。返回键：``macs_implemented`` / ``macs_theoretical`` /
    ``flops_implemented`` / ``flops_theoretical``。
    """
    for name, value in (
        ("n_nodes", n_nodes),
        ("sensory_dim", sensory_dim),
        ("support_edges", support_edges),
        ("n_active", n_active),
    ):
        if value < 0:
            raise ValueError(f"{name} 必须非负，实际 {value}")
    if n_active > n_nodes:
        raise ValueError(f"n_active({n_active}) 不得超过 n_nodes({n_nodes})")
    macs_implemented = n_nodes * n_nodes + n_nodes * sensory_dim
    macs_theoretical = support_edges + n_active * sensory_dim
    return {
        "macs_implemented": macs_implemented,
        "macs_theoretical": macs_theoretical,
        "flops_implemented": 2 * macs_implemented,
        "flops_theoretical": 2 * macs_theoretical,
    }


def measure_latency(
    net: Steppable,
    observation: Any,
    *,
    warmup: int = DEFAULT_WARMUP,
    iters: int = DEFAULT_ITERS,
) -> dict[str, float]:
    """单步前向 wall-clock 延迟（ms）；p50 / p95 用线性插值百分位。

    返回 ``p50_ms`` / ``p95_ms`` / ``mean_ms`` / ``n_iters``。
    """
    if warmup < 0:
        raise ValueError(f"warmup 必须非负，实际 {warmup}")
    if iters < 1:
        raise ValueError(f"iters 必须 ≥ 1，实际 {iters}")
    for _ in range(warmup):
        net.step(observation)
    samples = np.empty(iters, dtype=np.float64)
    for i in range(iters):
        start = time.perf_counter()
        net.step(observation)
        samples[i] = (time.perf_counter() - start) * 1e3
    return {
        "p50_ms": float(np.percentile(samples, 50)),
        "p95_ms": float(np.percentile(samples, 95)),
        "mean_ms": float(statistics.fmean(samples)),
        "n_iters": float(iters),
    }


def peak_memory_bytes(run_episode: Callable[[], Any]) -> int:
    """§2.4：``tracemalloc`` 追踪的 Python 分配峰值（B）。

    ``run_episode`` 应为「跑完一整段」的可调用对象（例如一个 episode 的 rollout）。
    """
    tracemalloc.start()
    try:
        run_episode()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return int(peak)


def network_complexity(net: Any, *, individual: int = 0) -> dict[str, int]:
    """从 `DanioNet` 读结构量并给出 §2.4 的双口径复杂度。

    读自（与 `scripts/probe_architecture.py` 同源）：``support``（支撑 *A* 的布尔 mask）、
    ``active_counts``（*M* 为真者）、``config.max_nodes``（*N*）、``config.sensory_dim``（*D*）。
    另返回 ``parameter_count``（支撑内有效可训练元素数）与 ``active_edges``。
    """
    support = net.support[individual]
    support_edges = int(support.sum().item())
    n_active = int(net.active_counts[individual])
    n_nodes = int(net.config.max_nodes)
    sensory_dim = int(net.config.sensory_dim)
    return {
        "parameter_count": support_edges,
        "active_edges": support_edges,
        "n_nodes": n_nodes,
        "n_active": n_active,
        "sensory_dim": sensory_dim,
        **count_flops(
            n_nodes=n_nodes,
            sensory_dim=sensory_dim,
            support_edges=support_edges,
            n_active=n_active,
        ),
    }
