from dataclasses import dataclass

import torch

CELL_TYPES = ("sensory", "prey", "threat", "memory", "inhibitory", "motor")


@dataclass
class DevelopmentState:
    grn: torch.Tensor
    positions: torch.Tensor
    domains: torch.Tensor
    active_mask: torch.Tensor


def division_probability(grn, w_div, b_div):
    return torch.sigmoid(grn @ w_div + b_div)


def cell_identity(grn, U, domain_bias):
    logits = grn @ U.T + domain_bias
    return torch.softmax(logits, dim=-1)


# TODO:
# seeded Bernoulli division; max once/precursor
# daughter position/state perturbation
# keep <=48 slots
# domain competence without post-hoc silently inserting cell types
