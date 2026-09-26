"""Arena 事件日志落盘的守护测试（`schemas/event_log.schema.json` 为唯一契约）。

守住：写出的 header + 每条事件**逐条通过冻结 schema**；行数 = 1 + len(events)；
`n_events` 与实际一致；同输入两次写盘逐字节一致。
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from evogenesis.arena.config import ArenaConfig
from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import ExpertPolicy
from evogenesis.experiment.events import episode_event_header, write_event_log

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "event_log.schema.json").read_text(encoding="utf-8"))


def _run_arena(steps: int = 20) -> DanioArena:
    arena = DanioArena(ArenaConfig(), spawn_seed=7, dynamics_seed=7)
    arena.reset()
    expert = ExpertPolicy()
    for _ in range(steps):
        actions = {fid: expert(arena.observe(fid)) for fid, f in arena.fish.items() if f.alive}
        if arena.step(actions).done:
            break
    return arena


def _header(n_events: int) -> dict:
    return episode_event_header(
        experiment_id="exp-events",
        episode_id="ep0001",
        environment_id="default",
        generation=0,
        episode_seed=1103,
        n_events=n_events,
    )


def test_writes_header_then_events_all_valid(tmp_path: Path):
    arena = _run_arena()
    path = write_event_log(tmp_path / "events.jsonl", _header(len(arena.events)), arena.events)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    header, *events = records
    assert header["record_type"] == "header"
    assert header["n_events"] == len(events) == len(arena.events)
    for record in records:
        jsonschema.validate(record, SCHEMA)


def test_same_input_writes_identical_bytes(tmp_path: Path):
    arena = _run_arena()
    header = _header(len(arena.events))
    a = write_event_log(tmp_path / "a.jsonl", header, arena.events)
    b = write_event_log(tmp_path / "b.jsonl", header, arena.events)
    assert a.read_bytes() == b.read_bytes()
