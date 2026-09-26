"""实验覆盖参数解析（`--override section.key=value`）。

供 Experiment D 消融臂（`experiment/实验与评价体系.md` §3.4 / `connectome §9`）在不改 YAML
的前提下换配置：如 `connectome.tau_min=5.5`、`connectome.distance_lambda=0`。值用
``yaml.safe_load`` 类型化（``5.5`` → float、``0`` → int、``true`` → bool）。owner：本文件
（薄解析，优先级与 `core` 的 `CLI > env > file > default` 一致）。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import yaml

from evogenesis.core.config import deep_update


def parse_overrides(items: Sequence[str]) -> dict[str, Any]:
    """把 ``["connectome.tau_min=5.5", ...]`` 解析成段级嵌套 dict。

    每项须形如 ``section.key=value``（单层字段）；重复段自动合并；非法形态抛 ``ValueError``。
    """
    overrides: dict[str, Any] = {}
    for item in items:
        key, sep, raw = item.partition("=")
        if not sep:
            raise ValueError(f"--override 需形如 section.key=value，得到 {item!r}")
        section, dot, field = key.partition(".")
        if not dot or not section or not field or "." in field:
            raise ValueError(f"--override 键须形如 section.key（单层字段），得到 {item!r}")
        deep_update(overrides, {section: {field: yaml.safe_load(raw)}})
    return overrides


__all__ = ["parse_overrides"]
