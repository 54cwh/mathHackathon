import torch


def discrete_grn(g0, q, pos, Wg, B, P, bias, rho: float = 0.35, steps: int = 12):
    """Frozen equation:
    g_{r+1}=(1-rho)g_r+rho*sigmoid(Wg g_r+B q+P p+b)
    """
    g = g0
    for _ in range(steps):
        recurrent = torch.einsum("...cd,de->...ce", g, Wg)
        genome_term = torch.einsum("...d,ed->...e", q, B).unsqueeze(-2)
        pos_term = torch.einsum("...cp,ep->...ce", pos, P)
        target = torch.sigmoid(recurrent + genome_term + pos_term + bias)
        g = (1.0 - rho) * g + rho * target
    return g
