"""Experiment E（删边退化）契约守护（`experiment §3.5`，草案待确认）。"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import numpy as np
import pytest
import torch
from test_learning_common import make_net

from evogenesis.arena.config import load_arena_config
from evogenesis.experiment.robustness_run import (
    FRACTIONS,
    drop_edges,
    dropped_edge_count,
    run_robustness,
    table_path,
)
from evogenesis.pipeline import load_model_chain_config

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "robustness.schema.json").read_text(encoding="utf-8"))
#: 含 viable 个体的种子（n_danio=48 下首个 viable 在 index 11），用于集成守护
SEED_WITH_VIABLE = 250927


def test_dropped_edge_count_rounds_and_clamps():
    assert dropped_edge_count(100, 0.0) == 0
    assert dropped_edge_count(100, 0.05) == 5
    assert dropped_edge_count(100, 0.10) == 10
    assert dropped_edge_count(100, 0.20) == 20
    assert dropped_edge_count(3, 1.0) == 3
    with pytest.raises(ValueError):
        dropped_edge_count(10, 1.5)


def test_drop_edges_removes_exact_count_keeps_others_and_is_deterministic():
    net = make_net()
    n_edges_before = int(net.support.sum().item())
    weights0_before = net.weights0.clone()
    removed = drop_edges(net, 0.25, rng=np.random.default_rng(0))

    assert removed == dropped_edge_count(n_edges_before, 0.25)
    assert int(net.support.sum().item()) == n_edges_before - removed
    # 被删处有效权重与 ΔW 均为 0
    assert float(net.effective_weights[~net.support].abs().sum()) == 0.0
    assert float(net.delta_weights[~net.support].abs().sum()) == 0.0
    # 未删处 W⁰ 逐元素不变
    assert torch.equal(net.weights0[net.support], weights0_before[net.support])

    first = make_net()
    second = make_net()
    drop_edges(first, 0.25, rng=np.random.default_rng(7))
    drop_edges(second, 0.25, rng=np.random.default_rng(7))
    assert torch.equal(first.support, second.support)


def test_run_robustness_payload_matches_schema_and_conditions():
    chain = load_model_chain_config()
    arena_config = load_arena_config(ROOT / "configs" / "default_arena.yaml")
    payload = run_robustness(
        experiment_id="expE-test",
        seeds=(SEED_WITH_VIABLE,),
        chain=chain,
        arena_config=arena_config,
        n_danio=48,
        steps=120,
    )
    jsonschema.validate(payload, SCHEMA)

    assert payload["status"] == "confirmed"
    assert payload["fractions"] == list(FRACTIONS)
    assert payload["steps"] == 120
    entry = payload["per_seed"][str(SEED_WITH_VIABLE)]
    assert entry["substrate"] is not None, "该 seed 应有 viable 底物"
    conditions = {c["fraction"]: c for c in entry["conditions"]}
    assert set(conditions) == set(FRACTIONS)
    assert conditions[0.0]["n_removed"] == 0
    n_edges = entry["n_edges"]
    assert conditions[0.05]["n_removed"] == dropped_edge_count(n_edges, 0.05)
    # 行为发散（主指标）：对照恒 ~0，删边 > 0；聚合表含全部比例
    assert conditions[0.0]["divergence"]["mean_abs_omega"] == 0.0
    assert conditions[0.0]["divergence"]["mean_abs_v"] == 0.0
    assert conditions[0.2]["divergence"]["mean_abs_v"] > 0.0
    assert set(payload["behavior_divergence"]) == {"0", "0.05", "0.1", "0.2"}
    assert payload["behavior_divergence"]["0.2"]["mean_abs_v"]["n"] == 1
    # 退化量表不含量基线 0，含 0.05/0.1/0.2
    assert set(payload["degradation"]) == {"0.05", "0.1", "0.2"}
    assert payload["degradation"]["0.05"]["composite_fitness"]["n"] == 1


def test_table_path():
    assert table_path("expE-0001", ROOT / "results").name == "expE-0001_robustness.json"
