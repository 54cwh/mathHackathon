"""模型 / 实验侧端点的 501 stub（`API接口.md` §2）。

这些端点定义请求 / 响应**形状**（`schemas.py`）并统一返回 `501`，使契约先于管线冻结、
双方可并行开发。本层不实现业务（`前端驱动-API实现清单.md` §4：重写服务层时不要顺手
把它们从 501 变成实现）。
"""

from fastapi import APIRouter, HTTPException

from evogenesis.api.schemas import (
    BreedingRequest,
    BreedingResult,
    DevelopmentRequest,
    DevelopmentResult,
    ExperimentCreate,
    ExperimentDetail,
    JobStatus,
    MutationRequest,
    MutationResult,
    Page,
    StoryMutation,
)

router = APIRouter(prefix="/v1")

_NOT_IMPL = HTTPException(
    status_code=501,
    detail=(
        "Pipeline not implemented yet -- owned by 池伟豪 (genome/development/breeding/evolution)."
    ),
)


@router.get("/story-mutations", response_model=list[StoryMutation])
def list_story_mutations() -> list[StoryMutation]:
    raise _NOT_IMPL


@router.post("/genomes/{genome_id}/mutations", response_model=MutationResult)
def mutate_genome(genome_id: str, req: MutationRequest) -> MutationResult:
    raise _NOT_IMPL


@router.post("/developments", response_model=DevelopmentResult)
def develop(req: DevelopmentRequest) -> DevelopmentResult:
    raise _NOT_IMPL


@router.post("/breedings", response_model=BreedingResult)
def breed(req: BreedingRequest) -> BreedingResult:
    raise _NOT_IMPL


@router.post("/sessions/{session_id}/evolutions", status_code=202, response_model=JobStatus)
def evolve(session_id: str) -> JobStatus:
    raise _NOT_IMPL


@router.post("/experiments", status_code=202, response_model=JobStatus)
def start_experiment(req: ExperimentCreate) -> JobStatus:
    raise _NOT_IMPL


@router.get("/experiments", response_model=Page)
def list_experiments(limit: int = 20, cursor: str | None = None) -> Page:
    raise _NOT_IMPL


@router.get("/experiments/{experiment_id}", response_model=ExperimentDetail)
def get_experiment(experiment_id: str) -> ExperimentDetail:
    raise _NOT_IMPL


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str) -> JobStatus:
    raise _NOT_IMPL


@router.post("/jobs/{job_id}/cancel", response_model=JobStatus)
def cancel_job(job_id: str) -> JobStatus:
    raise _NOT_IMPL
