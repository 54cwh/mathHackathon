"""run 终态登记到 MLflow 本地 file store（owner：`experiment/实验与评价体系.md` §5.1 / §5.2）。

字段对齐 `core.tracking.RunTracker`（MLflow Tracking）：`params`（seed / config / status）、
`tags`（`experiment_id` / `seed` / `environment` / `generation` 等）、`metrics`（`seed_summary`
标量）、`artifacts`（`metadata.json` / `seed_summary.json`）。生成的 `run_id` 回写
`metadata.json.mlflow_run_id`，作为 registry 血缘 `source_run_id`。store 默认 `results/mlruns/`，
现场离线 file store。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from evogenesis.core.tracking import RunTracker
from evogenesis.experiment.metrics import SCALAR_METRICS


def tracking_root_for(run_dir: Path) -> Path:
    """默认 store：`results/runs/<id>-s<seed>` 的祖父目录 `results/mlruns/`。"""
    return Path(run_dir).resolve().parent.parent / "mlruns"


def scalar_metrics(seed_summary_row: Mapping) -> dict[str, float]:
    """从 `seed_summary.json` 的一行取标量指标（`metrics.SCALAR_METRICS`，跳过 `None`）。"""
    return {
        name: float(seed_summary_row[name])
        for name in SCALAR_METRICS
        if seed_summary_row.get(name) is not None
    }


def track_run(
    run_dir: str | Path,
    *,
    status: str,
    metrics: Mapping[str, float] | None = None,
    tags: Mapping[str, object] | None = None,
    tracking_root: str | Path | None = None,
) -> str:
    """把一个已完成的 run 登记进 MLflow file store，返回 `run_id` 并回写 `metadata.json`。"""
    run_dir = Path(run_dir)
    metadata_path = run_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    experiment_id = str(metadata["experiment_id"])
    seed = int(metadata["seed"])
    root = Path(tracking_root) if tracking_root is not None else tracking_root_for(run_dir)

    run_tags = {
        "experiment_id": experiment_id,
        "seed": str(seed),
        "config": str(metadata.get("config", "")),
        "status": status,
    }
    if tags:
        run_tags.update({key: str(value) for key, value in tags.items()})

    tracker = RunTracker(root, experiment_id, run_name=f"s{seed}", tags=run_tags).start()
    try:
        tracker.log_params({"seed": seed, "config": metadata.get("config"), "status": status})
        if metrics:
            tracker.log_metrics({k: float(v) for k, v in metrics.items() if v is not None})
        for name in ("metadata.json", "seed_summary.json"):
            artifact = run_dir / name
            if artifact.is_file():
                tracker.log_artifact(artifact)
        run_id = tracker.run_id
    finally:
        tracker.end("FINISHED")

    metadata["mlflow_run_id"] = run_id
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return run_id


__all__ = ["scalar_metrics", "track_run", "tracking_root_for"]
