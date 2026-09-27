"""环境选择实验（Experiment F）端点（`API接口.md` §2.2）。

`POST /v1/environmental-selections` 启动一次**环境选择实验**（`experiment §3.6`：`seeds` ×
`generations` 代 × `environment`，48 个体）。每个 seed 复用 `run_evolution`
（`experiment/evolution_run.py`），产出一个 **`ExperimentRun`** 目录
`results/runs/<experiment_id>-s<seed>/`（run 目录布局 owner = `experiment/runlayout.py`）。
请求即时返回 `202` + `job_id`，随后后台线程执行；
`GET /v1/jobs/{job_id}` 轮询进度，`POST /v1/jobs/{job_id}/cancel` 在 seed 边界协作式取消。

> **仅环境选择（Experiment F）**：A–E / BC / penetrance 等其余协议**不在此资源**下。通用实验资源
> `/v1/experiments` 未实现（无消费者、协议未定）；本资源是**其唯一已落地的协议实例**。

本模块只做**编排 + 任务登记**：仿真/评估/演化算法归 `experiment` / `pipeline` / `evolution`，
不在此定义。实验与任务均为进程内内存态（无持久化；重启即失，`API接口.md` §7.1）。
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import APIRouter, HTTPException

from evogenesis.api import ws as ws_hub
from evogenesis.api.schemas import (
    EnvironmentalSelectionDetail,
    EnvironmentalSelectionLaunch,
    EnvironmentalSelectionSummary,
    JobStatus,
    JobStatusKind,
    Page,
    Problem,
)
from evogenesis.arena.config import load_arena_config
from evogenesis.evolution.config import load_evolution_config
from evogenesis.experiment import runlayout
from evogenesis.experiment.config import DEFAULT_EXPERIMENT_CONFIG_PATH
from evogenesis.experiment.environments import load_environment
from evogenesis.experiment.evolution_run import run_evolution
from evogenesis.experiment.tracking_run import track_run
from evogenesis.pipeline import load_model_chain_config

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MODEL = _REPO_ROOT / "configs" / "default_model.yaml"
_DEFAULT_ARENA = _REPO_ROOT / "configs" / "default_arena.yaml"
_DEFAULT_EVOLUTION = _REPO_ROOT / "configs" / "evolution.yaml"
_OUT_ROOT = _REPO_ROOT / "results" / "runs"
_TRACKING_ROOT = _REPO_ROOT / "results" / "mlruns"


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(_REPO_ROOT))
    except ValueError:
        return str(path)


@dataclass
class _Job:
    job_id: str
    status: JobStatusKind = "queued"
    progress: float = 0.0
    detail: dict = field(default_factory=dict)
    cancelled: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class _Selection:
    experiment_id: str
    name: str
    seeds: list[int]
    environment: str
    generations: int
    #: 演示用覆盖：`population_size` 覆盖 evolution 配置；`steps` 覆盖每代 episode 步数。
    #: None ⇒ 用 configs 里的正式规模。
    population_size: int | None = None
    steps: int | None = None
    job_id: str = ""
    status: JobStatusKind = "queued"
    runs: list[dict] = field(default_factory=list)


_selections: dict[str, _Selection] = {}
_jobs: dict[str, _Job] = {}


def _job_status(job: _Job) -> JobStatus:
    return JobStatus(job_id=job.job_id, status=job.status, progress=job.progress, detail=job.detail)


def _emit(job: _Job) -> None:
    """广播 `job.progress`（`API与系统工程.md` §5）。"""
    ws_hub.publish_job_progress(job.job_id, job.status, job.progress)


def _run_one(
    selection: _Selection, seed: int, *, on_seed_progress: Callable[[float], None] | None = None
) -> dict:
    """跑单个 seed 的环境选择实验，返回该 `ExperimentRun` 的摘要。"""
    overrides = (
        None if selection.environment == "default" else load_environment(selection.environment)
    )
    chain = load_model_chain_config(_DEFAULT_MODEL)
    arena_config = load_arena_config(_DEFAULT_ARENA, overrides=overrides)
    evolution_config = load_evolution_config(_DEFAULT_EVOLUTION)
    if selection.population_size is not None:
        evolution_config = evolution_config.model_copy(
            update={"population_size": selection.population_size}
        )
    run_dir = runlayout.create_run_dir(
        experiment_id=selection.experiment_id,
        seed=seed,
        config_path=str(_DEFAULT_ARENA),
        overrides=overrides,
        out_root=_OUT_ROOT,
        extra_configs=(_DEFAULT_MODEL, _DEFAULT_EVOLUTION, DEFAULT_EXPERIMENT_CONFIG_PATH),
    )
    result = run_evolution(
        experiment_id=selection.experiment_id,
        master_seed=seed,
        generations=selection.generations,
        chain=chain,
        arena_config=arena_config,
        evolution_config=evolution_config,
        run_dir=run_dir,
        environment_id=selection.environment,
        steps=selection.steps,
        on_seed_progress=on_seed_progress,
    )
    last = result.summaries[-1] if result.summaries else None
    metrics: dict[str, float] = {}
    if last is not None:
        for key, value in (
            ("fitness_mean", last.fitness_mean),
            ("fitness_std", last.fitness_std),
            ("n_viable", last.n_viable),
        ):
            if value is not None:
                metrics[key] = float(value)
    track_run(
        run_dir,
        status="bottleneck" if result.bottleneck else "completed",
        metrics=metrics,
        tags={"generations_run": result.generations_run},
        tracking_root=_TRACKING_ROOT,
    )
    return {
        "seed": seed,
        "run_dir": _rel(run_dir),
        "generations_run": result.generations_run,
        "bottleneck": result.bottleneck,
    }


def _worker(selection: _Selection, job: _Job) -> None:
    with job.lock:
        if job.cancelled:
            job.status = "cancelled"
            selection.status = "cancelled"
            _emit(job)
            return
        job.status = "running"
        selection.status = "running"
        _emit(job)
    try:
        total = max(1, len(selection.seeds))
        for index, seed in enumerate(selection.seeds, start=1):
            with job.lock:
                if job.cancelled:
                    job.status = "cancelled"
                    selection.status = "cancelled"
                    _emit(job)
                    return
            total_seeds = max(1, len(selection.seeds))
            seed_index = selection.seeds.index(seed) + 1

            def _seed_progress(
                frac: float, index: int = seed_index, total: int = total_seeds
            ) -> None:
                """把"第 index 个种子内的 0→1 进度"映射成作业总进度并广播。"""
                with job.lock:
                    job.progress = ((index - 1) + max(0.0, min(1.0, frac))) / total
                    _emit(job)

            info = _run_one(selection, seed, on_seed_progress=_seed_progress)
            with job.lock:
                selection.runs.append(info)
                job.progress = index / total
                if job.cancelled:
                    job.status = "cancelled"
                    selection.status = "cancelled"
                    _emit(job)
                    return
                _emit(job)
        with job.lock:
            job.status = "done"
            selection.status = "done"
            job.progress = 1.0
            _emit(job)
    except Exception as exc:  # noqa: BLE001 - 后台任务：失败须落到 job 状态而非进程
        with job.lock:
            job.status = "failed"
            selection.status = "failed"
            job.detail = {"error": str(exc)}
            _emit(job)


router = APIRouter(
    prefix="/v1",
    responses={404: {"model": Problem, "description": "实验 / 任务不存在"}},
)


def launch(
    *,
    name: str,
    seeds: list[int],
    environment: str,
    generations: int,
    population_size: int | None = None,
    steps: int | None = None,
) -> tuple[str, JobStatus]:
    """登记一次环境选择实验并起后台线程，返回 `(experiment_id, JobStatus)`。

    供本模块 `POST /v1/environmental-selections` 与会话内演化
    `POST /v1/sessions/{id}/evolutions`（`API接口.md` §2.3）共用。
    """
    experiment_id = f"exp_{uuid.uuid4().hex[:12]}"
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    selection = _Selection(
        experiment_id=experiment_id,
        name=name,
        seeds=list(seeds),
        environment=environment,
        generations=generations,
        population_size=population_size,
        steps=steps,
        job_id=job_id,
    )
    job = _Job(job_id=job_id)
    _selections[experiment_id] = selection
    _jobs[job_id] = job
    threading.Thread(target=_worker, args=(selection, job), daemon=True).start()
    return experiment_id, _job_status(job)


@router.post("/environmental-selections", status_code=202, response_model=JobStatus)
def start_environmental_selection(launch_request: EnvironmentalSelectionLaunch) -> JobStatus:
    _, status = launch(
        name=launch_request.name,
        seeds=launch_request.seeds,
        environment=launch_request.environment,
        generations=launch_request.generations,
        population_size=launch_request.population_size,
        steps=launch_request.steps,
    )
    return status


@router.get("/environmental-selections", response_model=Page[EnvironmentalSelectionSummary])
def list_environmental_selections(
    limit: int = 20, cursor: str | None = None
) -> Page[EnvironmentalSelectionSummary]:
    items = [
        EnvironmentalSelectionSummary(
            experiment_id=s.experiment_id, name=s.name, status=s.status, seeds=s.seeds
        )
        for s in sorted(_selections.values(), key=lambda x: x.experiment_id)
    ]
    if cursor:
        try:
            start = int(cursor)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"invalid cursor: {cursor!r}") from None
    else:
        start = 0
    if start < 0:
        raise HTTPException(status_code=422, detail=f"invalid cursor: {cursor!r}")
    page = items[start : start + limit]
    next_cursor = str(start + limit) if start + limit < len(items) else None
    return Page[EnvironmentalSelectionSummary](items=page, next_cursor=next_cursor)


def _get_selection(experiment_id: str) -> _Selection:
    selection = _selections.get(experiment_id)
    if selection is None:
        raise HTTPException(status_code=404, detail=f"experiment {experiment_id} not found")
    return selection


@router.get(
    "/environmental-selections/{experiment_id}", response_model=EnvironmentalSelectionDetail
)
def get_environmental_selection(experiment_id: str) -> EnvironmentalSelectionDetail:
    selection = _get_selection(experiment_id)
    return EnvironmentalSelectionDetail(
        experiment_id=selection.experiment_id,
        name=selection.name,
        status=selection.status,
        seeds=selection.seeds,
        results={
            "environment": selection.environment,
            "generations": selection.generations,
            "job_id": selection.job_id,
            "runs": selection.runs,
        },
    )


def _get_job(job_id: str) -> _Job:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    return job


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str) -> JobStatus:
    return _job_status(_get_job(job_id))


@router.post("/jobs/{job_id}/cancel", response_model=JobStatus)
def cancel_job(job_id: str) -> JobStatus:
    job = _get_job(job_id)
    with job.lock:
        job.cancelled = True
        if job.status in ("queued", "running"):
            job.status = "cancelled"
        _emit(job)
    return _job_status(job)
