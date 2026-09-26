"""API 契约测试（`API接口.md` §1/§3/§4；`前端驱动-API实现清单.md` §1/§7）。

覆盖前端 Demo 必需的 6 个 REST 端点（含 snapshot 的 `prey`/`predators`/`obstacles`
三键）、204 无体、RFC 7807（404/422/501）、stub 501、WS 信封、`master_seed` 复现性、
`environment` 仅回显、坐标边界，以及 release 止步于 `episode_steps`。
"""

from __future__ import annotations

import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from evogenesis.api import environmental_selections as selections_mod
from evogenesis.api import genome_lab as lab_mod
from evogenesis.api import ws as ws_mod
from evogenesis.api.app import app
from evogenesis.api.session import _manager

client = TestClient(app)

WORLD_W, WORLD_H = 100.0, 60.0


@pytest.fixture(autouse=True)
def _clean_sessions():
    """每个测试独立：清空模块级内存会话/实验/任务表。"""
    _manager._sessions.clear()
    selections_mod._selections.clear()
    selections_mod._jobs.clear()
    ws_mod._subs.clear()
    ws_mod._seq.clear()
    ws_mod._loop = None
    lab_mod._genomes.clear()
    lab_mod._lineage.clear()
    lab_mod._counter = 0
    yield
    _manager._sessions.clear()
    selections_mod._selections.clear()
    selections_mod._jobs.clear()
    ws_mod._subs.clear()
    ws_mod._seq.clear()
    ws_mod._loop = None
    lab_mod._genomes.clear()
    lab_mod._lineage.clear()
    lab_mod._counter = 0


