"""BC 生命周期学习编排测试（`experiment §3.8`；`learning §1–§6`；非遗传证据 `learning §4`）。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from evogenesis.arena.config import load_arena_config
from evogenesis.core.io import write_jsonl
from evogenesis.experiment import learning_run
from evogenesis.pipeline import load_model_chain_config

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_bc.py"
#: n=6 时 seed=23 有 1 个 viable 个体（seed=1103 全灭）；见 tests 注释与 review。
VIABLE_SEED = 23
STERILE_SEED = 1103
N = 6
STEPS = 8
N_EPISODES = 2
TOL = 1e-5


def _trajectories(dir_path: Path, *, n_episodes: int = N_EPISODES, steps: int = STEPS) -> Path:
    """合成 ``n_episodes`` 条合法轨迹（观测 ∈[0,1]、动作 2 维），落 ``episode_ep####.jsonl``。"""
    dir_path.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    for index in range(n_episodes):
        episode_id = f"ep{index + 1:04d}"
        header = {
            "record_type": "header",
            "schema_version": "1.0.0",
            "experiment_id": "exp-test",
            "episode_id": episode_id,
            "environment_id": "default",
            "generation": 0,
            "episode_seed": 1000 + index,
            "total_steps": steps,
            "terminated": False,
            "truncated": True,
        }
        records = [header]
        for step in range(steps):
            records.append(
                {
                    "record_type": "step",
                    "fish_id": "exp-test:g0000:fish0000",
                    "genome_id": "exp-test:g0000:genome0000",
                    "step": step,
                    "observation": [float(x) for x in rng.uniform(0.0, 1.0, size=12)],
                    "expert_action": [float(rng.uniform(-1.0, 1.0)), float(rng.uniform(0.0, 1.0))],
                }
            )
        write_jsonl(dir_path / f"episode_{episode_id}.jsonl", records)
    return dir_path


def _run(tmp_path: Path, *, seed: int = VIABLE_SEED, sign_constrained: bool = True):
    chain = load_model_chain_config(ROOT / "configs" / "default_model.yaml")
    arena_config = load_arena_config(ROOT / "configs" / "default_arena.yaml")
    learning_cfg = learning_run.load_learning_config(ROOT / "configs" / "default_model.yaml")
    learning_cfg = learning_cfg.model_copy(update={"mini_batch_updates": 2, "batch_size": 2})
    return learning_run.run_lifetime_learning(
        experiment_id="exp-test",
        master_seed=seed,
        chain=chain,
        arena_config=arena_config,
        learning_config=learning_cfg,
        trajectories_dir=_trajectories(tmp_path / "trajectories"),
        generation=0,
        n=N,
        steps=STEPS,
        sign_constrained=sign_constrained,
    )


def test_end_to_end_trains_and_records_pre_post(tmp_path):
    result = _run(tmp_path)
    assert result.n_viable == 1
    assert result.pre is not None and result.post is not None
    assert len(result.train_results) == 1 and len(result.reports) == 1
    assert result.train_results[0].n_updates == 2
    assert result.mean_final_loss > 0.0


def test_training_changes_delta_w_but_genome_is_unchanged(tmp_path):
    result = _run(tmp_path)
    # 训练确实改变 ΔW（非零）
    assert result.delta_w_norm[0] > 0.0
    # 非遗传证据：重新发育同 genome ⇒ ΔW 在数值容差内为 0、W⁰ 逐元素相同
    assert result.noninheritance is not None
    assert result.noninheritance.fresh_delta_w_max_abs < TOL
    assert result.noninheritance.weights0_max_abs_diff == 0.0


def test_unconstrained_ablation_runs_and_stays_noninherited(tmp_path):
    result = _run(tmp_path, sign_constrained=False)
    assert result.sign_constrained is False
    assert result.noninheritance is not None
    assert result.noninheritance.fresh_delta_w_max_abs < TOL
    assert result.noninheritance.weights0_max_abs_diff == 0.0


def test_no_viable_individuals_returns_without_training(tmp_path):
    result = _run(tmp_path, seed=STERILE_SEED)
    assert result.n_viable == 0
    assert result.pre is None and result.post is None
    assert result.train_results == () and result.noninheritance is None


def test_training_is_deterministic_for_same_seed(tmp_path):
    first = _run(tmp_path / "a")
    second = _run(tmp_path / "b")
    assert first.mean_final_loss == pytest.approx(second.mean_final_loss)
    assert first.delta_w_norm == pytest.approx(second.delta_w_norm)


def test_metric_rows_cover_pre_and_post(tmp_path):
    result = _run(tmp_path)
    arena_config = load_arena_config(ROOT / "configs" / "default_arena.yaml")
    rows = learning_run.metric_rows(
        result, seed=VIABLE_SEED, episode_steps=STEPS, arena_config=arena_config
    )
    assert {row["phase"] for row in rows} == {"pre", "post"}
    assert all(row["fish_id"] for row in rows)


def test_cli_smoke(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--experiment-id",
            "exp-bc-cli",
            "--seed",
            str(VIABLE_SEED),
            "--n",
            str(N),
            "--steps",
            str(STEPS),
            "--trajectories",
            str(N_EPISODES),
            "--out-root",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr
    run_dir = tmp_path / f"exp-bc-cli-s{VIABLE_SEED}"
    for name in ("metrics.csv", "learning.jsonl", "seed_summary.json", "learning_summary.json"):
        assert (run_dir / name).is_file(), name
