"""Contract stubs for modules owned by 池伟豪 (genome/development/breeding/
evolution/experiments/jobs).

These endpoints define the request/response SHAPE (schemas.py) and return
HTTP 501 so both sides can develop against the frozen contract before the
pipeline lands (doc 10 section 4.3, R7).
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
def list_story_mutations():
    raise _NOT_IMPL


@router.post("/genomes/{genome_id}/mutations", response_model=MutationResult)
def mutate_genome(genome_id: str, req: MutationRequest):
    raise _NOT_IMPL


@router.post("/developments", response_model=DevelopmentResult)
def develop(req: DevelopmentRequest):
    raise _NOT_IMPL


@router.post("/breedings", response_model=BreedingResult)
def breed(req: BreedingRequest):
    raise _NOT_IMPL


@router.post("/sessions/{session_id}/evolutions", status_code=202, response_model=JobStatus)
def evolve(session_id: str):
    raise _NOT_IMPL


@router.post("/experiments", status_code=202, response_model=JobStatus)
def start_experiment(req: ExperimentCreate):
    raise _NOT_IMPL


@router.get("/experiments", response_model=Page)
def list_experiments(limit: int = 20, cursor: str | None = None):
    raise _NOT_IMPL


@router.get("/experiments/{experiment_id}", response_model=ExperimentDetail)
def get_experiment(experiment_id: str):
    raise _NOT_IMPL


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    raise _NOT_IMPL


@router.post("/jobs/{job_id}/cancel", response_model=JobStatus)
def cancel_job(job_id: str):
    raise _NOT_IMPL
