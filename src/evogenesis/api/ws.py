"""WebSocket 契约端点（`API与系统工程.md` §5 / R11；`API接口.md` §3）。

MVP：只建立**信封契约**（每条消息为 `WSMessage {v, type, seq, ts, payload}`）。
当前下发 `sys.hello`（连接即一条）与 `sys.error`（收到非法信封时）；业务推送
（`arena.*` / `brain.*` / `job.*`）与 `sys.echo` 均未实现 —— 前者待采样率与推送清单
定稿（`交互与可视化.md` 阅读问题 8），后者待认领（`API接口.md` §11 B5）。
"""

from __future__ import annotations

import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from evogenesis.api.schemas import WSMessage

router = APIRouter()
_ws_seq = 0


def _next_seq() -> int:
    global _ws_seq
    _ws_seq += 1
    return _ws_seq


def _frame(msg_type: str, payload: dict) -> str:
    return WSMessage(
        type=msg_type, seq=_next_seq(), ts=time.time(), payload=payload
    ).model_dump_json()


@router.websocket("/v1/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    await ws.send_text(_frame("sys.hello", {"note": "EvoGenesis WS contract v1 (R11 envelope)"}))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                WSMessage.model_validate_json(raw)
            except Exception:
                await ws.send_text(_frame("sys.error", {"echo": raw}))
    except WebSocketDisconnect:
        return
