"""漂移守护：`configs/*.yaml` ↔ `docs/参数总表.json` 的值同步。

规则（`AGENTS.md` 属地）：参数**取值** owner 是 `configs/`，参数总表须同步；值冲突以
`configs/` 为准。本测试对参数总表中每条带 `config` 定位（形如
``configs/xxx.yaml → a.b.c``）且 `value` 为标量的条目，断言其值等于该配置文件对应键的
实际值。派生量（无 `config`）与结构化值（dict/list、或 `value` 为描述串而对端为 dict，
如 `env_*`）不在此守护范围。

它是**只读**守护：不改任何文档或配置，仅检出漂移。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
TABLE_PATH = ROOT / "docs" / "参数总表.json"
_CONFIG_RE = re.compile(r"^(configs/[^\s]+\.ya?ml)\s*→\s*([A-Za-z0-9_.]+)\s*$")


def _load_yaml(path: str) -> Any:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def _navigate(data: Any, dotted: str) -> tuple[bool, Any]:
    cursor = data
    for key in dotted.split("."):
        if not isinstance(cursor, dict) or key not in cursor:
            return False, None
        cursor = cursor[key]
    return True, cursor


def _scalar_equal(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-12
    return a == b


def test_param_table_config_paths_have_expected_format() -> None:
    """每条带 `config` 的条目都须是 ``configs/*.yaml → a.b.c`` 形式（防格式漂移）。"""
    table = json.loads(TABLE_PATH.read_text(encoding="utf-8"))
    bad = [
        (p["name"], p["config"])
        for p in table["parameters"]
        if p.get("config") and not _CONFIG_RE.match(p["config"])
    ]
    assert not bad, f"参数总表 config 定位格式异常：{bad}"


def test_param_table_values_match_configs() -> None:
    """参数总表的标量值与对应 `configs/*.yaml` 实际值逐条一致。"""
    table = json.loads(TABLE_PATH.read_text(encoding="utf-8"))
    cache: dict[str, Any] = {}
    mismatches: list[tuple[str, Any, Any, str]] = []
    asserted = 0
    for param in table["parameters"]:
        config = param.get("config")
        value = param.get("value")
        if not config:
            continue
        match = _CONFIG_RE.match(config)
        if match is None:
            continue
        path, dotted = match.group(1), match.group(2)
        cache.setdefault(path, _load_yaml(path))
        found, actual = _navigate(cache[path], dotted)
        # 派生量 / 结构化值 / 描述串对 dict（如 env_*）不在此守护范围。
        if (
            not found
            or actual is None
            or value is None
            or isinstance(actual, (dict, list))
            or isinstance(value, (dict, list))
        ):
            continue
        asserted += 1
        if not _scalar_equal(actual, value):
            mismatches.append((param["name"], value, actual, config))
    assert asserted > 0, "未断言任何参数，参数总表 config 定位可能已整体失效"
    assert not mismatches, f"参数总表与 configs 漂移（以 configs 为准）：{mismatches}"
