"""penetrance 报告层（契约 owner：``genome/生物学与进化遗传学基础.md`` §3）。

实验登记：``experiment/实验与评价体系.md`` §3.9。

本模块是 **penetrance 的唯一实现**：把 §3 定稿的定义落成可复算的报告。
- 期望档 ``a*(g)``：由 ``E_A,E_B`` 对 ``θ_N=θ_H=0.25`` 判定（``genome.architecture``）。
- 观测档 ``â_i``：由发育产物 ``N_i=|M|``、``H_i=CV_τ``（active 子集）对**观测量阈值**
  ``(θ_N^obs, θ_H^obs)`` 二分。
- ``pen(g)=#{g_i=g, â_i=a*(g)}/#{g_i=g}``，并列报 Wilson 95% CI 与 2×2 观测档计数。

**校准与报告分离**：``θ^obs`` 只能在**独立校准集**上定（§3），报告集不得调阈值。
校准集 = ``AaBb × AaBb`` 自交（``genome.mendel_founder`` + ``genome.make_gamete/fertilize``，
``pc=μ=0``，genome §3）；报告集 = 另一组独立样本（同 master seed 的不同命名空间）。
校准规则二选一并列报：**错分最小点**（参数总表 basis「最大化与期望档分类一致性」）与
**两类类内中位数中点**（``research/reference/delta-B-and-penetrance.md`` §2.2）。

状态：``θ^obs`` 数值与校准集规模仍属 **草案待确认**（本模块不含默认数值，只读
``configs/penetrance.yaml``；冻结前不得作为结论引用）。随机数一律经 ``core.seed.SeedManager``
派生（禁自建随机源）；产物不含时间戳，``digest`` 给内容 sha256。
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import torch
from scipy.stats import mannwhitneyu

from evogenesis.core.config import load_config, read_yaml
from evogenesis.core.ids import mint_id
from evogenesis.core.seed import SeedManager
from evogenesis.development.rgcd import ConnectomePhenotype
from evogenesis.genome.config import DEFAULT_LAYOUT, GenomeLayout
from evogenesis.genome.genome import (
    Architecture,
    DiploidGenome,
    architecture,
    expression_A,
    expression_B,
    fertilize,
    make_gamete,
    mendel_founder,
)
from evogenesis.pipeline.model_chain import (
    ChainIndividual,
    ModelChainConfig,
    load_model_chain_config,
    motif_catalog,
    phenotypes_of,
)

#: 四类基因型/架构档标签（genome §3；顺序固定，避免字典序漂移）。
CLASS_ORDER: tuple[str, ...] = ("A_B_", "A_bb", "aaB_", "aabb")
#: 期望 `high_N` 的类（`E_A>θ_N`；genome §3 的四类赋值）。
EXPECTED_HIGH_N: frozenset[str] = frozenset({"A_B_", "A_bb"})
#: 期望 `high_H` 的类（`E_B>θ_H`）。
EXPECTED_HIGH_H: frozenset[str] = frozenset({"A_B_", "aaB_"})
#: AaBb×AaBb 的四类理想比例（genome §3）。
EXPECTED_9331: dict[str, float] = {"A_B_": 9 / 16, "A_bb": 3 / 16, "aaB_": 3 / 16, "aabb": 1 / 16}
#: Wilson 95% 的正态分位。
WILSON_Z: float = 1.959963985
#: τ 异质性统计量（genome §3 定稿：CV）。
TAU_STATISTIC = "cv_tau"

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PENETRANCE_CONFIG = _REPO_ROOT / "configs" / "penetrance.yaml"
DEFAULT_MODEL_CONFIG = _REPO_ROOT / "configs" / "default_model.yaml"

_CONFUSION_KEYS = ("highN_highH", "highN_lowH", "lowN_highH", "lowN_lowH")


# ---------------------------------------------------------------------------
# 单个体读数量
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PenetranceRow:
    """penetrance 的逐个体读数（期望档 + 两个观测量）。"""

    genome_id: str
    fish_id: str
    expected_class: str
    e_a: float
    e_b: float
    n_neurons: int
    cv_tau: float
    viable: bool


def cv_tau(tau: torch.Tensor, active_mask: torch.Tensor) -> float:
    r"""``H=CV_τ=SD_τ/mean_τ``，仅在 **active 子集**（``M`` 为真）上算（genome §3 / RGCD §7）。

    ``active`` 少于 2 个神经元时方差不可估，返回 ``0.0``（单神经元无「异质性」）。
    """
    active = active_mask.bool()
    values = tau[active].double()
    n = int(values.numel())
    if n < 2:
        return 0.0
    mean = float(values.mean())
    if mean == 0.0:
        return float("nan")
    return float(values.std(unbiased=True)) / mean


def observed_architecture(
    n_neurons: int, cv_tau_value: float, theta_N_obs: float, theta_H_obs: float
) -> Architecture:
    r"""观测档 ``â_i=(1[N_i>θ_N^obs], 1[H_i>θ_H^obs])``（genome §3，严格大于）。

    注意：观测阈值以**物理量纲**为单位（neuron 数 / CV），**不受** ``genome.architecture``
    的 ``θ∈(0,0.5)`` 约束，故此处不套用该函数的校验。
    """
    return Architecture(
        high_N=bool(n_neurons > theta_N_obs),
        high_H=bool(cv_tau_value > theta_H_obs),
    )


def _confusion_key(arch: Architecture) -> str:
    if arch.high_N and arch.high_H:
        return "highN_highH"
    if arch.high_N:
        return "highN_lowH"
    if arch.high_H:
        return "lowN_highH"
    return "lowN_lowH"


def _empty_confusion() -> dict[str, int]:
    return {key: 0 for key in _CONFUSION_KEYS}


# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------


def wilson_interval(successes: int, n: int, *, z: float = WILSON_Z) -> tuple[float, float] | None:
    """二项比例 ``k/n`` 的 Wilson 95% 区间（genome §3 要求）；``n=0`` 返回 ``None``。"""
    if n < 0 or successes < 0 or successes > n:
        raise ValueError(f"非法计数 successes={successes}, n={n}")
    if n == 0:
        return None
    p = successes / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def min_misclassification_threshold(
    values: Sequence[float], expected_high: Sequence[bool]
) -> tuple[float, float]:
    """取使 ``(value > θ) == expected_high`` **错分最少**的阈值（返回 ``(θ, 错分率)``）。

    候选阈值取排序后相邻不同值的**中点**（含端点外区间）；并列取**最小** θ，保证确定性。
    """
    if len(values) != len(expected_high):
        raise ValueError("values 与 expected_high 长度不一致")
    if not values:
        raise ValueError("标定需要至少一个样本")
    group = sorted(zip(values, expected_high, strict=True))
    order = [v for v, _ in group]
    labels = [e for _, e in group]
    uniq = sorted(set(order))
    best_theta = uniq[0]
    best_errors = sum(1 for flag in labels if flag)  # θ = uniq[0] ⇒ 全部判 low
    for low, high in zip(uniq[:-1], uniq[1:], strict=True):
        theta = (low + high) / 2.0
        errors = sum(
            1 for value, flag in zip(order, labels, strict=True) if (value > theta) != flag
        )
        if errors < best_errors:
            best_errors = errors
            best_theta = theta
    return best_theta, best_errors / len(order)


def median_midpoint_threshold(values: Sequence[float], expected_high: Sequence[bool]) -> float:
    """高/低两档类内**中位数之中点**（delta-B §2.2 备选口径）。两档都需有样本。"""
    high = [v for v, flag in zip(values, expected_high, strict=True) if flag]
    low = [v for v, flag in zip(values, expected_high, strict=True) if not flag]
    if not high or not low:
        raise ValueError("中位数中点口径要求 high/low 两档都非空")
    return (statistics.median(high) + statistics.median(low)) / 2.0


def _axis_arrays(
    rows: Sequence[PenetranceRow],
) -> tuple[list[float], list[bool], list[float], list[bool]]:
    n_values = [float(r.n_neurons) for r in rows]
    h_values = [r.cv_tau for r in rows]
    high_n = [r.expected_class in EXPECTED_HIGH_N for r in rows]
    high_h = [r.expected_class in EXPECTED_HIGH_H for r in rows]
    return n_values, high_n, h_values, high_h


def axis_separation(values: Sequence[float], expected_high: Sequence[bool]) -> dict[str, Any]:
    """观测轴对期望档的**区分力诊断**（无信号时 ``θ^obs`` 不可辨识，不得冻结）。

    返回主口径阈值与错分率、多数类基线错分率、``separable``（错分 < 基线）、AUC 与
    Mann–Whitney 双侧 p。``separable=false`` 表示该轴对基因型期望档无区分力，此时
    ``θ^obs`` 无意义，报告须显式标注而非冻结成 ``confirmed``。
    """
    if len(values) != len(expected_high) or not values:
        raise ValueError("分离度诊断需要等长且非空的样本")
    high = [float(v) for v, flag in zip(values, expected_high, strict=True) if flag]
    low = [float(v) for v, flag in zip(values, expected_high, strict=True) if not flag]
    theta, error = min_misclassification_threshold(values, expected_high)
    baseline = min(len(high), len(low)) / len(values)
    if not high or not low:
        return {
            "theta_min_misclass": theta,
            "min_misclassification_error": error,
            "majority_baseline_error": baseline,
            "separable": False,
            "auc": None,
            "mannwhitney_p": None,
        }
    test = mannwhitneyu(high, low, alternative="two-sided")
    auc = float(test.statistic) / (len(high) * len(low))
    return {
        "theta_min_misclass": theta,
        "min_misclassification_error": error,
        "majority_baseline_error": baseline,
        # 1e-12 容差：错分恰好等于基线视为不可分离（naive 分类器同效）
        "separable": bool(error < baseline - 1e-12),
        "auc": auc,
        "mannwhitney_p": float(test.pvalue),
    }


@dataclass(frozen=True)
class CalibrationResult:
    """校准集上两种口径的观测阈值、错分率与分离度诊断。"""

    theta_N_obs_min_misclass: float
    theta_N_obs_median_midpoint: float
    theta_H_obs_min_misclass: float
    theta_H_obs_median_midpoint: float
    n_rows: int
    misclass_rate_N: float
    misclass_rate_H: float
    separation_N: dict[str, Any]
    separation_H: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "theta_N_obs_min_misclass": self.theta_N_obs_min_misclass,
            "theta_N_obs_median_midpoint": self.theta_N_obs_median_midpoint,
            "theta_H_obs_min_misclass": self.theta_H_obs_min_misclass,
            "theta_H_obs_median_midpoint": self.theta_H_obs_median_midpoint,
            "n_rows": self.n_rows,
            "misclass_rate_N": self.misclass_rate_N,
            "misclass_rate_H": self.misclass_rate_H,
            "separation_N": self.separation_N,
            "separation_H": self.separation_H,
        }


def calibrate(rows: Sequence[PenetranceRow], *, rule: str = "min_misclass") -> CalibrationResult:
    """在**独立校准集**上定 ``θ^obs``；两种口径都算并回报（``rule`` 只影响主读数选择）。"""
    if not rows:
        raise ValueError("校准集为空")
    n_values, high_n, h_values, high_h = _axis_arrays(rows)
    n_min, n_err = min_misclassification_threshold(n_values, high_n)
    h_min, h_err = min_misclassification_threshold(h_values, high_h)
    return CalibrationResult(
        theta_N_obs_min_misclass=n_min,
        theta_N_obs_median_midpoint=median_midpoint_threshold(n_values, high_n),
        theta_H_obs_min_misclass=h_min,
        theta_H_obs_median_midpoint=median_midpoint_threshold(h_values, high_h),
        n_rows=len(rows),
        misclass_rate_N=n_err,
        misclass_rate_H=h_err,
        separation_N=axis_separation(n_values, high_n),
        separation_H=axis_separation(h_values, high_h),
    )


def penetrance_stats(
    rows: Sequence[PenetranceRow], theta_N_obs: float, theta_H_obs: float
) -> dict[str, Any]:
    """逐类 ``pen(g)`` + Wilson CI + 观测档 2×2 计数（genome §3 / delta-B §2.4）。"""
    per_class: dict[str, Any] = {}
    totals = _empty_confusion()
    for label in CLASS_ORDER:
        subset = [r for r in rows if r.expected_class == label]
        n = len(subset)
        confusion = _empty_confusion()
        hits = 0
        for row in subset:
            arch = observed_architecture(row.n_neurons, row.cv_tau, theta_N_obs, theta_H_obs)
            confusion[_confusion_key(arch)] += 1
            totals[_confusion_key(arch)] += 1
            hits += int(arch.class_label == label)
        interval = wilson_interval(hits, n)
        per_class[label] = {
            "n": n,
            "hits": hits,
            "penetrance": (hits / n) if n else None,
            "wilson_low": None if interval is None else interval[0],
            "wilson_high": None if interval is None else interval[1],
            "observed_2x2": confusion,
        }
    return {"per_class": per_class, "observed_architecture_counts": totals}


def _axis_summary(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "mean": round(statistics.fmean(values), 6),
        "max": max(values),
    }


def continuous_summary(rows: Sequence[PenetranceRow]) -> dict[str, Any]:
    """连续 ``N`` 与 ``CV_τ`` 的逐类分布（delta-B §2.4 #3：pen 是派生摘要，须与分布并列）。"""
    out: dict[str, Any] = {}
    for label in CLASS_ORDER:
        subset = [r for r in rows if r.expected_class == label]
        out[label] = {
            "n_neurons": _axis_summary([float(r.n_neurons) for r in subset]),
            "cv_tau": _axis_summary([r.cv_tau for r in subset]),
        }
    return out


