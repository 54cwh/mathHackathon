"""`experiment/measure.py`（§2.4 测量三件套）的守护测试。"""

from __future__ import annotations

import numpy as np
import pytest

from evogenesis.connectome.config import DEFAULT_NETWORK_CONFIG
from evogenesis.connectome.danionet import DanioNet
from evogenesis.development import develop
from evogenesis.experiment.measure import (
    count_flops,
    measure_latency,
    network_complexity,
    peak_memory_bytes,
)

MASTER_SEED = 250927
VIABLE_INDEX = 6
VIABLE_Q = np.array(
    [
        0.5077722072601318,
        0.8713393807411194,
        0.36126405000686646,
        0.5981840491294861,
        0.05925164371728897,
        0.3876318037509918,
        0.3230363428592682,
        0.15019972622394562,
    ],
    dtype=np.float32,
)


def _obs(hunger: float = 1.0) -> np.ndarray:
    obs = np.zeros((1, DEFAULT_NETWORK_CONFIG.sensory_dim), dtype=np.float32)
    obs[0, 11] = hunger
    return obs


def test_count_flops_matches_documented_formulas():
    got = count_flops(n_nodes=48, sensory_dim=12, support_edges=300, n_active=30)
    assert got["macs_implemented"] == 48 * 48 + 48 * 12
    assert got["macs_theoretical"] == 300 + 30 * 12
    assert got["flops_implemented"] == 2 * got["macs_implemented"]
    assert got["flops_theoretical"] == 2 * got["macs_theoretical"]
    assert got["macs_theoretical"] < got["macs_implemented"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"n_nodes": -1, "sensory_dim": 12, "support_edges": 0, "n_active": 0}, "n_nodes"),
        ({"n_nodes": 48, "sensory_dim": -1, "support_edges": 0, "n_active": 0}, "sensory_dim"),
        ({"n_nodes": 48, "sensory_dim": 12, "support_edges": -1, "n_active": 0}, "support_edges"),
        ({"n_nodes": 48, "sensory_dim": 12, "support_edges": 0, "n_active": 49}, "n_active"),
    ],
)
def test_count_flops_rejects_invalid_inputs(kwargs, message):
    with pytest.raises(ValueError, match=message):
        count_flops(**kwargs)


class _CountingNet:
    def __init__(self) -> None:
        self.calls = 0

    def step(self, observations):  # noqa: ARG002
        self.calls += 1
        return 0.0, 0.0


def test_measure_latency_call_count_and_ordering():
    net = _CountingNet()
    stats = measure_latency(net, _obs(), warmup=3, iters=11)
    assert net.calls == 3 + 11
    assert stats["n_iters"] == 11
    assert 0.0 <= stats["p50_ms"] <= stats["p95_ms"]
    assert stats["mean_ms"] >= 0.0


@pytest.mark.parametrize(("warmup", "iters"), [(-1, 10), (1, 0)])
def test_measure_latency_rejects_bad_budget(warmup, iters):
    with pytest.raises(ValueError):
        measure_latency(_CountingNet(), _obs(), warmup=warmup, iters=iters)


def test_peak_memory_tracks_python_allocations():
    def run() -> None:
        _ = [bytearray(4096) for _ in range(256)]

    peak = peak_memory_bytes(run)
    assert isinstance(peak, int)
    assert peak >= 256 * 4096


def test_network_complexity_uses_sparse_support():
    phenotype = develop(VIABLE_Q, master_seed=MASTER_SEED, index=VIABLE_INDEX)
    assert phenotype.viable, phenotype.viability_reason
    net = DanioNet([phenotype], master_seed=MASTER_SEED)
    got = network_complexity(net)
    assert got["n_nodes"] == DEFAULT_NETWORK_CONFIG.max_nodes
    assert got["sensory_dim"] == DEFAULT_NETWORK_CONFIG.sensory_dim
    assert 0 < got["active_edges"] < got["n_nodes"] ** 2
    assert got["parameter_count"] == got["active_edges"]
    assert got["macs_theoretical"] < got["macs_implemented"]
