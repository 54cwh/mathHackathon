"""run / 逐代产物的 schema 守护（`experiment §5.2`、`代循环编排.md §5`）。

用生产者函数（`run_artifacts` / `metrics`）造出的真实行结构逐条过各自 schema；另校验
`metadata.json` 与跨 seed 汇总的样例。避免 subprocess 写仓库 `results/`。
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from evogenesis.experiment.metrics import aggregate_by_seed, episode_metrics, summarise_over_seeds
from evogenesis.experiment.run_artifacts import episode_row, population_record

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "schemas"


def _schema(name: str) -> dict:
    return json.loads((S / name).read_text(encoding="utf-8"))


def _per_fish() -> dict:
    return {
        "survival_steps": 20,
        "captures": 1,
        "capture_attempts": 2,
        "encounters": 5,
        "predator_encounters": 1,
        "escape_successes": 0,
        "collisions": 0,
        "energy_trajectory": [1.0, 0.9],
        "size_trajectory": [1.0, 1.1],
        "motor_commands": [(0.0, 0.5)] * 20,
    }


def test_population_record_passes_schema():
    rec = _per_fish()
    record = population_record(1103, "exp:g0:fish0000", rec)
    jsonschema.validate(record, _schema("population.schema.json"))


def test_episode_row_passes_schema():
    jsonschema.validate(
        episode_row(1103, [], {"exp:g0:fish0000": _per_fish()}, 20, 0.1),
        _schema("episodes.schema.json"),
    )


def test_metrics_and_seed_summary_pass_schema():
    rows = [
        {
            "seed": 1103,
            "fish_id": "exp:g0:fish0000",
            **episode_metrics(_per_fish(), episode_steps=20, e_max=1.0),
        }
    ]
    summary = aggregate_by_seed(rows)
    jsonschema.validate(summary, _schema("seed_summary.schema.json"))


def test_run_table_summary_passes_schema():
    rows = [
        {"seed": 1103, "n_individuals": 12, "survival": 0.5, "composite_fitness": None},
    ]
    table = {
        "experiment_id": "exp-x",
        "environment": "default",
        "emit_behavior_trace": False,
        "seeds": [1103],
        "steps": 20,
        "n_individuals": 12,
        "per_metric": summarise_over_seeds(rows, metrics=("survival", "composite_fitness")),
    }
    jsonschema.validate(table, _schema("run_table_summary.schema.json"))


def test_run_metadata_passes_schema():
    metadata = {
        "experiment_id": "exp-x",
        "seed": 1103,
        "config": "configs/default_arena.yaml",
        "status": "completed",
        "arena_config_resolved": True,
        "extras": ["configs/default_model.yaml"],
        "created_at": "2026-09-26T00:00:00Z",
    }
    jsonschema.validate(metadata, _schema("run_metadata.schema.json"))


def test_fitness_and_evolution_line_pass_schema():
    jsonschema.validate(
        {
            "generation": 0,
            "genome_id": "exp:g0:genome0000",
            "fish_id": None,
            "viable": False,
            "failure_reason": "missing_fate:motor",
            "fitness": 0.0,
        },
        _schema("fitness.schema.json"),
    )
    jsonschema.validate(
        {
            "generation": 0,
            "n_individuals": 8,
            "n_viable": 0,
            "fitness_mean": None,
            "fitness_std": None,
            "bottleneck": True,
            "event": "evolution.population_bottleneck",
        },
        _schema("evolution.schema.json"),
    )


def test_learning_artifacts_pass_schema():
    record = {
        "fish_id": "exp:g0:fish0000",
        "genome_id": "exp:g0:genome0000",
        "sign_constrained": True,
        "final_loss": 0.25,
        "n_updates": 20,
        "epochs": 6.4,
        "coverage_steps": 6.4,
        "visible_steps": 768000,
        "flip_rate": 0.1,
        "spectral_radius": 0.9,
        "delta_w_norm": 0.01,
        "loss_weight_omega": 0.4,
        "loss_weight_v": 1.6,
    }
    jsonschema.validate(record, _schema("learning.schema.json"))
    summary = {
        "seed": 1103,
        "sign_constrained": True,
        "n_individuals": 12,
        "n_viable": 2,
        "mean_final_loss": 0.25,
        "mean_epochs": 6.4,
        "mean_delta_w_norm": 0.015,
        "noninheritance": {"fresh_delta_w_max_abs": 0.0, "weights0_max_abs_diff": 0.0},
    }
    jsonschema.validate(summary, _schema("learning_summary.schema.json"))
