"""run / 逐代产物写者（字段 owner：`experiment/实验与评价体系.md` §5.1–§5.2）。

run（`run_arena.py`）与代循环（`evolution_run.py`）共用同一套产物字段与写者，避免两处漂移。
本模块只做写盘与行组装，指标口径来自 `experiment/metrics.py`，事件词表来自 `arena §18.4.2`。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from evogenesis.core.io import write_csv, write_jsonl

#: Arena 事件词表（权威 = `arena §18.4.2` + `tests::KNOWN_EVENTS`）；用于 episodes.jsonl 计数列。
EVENT_KEYS: tuple[str, ...] = (
    "arena.spawn",
    "arena.capture_attempt",
    "arena.prey_captured",
    "arena.collision",
    "arena.escape",
    "arena.energy_depleted",
    "arena.fish_captured",
    "arena.episode_end",
)

#: `metrics.csv` 的指标列（原始计数 + §2.1 指标 + 复合分）。
METRIC_COLUMNS: tuple[str, ...] = (
    "survival_steps",
    "captures",
    "capture_attempts",  # 诊断列（§2.1 分母为 encounters）
    "encounters",
    "predator_encounters",
    "escape_successes",
    "collisions",
    "energy_final",
    "survival",
    "capture_rate",
    "prey_capture",
    "escape_success",
    "energy_efficiency",
    "composite_fitness",
)


def dump_json(path: Path, payload: object, *, indent: int | None = None) -> None:
    """写一个 JSON 文件（`seed_summary.json` / 跨 seed 汇总等）。"""
    path.write_text(
        json.dumps(payload, indent=indent, ensure_ascii=False) + chr(10), encoding="utf-8"
    )


def write_metrics_csv(run_dir: Path, rows: list[dict]) -> None:
    """写 `metrics.csv`（逐个体一行）。

    列 = `seed`/`fish_id` + `METRIC_COLUMNS` + **行内出现的附加键**（按首次出现顺序，如
    BC 生命周期的 `phase` / `generation`）——后者不被静默丢弃（`experiment §5.2`）。
    """
    extras: list[str] = []
    for row in rows:
        for key in row:
            if key not in ("seed", "fish_id", *METRIC_COLUMNS) and key not in extras:
                extras.append(key)
    fields = ["seed", "fish_id", *METRIC_COLUMNS, *extras]
    write_csv(
        run_dir / "metrics.csv",
        ({key: row.get(key) for key in fields} for row in rows),
        fieldnames=fields,
    )


def population_record(seed: int, fish_id: str, rec: dict) -> dict:
    """`population.jsonl` 的一行：逐鱼能量/体型轨迹幅度与 motor 命令数（供作图）。"""
    energy = rec.get("energy_trajectory") or []
    size = rec.get("size_trajectory") or []
    return {
        "seed": seed,
        "fish_id": fish_id,
        "generation": rec.get("generation"),
        "survival_steps": rec.get("survival_steps"),
        "captures": rec.get("captures"),
        "encounters": rec.get("encounters"),
        "predator_encounters": rec.get("predator_encounters"),
        "escape_successes": rec.get("escape_successes"),
        "collisions": rec.get("collisions"),
        "energy_first": energy[0] if energy else None,
        "energy_last": energy[-1] if energy else None,
        "energy_min": min(energy) if energy else None,
        "size_first": size[0] if size else None,
        "size_last": size[-1] if size else None,
        "n_motor_commands": len(rec.get("motor_commands") or []),
    }


def write_population(run_dir: Path, seed: int, per_fish: dict[str, dict]) -> None:
    """写 `population.jsonl`（逐个体一行，按 `fish_id` 排序；经 `core.io.write_jsonl`）。"""
    write_jsonl(
        run_dir / "population.jsonl",
        (population_record(seed, fish_id, rec) for fish_id, rec in sorted(per_fish.items())),
    )


def episode_row(
    seed: int, events: Sequence, per_fish: dict[str, dict], steps: int, elapsed: float
) -> dict:
    """`episodes.jsonl` 的一行：事件计数 + 吞吐 + 末步存活数。"""
    counts = {key: 0 for key in EVENT_KEYS}
    for event in events:
        if event.type in counts:
            counts[event.type] += 1
    row: dict = {"seed": seed, "steps": steps, "steps_per_s": round(steps / elapsed, 1)}
    for key in EVENT_KEYS:
        row[key.replace("arena.", "")] = counts[key]
    row["fish_alive_end"] = sum(1 for r in per_fish.values() if r["survival_steps"] >= steps)
    row["n_events_total"] = len(events)
    return row


__all__ = [
    "EVENT_KEYS",
    "METRIC_COLUMNS",
    "dump_json",
    "episode_row",
    "population_record",
    "write_metrics_csv",
    "write_population",
]
