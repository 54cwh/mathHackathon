"""API 契约测试（`API接口.md` §1/§3/§4；`前端驱动-API实现清单.md` §1/§7）。

覆盖前端 Demo 必需的 6 个 REST 端点（含 snapshot 的 `prey`/`predators`/`obstacles`
三键）、204 无体、RFC 7807、stub 501、WS 信封，以及 `master_seed` 复现性。
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from evogenesis.api.app import app

client = TestClient(app)


def _create(master_seed: int = 250927, environment: str = "food_rich") -> dict:
    resp = client.post(
        "/v1/sessions", json={"master_seed": master_seed, "environment": environment}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_health() -> None:
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_session_and_snapshot_full_field_set() -> None:
    summary = _create()
    assert summary["session_id"].startswith("session_")
    assert summary["fish_alive"] == 12
    assert summary["prey_remaining"] == 24
    assert summary["master_seed"] == 250927
    assert summary["environment"] == "food_rich"

    snap = client.get(f"/v1/sessions/{summary['session_id']}/snapshot").json()
    assert snap["step"] == 0
    # 渲染硬依赖：prey / predators / obstacles 缺任一键前端会抛 TypeError
    assert len(snap["fish"]) == 12
    assert len(snap["prey"]) == 24
    assert len(snap["predators"]) == 3
    assert len(snap["obstacles"]) == 6
    assert {"x", "y", "heading", "energy", "size", "alive"} <= set(
        next(iter(snap["fish"].values()))
    )
    assert {"x", "y", "size", "alive"} <= set(next(iter(snap["prey"].values())))
    assert {"x", "y", "size"} <= set(next(iter(snap["predators"].values())))
    assert {"x", "y", "radius"} <= set(snap["obstacles"][0])
    assert snap["events"]  # 初始 39 条 arena.spawn


def test_release_advances_and_returns_summary() -> None:
    sid = _create()["session_id"]
    resp = client.post(f"/v1/sessions/{sid}/release?steps=30&use_expert=true")
    assert resp.status_code == 200
    assert {"generation", "population", "fish_alive", "prey_remaining", "master_seed"} <= set(
        resp.json()
    )
    assert client.get(f"/v1/sessions/{sid}/snapshot").json()["step"] == 30


def test_reset_returns_to_step_zero() -> None:
    sid = _create()["session_id"]
    client.post(f"/v1/sessions/{sid}/release?steps=50")
    resp = client.post(f"/v1/sessions/{sid}/reset")
    assert resp.status_code == 200
    assert resp.json()["generation"] == 0
    assert client.get(f"/v1/sessions/{sid}/snapshot").json()["step"] == 0


def test_delete_returns_204_without_body() -> None:
    sid = _create()["session_id"]
    resp = client.delete(f"/v1/sessions/{sid}")
    assert resp.status_code == 204
    assert resp.content == b""


def test_missing_session_returns_rfc7807() -> None:
    resp = client.get("/v1/sessions/session_nope/snapshot")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    body = resp.json()
    assert {"type", "title", "status", "detail", "instance"} <= set(body)
    assert body["status"] == 404 and body["detail"]


def test_pause_toggles_and_blocks_release() -> None:
    sid = _create()["session_id"]
    assert client.post(f"/v1/sessions/{sid}/pause").json()["running"] is False
    client.post(f"/v1/sessions/{sid}/release?steps=5")
    assert client.get(f"/v1/sessions/{sid}/snapshot").json()["step"] == 0
    assert client.post(f"/v1/sessions/{sid}/pause").json()["running"] is True
    client.post(f"/v1/sessions/{sid}/release?steps=5")
    assert client.get(f"/v1/sessions/{sid}/snapshot").json()["step"] == 5


def test_master_seed_reproducible() -> None:
    a = _create(master_seed=250927)["session_id"]
    b = _create(master_seed=250927)["session_id"]
    sa = client.get(f"/v1/sessions/{a}/snapshot").json()
    sb = client.get(f"/v1/sessions/{b}/snapshot").json()
    assert sa["fish"] == sb["fish"]  # 同一 master_seed 布局完全一致


def test_model_stubs_return_501() -> None:
    assert client.post("/v1/developments", json={"genome_id": "g0", "seed": 0}).status_code == 501
    assert client.post("/v1/breedings", json={"genome_a": "a", "genome_b": "b"}).status_code == 501


def test_ws_hello_and_error_envelope() -> None:
    with client.websocket_connect("/v1/ws") as ws:
        hello = ws.receive_json()
        assert hello["v"] == 1
        assert hello["type"] == "sys.hello"
        assert {"seq", "ts", "payload"} <= set(hello)
        ws.send_text(json.dumps({"not": "an envelope"}))
        err = ws.receive_json()
        assert err["type"] == "sys.error"
