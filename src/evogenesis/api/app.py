"""EvoGenesis FastAPI 应用（`API与系统工程.md` §4/§5；`API接口.md`）。

挂载契约路由：
  - `/v1/sessions*`      functional（Arena 侧，`session.py`）
  - `/v1/story-mutations` 等 501 stub（`stubs.py`）
  - `/v1/ws`             信封契约（`ws.py`）
存在 `frontend/dist` 时以静态文件托管（生产同源，免 CORS；见 `API与系统工程.md` §9）。
错误体统一 RFC 7807（R10）。
"""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from evogenesis.api.environmental_selections import router as selections_router
from evogenesis.api.genomes import router as genomes_router
from evogenesis.api.schemas import Problem
from evogenesis.api.session import router as sessions_router
from evogenesis.api.stubs import router as stubs_router
from evogenesis.api.ws import router as ws_router

_REPO_ROOT = Path(__file__).resolve().parents[3]

app = FastAPI(title="EvoGenesis API", version="0.1.0")

app.include_router(sessions_router)
app.include_router(genomes_router)
app.include_router(selections_router)
app.include_router(stubs_router)
app.include_router(ws_router)


@app.get("/v1/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "manual_control": True}


def _problem(
    request: Request, status: int, detail: str, type_uri: str = "about:blank"
) -> JSONResponse:
    """RFC 7807 problem details（R10）。非标准状态码安全回退，避免处理器自身抛错。"""
    try:
        title = HTTPStatus(status).phrase
    except ValueError:
        title = "Error"
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content=Problem(
            type=type_uri,
            title=title,
            status=status,
            detail=detail,
            instance=request.url.path,
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return _problem(request, exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _problem(request, 422, str(exc.errors()))


_dist = _REPO_ROOT / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
