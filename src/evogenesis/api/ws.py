"""WebSocket 实时信道（`API与系统工程.md` §5；`API接口.md` §3）。

信封 `{v, type, seq, ts, payload}`（R11）。可选订阅 `/v1/ws?session_id=<id>`：订阅某会话后
收该会话的 `arena.*`；`job.progress` 为全局。**每连接**单调 `seq`（原进程级已废弃）。

推送清单与采样率为 `草案待确认`（实现已先行、待确认）：**事件驱动**（`arena.*` 由 `release`
触发，无定时采样）；`brain.activation` 未接（无模型驱动会话/DanioNet 生产者）。
"""

from __future__ import annotations

import asyncio
import threading
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from evogenesis.api.schemas import WSMessage

router = APIRouter()
_MAX_ECHO = 4096  # 回显上限：防误发/恶意大消息被放大回传

_seq: dict[WebSocket, int] = {}
_subs: dict[WebSocket, str | None] = {}
_loop: asyncio.AbstractEventLoop | None = None
_lock = threading.Lock()


def _next_seq(ws: WebSocket) -> int:
    with _lock:
        value = _seq.get(ws, 0) + 1
        _seq[ws] = value
        return value


def _frame(ws: WebSocket, msg_type: str, payload: dict) -> str:
    return WSMessage(
        type=msg_type, seq=_next_seq(ws), ts=time.time(), payload=payload
    ).model_dump_json()


def publish(msg_type: str, payload: dict, *, session_id: str | None = None) -> None:
    """向订阅者广播一帧（可从任意线程调用）。

    `session_id=None` 的帧发给**所有**订阅者（如 `job.progress`）；否则只发给订阅该
    `session_id` 的连接。无连接或无事件循环时静默返回。
    """
    loop = _loop
    if loop is None:
        return
    with _lock:
        targets = [ws for ws, sub in _subs.items() if session_id is None or sub == session_id]
    if not targets:
        return
    try:
        asyncio.run_coroutine_threadsafe(_deliver(targets, msg_type, payload), loop)
    except RuntimeError:  # 事件循环已关闭（服务下线）
        return


async def _deliver(targets: list[WebSocket], msg_type: str, payload: dict) -> None:
    for ws in targets:
        try:
            await ws.send_text(_frame(ws, msg_type, payload))
        except Exception:  # noqa: BLE001 - 单连接发送失败不影响其他订阅者
            continue


def publish_fish_state(session_id: str, step: int, fish: dict) -> None:
    publish(
        "arena.fish_state",
        {"session_id": session_id, "step": step, "fish": fish},
        session_id=session_id,
    )


def publish_events(session_id: str, events: list[dict]) -> None:
    publish("arena.events", {"session_id": session_id, "events": events}, session_id=session_id)


def publish_job_progress(job_id: str, status: str, progress: float) -> None:
    publish("job.progress", {"job_id": job_id, "status": status, "progress": progress})


@router.websocket("/v1/ws")
async def ws_endpoint(ws: WebSocket, session_id: str | None = None) -> None:
    global _loop
    await ws.accept()
    _loop = asyncio.get_running_loop()
    with _lock:
        _subs[ws] = session_id
        _seq[ws] = 0
    await ws.send_text(
        _frame(
            ws,
            "sys.hello",
            {"note": "EvoGenesis WS contract v1 (R11 envelope)", "session_id": session_id},
        )
    )
    try:
        while True:
            raw = await ws.receive_text()
            try:
                WSMessage.model_validate_json(raw)
            except Exception:
                await ws.send_text(_frame(ws, "sys.error", {"echo": raw[:_MAX_ECHO]}))
    except WebSocketDisconnect:
        return
    finally:
        with _lock:
            _subs.pop(ws, None)
            _seq.pop(ws, None)
