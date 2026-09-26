"""序列化读写（core §0 / §7）。

JSONL（元数据/轨迹/事件）、CSV（指标表）、Parquet（大表）；数组统一 ``float32``（§7），
时间戳 ISO-8601 UTC（``Z``）。
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


def now_iso() -> str:
    """当前时间，ISO-8601 UTC（RFC 3339 ``Z``）。"""
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_jsonl(path: str | Path, records: Iterable[Mapping[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path)
    with target.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, Any]],
    fieldnames: list[str] | None = None,
) -> None:
    materialized = list(rows)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        if not materialized:
            target.write_text("", encoding="utf-8")
            return
        fieldnames = list(materialized[0].keys())
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(materialized)


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_parquet(path: str | Path, records: Iterable[Mapping[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(list(records)), target)


def read_parquet(path: str | Path) -> list[dict[str, Any]]:
    return pq.read_table(Path(path)).to_pylist()


def _npz_path(path: str | Path) -> Path:
    target = Path(path)
    return target if target.suffix == ".npz" else target.with_suffix(".npz")


def save_array(path: str | Path, array: Any, key: str = "arr") -> Path:
    """以 ``float32`` 存数组（§7：禁止隐式提升为 float64）。"""
    target = _npz_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(target, **{key: np.asarray(array, dtype=np.float32)})
    return target


def load_array(path: str | Path, key: str = "arr") -> np.ndarray:
    with np.load(_npz_path(path)) as data:
        return data[key]
