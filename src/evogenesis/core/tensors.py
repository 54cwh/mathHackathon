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
    """把数组转为 ``torch.float32`` 张量；``device=None`` 时留在当前默认设备（``core §7``）。"""
    tensor = torch.from_numpy(np.asarray(array, dtype=np.float32))
    return tensor if device is None else tensor.to(device)
