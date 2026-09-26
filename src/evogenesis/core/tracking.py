"""实验跟踪（core §0）。

字段对齐 **MLflow Tracking**（``run_id / experiment_id / status / start_time / end_time``
``/ metrics / params / tags / artifacts``），使用本地 file store，现场离线可用。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

import mlflow  # noqa: E402  (须在设置环境变量后导入)

_METRIC_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-./ ")


def _sanitize_metric_name(name: str) -> str:
    cleaned = "".join(c if c in _METRIC_CHARS else "_" for c in name)
    return cleaned[:250]


class RunTracker:
    """一次实验 run 的薄封装：本地 MLflow file store。"""

    def __init__(
        self,
        tracking_dir: str | Path,
        experiment_id: str,
        *,
        run_name: str | None = None,
        tags: Mapping[str, str] | None = None,
    ) -> None:
        self._tracking_dir = Path(tracking_dir)
        self._experiment_id = experiment_id
        self._run_name = run_name
        self._tags = dict(tags or {})
        self._run: Any = None

    @property
    def experiment_id(self) -> str:
        return self._experiment_id

    @property
    def run_id(self) -> str:
        if self._run is None:
            raise RuntimeError("run 尚未 start()")
        return self._run.info.run_id

    def start(self) -> RunTracker:
        self._tracking_dir.mkdir(parents=True, exist_ok=True)
        mlflow.set_tracking_uri(self._tracking_dir.resolve().as_uri())
        if mlflow.get_experiment_by_name(self._experiment_id) is None:
            artifact_uri = (self._tracking_dir / "artifacts").resolve().as_uri()
            mlflow.create_experiment(self._experiment_id, artifact_location=artifact_uri)
        mlflow.set_experiment(self._experiment_id)
        self._run = mlflow.start_run(run_name=self._run_name, tags=self._tags or None)
        return self

    def log_params(self, params: Mapping[str, Any]) -> None:
        mlflow.log_params({k: str(v) for k, v in params.items()})

    def log_metrics(self, metrics: Mapping[str, float], step: int | None = None) -> None:
        mlflow.log_metrics(
            {_sanitize_metric_name(k): float(v) for k, v in metrics.items()}, step=step
        )

    def set_tags(self, tags: Mapping[str, str]) -> None:
        mlflow.set_tags(dict(tags))

    def log_artifact(self, path: str | Path) -> None:
        mlflow.log_artifact(str(path))

    def end(self, status: str = "FINISHED") -> None:
        if self._run is not None:
            mlflow.end_run(status=status)
            self._run = None

    def __enter__(self) -> RunTracker:
        return self.start()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.end("FAILED" if exc_type is not None else "FINISHED")
