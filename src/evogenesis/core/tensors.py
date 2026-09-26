"""跨框架转换：NumPy → torch（``core §7``，已定稿）。

producer 保持零 torch 依赖（如 ``genome`` 产出 NumPy ``float32``）；转换由**消费方**
在其入口调用 :func:`to_float32_tensor` 完成。dtype 固定 ``torch.float32``，``device``
由调用方显式给出（``core §7``：禁止隐式提升为 ``float64``）。
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch


def to_float32_tensor(array: Any, *, device: str | None = None) -> torch.Tensor:
    """把数组转为 ``torch.float32`` 张量；``device=None`` 时留在当前默认设备（``core §7``）。

    - ``array`` 已是 ``torch.Tensor``：仅对齐 ``dtype``/``device``（该分支是 CUDA 张量的
      唯一可行路径——``np.asarray`` 不能转换 CUDA 张量）；
    - 否则经 ``np.asarray(..., dtype=float32)`` 归一后 ``torch.from_numpy``。

    **零拷贝**：输入已是（NumPy 或 torch）``float32`` 时返回与输入**共享内存**的张量；
    调用方不得对结果原地写入（会改到 producer 数组），需独立副本时先
    ``np.array(x, dtype=np.float32, copy=True)``。
    """
    if isinstance(array, torch.Tensor):
        tensor = array.to(dtype=torch.float32)
        return tensor if device is None else tensor.to(device)
    tensor = torch.from_numpy(np.asarray(array, dtype=np.float32))
    return tensor if device is None else tensor.to(device)