def _wait_job(job_id: str, timeout: float = 60.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.get(f"/v1/jobs/{job_id}").json()
        if status["status"] in ("done", "failed", "cancelled"):
            return status
        time.sleep(0.1)
    raise AssertionError("job did not finish in time")


def _create(master_seed: int = 250927, environment: str = "food_rich") -> dict:
    resp = client.post(
        "/v1/sessions", json={"master_seed": master_seed, "environment": environment}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _layout(snap: dict) -> list:
    """把快照的鱼层压成与 ID 无关的布局（会话 ID 会进 fish_id，不能直接比字典）。"""
    return sorted(
        (round(f["x"], 9), round(f["y"], 9), round(f["heading"], 9)) for f in snap["fish"].values()
    )


def test_session_population_is_genome_driven() -> None:
    """§1.1（2026-09-27 定稿）：默认会话种群由 genome 生成，每条鱼可回查 DNA、由自己的网驱动。"""
    sid = _create()["session_id"]
    entries = client.get(f"/v1/sessions/{sid}/leaderboard").json()["entries"]
    assert len(entries) == 12
    for entry in entries:
        card = client.get(f"/v1/sessions/{sid}/fish/{entry['fish_id']}").json()
        assert card["genome_id"] == card["fish_id"]  # fish_id == genome_id
        assert card["metrics"]["n_neurons"] > 0 and card["metrics"]["n_edges"] > 0
        # 该 genome 在 Lab 可查（点 Arena 的鱼回看 DNA）
        assert client.get(f"/v1/genomes/{card['genome_id']}").status_code == 200


def test_population_size_is_honoured() -> None:
    """§1.1：`population_size` 决定生成多少个基因组（demo 小种群用）。"""
    resp = client.post("/v1/sessions", json={"master_seed": 250927, "population_size": 4})
    assert resp.status_code == 201
    sid = resp.json()["session_id"]
    assert resp.json()["population"] == 4
    assert len(client.get(f"/v1/sessions/{sid}/snapshot").json()["fish"]) == 4


def test_list_individuals_returns_population() -> None:
    """§1.11 GET：会话内个体列表 = 初始种群（+ 追加），与 Arena 的鱼一一对应。"""
    sid = _create()["session_id"]
    items = client.get(f"/v1/sessions/{sid}/individuals").json()
    assert len(items) == 12
    snap = client.get(f"/v1/sessions/{sid}/snapshot").json()
    assert {it["fish_id"] for it in items} == set(snap["fish"])
    for it in items:
        assert it["fish_id"] == it["genome_id"]
        assert it["n_neurons"] > 0 and it["n_edges"] > 0


def test_session_evolution_step(monkeypatch) -> None:
    """§2.3：会话内逐代推进 —— 一代产出 summary、会话代次 +1、种群换代（子代可查 DNA）。

    把演示步数压到 5（`configs/demo_session.yaml` 的 `evolution_steps`）以便快速跑通契约；
    真实取值 200 由该配置承担。
    """
    import types

    from evogenesis.api import session as session_mod

    monkeypatch.setattr(
        session_mod, "load_demo_session_config", lambda: types.SimpleNamespace(evolution_steps=5)
    )
    sid = _create()["session_id"]
    before = {i["genome_id"] for i in client.get(f"/v1/sessions/{sid}/individuals").json()}
    assert client.get(f"/v1/sessions/{sid}").json()["generation"] == 0

    resp = client.post(f"/v1/sessions/{sid}/evolutions/step")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["summary"]["generation"] == 0
    assert body["summary"]["n_individuals"] == 12
    assert body["session"]["generation"] == 1

    after = {i["genome_id"] for i in client.get(f"/v1/sessions/{sid}/individuals").json()}
    assert after and before.isdisjoint(after), "子代应换成新的 genome_id（同群换代）"
    assert client.get(f"/v1/genomes/{next(iter(after))}").status_code == 200


def test_health() -> None:
    """`status` 是状态，`manual_control` 是**能力位**（`API接口.md` §1.10）。

    能力位用于让前端识别"旧进程静默忽略新查询参数"（Manual Control 踩过）：
    旧进程没有该字段，`release` 会忽略 `fish_id/omega/speed`。
    """
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["manual_control"] is True


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


def test_get_session() -> None:
    sid = _create()["session_id"]
    resp = client.get(f"/v1/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == sid


def test_fish_card_and_leaderboard() -> None:
    sid = _create()["session_id"]
    board = client.get(f"/v1/sessions/{sid}/leaderboard")
    assert board.status_code == 200
    entries = board.json()["entries"]
    assert len(entries) == 12
    fid = entries[0]["fish_id"]
    card = client.get(f"/v1/sessions/{sid}/fish/{fid}")
    assert card.status_code == 200
    assert card.json()["fish_id"] == fid
    assert card.json()["genome_id"] == fid  # §1.1：种群基因组化后 fish_id == genome_id


def test_release_advances_and_returns_summary() -> None:
    sid = _create()["session_id"]
    resp = client.post(f"/v1/sessions/{sid}/release?steps=30&use_expert=true")
    assert resp.status_code == 200
    assert {"generation", "population", "fish_alive", "prey_remaining", "master_seed"} <= set(
        resp.json()
    )
    assert client.get(f"/v1/sessions/{sid}/snapshot").json()["step"] == 30


def test_release_clamps_at_episode_end() -> None:
    sid = _create()["session_id"]
    client.post(f"/v1/sessions/{sid}/release?steps=601")
    assert client.get(f"/v1/sessions/{sid}/snapshot").json()["step"] == 600


def test_release_use_expert_false_advances() -> None:
    sid = _create()["session_id"]
    client.post(f"/v1/sessions/{sid}/release?steps=5&use_expert=false")
    assert client.get(f"/v1/sessions/{sid}/snapshot").json()["step"] == 5


def test_release_manual_control_overrides_that_fish() -> None:
    """Manual Control（`交互与可视化.md` §10）：手动动作**覆盖**被控鱼自己的网。

    默认种群由逐鱼 DanioNet 驱动（§1.1），故 `use_expert` 不再决定"动不动"；
    本测试钉住：给 `fish_id` 手动动作后该鱼确实按指令运动、航向被 `omega` 改变。
    """
    sid = _create()["session_id"]
    fid = client.get(f"/v1/sessions/{sid}/leaderboard").json()["entries"][0]["fish_id"]
    before = client.get(f"/v1/sessions/{sid}/snapshot").json()["fish"][fid]
    resp = client.post(
        f"/v1/sessions/{sid}/release?steps=1&use_expert=false&fish_id={fid}&omega=1.0&speed=1.0"
    )
    assert resp.status_code == 200
    after = client.get(f"/v1/sessions/{sid}/snapshot").json()["fish"][fid]
    moved = (after["x"] - before["x"]) ** 2 + (after["y"] - before["y"]) ** 2
    assert moved > 0, "被控鱼必须动起来"
    assert after["heading"] != before["heading"], "omega 必须改变航向"


def test_release_manual_control_clamps_and_ignores_unknown_fish() -> None:
    """越界动作被裁剪；未知 / 已死 fish_id 静默忽略（前端 10Hz 连发不报错）。"""
    sid = _create()["session_id"]
    resp = client.post(
        f"/v1/sessions/{sid}/release?steps=1&use_expert=false&fish_id=fish_99&omega=9.0&speed=9.0"
    )
    assert resp.status_code == 200
    after_clamped = client.post(
        f"/v1/sessions/{sid}/release?steps=1&use_expert=false&fish_id=fish_00&omega=9.0&speed=9.0"
    )
    assert after_clamped.status_code == 200
    snap = client.get(f"/v1/sessions/{sid}/snapshot").json()
    assert snap["step"] == 2


def test_develop_trace_is_opt_in_and_ordered() -> None:
    """`?with_trace=true` 才返回轨迹；阶段顺序与数量守恒可对账（`API接口.md` §2.3）。"""
    genome = client.post("/v1/genomes", json={}).json()
    plain = client.post(
        "/v1/developments", json={"genome_id": genome["genome_id"], "seed": 0}
    ).json()
    assert plain.get("trace") is None, "默认不得返回轨迹（契约：可选）"

    traced = client.post(
        "/v1/developments?with_trace=true", json={"genome_id": genome["genome_id"], "seed": 0}
    ).json()
    trace = traced["trace"]
    assert trace is not None and len(trace) > 2
    assert trace[0]["stage"] == "grn" and trace[-1]["stage"] == "connectome"
    assert trace[-1]["n_edges"] == traced["phenotype"]["n_edges"]
    assert trace[-1]["n_neurons"] == traced["phenotype"]["n_neurons"]
    # 同一 genome/seed：开关 trace 的表型必须逐位一致
    assert plain["phenotype"] == traced["phenotype"]
    assert plain["dev_trace"] == traced["dev_trace"]


def test_develop_cell_type_counts_are_real_counts() -> None:
    """`dev_trace.cell_type_counts` 必须是**真实计数**（键=fate 序号，值=个体数）。

    旧实现写成 `{str(i): int(c) for i, c in enumerate(counter)}`：`Counter` 迭代产出的是
    key，于是恒得 `{"0":0,"1":1,...}`（与命运分布无关）。此处用守恒量钉住：
    各 fate 计数之和 == 表型 `n_neurons`。
    """
    genome = client.post("/v1/genomes", json={}).json()
    result = client.post(
        "/v1/developments", json={"genome_id": genome["genome_id"], "seed": 0}
    ).json()
    counts = result["dev_trace"]["cell_type_counts"]
    assert set(counts) == {"0", "1", "2", "3", "4", "5"}, counts
    assert sum(counts.values()) == result["phenotype"]["n_neurons"], (counts, result["phenotype"])
    assert counts != {str(i): i for i in range(6)}, "计数退化为 enumerate(Counter) 的旧错误"


def test_spawn_individual_into_session() -> None:
    """§1.11：把发育好的个体追加进 Arena —— 真实 genome_id、自己的网驱动、可回查卡片。"""
    sid = _create()["session_id"]
    genome = client.post("/v1/genomes", json={}).json()
    before = client.get(f"/v1/sessions/{sid}/snapshot").json()["fish"]
    resp = client.post(
        f"/v1/sessions/{sid}/individuals",
        json={"genome_id": genome["genome_id"], "seed": 0},
    )
    assert resp.status_code == 201
    spawned = resp.json()
    assert spawned["fish_id"] == genome["genome_id"], "稳定 ID：fish_id == genome_id"
    assert spawned["n_neurons"] > 0 and spawned["n_edges"] > 0
    assert sum(spawned["cell_type_counts"].values()) == spawned["n_neurons"]

    after = client.get(f"/v1/sessions/{sid}/snapshot").json()["fish"]
    assert len(after) == len(before) + 1
    assert genome["genome_id"] in after, "新个体必须出现在快照里"

    card = client.get(f"/v1/sessions/{sid}/fish/{genome['genome_id']}").json()
    assert card["genome_id"] == genome["genome_id"], "鱼卡必须回真实基因组（旧版恒 unknown）"
    assert card["metrics"]["n_edges"] == spawned["n_edges"]
    assert sum(card["cell_counts"].values()) == spawned["n_neurons"]

    # 重复追加同一 genome -> 409；未知 genome -> 404
    assert (
        client.post(
            f"/v1/sessions/{sid}/individuals", json={"genome_id": genome["genome_id"]}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/v1/sessions/{sid}/individuals", json={"genome_id": "lab:g0:genome9999"}
        ).status_code
        == 404
    )


def test_spawned_individual_is_driven_by_its_own_net() -> None:
    """实验室个体由**自己的网**驱动：`use_expert=false` 时它动、默认鱼不动。"""
    sid = _create()["session_id"]
    genome = client.post("/v1/genomes", json={}).json()
    client.post(f"/v1/sessions/{sid}/individuals", json={"genome_id": genome["genome_id"]})
    before = client.get(f"/v1/sessions/{sid}/snapshot").json()["fish"]
    client.post(f"/v1/sessions/{sid}/release?steps=1&use_expert=false")
    after = client.get(f"/v1/sessions/{sid}/snapshot").json()["fish"]

    fid = genome["genome_id"]
    moved = after[fid]["x"] != before[fid]["x"] or after[fid]["y"] != before[fid]["y"]
    assert moved, "实验室个体必须由其网络驱动而移动"
    # §1.1：默认种群也是逐鱼网 —— `use_expert=false` 不妨碍它们运动
    default_moved = any(
        after[k]["x"] != before[k]["x"] or after[k]["y"] != before[k]["y"]
        for k in before
        if k != fid
    )
    assert default_moved, "默认种群应由各自的网驱动"


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


def test_validation_error_returns_rfc7807_422() -> None:
    resp = client.post("/v1/sessions", json={"master_seed": "not-an-int"})
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["status"] == 422


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
    # fish_id 含 session_id（稳定 ID 前缀），故比**布局**而非字典键。
    assert _layout(sa) == _layout(sb)  # 同一 master_seed 布局完全一致


def test_environment_is_echo_only() -> None:
    a = _create(master_seed=250927, environment="food_rich")
    b = _create(master_seed=250927, environment="predator_rich")
    assert a["environment"] == "food_rich" and b["environment"] == "predator_rich"
    sa = client.get(f"/v1/sessions/{a['session_id']}/snapshot").json()
    sb = client.get(f"/v1/sessions/{b['session_id']}/snapshot").json()
    assert _layout(sa) == _layout(sb)  # environment 不改变任何 Arena 参数（§7 硬边界）


def test_snapshot_within_world_bounds() -> None:
    sid = _create()["session_id"]
    snap = client.get(f"/v1/sessions/{sid}/snapshot").json()
    for f in snap["fish"].values():
        assert 0.0 <= f["x"] <= WORLD_W and 0.0 <= f["y"] <= WORLD_H
    for p in snap["prey"].values():
        assert 0.0 <= p["x"] <= WORLD_W and 0.0 <= p["y"] <= WORLD_H


def test_model_stubs_return_501() -> None:
    resp = client.get("/v1/story-mutations")
    assert resp.status_code == 501
    assert resp.headers["content-type"].startswith("application/problem+json")
    body = resp.json()
    assert {"type", "title", "status", "detail", "instance"} <= set(body)
    assert body["instance"] == "/v1/story-mutations"


def test_openapi_exposes_problem_and_experiment_summary() -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "Problem" in schemas  # S-5：错误体进 OpenAPI
    assert any("EnvironmentalSelectionSummary" in key for key in schemas)  # S-3：模型已接线


def test_ws_hello_and_error_envelope() -> None:
    with client.websocket_connect("/v1/ws") as ws:
        hello = ws.receive_json()
        assert hello["v"] == 1
        assert hello["type"] == "sys.hello"
        assert {"seq", "ts", "payload"} <= set(hello)
        ws.send_text(json.dumps({"not": "an envelope"}))
        err = ws.receive_json()
        assert err["type"] == "sys.error"


def test_experiment_launch_lifecycle(tmp_path, monkeypatch) -> None:
    """实验启动 → job 完成 → 列表/详情可见（用假 _run_one，不跑真实演化）。"""
    monkeypatch.setattr(selections_mod, "_OUT_ROOT", tmp_path / "runs")
    monkeypatch.setattr(selections_mod, "_TRACKING_ROOT", tmp_path / "mlruns")

    def fake_run_one(expt, seed):
        return {"seed": seed, "run_dir": f"runs/{expt.experiment_id}-s{seed}", "generations_run": 0}

    monkeypatch.setattr(selections_mod, "_run_one", fake_run_one)
    resp = client.post(
        "/v1/environmental-selections",
        json={"name": "exp-a", "seeds": [1103, 2207], "environment": "default", "generations": 3},
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    final = _wait_job(job_id)
    assert final["status"] == "done"
    assert final["progress"] == 1.0

    listed = client.get("/v1/environmental-selections").json()
    assert listed["items"][0]["name"] == "exp-a"
    eid = listed["items"][0]["experiment_id"]
    detail = client.get(f"/v1/environmental-selections/{eid}").json()
    assert [r["seed"] for r in detail["results"]["runs"]] == [1103, 2207]
    assert detail["results"]["generations"] == 3


def test_experiment_cancel_at_seed_boundary(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(selections_mod, "_OUT_ROOT", tmp_path / "runs")
    monkeypatch.setattr(selections_mod, "_TRACKING_ROOT", tmp_path / "mlruns")
    started = threading.Event()

    def slow_run_one(expt, seed):
        started.set()
        time.sleep(0.5)
        return {"seed": seed, "run_dir": "x"}

    monkeypatch.setattr(selections_mod, "_run_one", slow_run_one)
    resp = client.post(
        "/v1/environmental-selections", json={"name": "c", "seeds": [1, 2], "generations": 1}
    )
    job_id = resp.json()["job_id"]
    assert started.wait(5.0)
    cancelled = client.post(f"/v1/jobs/{job_id}/cancel").json()
    assert cancelled["status"] == "cancelled"
    assert _wait_job(job_id)["status"] == "cancelled"


def test_experiment_and_job_not_found() -> None:
    assert client.get("/v1/environmental-selections/exp_nope").status_code == 404
    assert client.get("/v1/jobs/job_nope").status_code == 404


def test_experiment_launch_real_run_generations_zero(tmp_path, monkeypatch) -> None:
    """真实跑通一次：generations=0（不入代循环）仍建 ExperimentRun 目录并落 evolution.jsonl。"""
    monkeypatch.setattr(selections_mod, "_OUT_ROOT", tmp_path / "runs")
    monkeypatch.setattr(selections_mod, "_TRACKING_ROOT", tmp_path / "mlruns")
    resp = client.post(
        "/v1/environmental-selections",
        json={"name": "real", "seeds": [1103], "environment": "default", "generations": 0},
    )
    job_id = resp.json()["job_id"]
    final = _wait_job(job_id)
    assert final["status"] == "done", final
    detail = client.get(
        f"/v1/environmental-selections/{next(iter(selections_mod._selections))}"
    ).json()
    run = detail["results"]["runs"][0]
    assert run["seed"] == 1103 and run["generations_run"] == 0
    assert (tmp_path / "runs" / f"{detail['experiment_id']}-s1103" / "evolution.jsonl").exists()


def test_ws_pushes_fish_state_and_events() -> None:
    sid = _create()["session_id"]
    with client.websocket_connect(f"/v1/ws?session_id={sid}") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "sys.hello" and hello["seq"] == 1
        assert hello["payload"]["session_id"] == sid
        client.post(f"/v1/sessions/{sid}/release?steps=3")
        # §1.1 后默认会话也有逐鱼网 ⇒ 额外推 `brain.activation`（本会话共 3 帧）。
        # 但 WS 上还有 `session_id=None` 的全局帧（`job.progress`），可能来自其他测试遗留的后台
        # job —— 故按类型收集、容忍无关帧，直到三件套齐或达上限。
        want = {"arena.fish_state", "arena.events", "brain.activation"}
        by_type: dict[str, dict] = {}
        seqs: list[int] = []
        for _ in range(10):
            m = ws.receive_json()
            seqs.append(m["seq"])
            by_type.setdefault(m["type"], m)
            if want <= set(by_type):
                break
        assert want <= set(by_type), f"缺帧：{want - set(by_type)}"
        fs = by_type["arena.fish_state"]["payload"]
        assert fs["session_id"] == sid and fs["step"] == 3 and len(fs["fish"]) == 12
        assert seqs == sorted(seqs)  # 每连接单调


def test_ws_does_not_push_other_session() -> None:
    a = _create()["session_id"]
    b = _create()["session_id"]
    with client.websocket_connect(f"/v1/ws?session_id={a}") as ws:
        ws.receive_json()  # hello
        client.post(f"/v1/sessions/{b}/release?steps=2")
        ws.send_text('{"probe": 1}')  # invalid envelope -> immediate sys.error
        # 容忍全局帧（`job.progress`）；断言收不到 b 的 `arena.*`
        for _ in range(10):
            m = ws.receive_json()
            assert not (m["type"].startswith("arena.") and m["payload"].get("session_id") == b)
            if m["type"] == "sys.error":
                break
        else:
            raise AssertionError("未收到 sys.error")


def test_ws_job_progress_push(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(selections_mod, "_OUT_ROOT", tmp_path / "runs")
    monkeypatch.setattr(selections_mod, "_TRACKING_ROOT", tmp_path / "mlruns")
    monkeypatch.setattr(
        selections_mod, "_run_one", lambda expt, seed: {"seed": seed, "run_dir": "x"}
    )
    with client.websocket_connect("/v1/ws") as ws:
        assert ws.receive_json()["type"] == "sys.hello"
        client.post(
            "/v1/environmental-selections",
            json={"name": "j", "seeds": [1], "generations": 0},
        )
        r = ws.receive_json()
        while r["type"] != "job.progress" or r["payload"]["status"] != "done":
            assert r["type"] == "job.progress"
            r = ws.receive_json()
        assert r["payload"]["status"] == "done" and r["payload"]["progress"] == 1.0


def _new_genome() -> str:
    resp = client.post("/v1/genomes", json={})
    assert resp.status_code == 201, resp.text
    return resp.json()["genome_id"]


def test_genome_create_and_get() -> None:
    gid = _new_genome()
    got = client.get(f"/v1/genomes/{gid}").json()
    assert got["genome_id"] == gid
    assert len(got["chromosome_pairs"]) == 2
    assert set(got["chromosome_pairs"][0]) == {"maternal", "paternal"}


def test_genome_mutation_creates_child_with_diff() -> None:
    gid = _new_genome()
    resp = client.post(f"/v1/genomes/{gid}/mutations", json={"position": 0, "base": "A"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["genome_id"] == gid and body["new_genome_id"] != gid
    assert body["diff"]["to_base"] == "A"
    child = client.get(f"/v1/genomes/{body['new_genome_id']}").json()
    assert child["lineage"] == gid  # 血缘


def test_genome_mutation_invalid_position_422() -> None:
    gid = _new_genome()
    resp = client.post(f"/v1/genomes/{gid}/mutations", json={"position": 99999, "base": "A"})
    assert resp.status_code == 422


def test_development_returns_trace_and_phenotype() -> None:
    gid = _new_genome()
    resp = client.post("/v1/developments", json={"genome_id": gid, "seed": 0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["genome_id"] == gid
    assert len(body["dev_trace"]["q"]) == 8  # 8 维 q(G)
    assert "viable" in body["phenotype"] and "n_neurons" in body["phenotype"]


def test_breeding_creates_offspring() -> None:
    a, b = _new_genome(), _new_genome()
    resp = client.post("/v1/breedings", json={"genome_a": a, "genome_b": b, "n_offspring": 3})
    assert resp.status_code == 201
    ids = resp.json()["offspring"]
    assert len(ids) == 3 and len(set(ids)) == 3
    assert all(i not in (a, b) for i in ids)


def test_genome_endpoints_404() -> None:
    assert client.get("/v1/genomes/lab:g0:genome9999").status_code == 404
    assert client.post("/v1/developments", json={"genome_id": "nope", "seed": 0}).status_code == 404


def test_session_evolution_launches_job(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(selections_mod, "_OUT_ROOT", tmp_path / "runs")
    monkeypatch.setattr(selections_mod, "_TRACKING_ROOT", tmp_path / "mlruns")
    monkeypatch.setattr(
        selections_mod, "_run_one", lambda sel, seed: {"seed": seed, "run_dir": "x"}
    )
    sid = _create()["session_id"]
    resp = client.post(f"/v1/sessions/{sid}/evolutions?generations=0")
    assert resp.status_code == 202
    assert _wait_job(resp.json()["job_id"])["status"] == "done"


def test_model_driven_session_pushes_brain_activation() -> None:
    """模型驱动会话（DanioNet）release 后经 WS 推 brain.activation。"""
    resp = client.post("/v1/sessions", json={"master_seed": 1103, "model_driven": True})
    assert resp.status_code == 201, resp.text
    sid = resp.json()["session_id"]
    with client.websocket_connect(f"/v1/ws?session_id={sid}") as ws:
        assert ws.receive_json()["type"] == "sys.hello"
        client.post(f"/v1/sessions/{sid}/release?steps=2")
        frames = []
        for _ in range(6):
            frames.append(ws.receive_json())
            if any(f["type"] == "brain.activation" for f in frames):
                break
        ba = next(f for f in frames if f["type"] == "brain.activation")
        assert ba["payload"]["session_id"] == sid
        fish = ba["payload"]["fish"]
        assert fish and all(isinstance(v, list) and v for v in fish.values())


def test_model_driven_session_loads_checkpoint() -> None:
    """`checkpoint_path`（`pipeline §6`）：直接加载冻结网络，population = checkpoint 个体数。"""
    resp = client.post(
        "/v1/sessions",
        json={
            "master_seed": 250927,
            "model_driven": True,
            "checkpoint_path": "artifacts/demo/checkpoint_v1.pt",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["population"] == 1
    with client.websocket_connect(f"/v1/ws?session_id={body['session_id']}") as ws:
        assert ws.receive_json()["type"] == "sys.hello"
        client.post(f"/v1/sessions/{body['session_id']}/release?steps=2")
        frames = []
        for _ in range(6):
            frames.append(ws.receive_json())
            if any(f["type"] == "brain.activation" for f in frames):
                break
        assert any(f["type"] == "brain.activation" for f in frames)
