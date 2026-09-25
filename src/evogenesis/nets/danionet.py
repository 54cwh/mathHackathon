import torch
import torch.nn as nn


class DanioNet(nn.Module):
    def __init__(self, sensory_dim: int = 12, max_neurons: int = 48):
        super().__init__()
        self.max_neurons = max_neurons
        self.input_proj = nn.Linear(sensory_dim, max_neurons, bias=False)
        self.motor_readout = nn.Linear(max_neurons, 2)

    def step(self, h, x, adjacency, weights, tau, neuron_mask):
        recurrent_matrix = adjacency * weights
        rec = torch.einsum("bij,bj->bi", recurrent_matrix, h)
        target = torch.tanh(rec + self.input_proj(x))
        inv_tau = 1.0 / tau.clamp_min(1.0)
        h_next = ((1.0 - inv_tau) * h + inv_tau * target) * neuron_mask
        raw = self.motor_readout(h_next)
        omega = torch.tanh(raw[:, 0:1])
        speed = torch.sigmoid(raw[:, 1:2])
        return h_next, torch.cat([omega, speed], dim=-1)
