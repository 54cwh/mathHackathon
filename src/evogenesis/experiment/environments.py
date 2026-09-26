"""环境对照三组（E-F）的加载（`实验与评价体系.md` §4 的取值实现）。

owner：`experiment/实验与评价体系.md` §4 定义**设计**（单因子对照）与 `environment_id`；
取值落 `configs/experiment_environments.yaml`（Tier-5）；依据与状态落 `docs/参数总表.json`。
本模块只做**读取与展开**，不定义任何数值，也不改变 Arena 契约。
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
ENVIRONMENTS_FILE = ROOT / "configs" / "experiment_environments.yaml"

# 基线（对照的参照物，不是三组之一）：默认 Arena 配置
BASELINE = "default"


def load_environments() -> dict:
    """返回 `environment_id -> 段级 overrides` 的映射（元信息键已剔除）。"""
    data = yaml.safe_load(ENVIRONMENTS_FILE.read_text(encoding="utf-8")) or {}
    envs = data.get("environments") or {}
    return {
        name: {k: v for k, v in spec.items() if isinstance(v, dict)} for name, spec in envs.items()
    }


def load_environment(name: str) -> dict:
    """取单个环境的**嵌套 overrides**（形状同 YAML 段），供 `load_arena_config(overrides=)`。"""
    envs = load_environments()
    if name not in envs:
        raise KeyError(
            f"未知 environment {name!r}；可选：{sorted(envs)}（见 {ENVIRONMENTS_FILE.name}）"
        )
    return envs[name]


def environment_env_vars(overrides: dict | None) -> dict[str, str]:
    """展成 `EVOGENESIS_<SECTION>__<FIELD>`（`core §config` 分层）。

    子进程 `run_experiment.py` 按同一分层加载，故其落盘的
    `arena_config_resolved.json` **如实反映**环境覆盖，而非一份假的默认快照。
    """
    out: dict[str, str] = {}
    for section, fields_ in (overrides or {}).items():
        for field_name, value in fields_.items():
            out[f"EVOGENESIS_{section.upper()}__{field_name.upper()}"] = str(value)
    return out


__all__ = [
    "BASELINE",
    "ENVIRONMENTS_FILE",
    "environment_env_vars",
    "load_environment",
    "load_environments",
]
