"""Arena 事件日志落盘（`core §5.1` 落盘层；run 目录布局 owner = `experiment §5.1`）。

契约：
- 文件：`results/runs/<experiment_id>-s<seed>/events.jsonl`（**不入库**，随 run 归档）；
- 格式：JSONL，首行 `header`（run 级上下文），其后逐条 arena 事件 `Event.to_dict()`
  `{seq, type, step, payload}`（信封/词表 owner = `arena §18.4`）；
- schema：`schemas/event_log.schema.json`（已冻结）。

本模块只做**写入与组 header**，不定义事件字段语义（照抄 arena）；run 级上下文
（`experiment_id / episode_id / environment_id / generation / episode_seed`）由调用方提供。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from evogenesis.arena.env import Event
from evogenesis.core.io import write_jsonl

#: 事件日志 schema 版本（独立于 trajectory；owner：`schemas/event_log.schema.json`）。
EVENT_SCHEMA_VERSION = "1.0.0"


def episode_event_header(
    *,
    experiment_id: str,
    episode_id: str,
    environment_id: str,
    generation: int,
    episode_seed: int,
    n_events: int,
) -> dict:
    """事件日志首行 header（`schemas/event_log.schema.json` `$defs/header` 的全部必填字段）。"""
    return {
        "record_type": "header",
        "schema_version": EVENT_SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "episode_id": episode_id,
        "environment_id": environment_id,
        "generation": generation,
        "episode_seed": episode_seed,
        "n_events": int(n_events),
    }


def event_record(event: Event) -> dict:
    """一条事件的磁盘形态（信封 owner = `arena §18.4.1`）。"""
    return event.to_dict()


def write_event_log(path: Path, header: dict, events: Iterable[Event]) -> Path:
    """写事件日志 JSONL：首行 header，其后逐事件（`core §5.1`）。"""
    write_jsonl(path, [header, *(event_record(event) for event in events)])
    return path


def write_episode_log(
    path: Path,
    *,
    experiment_id: str,
    environment_id: str,
    generation: int,
    episode_seed: int,
    events: Sequence[Event],
    episode_id: str = "ep0001",
) -> Path:
    """组 header 并写事件日志（一次调用，避免各入口重复拼 header）。"""
    header = episode_event_header(
        experiment_id=experiment_id,
        episode_id=episode_id,
        environment_id=environment_id,
        generation=generation,
        episode_seed=episode_seed,
        n_events=len(events),
    )
    return write_event_log(path, header, events)


__all__ = ["episode_event_header", "event_record", "write_episode_log", "write_event_log"]
