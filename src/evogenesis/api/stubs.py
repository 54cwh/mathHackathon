"""模型侧端点中唯一未实现的一条（`API接口.md` §2.1）。

`story-mutations` 的「预验证位点」判据（`交互与可视化.md` 阅读问题 6）依赖 **H3 探针**
（`arena §14`，未落地），故仍返回 `501`。genome / development / breeding / 会话内演化
已实现（见 `genomes.py` / `session.py`）。
"""

from fastapi import APIRouter, HTTPException

from evogenesis.api.schemas import Problem, StoryMutation

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
