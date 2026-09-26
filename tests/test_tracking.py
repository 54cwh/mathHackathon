from pathlib import Path
from urllib.parse import urlparse

import mlflow

from evogenesis.core.tracking import RunTracker


def test_run_records_params_metrics_tags(tmp_path):
    tracker = RunTracker(tmp_path / "mlruns", "exp1", run_name="r1", tags={"git_commit": "abc"})
    with tracker:
        run_id = tracker.run_id
        tracker.log_params({"lr": 0.001, "optimizer": "adam"})
        tracker.log_metrics({"loss": 0.5, "accuracy": 0.8}, step=0)
        tracker.set_tags({"status_note": "smoke"})

    run = mlflow.get_run(run_id)
    assert run.data.params["lr"] == "0.001"
    assert run.data.params["optimizer"] == "adam"
    assert run.data.metrics["loss"] == 0.5
    assert run.data.metrics["accuracy"] == 0.8
    assert run.data.tags["git_commit"] == "abc"
    assert run.data.tags["status_note"] == "smoke"


def test_distinguishes_project_experiment_id_from_mlflow_id(tmp_path):
    tracker = RunTracker(tmp_path / "mlruns", "exp-stable")
    with tracker:
        run_id = tracker.run_id
        assert tracker.experiment_name == "exp-stable"
        assert tracker.mlflow_experiment_id != "exp-stable"
        assert mlflow.get_run(run_id).data.tags["experiment_id"] == "exp-stable"


def test_mlflow_experiment_id_before_start_raises(tmp_path):
    import pytest

    tracker = RunTracker(tmp_path / "mlruns", "exp5")
    with pytest.raises(RuntimeError):
        _ = tracker.mlflow_experiment_id


def test_context_manager_marks_failed(tmp_path):
    tracker = RunTracker(tmp_path / "mlruns", "exp2")
    try:
        with tracker:
            run_id = tracker.run_id
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert mlflow.get_run(run_id).info.status == "FAILED"


def test_run_id_before_start_raises(tmp_path):
    tracker = RunTracker(tmp_path / "mlruns", "exp3")
    import pytest

    with pytest.raises(RuntimeError):
        _ = tracker.run_id


def test_artifact_logged(tmp_path):
    artifact = tmp_path / "note.txt"
    artifact.write_text("hi", encoding="utf-8")
    tracker = RunTracker(tmp_path / "mlruns", "exp4")
    with tracker:
        tracker.log_artifact(artifact)
        run_id = tracker.run_id
    artifact_dir = Path(urlparse(mlflow.get_run(run_id).info.artifact_uri).path)
    assert (artifact_dir / "note.txt").is_file()
