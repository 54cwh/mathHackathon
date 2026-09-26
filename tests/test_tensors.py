"""跨框架转换 helper（``core §7``）。"""

import numpy as np
import torch

from evogenesis.core.tensors import to_float32_tensor


def test_to_float32_tensor_dtype_and_values():
    tensor = to_float32_tensor(np.array([1, 2, 3], dtype=np.float64))
    assert tensor.dtype == torch.float32
    assert torch.equal(tensor, torch.tensor([1, 2, 3], dtype=torch.float32))


def test_to_float32_tensor_device():
    tensor = to_float32_tensor(np.zeros(2, dtype=np.float32), device="cpu")
    assert tensor.device.type == "cpu"


def test_to_float32_tensor_no_float64_promotion():
    tensor = to_float32_tensor(np.array([0.1], dtype=np.float64))
    assert tensor.dtype == torch.float32
