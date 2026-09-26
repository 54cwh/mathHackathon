"""环境对照图（E-F 前置检查）：`实验与评价体系.md` §4 的证据图。

读 `results/tables/exp_env_*_summary.json`（由 `run_arena.py` 产出），
出两张图到 `results/figs/env_compare/`：
1. `fig_env_ratios.png`   —— §2.1 的四项 rate（mean ± std，跨 seed）
2. `fig_env_absolute.png` —— **绝对量**（captures / encounters 每 episode）；
   这是关键：比值指标会把猎物密度效应掩盖掉（见 §4 结论 2）。

用法：.venv/Scripts/python.exe scripts/make_env_compare.py
"""

from __future__ import annotations

import csv
import glob
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from evogenesis.viz.figdata import export_workbook  # noqa: E402
from evogenesis.viz.paths import REPO_ROOT as ROOT  # noqa: E402

TABLES = ROOT / "results" / "tables"
OUT = ROOT / "results" / "figs" / "env_compare"

CONDITIONS = [
    ("exp_env_baseline", "baseline\n(prey 24, pred 3)"),
    ("exp_env_food_rich", "food_rich\n(prey 48)"),
    ("exp_env_predator_rich", "predator_rich\n(pred 6)"),
    ("exp_env_resource_scarce", "resource_scarce\n(prey 12)"),
]
METRICS = ["survival", "capture_rate", "prey_capture", "escape_success", "composite_fitness"]


def _environment_id(run_id: str) -> str:
    """实验 id → `environment_id`（默认环境组用标准名 `default`，`experiment §4`）。"""
    return "default" if run_id == "exp_env_baseline" else run_id.removeprefix("exp_env_")


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def load_summary(exp_id: str) -> dict:
    path = TABLES / f"{exp_id}_summary.json"
    if not path.exists():
        raise SystemExit(f"缺少 {path}；先跑 scripts/run_arena.py --experiment-id {exp_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def absolute_totals(exp_id: str) -> tuple[int, int, int]:
    """返回 (captures 合计, encounters 合计, 个体数)，取自各 run 的 metrics.csv。"""
    c = e = n = 0
    for f in glob.glob(str(ROOT / "results" / "runs" / f"{exp_id}-s*" / "metrics.csv")):
        for row in csv.DictReader(Path(f).open(encoding="utf-8")):
            c += int(row["captures"])
            e += int(row["encounters"])
            n += 1
    return c, e, n


def stamp(fig, note: str) -> None:
    fig.text(0.995, 0.005, note, ha="right", va="bottom", fontsize=6.5, color="0.45")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    note = f"E-F env pre-check @ {_commit()} (ExpertPolicy, 3 seeds x 600 steps)"
    summaries = {exp: load_summary(exp) for exp, _ in CONDITIONS}
    labels = [lab for _, lab in CONDITIONS]
    made = []

    # 图 1：四项 rate
    fig, axes = plt.subplots(1, len(METRICS), figsize=(14, 4.2))
    for ax, m in zip(axes, METRICS, strict=True):
        means = [summaries[e]["per_metric"][m]["mean"] for e, _ in CONDITIONS]
        stds = [summaries[e]["per_metric"][m]["std"] or 0.0 for e, _ in CONDITIONS]
        ax.bar(range(len(labels)), means, yerr=stds, capsize=3, color="tab:blue")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_title(m, fontsize=9)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Env pre-check: §2.1 rate metrics (mean +/- std across 3 seeds)", fontsize=11)
    stamp(fig, note)
    p1 = OUT / "fig_env_ratios.png"
    fig.tight_layout()
    fig.savefig(p1, dpi=150)
    plt.close(fig)
    made.append(p1)
    export_workbook(
        p1,
        {
            "rates_by_condition": pd.DataFrame(
                [
                    {
                        "condition": exp,
                        "environment_id": _environment_id(exp),
                        "metric": m,
                        "mean": summaries[exp]["per_metric"][m]["mean"],
                        "std": summaries[exp]["per_metric"][m]["std"],
                        "n_seeds": summaries[exp]["per_metric"][m]["n"],
                    }
                    for exp, _ in CONDITIONS
                    for m in METRICS
                ]
            ),
        },
        caption="E-F env pre-check: §2.1 rate metrics per condition (mean +/- std across seeds)",
        sources={
            "rates_by_condition": (
                "results/tables/exp_env_*_summary.json；"
                "个体先 seed 内等权平均，再沿 seed 轴 mean/std（n=3）"
            )
        },
        provenance={"note": note},
    )

    # 图 2：绝对量（比值的分子/分母）
    tot = {e: absolute_totals(e) for e, _ in CONDITIONS}
    cap = [tot[e][0] for e, _ in CONDITIONS]
    enc = [tot[e][1] for e, _ in CONDITIONS]
    x = np.arange(len(labels))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    axes[0].bar(x - 0.2, cap, width=0.4, label="captures", color="tab:green")
    axes[0].bar(x + 0.2, enc, width=0.4, label="encounters", color="tab:gray")
    axes[0].set_yscale("log")
    axes[0].set_ylabel("per episode (log scale)")
    axes[0].set_title("Absolute counts (all individuals x 3 seeds)")
    axes[1].bar(x, [c / max(e, 1) for c, e in zip(cap, enc, strict=True)], color="tab:orange")
    axes[1].set_title("Pooled ratio = sum(captures) / sum(encounters)")
    axes[1].set_ylabel("pooled ratio")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7)
        ax.grid(axis="y", alpha=0.3)
    axes[0].legend(fontsize=8)
    fig.suptitle(
        "Why ratios hide the prey-density effect: numerator AND denominator move",
        fontsize=11,
    )
    stamp(fig, note)
    p2 = OUT / "fig_env_absolute.png"
    fig.tight_layout()
    fig.savefig(p2, dpi=150)
    plt.close(fig)
    made.append(p2)
    export_workbook(
        p2,
        {
            "absolute_counts": pd.DataFrame(
                [
                    {
                        "condition": exp,
                        "environment_id": _environment_id(exp),
                        "captures_total": tot[exp][0],
                        "encounters_total": tot[exp][1],
                        "n_individuals": tot[exp][2],
                        "pooled_ratio": (tot[exp][0] / max(tot[exp][1], 1)),
                    }
                    for exp, _ in CONDITIONS
                ]
            ),
        },
        caption=("Why ratios hide the prey-density effect: numerator AND denominator move"),
        sources={
            "absolute_counts": (
                "各 run 的 metrics.csv 汇总；"
                "pooled_ratio = Σcaptures / Σencounters（≠ 个体比值均值，见 §2.1）"
            )
        },
        provenance={"note": note},
    )

    print("环境对照图：")
    for p in made:
        print(f"  {p.relative_to(ROOT)}")
    print()
    print(f"{'条件':22s}{'captures':>10s}{'encounters':>12s}{'pooled':>9s}")
    for e, lab in CONDITIONS:
        c, n, _ = tot[e]
        print(f"{lab.splitlines()[0]:22s}{c:>10d}{n:>12d}{c / max(n, 1):>9.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
