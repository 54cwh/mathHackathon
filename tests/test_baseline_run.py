"""Experiment C baseline 对照的守护（`实验与评价体系.md` §3.3）。

用合成的小轨迹 + 默认模型/竞技场配置跑通「构造 → BC 训练 → Arena → 指标/复杂度 → 跨模型
汇总 → 对照表 schema」，避免真实 600 步数据。`MODELS` 被临时收窄为两个基线以提速。
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from evogenesis.arena.config import ArenaConfig
from evogenesis.connectome.baselines import MLPPolicy
from evogenesis.core.config import LearningConfig, read_yaml
from evogenesis.core.io import write_jsonl
from evogenesis.evolution.config import load_evolution_config
from evogenesis.experiment import baseline_run
from evogenesis.experiment.baseline_run import comparison_payload, run_baseline_comparison
from evogenesis.experiment.learning_run import load_learning_config
from evogenesis.experiment.metrics import SCALAR_METRICS
from evogenesis.pipeline import ModelChainConfig, drive_arena_with_ids, load_model_chain_config

ROOT = Path(__file__).resolve().parents[1]
MODEL_CONFIG = ROOT / "configs" / "default_model.yaml"
EVOLUTION_CONFIG = ROOT / "configs" / "evolution.yaml"


def _write_trajectory(
    directory: Path, name: str, *, steps: int, experiment_id: str = "expC"
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


def _prepare(tmp_path: Path) -> tuple[Path, ModelChainConfig, LearningConfig]:
    trajectories = tmp_path / "trajectories"
    trajectories.mkdir()
    _write_trajectory(trajectories, "episode_ep0001.jsonl", steps=3)
    _write_trajectory(trajectories, "episode_ep0002.jsonl", steps=3)
    return trajectories, load_model_chain_config(MODEL_CONFIG), load_learning_config(MODEL_CONFIG)


def test_baseline_comparison_runs_and_matches_schema(tmp_path: Path, monkeypatch) -> None:
    trajectories, chain, learning_config = _prepare(tmp_path)
    monkeypatch.setattr(baseline_run, "MODELS", ("mlp", "gru"))
    result = run_baseline_comparison(
        experiment_id="expC",
        seeds=(1103,),
        chain=chain,
        arena_config=ArenaConfig(),
        learning_config=learning_config,
        evolution_config=load_evolution_config(EVOLUTION_CONFIG),
        trajectories_dir=trajectories,
        n_danio=2,
        steps=5,
    )
    assert [m["model"] for m in result.models] == ["mlp", "gru"]
    for model in result.models:
        assert model["metrics"] is not None
        for metric in SCALAR_METRICS:
            assert set(model["metrics"][metric]) == {"mean", "std", "n"}
        assert model["complexity"]["parameter_count"] > 0

    payload = comparison_payload(result, n_agents=1)
    schema = json.loads((ROOT / "schemas" / "baseline_comparison.schema.json").read_text("utf-8"))
    jsonschema.validate(payload, schema)


def test_drive_arena_with_ids_rejects_batch_mismatch(tmp_path: Path) -> None:
    _trajectories, chain, _learning_config = _prepare(tmp_path)
    net = MLPPolicy(master_seed=1103, index=0)
    with pytest.raises(ValueError, match="不一致"):
        drive_arena_with_ids(
            fish_ids=["expC:g0:fish0000", "expC:g0:fish0001"],
            genome_ids=["expC:g0:genome0000", "expC:g0:genome0001"],
            net=net,
            master_seed=1103,
            chain=chain,
            arena_config=ArenaConfig(),
            steps=1,
        )


def test_param_configs_loadable_for_experiment_c() -> None:
    # 冒烟：Experiment C 依赖的配置可解析（字段漂移由各模块守护测试负责）。
    assert read_yaml(MODEL_CONFIG)["network"]["sensory_dim"] == 12
    assert load_learning_config(MODEL_CONFIG).batch_size >= 1
