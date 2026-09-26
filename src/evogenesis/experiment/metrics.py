"""实验指标（口径 owner：`实验与评价体系.md` §4 / §9）。

口径来源：`实验与评价体系.md` §4 的「指标定义（供 §9 与 fitness 复用）」段。

设计原则（`AGENTS.md`「禁止 AI 填空」）：**只实现文档已定义的量**；文档提到但未定义的量
一律不猜，登记在 `BLOCKED_METRICS` 里，并在返回值中置 `None`（**当前该表为空**）。

`prey_capture` 的分母**曾**取「进过口」口径（每鱼每步至多 1 次判定），但实测 **36/36 个体**
`capture_attempts == captures`（捕获确定性 `P_capture_success = 1.0`），指标退化为「是否有过机会」。
**2026-09-26 用户裁决改分母**：改用 **`encounters`**（进入 `capture_radius` 的猎物数，
**尺寸门之前**，S6 距离口径）。`capture_attempts` 仍记录，作为**诊断列**。

统计口径（补齐 `实验与评价体系.md` §1 的阅读问题 #1）：

1. 每个 seed 各跑一遍，个体指标先在 **seed 内对个体取等权均值** → 该 seed 的一行；
2. 再沿 **seed 轴**报告 mean ± std（样本标准差，n-1；`n < 2` 时 std 为 `None`）；
3. 逐个体原值全部保留在 `results/runs/<id>/metrics.csv`，任何人都能重算。

seeds 取自 `configs/experiment_seeds.yaml`（`[1103, 2207, 3301]`，`minimum_formal_replicates: 3`）。
"""

from __future__ import annotations

from statistics import fmean, stdev
from typing import Any

#: composite fitness 权重：§4 的四个指标 → 一个标量。
COMPOSITE_WEIGHTS: dict[str, float] = {
    "survival": 0.35,
    "prey_capture": 0.25,
    "escape_success": 0.20,
    "energy_efficiency": 0.20,
}

#: 文档提到、但**上游未定义**因而本模块拒绝计算的量。键 = 指标名，值 = 为何算不出 / 需要什么决定。
BLOCKED_METRICS: dict[str, str] = {}
#: 2026-09-26：`prey_capture`（分母 `capture_attempts` 未定义）曾是唯一阻断项；
#: 用户裁定「进过口」口径后已实现，见模块 docstring 与 `arena/Danio_Arena设计与实现说明.md` §8。


def composite_fitness(
    survival: float,
    prey_capture: float,
    escape_success: float,
    energy_efficiency: float,
) -> float:
    """§4 的加权合成（权重见 `COMPOSITE_WEIGHTS`）。"""
    return (
        COMPOSITE_WEIGHTS["survival"] * survival
        + COMPOSITE_WEIGHTS["prey_capture"] * prey_capture
        + COMPOSITE_WEIGHTS["escape_success"] * escape_success
        + COMPOSITE_WEIGHTS["energy_efficiency"] * energy_efficiency
    )


def capture_rate(captures: int, episode_steps: int) -> float:
    """§2.1 **主口径**：`capture_rate = captures / episode_steps`（单位时间捕食数）。

    2026-09-26 用户裁定：确定性捕获（`P_capture_success = 1.0`）下，任何以「接触」为单位的
    比值口径都会退化/受停留影响，故主指标取绝对速率（无偏、可跨环境比较）。
    """
    if episode_steps <= 0:
        raise ValueError("episode_steps 必须为正")
    return captures / episode_steps


def survival_rate(survival_steps: int, episode_steps: int) -> float:
    """§4：`survival = survival_steps / episode_steps`。"""
    if episode_steps <= 0:
        raise ValueError("episode_steps 必须为正")
    return survival_steps / episode_steps


def escape_success_rate(escape_successes: int, predator_encounters: int) -> float:
    """§4：`escape success = escape_successes / max(predator_encounters, 1)`。

    `predator_encounters` = **被捕食者锁定的次数**（目标获取计数，`arena` §18.3.2 S7），
    与 `arena.escape`「放弃锁定」事件同口径，故比值语义为「每次被锁定中成功逃脱的比例」。
    """
    return escape_successes / max(predator_encounters, 1)


def prey_capture_rate(captures: int, opportunities: int) -> float:
    """§4：`prey capture = captures / max(opportunities, 1)`。

    `opportunities` = **`encounters`**（进入 `capture_radius` 的猎物数，**尺寸门之前**，
    S6 距离口径）。
    这是 2026-09-26 用户裁决：原分母 `capture_attempts` 在确定性捕获下与 `captures` 恒等，
    使指标退化为「是否有过机会」；改用距离口径后它度量「**追近的猎里有多少吃到了**」。
    见 `arena/Danio_Arena设计与实现说明.md` §8 与实验文档 §4。
    """
    return captures / max(opportunities, 1)


