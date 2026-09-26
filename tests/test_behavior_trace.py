"""整群行为 trace 守护测试（`schemas/behavior_trace.schema.json`；producer=experiment）。

守住：header/step 逐条过 schema；多鱼（all-fish）；死鱼止步的稀疏性；`is_first`/`is_last`
标记；`header.total_steps` = episode 长度（非文件行数）；`write_trace` 的 JSONL 形态。
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from evogenesis.arena.config import load_arena_config
from evogenesis.arena.env import DanioArena
from evogenesis.core.ids import mint_id
from evogenesis.core.seed import SeedManager
from evogenesis.experiment.arena_rollout import expert_rollout
from evogenesis.experiment.behavior_trace import (
    OBS_DIM_NAMES,
    TraceCollector,
    trace_header,
    write_trace,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "behavior_trace.schema.json").read_text("utf-8"))
FROZEN_12 = (
    "prey_left_signal",
    "prey_right_signal",
    "threat_left_signal",
    "threat_right_signal",
    "obstacle_left_signal",
    "obstacle_right_signal",
    "prey_relative_size",
    "predator_relative_size",
    "looming_rate",
    "current_speed",
    "energy",
    "hunger",
)
EXPERIMENT_ID = "exp-btrace"
MASTER_SEED = 1103
STEPS = 6


def _run(n_fish: int = 6) -> tuple[dict, list[dict], list[str]]:
    config = load_arena_config(
        ROOT / "configs" / "default_arena.yaml",
        overrides={"world": {"episode_steps": STEPS}, "population": {"n_fish": n_fish}},
    )
    fish_ids = [mint_id(EXPERIMENT_ID, "fish", 0, i) for i in range(n_fish)]
    genome_ids = [mint_id(EXPERIMENT_ID, "genome", 0, i) for i in range(n_fish)]
    manager = SeedManager(MASTER_SEED)
    arena = DanioArena(
        config,
        spawn_seed=manager.seed("arena_spawn", 0),
        dynamics_seed=manager.seed("arena_dynamics", 0),
        fish_ids=fish_ids,
        genome_ids=genome_ids,
    )
    arena.reset()
    collector = TraceCollector(arena)
    for rollout in expert_rollout(arena, steps=STEPS):
        collector.add(rollout)
    header = trace_header(
        experiment_id=EXPERIMENT_ID,
        episode_id="ep0001",
        environment_id="default",
        generation=0,
        episode_seed=manager.seed("arena_spawn", 0),
        dynamics_seed=manager.seed("arena_dynamics", 0),
        total_steps=STEPS,
        terminated=False,
        truncated=False,
        fish_ids=fish_ids,
    )
    return header, collector.records(), fish_ids


def test_obs_dim_names_match_frozen_spec():
    assert tuple(OBS_DIM_NAMES) == FROZEN_12


def test_records_pass_schema():
    header, steps, _ = _run()
    jsonschema.validate(header, SCHEMA)
    assert steps
    for rec in steps:
        jsonschema.validate(rec, SCHEMA)


def test_header_carries_self_contained_replay_seeds():
    header, _, _ = _run()
    assert isinstance(header["episode_seed"], int)
    assert isinstance(header["dynamics_seed"], int)
    assert header["episode_seed"] != header["dynamics_seed"]
    assert header["total_steps"] == STEPS


def test_records_cover_all_fish_and_steps_are_contiguous():
    header, steps, fish_ids = _run()
    assert set(header["fish_ids"]) == set(fish_ids)
    by_fish: dict[str, list[int]] = {}
    for rec in steps:
        assert rec["fish_id"] in fish_ids
        by_fish.setdefault(rec["fish_id"], []).append(rec["step"])
    assert by_fish, "无记录"
    for fid, seq in by_fish.items():
        assert seq == list(range(len(seq))), fid


def test_is_first_is_last_mark_each_fish_boundary():
    _, steps, _ = _run()
    for fid in {rec["fish_id"] for rec in steps}:
        own = [rec for rec in steps if rec["fish_id"] == fid]
        assert [rec["is_first"] for rec in own] == [True] + [False] * (len(own) - 1)
        assert [rec["is_last"] for rec in own] == [False] * (len(own) - 1) + [True]


def test_trace_is_sparse_when_fish_are_fewer_than_episode():
    """稀疏性守卫：每鱼记录数 ≤ total_steps（死鱼止步），行数 = Σ 每鱼步数。"""
    header, steps, _ = _run()
    assert len(steps) <= header["total_steps"] * len(header["fish_ids"])


def test_write_trace_jsonl_shape(tmp_path: Path):
    header, steps, _ = _run()
    out = write_trace(tmp_path / "behavior_trace" / "episode_ep0001.jsonl", header, steps)
    lines = out.read_text(encoding="utf-8").strip().split(chr(10))
    assert len(lines) == 1 + len(steps)
    recs = [json.loads(line) for line in lines]
    assert recs[0]["record_type"] == "header"
    assert all(rec["record_type"] == "step" for rec in recs[1:])
