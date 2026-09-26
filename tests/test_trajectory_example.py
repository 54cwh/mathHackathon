"""契约示例 `trajectory_example.jsonl` 与 `schemas/trajectory.schema.json` 的一致性守护。

只校验示例文件本身（首行 header + 逐条 step 过冻结 schema、观测 12 维、动作 2 维），不驱动仿真。
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "schemas" / "examples" / "trajectory_example.jsonl"
SCHEMA = json.loads((ROOT / "schemas" / "trajectory.schema.json").read_text(encoding="utf-8"))


def _records() -> list[dict]:
    return [json.loads(line) for line in EXAMPLE.read_text(encoding="utf-8").splitlines() if line]


def test_example_is_header_then_steps_all_valid():
    records = _records()
    assert records, "示例文件为空"
    header, *steps = records
    assert header["record_type"] == "header"
    assert header["total_steps"] == len(steps) == 8
    for record in records:
        jsonschema.validate(record, SCHEMA)


def test_example_steps_have_stable_ids_and_frozen_dims():
    _, *steps = _records()
    for index, record in enumerate(steps):
        assert record["step"] == index
        assert record["fish_id"].startswith("exp-example:g0:fish")
        assert record["genome_id"].startswith("exp-example:g0:genome")
        assert len(record["observation"]) == 12
        assert all(0.0 <= value <= 1.0 for value in record["observation"])
        assert len(record["expert_action"]) == 2
