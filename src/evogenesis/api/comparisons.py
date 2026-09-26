"""对比产物只读接口（`results/tables/`）—— COMPARE 段数据源（`API接口.md` §2.5）。

产物由离线脚本（`scripts/run_baselines.py` 等）写入 `results/tables/*.json`（格式 owner：
`experiment/实验与评价体系.md`）。本端点**只读曝光**：不改表、不补值、不建强类型
（字段随 producer 版本变化，前端对缺失项显示「未记录」）。

范围与安全：只读 `results/tables/` 下**一层**的既有 `.json`；`id` 必须是单个路径段
（禁 `/`、`\\`、`..`），解析后再断言仍位于该根目录之内；不写入、不递归。
`results/` 被 git 忽略，故全新检出时列表为空（前端须容忍空表）。
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from evogenesis.api.schemas import ComparisonTable, ComparisonTableSummary

router = APIRouter(prefix="/v1")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TABLES_ROOT = _REPO_ROOT / "results" / "tables"


def _kind(payload: dict) -> str:
    """按顶层键判定表种类（`API接口.md` §2.5）。"""
    if isinstance(payload.get("arms"), list):
        return "ablation"
    if "aggregate" in payload and "degradation" in payload:
        return "robustness"
    if isinstance(payload.get("per_metric"), dict):
        return "environment_baseline"
    return "other"


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _table_path(table_id: str) -> Path:
    """`id` -> 文件路径；非法或不安全一律 404（不泄露路径细节）。"""
    if not table_id or "/" in table_id or "\\" in table_id or table_id in {".", ".."}:
        raise HTTPException(status_code=404, detail=f"comparison {table_id!r} not found")
    root = _TABLES_ROOT.resolve()
    candidate = (root / f"{table_id}.json").resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise HTTPException(status_code=404, detail=f"comparison {table_id!r} not found")
    return candidate


@router.get("/comparisons", response_model=list[ComparisonTableSummary])
def list_comparisons() -> list[ComparisonTableSummary]:
    """列出可用对比表（`id` = 文件名去 `.json`）。（`API接口.md` §2.5）"""
    if not _TABLES_ROOT.is_dir():
        return []
    items: list[ComparisonTableSummary] = []
    for path in sorted(_TABLES_ROOT.glob("*.json")):
        payload = _read_json(path)
        if payload is None:
            continue
        items.append(
            ComparisonTableSummary(
                id=path.stem,
                kind=_kind(payload),
                experiment_id=str(payload.get("experiment_id") or ""),
            )
        )
    return items


@router.get("/comparisons/{table_id}", response_model=ComparisonTable)
def get_comparison(table_id: str) -> ComparisonTable:
    """读取一张对比表全文（`payload` 原样透传）。（`API接口.md` §2.5）"""
    payload = _read_json(_table_path(table_id))
    if payload is None:
        raise HTTPException(status_code=404, detail=f"comparison {table_id!r} not found")
    return ComparisonTable(id=table_id, kind=_kind(payload), payload=payload)


__all__ = ["router"]