def _aggregate_per_class(per_seed: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """跨 seed 汇总逐类 ``penetrance``（mean ± std，n-1；``n<2`` 时 std 为 ``None``）。"""
    out: dict[str, Any] = {}
    for label in CLASS_ORDER:
        values = [
            seed["per_class"][label]["penetrance"]
            for seed in per_seed
            if seed["per_class"][label]["penetrance"] is not None
        ]
        if not values:
            out[label] = {"n_seeds": 0, "mean": None, "std": None}
            continue
        out[label] = {
            "n_seeds": len(values),
            "mean": statistics.fmean(values),
            "std": statistics.stdev(values) if len(values) > 1 else None,
        }
    return out


# ---------------------------------------------------------------------------
# 数据构造（AaBb × AaBb；genome §3）
# ---------------------------------------------------------------------------


def _draw_child(
    founder: DiploidGenome,
    *,
    crossover_rng: np.random.Generator,
    mutation_rng: np.random.Generator,
    crossover_probability: float,
    mutation_rate: float,
    layout: GenomeLayout,
) -> DiploidGenome:
    """一次 ``founder`` 自交：两配子 → 子代（未铸 id）。"""
    gamete_a = make_gamete(
        founder, mutation_rate, crossover_probability, crossover_rng, mutation_rng, layout=layout
    )
    gamete_b = make_gamete(
        founder, mutation_rate, crossover_probability, crossover_rng, mutation_rng, layout=layout
    )
    return fertilize(gamete_a, gamete_b, layout=layout)


def _mint_individuals(
    genomes: Sequence[DiploidGenome], *, experiment_id: str
) -> tuple[ChainIndividual, ...]:
    """给一组（有序）子代铸**紧凑** ``genome_id``/``fish_id``（``core §3.1``）。

    紧凑重编号使 ``pipeline.phenotypes_of`` 由 ``genome_id`` 反解的发育 ``index`` 不随抽样
    规模膨胀（分层抽样可能丢弃大量候选，避免 spawn 树退化）。
    """
    individuals: list[ChainIndividual] = []
    for index, genome in enumerate(genomes):
        genome_id = mint_id(experiment_id, "genome", 0, index)
        fish_id = mint_id(experiment_id, "fish", 0, index)
        individuals.append(
            ChainIndividual(
                genome_id=genome_id, fish_id=fish_id, genome=replace(genome, genome_id=genome_id)
            )
        )
    return tuple(individuals)


def mendel_offspring(
    founder: DiploidGenome,
    n: int,
    *,
    master_seed: int,
    namespace: str,
    experiment_id: str,
    crossover_probability: float = 0.0,
    mutation_rate: float = 0.0,
    stream_index: int = 0,
    layout: GenomeLayout = DEFAULT_LAYOUT,
) -> tuple[ChainIndividual, ...]:
    """``founder`` 自交 ``n`` 个子代（**未分层**）；``pc=μ=0`` 给理想分离（genome §3）。

    随机流经 ``SeedManager(master_seed).spawn_rng(namespace, {0,1})`` 派生
    （``0``=crossover、``1``=mutation）；``genome_id``/``fish_id`` 经 ``core.ids.mint_id`` 铸造，
    使 ``pipeline.phenotypes_of`` 能由 ``genome_id`` 反解发育 ``index``。此函数用于
    9:3:3:1 的**计数演示**；penetrance 估计用 ``stratified_offspring``。
    """
    if n < 1:
        raise ValueError("n 必须 ≥ 1")
    manager = SeedManager(master_seed)
    crossover_rng = manager.spawn_rng(namespace, stream_index)
    mutation_rng = manager.spawn_rng(namespace, stream_index + 1)
    genomes = [
        _draw_child(
            founder,
            crossover_rng=crossover_rng,
            mutation_rng=mutation_rng,
            crossover_probability=crossover_probability,
            mutation_rate=mutation_rate,
            layout=layout,
        )
        for _ in range(n)
    ]
    return _mint_individuals(genomes, experiment_id=experiment_id)


def stratified_offspring(
    founder: DiploidGenome,
    motifs: Sequence[str],
    *,
    theta_N: float,
    theta_H: float,
    per_class: int,
    master_seed: int,
    namespace: str,
    experiment_id: str,
    max_offspring: int | None = None,
    crossover_probability: float = 0.0,
    mutation_rate: float = 0.0,
    stream_index: int = 0,
    layout: GenomeLayout = DEFAULT_LAYOUT,
) -> tuple[tuple[ChainIndividual, ...], dict[str, int]]:
    """**分层平衡**抽样：从 ``AaBb × AaBb`` 子代抽到每类恰 ``per_class`` 个。

    动机：``pen(g)`` 以基因型类为条件，故分层抽样对它是无偏估计，且能让最小类
    （``aabb``，9:3:3:1 下 1/16）的 Wilson CI 可控（直接抽 160 例时 ``aabb`` 仅约 10）。
    仅**选中**的个体进入发育，未选中者丢弃。返回 ``(个体, 每类实际计数)``；
    若在 ``max_offspring`` 内未凑满某类，则按实际计数返回（``counts`` 显式暴露缺口）。
    """
    if per_class < 1:
        raise ValueError("per_class 必须 ≥ 1")
    cap = per_class * 24 if max_offspring is None else max_offspring
    manager = SeedManager(master_seed)
    crossover_rng = manager.spawn_rng(namespace, stream_index)
    mutation_rng = manager.spawn_rng(namespace, stream_index + 1)
    buckets: dict[str, list[DiploidGenome]] = {label: [] for label in CLASS_ORDER}
    drawn = 0
    while drawn < cap and any(len(buckets[label]) < per_class for label in CLASS_ORDER):
        child = _draw_child(
            founder,
            crossover_rng=crossover_rng,
            mutation_rng=mutation_rng,
            crossover_probability=crossover_probability,
            mutation_rate=mutation_rate,
            layout=layout,
        )
        e_a = float(expression_A(child, motifs))
        e_b = float(expression_B(child, motifs))
        label = architecture(np.float32(e_a), np.float32(e_b), theta_N, theta_H).class_label
        buckets[label].append(child)
        drawn += 1
    selected: list[DiploidGenome] = []
    for label in CLASS_ORDER:
        selected.extend(buckets[label][:per_class])
    counts = {label: min(len(buckets[label]), per_class) for label in CLASS_ORDER}
    return _mint_individuals(selected, experiment_id=experiment_id), counts


def _founder_for(motifs: Sequence[str], layout: GenomeLayout) -> DiploidGenome:
    """由实验 motif 目录的 ``K_A``/``K_B`` 位点 motif 构造 AaBb founder（genome §3）。"""
    indices = (layout.motif_subset_A, layout.motif_subset_B)
    return mendel_founder(motifs[indices[0]], motifs[indices[1]], layout=layout)


def rows_of(
    individuals: Sequence[ChainIndividual],
    motifs: Sequence[str],
    *,
    master_seed: int,
    config: ModelChainConfig,
    theta_N: float,
    theta_H: float,
    device: str = "cpu",
) -> list[PenetranceRow]:
    """发育一批个体并读出 ``(expected_class, N, CV_τ, viable)``。"""
    phenotypes: list[ConnectomePhenotype] = phenotypes_of(
        individuals, motifs, master_seed=master_seed, config=config.rgcd, device=device
    )
    rows: list[PenetranceRow] = []
    for individual, phenotype in zip(individuals, phenotypes, strict=True):
        e_a = float(expression_A(individual.genome, motifs))
        e_b = float(expression_B(individual.genome, motifs))
        expected = architecture(np.float32(e_a), np.float32(e_b), theta_N, theta_H).class_label
        rows.append(
            PenetranceRow(
                genome_id=individual.genome_id,
                fish_id=individual.fish_id,
                expected_class=expected,
                e_a=e_a,
                e_b=e_b,
                n_neurons=int(phenotype.active_mask.sum().item()),
                cv_tau=cv_tau(phenotype.tau, phenotype.active_mask),
                viable=bool(phenotype.viable),
            )
        )
    return rows


# ---------------------------------------------------------------------------
# 配置与产物
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PenetranceConfig:
    """``configs/penetrance.yaml`` 的解析结果（校准/报告独立样本 + 冻结后的 θ^obs）。

    校准与报告都用**分层平衡**抽样（每类 ``per_class`` 个），故配置里是「每类规模」而非总规模；
    ``max_offspring`` 为凑不满时的抽样上限（``None`` 取 ``per_class*24``）。报告另可用
    ``demo_offspring`` 抽一组**未分层**样本，专供 9:3:3:1 计数演示。
    """

    theta_N_obs: float | None
    theta_H_obs: float | None
    calibration_master_seeds: tuple[int, ...]
    calibration_per_class: int
    calibration_max_offspring: int | None
    report_master_seeds: tuple[int, ...]
    report_per_class: int
    report_max_offspring: int | None
    report_demo_offspring: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PenetranceConfig:
        calibration = data.get("calibration", {})
        report = data.get("report", {})
        return cls(
            theta_N_obs=data.get("theta_N_obs"),
            theta_H_obs=data.get("theta_H_obs"),
            calibration_master_seeds=tuple(int(s) for s in calibration.get("master_seeds", ())),
            calibration_per_class=int(calibration.get("per_class", 0)),
            calibration_max_offspring=calibration.get("max_offspring"),
            report_master_seeds=tuple(int(s) for s in report.get("master_seeds", ())),
            report_per_class=int(report.get("per_class", 0)),
            report_max_offspring=report.get("max_offspring"),
            report_demo_offspring=int(report.get("demo_offspring", 0)),
        )


def load_penetrance_config(
    path: str | Path | None = DEFAULT_PENETRANCE_CONFIG,
) -> PenetranceConfig:
    if path is None:
        raise ValueError("penetrance 无冻结默认值，必须给出 configs/penetrance.yaml 路径")
    resolved = Path(path)
    if not resolved.is_file():
        resolved = _REPO_ROOT / resolved
    return PenetranceConfig.from_dict(read_yaml(resolved))


def content_digest(payload: Mapping[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "digest"}
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _thetas(model_config_path: str | Path) -> tuple[float, float]:
    config = load_config(model_config_path)
    return float(config.phenotype.theta_N), float(config.phenotype.theta_H)


def _config_meta(model_config_path: str | Path) -> dict[str, Any]:
    path = Path(model_config_path)
    if not path.is_absolute():
        path = _REPO_ROOT / path
    return {
        "model_config_path": str(path.relative_to(_REPO_ROOT)),
        "model_config_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def run_calibration(
    experiment_id: str,
    *,
    model_config_path: str | Path = DEFAULT_MODEL_CONFIG,
    penetrance_config: PenetranceConfig,
    device: str = "cpu",
) -> dict[str, Any]:
    """在独立校准集上定 ``θ^obs``，返回可落盘 payload（**不**写 config，冻结由人签署）。

    校准集用**分层平衡**抽样（每类 ``calibration_per_class``），使每轴 high/low 两档样本均衡；
    ``calibration.separation_*`` 给出该轴是否真有区分力——``separable=false`` 时 θ 不可辨识，
    不得冻结为 ``confirmed``。
    """
    if (
        penetrance_config.calibration_per_class < 1
        or not penetrance_config.calibration_master_seeds
    ):
        raise ValueError("校准配置不完整（master_seeds / per_class）")
    chain = load_model_chain_config(model_config_path)
    theta_N, theta_H = _thetas(model_config_path)
    pooled: list[PenetranceRow] = []
    per_seed: dict[str, Any] = {}
    sampled = {label: 0 for label in CLASS_ORDER}
    for seed in penetrance_config.calibration_master_seeds:
        motifs = motif_catalog(seed, chain.layout)
        founder = _founder_for(motifs, chain.layout)
        individuals, counts = stratified_offspring(
            founder,
            motifs,
            theta_N=theta_N,
            theta_H=theta_H,
            per_class=penetrance_config.calibration_per_class,
            max_offspring=penetrance_config.calibration_max_offspring,
            master_seed=seed,
            namespace="penetrance_calibration",
            experiment_id=f"{experiment_id}-calib",
            layout=chain.layout,
        )
        for label in CLASS_ORDER:
            sampled[label] += counts[label]
        rows = rows_of(
            individuals,
            motifs,
            master_seed=seed,
            config=chain,
            theta_N=theta_N,
            theta_H=theta_H,
            device=device,
        )
        pooled.extend(rows)
        per_seed[str(seed)] = calibrate(rows).to_dict()
    result = calibrate(pooled)
    payload: dict[str, Any] = {
        "kind": "penetrance_calibration",
        "experiment_id": experiment_id,
        "generated_by": "experiment/penetrance.py::run_calibration",
        "status": "草案待确认",
        "sampling": "stratified_balanced",
        "theta_N": theta_N,
        "theta_H": theta_H,
        "tau_statistic": TAU_STATISTIC,
        "calibration": result.to_dict(),
        "per_seed": per_seed,
        "pooled_rows": len(pooled),
        "sampled_per_class": sampled,
        "genotype_counts": _genotype_counts(pooled),
        **_config_meta(model_config_path),
    }
    payload["digest"] = content_digest(payload)
    return payload


def _separation_of_rows(rows: Sequence[PenetranceRow]) -> dict[str, Any]:
    """两观测轴对期望档的分离度诊断（用于报告 payload）。"""
    return {
        "N": axis_separation(
            [float(r.n_neurons) for r in rows],
            [r.expected_class in EXPECTED_HIGH_N for r in rows],
        ),
        "H": axis_separation(
            [r.cv_tau for r in rows],
            [r.expected_class in EXPECTED_HIGH_H for r in rows],
        ),
    }


def run_report(
    experiment_id: str,
    *,
    model_config_path: str | Path = DEFAULT_MODEL_CONFIG,
    penetrance_config: PenetranceConfig,
    device: str = "cpu",
) -> dict[str, Any]:
    """用**冻结的** ``θ^obs``（读自 config）在独立报告集上出 penetrance（不得再调阈值）。

    报告集用**分层平衡**抽样以稳定最小类（``aabb``）的 CI；另可选抽一组**未分层**样本
    （``report_demo_offspring``）专供 9:3:3:1 计数演示（两者分开，见 delta-B §2.4）。
    """
    theta_N_obs = penetrance_config.theta_N_obs
    theta_H_obs = penetrance_config.theta_H_obs
    if theta_N_obs is None or theta_H_obs is None:
        raise ValueError(
            "报告模式要求 configs/penetrance.yaml 已冻结 theta_N_obs/theta_H_obs"
            "（先跑校准并在文档签署后写入）"
        )
    if penetrance_config.report_per_class < 1 or not penetrance_config.report_master_seeds:
        raise ValueError("报告配置不完整（master_seeds / per_class）")
    chain = load_model_chain_config(model_config_path)
    theta_N, theta_H = _thetas(model_config_path)
    per_seed: dict[str, Any] = {}
    per_seed_stats: list[dict[str, Any]] = []
    all_rows: list[PenetranceRow] = []
    demo_rows: list[PenetranceRow] = []
    sampled = {label: 0 for label in CLASS_ORDER}
    for seed in penetrance_config.report_master_seeds:
        motifs = motif_catalog(seed, chain.layout)
        founder = _founder_for(motifs, chain.layout)
        individuals, counts = stratified_offspring(
            founder,
            motifs,
            theta_N=theta_N,
            theta_H=theta_H,
            per_class=penetrance_config.report_per_class,
            max_offspring=penetrance_config.report_max_offspring,
            master_seed=seed,
            namespace="penetrance_report",
            experiment_id=f"{experiment_id}-report",
            layout=chain.layout,
        )
        for label in CLASS_ORDER:
            sampled[label] += counts[label]
        rows = rows_of(
            individuals,
            motifs,
            master_seed=seed,
            config=chain,
            theta_N=theta_N,
            theta_H=theta_H,
            device=device,
        )
        stats = penetrance_stats(rows, theta_N_obs, theta_H_obs)
        per_seed[str(seed)] = stats
        per_seed_stats.append(stats)
        all_rows.extend(rows)
        if penetrance_config.report_demo_offspring > 0:
            demo_individuals = mendel_offspring(
                founder,
                penetrance_config.report_demo_offspring,
                master_seed=seed,
                namespace="penetrance_report",
                experiment_id=f"{experiment_id}-demo",
                stream_index=2,
                layout=chain.layout,
            )
            demo_rows.extend(
                rows_of(
                    demo_individuals,
                    motifs,
                    master_seed=seed,
                    config=chain,
                    theta_N=theta_N,
                    theta_H=theta_H,
                    device=device,
                )
            )
    pooled_stats = penetrance_stats(all_rows, theta_N_obs, theta_H_obs)
    payload: dict[str, Any] = {
        "kind": "penetrance_report",
        "experiment_id": experiment_id,
        "generated_by": "experiment/penetrance.py::run_report",
        "status": "草案待确认",
        "sampling": "stratified_balanced",
        "theta_N": theta_N,
        "theta_H": theta_H,
        "tau_statistic": TAU_STATISTIC,
        "observation_thresholds": {"theta_N_obs": theta_N_obs, "theta_H_obs": theta_H_obs},
        "report": {
            "master_seeds": list(penetrance_config.report_master_seeds),
            "per_class": penetrance_config.report_per_class,
            "sampled_per_class": sampled,
            "per_seed": per_seed,
            "pooled": pooled_stats,
            "cross_seed": _aggregate_per_class(per_seed_stats),
            "continuous": continuous_summary(all_rows),
            "separation": _separation_of_rows(all_rows),
            "demo_9331": {
                "offspring_per_seed": penetrance_config.report_demo_offspring,
                "pooled_expected_counts": _genotype_counts(demo_rows),
                "observed_counts": _genotype_counts(
                    demo_rows, observed=True, theta=(theta_N_obs, theta_H_obs)
                ),
            },
        },
        "expected_9331": EXPECTED_9331,
        **_config_meta(model_config_path),
    }
    payload["digest"] = content_digest(payload)
    return payload


def _genotype_counts(
    rows: Sequence[PenetranceRow],
    *,
    observed: bool = False,
    theta: tuple[float, float] | None = None,
) -> dict[str, int]:
    counts = {label: 0 for label in CLASS_ORDER}
    for row in rows:
        if observed:
            assert theta is not None
            label = observed_architecture(row.n_neurons, row.cv_tau, theta[0], theta[1]).class_label
        else:
            label = row.expected_class
        counts[label] += 1
    return counts


def table_path(experiment_id: str, *, kind: str = "report") -> Path:
    suffix = "penetrance_calibration" if kind == "calibration" else "penetrance"
    return _REPO_ROOT / "results" / "tables" / f"{experiment_id}_{suffix}.json"


__all__ = [
    "CLASS_ORDER",
    "CalibrationResult",
    "PenetranceConfig",
    "PenetranceRow",
    "calibrate",
    "content_digest",
    "EXPECTED_9331",
    "axis_separation",
    "continuous_summary",
    "cv_tau",
    "load_penetrance_config",
    "median_midpoint_threshold",
    "mendel_offspring",
    "min_misclassification_threshold",
    "observed_architecture",
    "penetrance_stats",
    "rows_of",
    "stratified_offspring",
    "run_calibration",
    "run_report",
    "table_path",
    "wilson_interval",
]
