"""WebSocket contract endpoint (API与系统工程.md section 5, R11).

MVP: establishes the envelope contract -- every WS message is a WSMessage
{v, type, seq, ts, payload}. This endpoint echoes any received message back
with type ``sys.echo`` as a contract demonstration; real arena.brain/job
broadcasts land in later iterations once the pipeline is wired.
"""

import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from evogenesis.api.schemas import WSMessage

router = APIRouter()
_ws_seq = 0


def _next_seq() -> int:
    global _ws_seq
    _ws_seq += 1
    return _ws_seq


@router.websocket("/v1/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    await ws.send_text(
        WSMessage(
            type="sys.hello",
            seq=_next_seq(),
            ts=time.time(),
            payload={"note": "EvoGenesis WS contract v1 (R11 envelope)"},
        ).model_dump_json()
    )
    try:
        while True:
            raw = await ws.receive_text()
            try:
                WSMessage.model_validate_json(raw)
                reply_type = "sys.echo"
            except Exception:
                reply_type = "sys.error"
            await ws.send_text(
                WSMessage(
                    type=reply_type,
                    seq=_next_seq(),
                    ts=time.time(),
                    payload={"echo": raw},
                ).model_dump_json()
            )
    except WebSocketDisconnect:
        return
