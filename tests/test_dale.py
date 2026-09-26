import torch

from evogenesis.development.rgcd import apply_dale_sign


def test_dale_sign():
    w = torch.ones(3, 3)
    types = torch.tensor([0, 4, 5])
    out = apply_dale_sign(w, types)
    assert torch.all(out[1] <= 0)
    assert torch.all(out[0] >= 0)
    assert torch.all(out[2] >= 0)


def test_danionet_sign_constrained_toggle():
    """`DanioNet §3`：约束路径 = sign(W⁰)·softplus(Θ)，非约束路径参数即权重，两路径同起点。"""
    import torch.nn.functional as F
    from test_learning_common import make_net

    constrained = make_net()
    assert constrained.sign_constrained is True
    assert torch.equal(constrained.delta_weights, torch.zeros_like(constrained.theta))

    unconstrained = make_net(sign_constrained=False)
    assert unconstrained.sign_constrained is False
    # 非约束路径：effective = support ⊙ theta，初值即 W⁰（ΔW=0）
    assert torch.equal(unconstrained.effective_weights, unconstrained.weights0)
    assert torch.equal(unconstrained.delta_weights, torch.zeros_like(unconstrained.theta))
    # 约束路径：等价于 sign(W⁰)·softplus(Θ) 的支撑屏蔽形式
    expected = constrained.support_sign0 * F.softplus(constrained.theta)
    assert torch.equal(constrained.effective_weights, expected)
