import torch

from evogenesis.design.rgcd import apply_dale_sign


def test_dale_sign():
    w = torch.ones(3, 3)
    types = torch.tensor([0, 4, 5])
    out = apply_dale_sign(w, types)
    assert torch.all(out[1] <= 0)
    assert torch.all(out[0] >= 0)
    assert torch.all(out[2] >= 0)
