"""run 目录布局（owner：`experiment/实验与评价体系.md` §5.1）。

``create_run_dir`` 是 ``results/runs/<experiment_id>-s<seed>/`` 的**唯一生产者**：创建目录并
写入 ``metadata.json`` / ``config_snapshot/`` / ``seed.txt`` / ``git_commit.txt`` / ``logs.jsonl``
（Arena 型配置另写 ``arena_config_resolved.json``）。``metadata.json`` 含 ``mlflow_run_id``
（初始 ``null``，run 终态由 ``tracking_run.track_run`` 回写）。``scripts/`` 下四个入口脚本
（``run_experiment.py`` / ``run_arena.py`` / ``run_chain.py`` / ``run_evolution.py``）
一律经此建目录，故布局与唯一性语义只有一份实现。运行日志经 ``core.logging`` 落 ``logs.jsonl``。
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from evogenesis.arena.config import (
    ARENA_SECTIONS,
    arena_config_snapshot,
    load_arena_config,
)
from evogenesis.core.config import read_yaml
from evogenesis.core.io import now_iso
from evogenesis.core.logging import configure_logging, get_logger

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_ROOT = _REPO_ROOT / "results" / "runs"


def git_commit(repo_root: Path = _REPO_ROOT) -> str:
    """当前 HEAD 短哈希；git 不可用时返回 ``"unknown"``。"""
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def update_run_status(run_dir: str | Path, status: str) -> None:
    """改写 run 的 ``metadata.json.status``（入口脚本/代循环在结束时置终态），并记一条运行日志。"""
    run_dir = Path(run_dir)
    metadata_path = run_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["status"] = status
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    configure_logging(
        run_dir / "logs.jsonl",
        resource={
            "experiment_id": metadata.get("experiment_id", ""),
            "seed": metadata.get("seed", ""),
        },
    )
    get_logger(__name__).info("run_status", status=status)


def create_run_dir(
    *,
    experiment_id: str,
    seed: int,
    config_path: str | Path,
    overrides: Mapping[str, object] | None = None,
    out_root: str | Path | None = None,
    extra_configs: Sequence[str | Path] = (),
) -> Path:
    """建 run 目录并写入元数据，返回目录路径。

    目录名 ``<experiment_id>-s<seed>``；**已存在即抛 `FileExistsError`**（同一
    ``experiment_id + seed`` 唯一）。``overrides`` 仅用于解析实际生效的 Arena 快照。
    ``extra_configs`` 为**附加输入配置**（如 model/evolution/experiment），一并复制进
    ``config_snapshot/`` 并登记于 ``metadata.json.extras``，使 run 自包含可复现。
    """
    path = Path(config_path)
    if not path.is_absolute():
        path = _REPO_ROOT / path
    if not path.is_file():
        raise FileNotFoundError(f"配置不存在: {path}")

    # 各 configs/*.yaml 的节 schema 不同，这里只做 YAML 解析校验，不套用单一模型。
    raw = read_yaml(path)

    # run 必须固定到「实际生效的取值」，而不只是固定文件：原始副本会与解析值漂移
    # （默认值 / env / overrides）。Arena 型配置（顶层键 ⊆ ARENA_SECTIONS）额外落解析快照。
    arena_resolved = None
    if raw and set(raw) <= set(ARENA_SECTIONS):
        arena_resolved = arena_config_snapshot(load_arena_config(path, overrides=overrides))

    base = Path(out_root) if out_root is not None else DEFAULT_OUT_ROOT
    run_dir = base / f"{experiment_id}-s{seed}"
    if run_dir.exists():
        raise FileExistsError(f"run 目录已存在（同一 experiment_id+seed 需唯一）: {run_dir}")

    (run_dir / "config_snapshot").mkdir(parents=True)
    (run_dir / "config_snapshot" / path.name).write_text(
        path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    extras: list[str] = []
    for extra in extra_configs:
        extra_path = Path(extra)
        if not extra_path.is_absolute():
            extra_path = _REPO_ROOT / extra_path
        if not extra_path.is_file():
            raise FileNotFoundError(f"附加配置不存在: {extra_path}")
        (run_dir / "config_snapshot" / extra_path.name).write_text(
            extra_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        extras.append(
            str(extra_path.relative_to(_REPO_ROOT))
            if extra_path.is_relative_to(_REPO_ROOT)
            else str(extra_path)
        )
    (run_dir / "seed.txt").write_text(f"{seed}\n", encoding="utf-8")
    if arena_resolved is not None:
        (run_dir / "arena_config_resolved.json").write_text(
            json.dumps(arena_resolved, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    (run_dir / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    metadata = {
        "experiment_id": experiment_id,
        "seed": seed,
        "config": str(path.relative_to(_REPO_ROOT))
        if path.is_relative_to(_REPO_ROOT)
        else str(path),
        "status": "created",
        "arena_config_resolved": arena_resolved is not None,
        "extras": extras,
        "created_at": now_iso(),
        "mlflow_run_id": None,
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    configure_logging(
        run_dir / "logs.jsonl", resource={"experiment_id": experiment_id, "seed": seed}
    )
    get_logger(__name__).info(
        "run_created",
        config=metadata["config"],
        arena_config_resolved=metadata["arena_config_resolved"],
    )
    return run_dir
