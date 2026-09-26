"""run 终态 MLflow 登记与运行日志接线（`experiment/tracking_run.py` + `runlayout`）。

离线 file store：本测试断言 `create_run_dir` 落 `logs.jsonl`（run_created）、`track_run`
回写 `metadata.json.mlflow_run_id` 并建 `mlruns/`；store 走 `tmp_path`，不污染仓库。
"""

from __future__ import annotations

import json
from pathlib import Path

from evogenesis.experiment.runlayout import create_run_dir
from evogenesis.experiment.tracking_run import scalar_metrics, track_run


def _make_run(tmp_path: Path) -> Path:
    cfg = tmp_path / "non_arena.yaml"
    cfg.write_text("x: 1\n", encoding="utf-8")
    return create_run_dir(
        experiment_id="exp-track", seed=7, config_path=cfg, out_root=tmp_path / "runs"
    )


def test_create_run_dir_wires_logging(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path)
    log_path = run_dir / "logs.jsonl"
    assert log_path.is_file()
    first = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
    assert first["event"] == "run_created"
    assert first["experiment_id"] == "exp-track"
    assert "severity_text" in first and "timestamp" in first


def test_track_run_writes_mlflow_run_id(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path)
    (run_dir / "seed_summary.json").write_text(
        json.dumps({"survival": 0.5, "capture_rate": None}, indent=2), encoding="utf-8"
    )
    store = tmp_path / "mlruns"
    run_id = track_run(run_dir, status="completed", metrics={"survival": 0.5}, tracking_root=store)
    assert run_id
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["mlflow_run_id"] == run_id
    assert store.is_dir()
    assert list(store.rglob("meta.yaml"))


def test_scalar_metrics_filters_none() -> None:
    assert scalar_metrics({"survival": 0.5, "capture_rate": None}) == {"survival": 0.5}
