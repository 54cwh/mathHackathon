"""Stage-1 专家轨迹落盘的守护测试（`schemas/trajectory.schema.json` 为唯一契约）。

守住三件事：
1. 写出的 header / step **逐条通过冻结的 JSON Schema 校验**（最强守护，不靠人眼对齐字段名）；
2. 12 维 observation 名与 `DanioNet设计规范.md` §2 的冻结表逐字一致（BC 的特征顺序）；
3. `write_episode` 的 JSONL 形态：首行 header、其后 step，行数 = 1 + len(steps)。
"""

import json
from pathlib import Path

import jsonschema
import pytest

from evogenesis.experiment.trajectories import (
    OBS_DIM_NAMES,
    SCHEMA_VERSION,
    episode_header,
    step_record,
    write_episode,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "trajectory.schema.json").read_text(encoding="utf-8"))

# §2 冻结表（DanioNet设计规范.md），逐字抄录作对照基线
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


def _header(**over) -> dict:
    base = dict(
        experiment_id="exp_test",
        episode_id="ep0001",
        environment_id="default",
        generation=0,
        episode_seed=1103,
        total_steps=600,
        environment_config={"n_prey": 24, "n_predators": 3},
    )
    base.update(over)
    return episode_header(**base)


def _step(**over) -> dict:
    base = dict(
        fish_id="f0001",
        genome_id="g0001",
        step=0,
        observation=[0.5] * 12,
        expert_action=[0.1, 0.6],
        is_first=True,
        is_last=False,
    )
    base.update(over)
    return step_record(**base)


def test_obs_dim_names_match_frozen_spec():
    assert tuple(OBS_DIM_NAMES) == FROZEN_12
    assert len(OBS_DIM_NAMES) == 12


def test_header_passes_schema():
    jsonschema.validate(_header(), SCHEMA)


def test_step_passes_schema():
    jsonschema.validate(_step(), SCHEMA)


def test_step_index_bound_is_not_hardcoded_in_schema():
    """step 上界 = header.total_steps − 1；episode_steps 可覆盖，schema 不硬编码 599。"""
    jsonschema.validate(_step(step=599), SCHEMA)
    jsonschema.validate(_header(total_steps=1200), SCHEMA)
    jsonschema.validate(_step(step=600), SCHEMA)  # 在 total_steps=1200 的 episode 内合法


def test_no_invented_fields():
    """`additionalProperties: false` —— 多余字段必须被拒（防「AI 填空」）。"""
    bad = _step()
    bad["reward_guess"] = 1.0
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


def test_schema_version_is_semver():
    assert SCHEMA_VERSION.count(".") == 2
    jsonschema.validate(_header(), SCHEMA)


def test_write_episode_jsonl_shape(tmp_path: Path):
    steps = [_step(step=i, is_first=(i == 0)) for i in range(3)]
    out = write_episode(tmp_path / "trajectories" / "episode_ep0001.jsonl", _header(), steps)
    lines = out.read_text(encoding="utf-8").strip().split(chr(10))
    assert len(lines) == 1 + len(steps)  # 首行 header + N 行 step
    recs = [json.loads(x) for x in lines]
    assert recs[0]["record_type"] == "header"
    assert [r["record_type"] for r in recs[1:]] == ["step", "step", "step"]
    for rec in recs:
        jsonschema.validate(rec, SCHEMA)
