"""论文用图（读**冻结产物**，不依赖 run 目录）：基线六指标 + penetrance 可辨识性。

与 `viz/figs.py` 的分工：`figs.py` 从 run 目录出跨 seed 报告图；本模块从**入库的冻结产物**
（`artifacts/baseline/exp_arena_expert_ref_v3_summary.json`、`results/tables/<id>_penetrance.json`）
出论文图 ⇒ 即使 run 目录被清理，论文图仍可复现（本仓「图可回溯」要求）。

输出（**直接写入论文目录**，便于论文自包含）：

    paper/latex/figs/fig_baseline_v3.png
    paper/latex/figs/fig_penetrance.png

用法：

    python scripts/make_fig_paper.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无显示环境

import matplotlib.pyplot as plt  # noqa: E402

from evogenesis.viz.paths import REPO_ROOT as ROOT  # noqa: E402

OUT = ROOT / "paper" / "latex" / "figs"
BASELINE = ROOT / "artifacts" / "baseline" / "exp_arena_expert_ref_v3_summary.json"
REPORT = ROOT / "results" / "tables" / "pen-ship-report.json"

#: 参考样式（投资学课程设计副本 charts_*.py）：SimHei、去上右边框、图 10 号字
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["font.size"] = 10
plt.rcParams["axes.titlesize"] = 12

RATIO_METRICS = ("survival", "prey_capture", "escape_success", "composite_fitness")
CLASS_ORDER = ("A_B_", "A_bb", "aaB_", "aabb")


def fig_baseline() -> Path:
    """基线六指标（冻结 v3 产物，mean ± std，n=3 seed）。"""
    per = json.loads(BASELINE.read_text(encoding="utf-8"))["per_metric"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), width_ratios=[3, 1])
    names = list(RATIO_METRICS)
    means = [per[n]["mean"] for n in names]
    stds = [per[n]["std"] for n in names]
    axes[0].barh(names, means, xerr=stds, capsize=4, color="tab:blue")
    axes[0].set_xlim(0, 1.05)
    axes[0].set_xlabel("均值 ± 标准差（跨 seed，n=3）")
    axes[0].set_title("Arena 主指标：比值类（0–1 标度）")
    axes[0].grid(axis="x", alpha=0.3)
    ee = per["energy_efficiency"]
    axes[1].bar(["能量效率"], [ee["mean"]], yerr=[ee["std"]], capsize=4, color="tab:orange")
    axes[1].axhline(0.0, color="0.4", lw=0.8)
    axes[1].set_title("每步速率")
    axes[1].ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    fig.tight_layout()
    p = OUT / "fig_baseline_v3.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def fig_penetrance() -> Path:
    """penetrance：逐类外显率（Wilson 95% CI）与两轴分离度。"""
    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    body = rep["report"]
    pooled = body["pooled"]["per_class"]
    sep = body["separation"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), width_ratios=[2, 1])
    labels = list(CLASS_ORDER)
    pen = [pooled[c]["penetrance"] for c in labels]
    lo = [pooled[c]["penetrance"] - pooled[c]["wilson_low"] for c in labels]
    hi = [pooled[c]["wilson_high"] - pooled[c]["penetrance"] for c in labels]
    axes[0].bar(labels, pen, yerr=[lo, hi], capsize=5, color="tab:green")
    axes[0].axhline(0.5, ls="--", color="0.4", lw=0.9, label="0.5 机遇水平")
    axes[0].set_ylim(0, 1.0)
    axes[0].set_ylabel("外显率 P(观测档 = 期望档)")
    axes[0].set_title("报告集逐类外显率（Wilson 95% 区间，n=1200/类）")
    axes[0].legend(fontsize=8)
    for i, c in enumerate(labels):
        axes[0].text(i, pen[i] + hi[i] + 0.02, f"{pen[i]:.3f}", ha="center", fontsize=8)
    axes[1].bar(["N 轴", "H 轴"], [sep["N"]["auc"], sep["H"]["auc"]], color=["tab:blue", "0.7"])
    axes[1].axhline(0.5, ls=":", color="0.4", lw=0.9)
    axes[1].axhline(0.70, ls="--", color="tab:red", lw=0.9, label="效应量下限 0.70")
    axes[1].set_ylim(0.4, 1.0)
    axes[1].set_title("分离度 AUC（两轴）")
    axes[1].legend(fontsize=8)
    for i, k in enumerate(("N", "H")):
        axes[1].text(i, sep[k]["auc"] + 0.01, f"{sep[k]['auc']:.3f}", ha="center", fontsize=8)
    fig.tight_layout()
    p = OUT / "fig_penetrance.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for p in (fig_baseline(), fig_penetrance()):
        print("  +", p.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
