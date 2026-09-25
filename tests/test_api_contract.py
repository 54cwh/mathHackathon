"""API contract smoke tests (api/API与系统工程.md section 4/5)."""

from fastapi.testclient import TestClient

from evogenesis.api.app import app

client = TestClient(app)


def test_health():
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_session_and_snapshot():
    r = client.post("/v1/sessions", json={"master_seed": 250927, "environment": "food_rich"})
    assert r.status_code == 201
    sid = r.json()["session_id"]
    assert r.json()["fish_alive"] == 12

    r = client.get(f"/v1/sessions/{sid}/snapshot")
    assert r.status_code == 200
    body = r.json()
    assert body["step"] == 0
    assert len(body["fish"]) == 12
    assert len(body["prey"]) == 24
    assert len(body["predators"]) == 3
    assert len(body["obstacles"]) == 6


def test_release_advances_arena():
    sid = client.post("/v1/sessions", json={"master_seed": 250927}).json()["session_id"]
    r = client.post(f"/v1/sessions/{sid}/release", params={"steps": 30})
    assert r.status_code == 200
    snap = client.get(f"/v1/sessions/{sid}/snapshot").json()
    assert snap["step"] == 30


def test_fish_card_and_leaderboard():
    sid = client.post("/v1/sessions", json={"master_seed": 7}).json()["session_id"]
    client.post(f"/v1/sessions/{sid}/release", params={"steps": 10})
    r = client.get(f"/v1/sessions/{sid}/fish/fish_00")
    assert r.status_code == 200
    assert r.json()["fish_id"] == "fish_00"

    r = client.get(f"/v1/sessions/{sid}/leaderboard")
    assert r.status_code == 200
    assert len(r.json()["entries"]) == 12


def test_reset_session():
    sid = client.post("/v1/sessions", json={"master_seed": 7}).json()["session_id"]
    client.post(f"/v1/sessions/{sid}/release", params={"steps": 50})
    assert client.get(f"/v1/sessions/{sid}/snapshot").json()["step"] == 50
    r = client.post(f"/v1/sessions/{sid}/reset")
    assert r.status_code == 200
    assert client.get(f"/v1/sessions/{sid}/snapshot").json()["step"] == 0


def test_missing_session_404():
    r = client.get("/v1/sessions/nope")
    assert r.status_code == 404
    body = r.json()
    # RFC 7807 problem details (R10)
    assert body["type"] == "about:blank"
    assert body["title"] == "Not Found"
    assert body["status"] == 404
    assert "detail" in body
    assert body["instance"] == "/v1/sessions/nope"


def test_stubs_return_501():
    r = client.post("/v1/developments", json={"genome_id": "g", "seed": 0})
    assert r.status_code == 501
    r = client.post("/v1/breedings", json={"genome_a": "a", "genome_b": "b"})
    assert r.status_code == 501


def test_ws_envelope_contract():
    with client.websocket_connect("/v1/ws") as ws:
        hello = ws.receive_json()
        assert hello["v"] == 1
        assert hello["type"] == "sys.hello"
        assert "ts" in hello and "seq" in hello
        ws.send_json(
            {
                "v": 1,
                "type": "arena.fish_state",
                "seq": 2,
                "ts": 1.0,
                "payload": {"fish_id": "fish_00"},
            }
        )
        echo = ws.receive_json()
        assert echo["type"] == "sys.echo"


def test_pause_blocks_advance():
    sid = client.post("/v1/sessions", json={"master_seed": 11}).json()["session_id"]
    assert client.post(f"/v1/sessions/{sid}/pause").json()["running"] is False
    client.post(f"/v1/sessions/{sid}/release", params={"steps": 5})
    assert client.get(f"/v1/sessions/{sid}/snapshot").json()["step"] == 0
    assert client.post(f"/v1/sessions/{sid}/pause").json()["running"] is True
    client.post(f"/v1/sessions/{sid}/release", params={"steps": 5})
    assert client.get(f"/v1/sessions/{sid}/snapshot").json()["step"] == 5
