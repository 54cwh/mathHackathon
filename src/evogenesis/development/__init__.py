"""RGCD 发育（`RGCD数学模型.md` §1–§11，v1.8 已定稿）。"""

from evogenesis.development.config import (
    DEFAULT_CONFIG,
    DOMAIN_ORDER,
    RGCDConfig,
    load_development_config,
)
from evogenesis.development.development import (
    DevelopmentState,
    block_origins,
    cell_identity,
    division_probability,
    place_precursors,
    proliferate,
)
from evogenesis.development.grn import discrete_grn, spectral_radius
from evogenesis.development.rgcd import (
    ConnectomePhenotype,
    RGCDParameters,
    apply_dale_sign,
    centered_bilinear,
    compatibility_prior,
    connection_logits,
    develop,
    expected_off_diagonal_density,
    initial_weights,
    initialize_parameters,
    softplus_inverse,
    solve_bias_for_density,
    tau_from_grn,
    viability_check,
)

__all__ = [
    "DEFAULT_CONFIG",
    "DOMAIN_ORDER",
    "ConnectomePhenotype",
    "DevelopmentState",
    "RGCDConfig",
    "RGCDParameters",
    "apply_dale_sign",
    "block_origins",
    "cell_identity",
    "centered_bilinear",
    "compatibility_prior",
    "connection_logits",
    "develop",
    "discrete_grn",
    "division_probability",
    "expected_off_diagonal_density",
    "initial_weights",
    "initialize_parameters",
    "load_development_config",
    "place_precursors",
    "proliferate",
    "softplus_inverse",
    "solve_bias_for_density",
    "spectral_radius",
    "tau_from_grn",
    "viability_check",
]
