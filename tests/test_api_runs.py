"""磁盘 run 只读接口测试（`API接口.md` §2.4；Evolution Dashboard 数据源）。

用 `tmp_path` 造合成 run，**不依赖仓库 `results/` 的真实产物**（否则测试会随实验产物漂移）。
覆盖：列表排序/分页、逐代解析、逐个体 fitness、缺产物时的降级，以及路径安全（越权一律 404）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from evogenesis.api import runs as runs_mod
from evogenesis.api.app import app

client = TestClient(app)


def _write_run(
    root: Path,
    run_id: str,
    *,
    seed: int,
    created_at: str,
    generations: list[dict],
    fitness: dict[int, list[float]] | None = None,
) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "experiment_id": run_id.split("-s")[0],
                "seed": seed,
                "status": "completed",
                "created_at": created_at,
            }
        ),
        encoding="utf-8",
    )
    with (run_dir / "evolution.jsonl").open("w", encoding="utf-8") as handle:
        for row in generations:
            handle.write(json.dumps(row) + "\n")
    for generation, values in (fitness or {}).items():
        gen_dir = run_dir / "generations" / f"g{generation:04d}"
        gen_dir.mkdir(parents=True)
        with (gen_dir / "fitness.jsonl").open("w", encoding="utf-8") as handle:
            for value in values:
                handle.write(
                    json.dumps(
                        {
                            "generation": generation,
                            "genome_id": "g",
                            "fish_id": "f",
                            "viable": True,
                            "failure_reason": None,
                            "fitness": value,
                        }
                    )
                    + "\n"
                )


@pytest.fixture
def runs_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """把接口的根目录指到合成目录（接口只读该全局，故 monkeypatch 即可）。"""
    monkeypatch.setattr(runs_mod, "_RUNS_ROOT", tmp_path)
    _write_run(
        tmp_path,
        "old-run-s1",
        seed=1,
        created_at="2026-09-25T00:00:00Z",
        generations=[{"generation": 0, "n_viable": 3, "fitness_mean": 0.5}],
    )
    _write_run(
        tmp_path,
        "new-run-s1103",
        seed=1103,
        created_at="2026-09-26T00:00:00Z",
        generations=[
            {"generation": 0, "p_A": 1.0, "p_B": 1.0, "n_viable": 4, "mean_neuron": 38.0},
            {"generation": 1, "p_A": 0.75, "p_B": 0.5, "n_viable": 2, "mean_neuron": 30.0},
        ],
        fitness={0: [0.1, 0.2, 0.3], 1: [0.4, 0.5]},
    )
    # 目录但无 metadata / 无 evolution：也要能列出（字段降级），不崩
    (tmp_path / "bare-run-s1").mkdir()
    return tmp_path


def test_list_runs_sorted_by_created_at_desc(runs_root: Path) -> None:
    resp = client.get("/v1/runs?limit=10")
    assert resp.status_code == 200
    body = resp.json()
    ids = [item["run_id"] for item in body["items"]]
    assert ids == ["new-run-s1103", "old-run-s1", "bare-run-s1"]
    assert body["next_cursor"] is None
    first = body["items"][0]
    assert first["experiment_id"] == "new-run"
    assert first["seed"] == 1103
    assert first["generations"] == 2


def test_list_runs_paginates(runs_root: Path) -> None:
    first = client.get("/v1/runs?limit=2").json()
    assert len(first["items"]) == 2
    assert first["next_cursor"] == "2"
    second = client.get(f"/v1/runs?limit=2&cursor={first['next_cursor']}").json()
    assert [item["run_id"] for item in second["items"]] == ["bare-run-s1"]
    assert second["next_cursor"] is None
    assert client.get("/v1/runs?cursor=abc").status_code == 422
    assert client.get("/v1/runs?cursor=-1").status_code == 422


def test_run_evolution_series_and_fitness(runs_root: Path) -> None:
    body = client.get("/v1/runs/new-run-s1103/evolution").json()
    assert body["run_id"] == "new-run-s1103"
    assert body["seed"] == 1103
    assert [row["generation"] for row in body["generations"]] == [0, 1]
    # 行原样透传（不重命名生产者字段）
    assert body["generations"][1]["p_A"] == 0.75
    assert body["fitness"] == [
        {"generation": 0, "values": [0.1, 0.2, 0.3]},
        {"generation": 1, "values": [0.4, 0.5]},
    ]


def test_run_evolution_degrades_when_artifacts_missing(runs_root: Path) -> None:
    """老 run 缺 `evolution.jsonl` / 缺逐个体 fitness 时返回空表，而不是报错。"""
    body = client.get("/v1/runs/old-run-s1/evolution").json()
    assert len(body["generations"]) == 1
    assert body["fitness"] == []  # 没有 generations/*/fitness.jsonl
    bare = client.get("/v1/runs/bare-run-s1/evolution").json()
    assert bare["generations"] == []
    assert bare["fitness"] == []


@pytest.mark.parametrize("run_id", ["nope", "..", "../etc", "a/b", "%2e%2e"])
def test_run_evolution_rejects_unsafe_or_unknown(run_id: str, runs_root: Path) -> None:
    assert client.get(f"/v1/runs/{run_id}/evolution").status_code == 404
