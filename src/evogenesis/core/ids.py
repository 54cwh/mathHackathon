"""稳定 ID 铸造（``core §3.1``，已定稿）。

``mint_id`` 为纯函数、确定性：同一 ``(experiment_id, role, generation, index)`` 恒得
同一结果。唯一性域为**单个 experiment**；``index`` 为该代内的稳定序号（写入后不得重排）。
``experiment_id`` / ``environment_id`` 由编排层与实验对照配置给定，本模块不铸造。
"""

from __future__ import annotations

import re

_ROLES = ("fish", "genome")

_ID_RE = re.compile(
    r"^(?P<experiment>[^:]+):g(?P<generation>\d+):(?P<role>fish|genome)(?P<index>\d{4,})$"
)


def mint_id(experiment_id: str, role: str, generation: int, index: int) -> str:
    """按 ``<experiment_id>:g<generation>:<role><index:04d>`` 铸造稳定 ID（``core §3.1``）。"""
    if not experiment_id:
        raise ValueError("experiment_id 不能为空")
    if ":" in experiment_id:
        raise ValueError("experiment_id 不得含 ':'（ID 以其为分隔符，须可无歧义解析）")
    if role not in _ROLES:
        raise ValueError(f"未知 role {role!r}；支持 {_ROLES}")
    if isinstance(generation, bool) or not isinstance(generation, int):
        raise ValueError("generation 必须是 int")
    if isinstance(index, bool) or not isinstance(index, int):
        raise ValueError("index 必须是 int")
    if generation < 0:
        raise ValueError("generation 必须 ≥ 0")
    if index < 0:
        raise ValueError("index 必须 ≥ 0")
    return f"{experiment_id}:g{generation}:{role}{index:04d}"


def parse_id(stable_id: str) -> tuple[str, int, str, int]:
    """`mint_id` 的逆：`<experiment_id>:g<generation>:<role><index:04d>` → 四元组。

    供需要「由稳定 ID 确定性取得实体序号 `t`」的消费方使用（`core §3`：`t` 不得取调用
    顺序）。对非法格式抛 `ValueError`。
    """
    match = _ID_RE.match(stable_id)
    if match is None:
        raise ValueError(f"非法稳定 ID: {stable_id!r}（期望 <exp>:g<gen>:<role><index>）")
    return (
        match.group("experiment"),
        int(match.group("generation")),
        match.group("role"),
        int(match.group("index")),
    )


def parse_index(stable_id: str) -> int:
    """由稳定 ID 取该代内序号 `index`（`core §3` 实体序号 `t` 的确定性来源）。"""
    return parse_id(stable_id)[3]
