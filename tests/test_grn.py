import torch

from evogenesis.design.grn import discrete_grn


def test_grn_range_and_shape():
    g0 = torch.zeros(1, 24, 8)
    q = torch.zeros(1, 8)
    pos = torch.zeros(1, 24, 2)
    Wg = torch.zeros(8, 8)
    B = torch.zeros(8, 8)
    P = torch.zeros(8, 2)
    bias = torch.zeros(8)
    out = discrete_grn(g0, q, pos, Wg, B, P, bias)
    assert out.shape == (1, 24, 8)
    assert torch.all((out >= 0) & (out <= 1))