def energy_efficiency(energy_final: float, e_max: float, survival_steps: int) -> float:
    """§4：`r_i = (E_i(T_i) - E_max) / T_i`（MVP；口径另见 `core/核心机制与数据流.md` §10 #12）。

    **按文档原式实现，不做「修正」**：该量为**非正** —— 它是「终末能量相对容量的平均缺口」，
    `E_i(T_i) == E_max` 时为 0，能量越低越负（量纲：能量/步）。
    """
    if survival_steps <= 0:
        raise ValueError("survival_steps 必须为正")
    return (energy_final - e_max) / survival_steps


def episode_metrics(
    record: dict[str, Any],
    *,
    episode_steps: int,
    e_max: float,
) -> dict[str, Any]:
    """`DanioArena.per_fish_log()` 的一条**每鱼记录** → 该个体的指标行。

    返回列：原始计数（`captures` / `capture_attempts` / `encounters` / `predator_encounters` /
    `escape_successes` / `collisions` / `survival_steps` / `energy_final`）
    + 主口径 `capture_rate`（§2.1）
    + 四项指标（`survival` / `prey_capture` / `escape_success` / `energy_efficiency`）
    + 由四项合成的 `composite_fitness`。
    """
    survival_steps = int(record["survival_steps"])
    energy_traj = record.get("energy_trajectory") or []
    energy_final = float(energy_traj[-1]) if energy_traj else float("nan")
    return {
        "survival_steps": survival_steps,
        "captures": int(record["captures"]),
        "encounters": int(record["encounters"]),
        "predator_encounters": int(record["predator_encounters"]),
        "escape_successes": int(record["escape_successes"]),
        "collisions": int(record.get("collisions", 0)),
        "capture_attempts": int(record["capture_attempts"]),
        "energy_final": energy_final,
        "survival": survival_rate(survival_steps, episode_steps),
        "capture_rate": capture_rate(int(record["captures"]), episode_steps),
        "prey_capture": prey_capture_rate(
            int(record["captures"]), int(record["encounters"])
        ),  # 分母 = encounters（尺寸门之前），见 prey_capture_rate
        "escape_success": escape_success_rate(
            int(record["escape_successes"]), int(record["predator_encounters"])
        ),
        "energy_efficiency": energy_efficiency(energy_final, e_max, survival_steps),
        "composite_fitness": composite_fitness(
            survival_rate(survival_steps, episode_steps),
            prey_capture_rate(int(record["captures"]), int(record["encounters"])),
            escape_success_rate(
                int(record["escape_successes"]), int(record["predator_encounters"])
            ),
            energy_efficiency(energy_final, e_max, survival_steps),
        ),
    }


#: `aggregate_by_seed` / `summarise_over_seeds` 默认汇总的指标列（未定义的列自动跳过）。
SCALAR_METRICS: tuple[str, ...] = (
    "survival",
    "capture_rate",
    "prey_capture",
    "escape_success",
    "energy_efficiency",
    "composite_fitness",
)


def aggregate_by_seed(
    rows: list[dict[str, Any]],
    *,
    seed_key: str = "seed",
    metrics: tuple[str, ...] = SCALAR_METRICS,
) -> list[dict[str, Any]]:
    """逐 seed 把个体指标取等权均值 → 每个 seed 一行（含 `n_individuals`）。"""
    seeds = sorted({r[seed_key] for r in rows})
    out: list[dict[str, Any]] = []
    for s in seeds:
        members = [r for r in rows if r[seed_key] == s]
        row: dict[str, Any] = {seed_key: s, "n_individuals": len(members)}
        for m in metrics:
            vals = [r[m] for r in members if r.get(m) is not None]
            row[m] = fmean(vals) if vals else None
        out.append(row)
    return out


def summarise_over_seeds(
    seed_rows: list[dict[str, Any]],
    *,
    metrics: tuple[str, ...] = SCALAR_METRICS,
) -> dict[str, dict[str, float | int | None]]:
    """沿 **seed 轴**汇总：`{指标: {"mean": ..., "std": ..., "n": ...}}`。

    std 为样本标准差（n-1）；`n < 2` 或该列全为 `None` 时 `mean` / `std` 为 `None`。
    """
    out: dict[str, dict[str, float | int | None]] = {}
    for m in metrics:
        vals = [r[m] for r in seed_rows if r.get(m) is not None]
        if not vals:
            out[m] = {"mean": None, "std": None, "n": 0}
            continue
        out[m] = {
            "mean": fmean(vals),
            "std": stdev(vals) if len(vals) > 1 else None,
            "n": len(vals),
        }
    return out


def edge_distance(a: Any, b: Any) -> float:
    return (a != b).float().mean().item()


def tau_distance(a: Any, b: Any) -> float:
    return (a - b).abs().mean().item()
