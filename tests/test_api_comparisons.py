"""对比产物只读端点（`API接口.md` §2.5）—— 用临时目录固定契约，不依赖 git 忽略的 `results/`。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from evogenesis.api import comparisons as comparisons_mod
from evogenesis.api.app import app

client = TestClient(app)

_ABLATION = {
    "experiment_id": "expD",
    "seeds": [1],
    "steps": 20,
    "n_agents": 1,
    "arms": [
        {"arm": "full", "kind": "architecture", "metrics": None, "complexity": {}, "note": ""},
        {
            "arm": "tau_homo",
            "kind": "architecture",
            "metrics": {"survival": {"mean": 1.0, "std": None, "n": 1}},
        },
    ],
}
_ROBUSTNESS = {"experiment_id": "expE", "aggregate": {}, "degradation": {}}


def _write(root: Path, name: str, payload: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(json.dumps(payload), encoding="utf-8")


def test_list_and_get_comparison(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(comparisons_mod, "_TABLES_ROOT", tmp_path)
    _write(tmp_path, "expD-abl.json", _ABLATION)
    _write(tmp_path, "expE-rob.json", _ROBUSTNESS)
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")

    items = client.get("/v1/comparisons").json()
    kinds = {i["id"]: (i["kind"], i["experiment_id"]) for i in items}
    assert kinds["expD-abl"] == ("ablation", "expD")
    assert kinds["expE-rob"] == ("robustness", "expE")
    assert "broken" not in kinds  # 坏文件跳过，不使整个列表失败

    body = client.get("/v1/comparisons/expD-abl").json()
    assert body["kind"] == "ablation"
    assert [a["arm"] for a in body["payload"]["arms"]] == ["full", "tau_homo"]


def test_comparison_path_safety_and_404(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(comparisons_mod, "_TABLES_ROOT", tmp_path)
    _write(tmp_path, "ok.json", _ABLATION)
    assert client.get("/v1/comparisons/missing").status_code == 404
    # 路径段安全性：含分隔符 / 上跳一律 404（不泄露、不越界）
    for bad in ("..%2Fok", "a%2Fb", "..", "a%5Cb"):
        assert client.get(f"/v1/comparisons/{bad}").status_code == 404


def test_comparison_missing_root_returns_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(comparisons_mod, "_TABLES_ROOT", tmp_path / "does-not-exist")
    assert client.get("/v1/comparisons").json() == []
