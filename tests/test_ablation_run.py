"""Experiment D 消融对照的守护（`实验与评价体系.md` §3.4）。

用合成小轨迹 + 小种群跑通「单变量覆盖 → 架构臂/BC 臂 → 指标/复杂度/学习量 → 跨 seed 汇总 →
对照表 schema」，避免真实 600 步数据。seed 2207 的首个 viable 个体 index=4，故 `n=5` 即可。
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from evogenesis.arena.config import ArenaConfig
from evogenesis.core.config import LearningConfig, read_yaml
from evogenesis.core.io import write_jsonl
from evogenesis.evolution.config import load_evolution_config
from evogenesis.experiment.ablation_run import (
    ARMS,
    active_edge_efficiency,
    arm_overrides,
    comparison_payload,
    run_ablation_comparison,
)
from evogenesis.experiment.learning_run import load_learning_config

ROOT = Path(__file__).resolve().parents[1]
MODEL_CONFIG = ROOT / "configs" / "default_model.yaml"
EVOLUTION_CONFIG = ROOT / "configs" / "evolution.yaml"
SEED = 2207


def _write_trajectory(
    directory: Path, name: str, *, steps: int, experiment_id: str = "expD"
) -> None:
    header = {
        "record_type": "header",
        "schema_version": "1.1.0",
        "experiment_id": experiment_id,
        "episode_id": name.removesuffix(".jsonl").removeprefix("episode_"),
        "environment_id": "default",
        "generation": 0,
        "episode_seed": 1,
        "total_steps": steps,
        "terminated": False,
        "truncated": True,
    }
    rows = [
        {
            "record_type": "step",
            "fish_id": f"{experiment_id}:g0:fish0000",
            "genome_id": f"{experiment_id}:g0:genome0000",
            "step": step,
            "observation": [0.0] * 12,
            "expert_action": [0.0, 0.5],
        }
        for step in range(steps)
    ]
    write_jsonl(directory / name, [header, *rows])


def _prepare(tmp_path: Path) -> tuple[Path, LearningConfig]:
    trajectories = tmp_path / "trajectories"
    trajectories.mkdir()
    _write_trajectory(trajectories, "episode_ep0001.jsonl", steps=3)
    _write_trajectory(trajectories, "episode_ep0002.jsonl", steps=3)
    return trajectories, load_learning_config(MODEL_CONFIG)


def test_arm_overrides_change_single_variable() -> None:
    assert arm_overrides("full", 5.5) is None
    assert arm_overrides("tau_homo", 5.5) == {"connectome": {"tau_min": 5.5, "tau_max": 5.5}}
    assert arm_overrides("no_wiring_cost", 5.5) == {"connectome": {"distance_lambda": 0.0}}
    assert arm_overrides("bc_dale", 5.5) is None
    with pytest.raises(ValueError, match="未知消融臂"):
        arm_overrides("nope", 5.5)


def test_active_edge_efficiency_definition() -> None:
    assert active_edge_efficiency(2.0, 4, 5) == pytest.approx(2.0 / 20)
    assert active_edge_efficiency(2.0, 0, 5) is None


def test_ablation_comparison_runs_and_matches_schema(tmp_path: Path) -> None:
    trajectories, learning_config = _prepare(tmp_path)
    result = run_ablation_comparison(
        experiment_id="expD",
        seeds=(SEED,),
        model_config_path=MODEL_CONFIG,
        arena_config=ArenaConfig(),
        learning_config=learning_config,
        evolution_config=load_evolution_config(EVOLUTION_CONFIG),
        trajectories_dir=trajectories,
        tau=5.5,
        n=5,
        steps=5,
    )
    assert [arm["arm"] for arm in result.arms] == list(ARMS)
    by_arm = {arm["arm"]: arm for arm in result.arms}
    for name in ("full", "tau_homo", "no_wiring_cost"):
        arm = by_arm[name]
        assert arm["metrics"] is not None
        assert arm["complexity"]["parameter_count"] > 0
        assert "active_edge_efficiency" in arm["metrics"]
    for name in ("bc_dale", "bc_no_dale"):
        arm = by_arm[name]
        assert arm["metrics"] is not None
        assert "flip_rate" in arm["metrics"]
        assert arm["learning"]["n_updates"] > 0

    payload = comparison_payload(result)
    schema = json.loads((ROOT / "schemas" / "ablation_comparison.schema.json").read_text("utf-8"))
    jsonschema.validate(payload, schema)


def test_ablation_comparison_skips_bc_without_trajectories(tmp_path: Path) -> None:
    del tmp_path
    result = run_ablation_comparison(
        experiment_id="expD",
        seeds=(SEED,),
        model_config_path=MODEL_CONFIG,
        arena_config=ArenaConfig(),
        learning_config=load_learning_config(MODEL_CONFIG),
        evolution_config=load_evolution_config(EVOLUTION_CONFIG),
        trajectories_dir=None,
        n=5,
        steps=3,
    )
    by_arm = {arm["arm"]: arm for arm in result.arms}
    assert by_arm["bc_dale"]["metrics"] is None
    assert by_arm["bc_dale"]["note"]
    assert by_arm["full"]["metrics"] is not None


def test_param_configs_loadable_for_experiment_d() -> None:
    assert read_yaml(MODEL_CONFIG)["network"]["sensory_dim"] == 12
    assert load_learning_config(MODEL_CONFIG).mini_batch_updates >= 1
