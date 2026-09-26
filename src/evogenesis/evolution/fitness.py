"""代内 fitness 合成（口径 owner：``evolution/遗传繁殖与演化模型.md`` §6）。

选择用的 ``F`` 由本模块产出：四项原始分量 ``S/P/E_esc/Q`` 先在**代内 viable 个体**上做
min-max 归一到 ``[0, 1]``，再加权 ``0.35 S + 0.25 P + 0.20 E_esc + 0.20 Q``。
- 某分量当代 ``max=min`` → 该分量置 0（不贡献）；
- non-viable / 无 F 者 → ``F=0``；
- 权重由 ``EvolutionConfig.fitness_weights`` 注入，本模块不硬编码。

边界：``F`` 只用于本代选择与展示；跨代/跨环境比较用原始指标（``experiment/实验与评价体系.md`` §4）。
数值 dtype 统一 ``float32``（``core/核心机制与数据流.md`` §7）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def minmax_normalize(
    values: Sequence[float] | np.ndarray,
    *,
    cohort_mask: Sequence[bool] | np.ndarray,
) -> np.ndarray:
    """在 ``cohort_mask`` 选中的子集上 min-max 归一到 ``[0, 1]``。

    子集内 ``max=min``（含子集为空）时该分量整体置 0；``cohort_mask`` 之外的条目返回 0。
    返回 ``float32`` 一维数组。
    """
    arr = np.asarray(values, dtype=np.float32)
    mask = np.asarray(cohort_mask, dtype=bool)
    if arr.ndim != 1:
        raise ValueError("values 必须是一维数组")
    if mask.shape != arr.shape:
        raise ValueError("cohort_mask 必须与 values 同形")
    out = np.zeros_like(arr, dtype=np.float32)
    cohort = arr[mask]
    if cohort.size == 0:
        return out
    lo = np.float32(cohort.min())
    hi = np.float32(cohort.max())
    if hi == lo:
        return out
    span = np.float32(hi - lo)
    normalized = ((arr - lo) / span).astype(np.float32)
    out[mask] = normalized[mask]
    return out


def composite_fitness(
    components: Mapping[str, Sequence[float] | np.ndarray],
    *,
    viable: Sequence[bool] | np.ndarray,
    weights: Mapping[str, float],
) -> np.ndarray:
    """按 ``evolution §6`` 产出选择用 ``F``（``float32`` 一维数组）。

    ``components`` 必须提供 ``weights`` 的全部键（``survival`` / ``prey_capture`` /
    ``escape_success`` / ``energy_efficiency``），且各分量等长；``viable`` 标记进入代内
    min-max 的个体。返回值在 ``viable=False`` 处置 0。
    """
    if set(components) != set(weights):
        raise ValueError(
            "components 的键必须与 weights 完全一致；"
            f"components={sorted(components)} weights={sorted(weights)}"
        )
    arrays = {name: np.asarray(components[name], dtype=np.float32) for name in weights}
    shapes = {value.shape for value in arrays.values()}
    if len(shapes) != 1:
        raise ValueError("各 fitness 分量长度必须一致")
    (shape,) = shapes
    if len(shape) != 1:
        raise ValueError("各 fitness 分量必须是一维数组")
    mask = np.asarray(viable, dtype=bool)
    if mask.shape != shape:
        raise ValueError("viable 必须与各分量同长")
    fitness = np.zeros(shape, dtype=np.float32)
    for name, weight in weights.items():
        normalized = minmax_normalize(arrays[name], cohort_mask=mask)
        fitness = (fitness + np.float32(weight) * normalized).astype(np.float32)
    fitness[~mask] = np.float32(0.0)
    return fitness
