"""EvoGenesis FastAPI app (doc 10 section 4/5).

Mounts the contract routers:
  - /v1/sessions*           functional (Arena is owned by 李辰钊)
  - /v1/story-mutations ... 501 stubs (pipeline owned by 池伟豪)
  - /v1/ws                  envelope contract
Static frontend served from frontend/dist when present.
"""

from http import HTTPStatus
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from evogenesis.api.schemas import Problem
from evogenesis.api.session import router as sessions_router
from evogenesis.api.stubs import router as stubs_router
from evogenesis.api.ws import router as ws_router

app = FastAPI(title="EvoGenesis API", version="0.1.0")

app.include_router(sessions_router)
app.include_router(stubs_router)
app.include_router(ws_router)


@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _problem(
    request: Request, status: int, detail: str, type_uri: str = "about:blank"
) -> JSONResponse:
    """RFC 7807 problem details (doc 10 R10)."""
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content=Problem(
            type=type_uri,
            title=HTTPStatus(status).phrase,
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


_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
