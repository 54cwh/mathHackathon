"""运行记录（磁盘 run）只读接口 —— Evolution Dashboard 的数据源（`API接口.md` §2.4）。

为什么按**磁盘目录**而不是内存实验表：`results/runs/<run_id>/` 是 runlayout 的落盘契约，
重启进程也不丢（内存的实验表会丢）。于是 `pilot20-s1103` 这类非本进程产生的 run 也能被前端看到。

范围：只读、只暴露 `results/runs/` 下**一层**目录里的既有产物（`metadata.json` /
`evolution.jsonl` / `generations/*/fitness.jsonl`）；不写入、不新建、不递归出该目录。
路径安全：`run_id` 必须是单个路径段（禁 `/`、`..`），解析后再断言仍在该根目录之内。
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from evogenesis.api.schemas import (
    Page,
    RunEvolution,
    RunFitnessDistribution,
    RunSummary,
)
from evogenesis.experiment.runlayout import DEFAULT_OUT_ROOT

router = APIRouter(prefix="/v1")

_RUNS_ROOT = Path(DEFAULT_OUT_ROOT)
#: `evolution.jsonl` 的行 = 一代；每代一行，字段见 `experiment §3.4`/`代循环编排.md`。
_EVOLUTION_FILE = "evolution.jsonl"
_FITNESS_TEMPLATE = "generations/g{generation:04d}/fitness.jsonl"


def _run_dir(run_id: str) -> Path:
    """`run_id` -> 目录；非法或不安全一律 404（不泄露路径细节）。"""
    if not run_id or "/" in run_id or "\\" in run_id or run_id in {".", ".."}:
        raise HTTPException(status_code=404, detail=f"run {run_id!r} not found")
    root = _RUNS_ROOT.resolve()
    candidate = (root / run_id).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_dir():
        raise HTTPException(status_code=404, detail=f"run {run_id!r} not found")
    return candidate


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _count_lines(path: Path) -> int | None:
    try:
        with path.open(encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    except OSError:
        return None


@router.get("/runs", response_model=Page[RunSummary])
def list_runs(limit: int = 20, cursor: str | None = None) -> Page[RunSummary]:
    """列出 `results/runs/` 下的 run（按 `created_at` 降序，其次目录名）。"""
    if not _RUNS_ROOT.is_dir():
        return Page[RunSummary](items=[], next_cursor=None)

    rows: list[RunSummary] = []
    for entry in sorted(_RUNS_ROOT.iterdir()):
        if not entry.is_dir():
            continue
        meta = _read_json(entry / "metadata.json") or {}
        rows.append(
            RunSummary(
                run_id=entry.name,
                experiment_id=str(meta.get("experiment_id") or entry.name),
                seed=int(meta["seed"]) if isinstance(meta.get("seed"), int) else None,
                status=str(meta.get("status") or "unknown"),
                created_at=str(meta.get("created_at") or ""),
                generations=_count_lines(entry / _EVOLUTION_FILE),
            )
        )

    rows.sort(key=lambda row: (row.created_at, row.run_id), reverse=True)
    try:
        start = int(cursor) if cursor else 0
    except ValueError:
        raise HTTPException(status_code=422, detail=f"invalid cursor: {cursor!r}") from None
    if start < 0:
        raise HTTPException(status_code=422, detail=f"invalid cursor: {cursor!r}")
    page = rows[start : start + limit]
    next_cursor = str(start + limit) if start + limit < len(rows) else None
    return Page[RunSummary](items=page, next_cursor=next_cursor)


@router.get("/runs/{run_id}/evolution", response_model=RunEvolution)
def run_evolution(run_id: str) -> RunEvolution:
    """该 run 的逐代指标（`evolution.jsonl`）+ 逐个体 fitness（用于分布直方图）。

    逐代行字段与 `evolution.jsonl` 一致（原样透传 `extra` 字段，避免与 producer 漂移）。
    逐个体 fitness 取 `generations/g<NNNN>/fitness.jsonl` 里数值型 `fitness`（缺失则空表）。
    """
    run_dir = _run_dir(run_id)
    generations: list[dict] = []
    evolution_path = run_dir / _EVOLUTION_FILE
    if evolution_path.is_file():
        try:
            with evolution_path.open(encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        generations.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue  # 单行坏掉不整段失败（run 可能是被中断的）
        except OSError:
            raise HTTPException(status_code=500, detail=f"cannot read {_EVOLUTION_FILE}") from None

    fitness: list[RunFitnessDistribution] = []
    for row in generations:
        generation = row.get("generation")
        if not isinstance(generation, int):
            continue
        path = run_dir / _FITNESS_TEMPLATE.format(generation=generation)
        if not path.is_file():
            continue
        values: list[float] = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                value = record.get("fitness")
                if isinstance(value, (int, float)):
                    values.append(float(value))
        fitness.append(RunFitnessDistribution(generation=generation, values=values))

    meta = _read_json(run_dir / "metadata.json") or {}
    return RunEvolution(
        run_id=run_id,
        experiment_id=str(meta.get("experiment_id") or run_id),
        seed=int(meta["seed"]) if isinstance(meta.get("seed"), int) else None,
        generations=generations,
        fitness=fitness,
    )
