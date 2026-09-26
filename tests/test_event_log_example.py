"""契约示例 `event_log_example.jsonl` 与 `schemas/event_log.schema.json` 的一致性守护。

权威词表 = `arena/Danio_Arena设计与实现说明.md` §18.4.2 + `tests/test_arena.py::KNOWN_EVENTS`。
本测试只校验示例文件本身（首行 header + 8 类事件齐全、逐条通过冻结 schema），不驱动仿真。
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "schemas" / "examples" / "event_log_example.jsonl"
SCHEMA = json.loads((ROOT / "schemas" / "event_log.schema.json").read_text(encoding="utf-8"))

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


def _records() -> list[dict]:
    return [json.loads(line) for line in EXAMPLE.read_text(encoding="utf-8").splitlines() if line]


def test_example_has_header_then_events_all_valid_against_schema():
    records = _records()
    assert records, "示例文件为空"
    header, *events = records
    assert header["record_type"] == "header"
    assert header["n_events"] == len(events) == len(KNOWN_EVENTS)
    for record in records:
        jsonschema.validate(record, SCHEMA)


def test_example_event_vocabulary_is_complete():
    _, *events = _records()
    for event in events:
        assert event["type"] in KNOWN_EVENTS
    assert {e["type"] for e in events} == KNOWN_EVENTS


def test_capture_attempt_example_is_consistent_with_size_gate():
    _, *events = _records()
    attempt = next(e for e in events if e["type"] == "arena.capture_attempt")
    assert attempt["payload"]["result"] == "too_small_to_eat"
    assert attempt["payload"]["size_ratio"] < attempt["payload"]["threshold"]
