"""模型侧端点中尚未实现的两条（`API接口.md` §2.1）。

`story-mutations` 的「预验证位点」判据（`交互与可视化.md` 阅读问题 6）与
`sessions/{id}/evolutions` 的语义（会话不持有模型链种群）**上游未定义**，故仍返回 `501`。
genome / development / breeding 已实现，见 `genomes.py`（§2.3）。
"""

from fastapi import APIRouter, HTTPException

from evogenesis.api.schemas import (
    JobStatus,
    Problem,
    StoryMutation,
)

router = APIRouter(
    prefix="/v1",
    responses={501: {"model": Problem, "description": "端点所属模块尚未实现"}},
)


def _not_impl() -> HTTPException:
    """每次新实例（不复用异常对象，避免 traceback 链累积）。"""
    return HTTPException(
        status_code=501,
        detail=(
            "Pipeline not implemented yet -- owned by 池伟豪 "
            "(genome/development/breeding/evolution)."
        ),
    )


@router.get("/story-mutations", response_model=list[StoryMutation])
def list_story_mutations() -> list[StoryMutation]:
    raise _not_impl()


@router.post("/sessions/{session_id}/evolutions", status_code=202, response_model=JobStatus)
def evolve(session_id: str) -> JobStatus:
    raise _not_impl()
