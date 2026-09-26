"""契约示例 `schemas/examples/event_log_example.jsonl` 与事件词表 v1 的一致性守护。

权威词表 = `arena/Danio_Arena设计与实现说明.md` §18.4.2 + `tests/test_arena.py::KNOWN_EVENTS`。
本测试只校验示例文件本身（类型齐全、payload 键正确），不驱动仿真。
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "schemas" / "examples" / "event_log_example.jsonl"

KNOWN_EVENTS = {
    "arena.spawn",
    "arena.prey_captured",
    "arena.capture_attempt",
    "arena.escape",
    "arena.energy_depleted",
    "arena.episode_end",
    "arena.fish_captured",
    "arena.collision",
}

REQUIRED_PAYLOAD_KEYS = {
    "arena.spawn": {"entity_id"},
    "arena.capture_attempt": {
        "fish_id",
        "prey_id",
        "distance",
        "size_ratio",
        "threshold",
        "capture_radius",
        "result",
    },
    "arena.prey_captured": {"fish_id", "prey_id", "distance", "size_ratio", "food_reward"},
    "arena.collision": {"fish_id", "obstacle_id"},
    "arena.escape": {"fish_id", "threat_source"},
    "arena.energy_depleted": {"fish_id", "survival_steps"},
    "arena.fish_captured": {"fish_id", "predator_id", "survival_steps"},
    "arena.episode_end": {"steps", "fish_alive", "prey_remaining"},
}


def _records() -> list[dict]:
    return [json.loads(line) for line in EXAMPLE.read_text(encoding="utf-8").splitlines() if line]


def test_example_envelope_and_vocabulary():
    records = _records()
    assert records, "示例文件为空"
    for record in records:
        assert set(record) == {"seq", "type", "step", "payload"}
        assert record["type"] in KNOWN_EVENTS
    assert {r["type"] for r in records} == KNOWN_EVENTS


def test_example_payload_keys_match_contract():
    for record in _records():
        assert REQUIRED_PAYLOAD_KEYS[record["type"]] <= set(record["payload"])


def test_capture_attempt_example_is_consistent_with_size_gate():
    attempt = next(r for r in _records() if r["type"] == "arena.capture_attempt")
    assert attempt["payload"]["result"] == "too_small_to_eat"
    assert attempt["payload"]["size_ratio"] < attempt["payload"]["threshold"]
