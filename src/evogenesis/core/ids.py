"""稳定 ID 铸造（``core §3.1``，已定稿）。

``mint_id`` 为纯函数、确定性：同一 ``(experiment_id, role, generation_id, index)`` 恒得
同一结果。唯一性域为**单个 experiment**；``index`` 为该代内的稳定序号（写入后不得重排）。
``experiment_id`` / ``environment_id`` 由编排层与实验对照配置给定，本模块不铸造。
"""

from __future__ import annotations

_ROLES = ("fish", "genome")


def mint_id(experiment_id: str, role: str, generation_id: int, index: int) -> str:
    """按 ``<experiment_id>:g<generation_id>:<role><index:04d>`` 铸造稳定 ID（``core §3.1``）。"""
    if not experiment_id:
        raise ValueError("experiment_id 不能为空")
    if ":" in experiment_id:
        raise ValueError("experiment_id 不得含 ':'（ID 以其为分隔符，须可无歧义解析）")
    if role not in _ROLES:
        raise ValueError(f"未知 role {role!r}；支持 {_ROLES}")
    if generation_id < 0:
        raise ValueError("generation_id 必须 ≥ 0")
    if index < 0:
        raise ValueError("index 必须 ≥ 0")
    return f"{experiment_id}:g{generation_id}:{role}{index:04d}"
