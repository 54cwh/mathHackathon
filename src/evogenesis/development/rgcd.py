from dataclasses import dataclass

import torch


@dataclass
class ConnectomePhenotype:
    adjacency: torch.Tensor
    weights0: torch.Tensor
    tau: torch.Tensor
    cell_type: torch.Tensor
    positions: torch.Tensor
    active_mask: torch.Tensor
    viable: bool
    viability_reason: str


def connection_logits(z, positions, compatibility, distance_lambda, regulatory_term, bias):
    type_term = z @ compatibility @ z.T
    dist = torch.cdist(positions, positions)
    logits = type_term - distance_lambda * dist + regulatory_term + bias
    logits.fill_diagonal_(-1e9)
    return logits


def tau_from_grn(grn, a, b):
    return 1.0 + 9.0 * torch.sigmoid(grn @ a + b)


def apply_dale_sign(weights_abs, cell_type, inhibitory_index: int = 4):
    sign = torch.ones(weights_abs.shape[0], device=weights_abs.device)
    sign[cell_type == inhibitory_index] = -1.0
    return weights_abs * sign[:, None]


def viability_check(adjacency, cell_type, active_mask):
    if int(active_mask.sum()) == 0:
        return False, "no_active_neurons"
    # TODO: all six fates, L/R motor, sensory->motor reachability,
    # zero-input dynamics test.
    return True, "ok"
