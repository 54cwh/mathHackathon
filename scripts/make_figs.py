"""图表生成：把 run 目录的数据画成报告用图。

对应 `实验与评价体系.md` §1.4「正式结果原则」中的「所有图可回溯到 run directory」。

输入（只读）：

    results/runs/<experiment_id>-s<seed>/metrics.csv
    results/runs/<experiment_id>-s<seed>/population.jsonl
    results/runs/<experiment_id>-s<seed>/episodes.jsonl
    results/tables/<experiment_id>_summary.json

输出：

    results/runs/<experiment_id>-s<seed>/plots/   逐 seed 诊断图
    results/figs/<experiment_id>/                 跨 seed 报告图

跨 seed 报告图每张都带脚注 `experiment_id @ git_commit`，满足「图可回溯」。
图的文字**一律用英文**：matplotlib 默认字体不含 CJK，中文会渲染成方框；中文叙述放表格。

用法：

    .venv/Scripts/python.exe scripts/make_figs.py
    .venv/Scripts/python.exe scripts/make_figs.py --experiment-id exp_arena_expert_ref_v2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无显示环境

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from evogenesis.experiment.figdata import export_workbook  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "results" / "runs"
FIGS = ROOT / "results" / "figs"
TABLES = ROOT / "results" / "tables"

#: 报告图的展示顺序与标题（键 = metrics.csv 里的列名）。
REPORT_METRICS = (
    ("survival", "survival"),
    ("prey_capture", "prey capture"),
    ("escape_success", "escape success"),
    ("energy_efficiency", "energy efficiency"),
    ("composite_fitness", "composite fitness"),
)


def discovery() -> list[str]:
    """列出可用的 experiment_id（有跨 seed 汇总的）。"""
    return sorted(p.name[: -len("_summary.json")] for p in TABLES.glob("*_summary.json"))


def load(experiment_id: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """读全部 run 目录 + 汇总；缺哪个 seed 就在错误信息里点名。"""
    dirs = sorted(RUNS.glob(f"{experiment_id}-s*"))
    if not dirs:
        raise SystemExit(f"找不到 run 目录：{RUNS}/{experiment_id}-s*（先跑 run_arena.py）")
    metrics, pop, eps = [], [], []
    for d in dirs:
        metrics.append(pd.read_csv(d / "metrics.csv"))
        pop.append(pd.read_json(d / "population.jsonl", lines=True))
        eps.append(pd.read_json(d / "episodes.jsonl", lines=True))
    summary_path = TABLES / f"{experiment_id}_summary.json"
    if not summary_path.is_file():
        raise SystemExit(f"缺跨 seed 汇总：{summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return (
        pd.concat(metrics, ignore_index=True),
        pd.concat(pop, ignore_index=True),
        pd.concat(eps, ignore_index=True),
        summary,
    )


def provenance(experiment_id: str) -> str:
    """图脚注：experiment_id + git commit（从任一 run 目录读，保证可回溯）。"""
    for d in sorted(RUNS.glob(f"{experiment_id}-s*")):
        f = d / "git_commit.txt"
        if f.is_file():
            return f"{experiment_id} @ {f.read_text(encoding='utf-8').strip()}"
    return experiment_id


def _stamp(fig, note: str) -> None:
    fig.text(0.995, 0.005, note, ha="right", va="bottom", fontsize=6, color="0.45")


def _export(fig_path: Path, sheets, *, caption: str, sources=None, provenance=None) -> Path:
    """导出该图的 Excel 底层数据（与图**同名**，放同级 `data/`）。

    长期要求（用户 2026-09-26）：每张图必须有配套数据表，命名与图对应，供后续统一
    美化时「改样式不改数据」。实现见 `experiment/figdata.py`。
    """
    out = export_workbook(fig_path, sheets, caption=caption, sources=sources, provenance=provenance)
    print(f"  + data: {out.relative_to(ROOT)}")
    return out


def per_seed_figs(run_dir: Path, metrics: pd.DataFrame, pop: pd.DataFrame, note: str) -> list[Path]:
    """逐 seed 诊断图：个体条形 + 能量摘要。"""
    out_dir = run_dir / "plots"
    out_dir.mkdir(exist_ok=True)
    made = []

    fig, ax = plt.subplots(figsize=(9, 4))
    idx = range(len(metrics))
    ax.bar([i - 0.2 for i in idx], metrics["capture_attempts"], width=0.4, label="attempts")
    ax.bar([i + 0.2 for i in idx], metrics["captures"], width=0.4, label="captures")
    ax.set_xticks(list(idx))
    ax.set_xticklabels(metrics["fish_id"], rotation=60, fontsize=7)
    ax.set_ylabel("count")
    ax.set_title(f"per-fish capture attempts vs captures (seed {int(metrics['seed'].iloc[0])})")
    ax.legend()
    _stamp(fig, note)
    p = out_dir / "fig_captures_by_fish.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    made.append(p)

    _export(
        p,
        {
            "per_fish": metrics[
                ["fish_id", "captures", "capture_attempts", "encounters", "survival"]
            ],
        },
        caption="Per-fish captures / attempts / encounters / survival for one seed",
        sources={"per_fish": "metrics.csv（run 目录）"},
        provenance={"note": note},
    )

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(pop["fish_id"], pop["energy_last"], label="final")
    ax.plot(pop["fish_id"], pop["energy_min"], "o", ms=3, color="tab:red", label="min")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("energy (fraction of E_max)")
    ax.set_title(f"per-fish energy: final and minimum (seed {int(metrics['seed'].iloc[0])})")
    ax.tick_params(axis="x", rotation=60, labelsize=7)
    ax.legend()
    _stamp(fig, note)
    p = out_dir / "fig_energy_by_fish.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    made.append(p)

    _export(
        p,
        {"per_fish": pop[["fish_id", "energy_last", "energy_min"]]},
        caption="Per-fish energy: final and minimum for one seed",
        sources={"per_fish": "population.jsonl（run 目录）"},
        provenance={"note": note},
    )
    return made


def report_figs(
    out_dir: Path, metrics: pd.DataFrame, eps: pd.DataFrame, summary: dict, note: str
) -> list[Path]:
    """跨 seed 报告图：指标 mean±std / fitness 逐 seed 点 / 事件计数 / attempts-captures 散点。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    per_metric = summary["per_metric"]
    seeds = summary["seeds"]

    # 左：比值类指标（同一 0-1 标度）；右：energy_efficiency 是**率**（~1e-3/步），
    # 单独一轴 —— 否则它在合图里会被压成 0，报告里是误导。
    ratios = [n for n, _ in REPORT_METRICS if n != "energy_efficiency"]
    means = [per_metric[n]["mean"] for n in ratios]
    stds = [per_metric[n]["std"] or 0.0 for n in ratios]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), width_ratios=[3, 1])
    axes[0].barh(ratios, means, xerr=stds, capsize=4, color="tab:blue")
    axes[0].set_xlim(0, 1.05)
    axes[0].set_xlabel("mean +/- std across seeds (ratio, 0-1)")
    axes[0].set_title(f"Arena metrics (n = {len(seeds)} seeds)")
    axes[0].grid(axis="x", alpha=0.3)
    ee = per_metric["energy_efficiency"]
    axes[1].bar(
        ["energy eff."], [ee["mean"]], yerr=[ee["std"] or 0.0], capsize=4, color="tab:orange"
    )
    axes[1].axhline(0.0, color="0.4", lw=0.8)
    axes[1].set_title("rate (per step)")
    axes[1].ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    _stamp(fig, note)
    p = out_dir / "fig_metrics_mean_std.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    made.append(p)

    _export(
        p,
        {
            "metrics_mean_std": pd.DataFrame(
                [
                    {
                        "metric": n,
                        "mean": per_metric[n]["mean"],
                        "std": per_metric[n]["std"],
                        "n_seeds": per_metric[n]["n"],
                        "unit": unit,
                    }
                    for n, unit in REPORT_METRICS
                ]
            ),
        },
        caption=(
            "Arena metrics: mean +/- std across seeds "
            "(ratios on 0-1; energy_efficiency is a per-step rate)"
        ),
        sources={
            "metrics_mean_std": (
                "results/tables/<id>_summary.json；个体先 seed 内等权平均，再沿 seed 轴 mean/std"
            )
        },
        provenance={"note": note},
    )

    seed_fit = metrics.groupby("seed")["composite_fitness"].mean()
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.bar([str(s) for s in seed_fit.index], seed_fit.to_numpy(), color="tab:green")
    ax.axhline(
        per_metric["composite_fitness"]["mean"],
        ls="--",
        color="0.3",
        label=f"mean {per_metric['composite_fitness']['mean']:.4f}",
    )
    ax.set_xlabel("seed")
    ax.set_ylabel("composite fitness")
    ax.set_title("Composite fitness per seed (individual mean)")
    ax.legend()
    _stamp(fig, note)
    p = out_dir / "fig_fitness_by_seed.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    made.append(p)

    _export(
        p,
        {"fitness_by_seed": seed_fit.rename("composite_fitness").reset_index()},
        caption="Composite fitness per seed (individual mean within seed)",
        sources={"fitness_by_seed": "metrics.csv 按 seed 取 composite_fitness 均值"},
        provenance={"note": note},
    )

    ev_cols = [
        c
        for c in eps.columns
        if c
        in (
            "spawn",
            "capture_attempt",
            "prey_captured",
            "collision",
            "escape",
            "energy_depleted",
            "fish_captured",
            "episode_end",
        )
    ]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = range(len(eps))
    w = 0.8 / max(len(ev_cols), 1)
    for i, c in enumerate(ev_cols):
        ax.bar([xi - 0.4 + w * (i + 0.5) for xi in x], eps[c].to_numpy(), width=w, label=c)
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"seed {int(s)}" for s in eps["seed"]])
    ax.set_ylabel("event count / episode")
    ax.set_title("Episode event counts")
    ax.legend(fontsize=8)
    _stamp(fig, note)
    p = out_dir / "fig_events_by_seed.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    made.append(p)

    _export(
        p,
        {"events_by_seed": eps[["seed", *ev_cols]]},
        caption="Episode event counts per seed",
        sources={"events_by_seed": "episodes.jsonl（run 目录）"},
        provenance={"note": note},
    )

    # §2.1 的关系图：分母 `encounters`（尺寸门之前）vs `captures`。
    # `capture_attempts` 自 2026-09-26 起只是**诊断列**，不进该指标，故只作参考线。
    fig, ax = plt.subplots(figsize=(6, 5))
    for s in seeds:
        sub = metrics[metrics["seed"] == s]
        ax.scatter(sub["encounters"], sub["captures"], s=28, label=f"seed {s}")
    lim = float(max(metrics["encounters"].max(), metrics["captures"].max())) + 1
    ax.plot([0, lim], [0, lim], ls=":", color="0.5", label="captures = encounters (upper bound)")
    ax.set_xlabel("encounters (pre-size-gate, §2.1 denominator)")
    ax.set_ylabel("captures")
    ax.set_title("Prey-capture denominator vs successful captures (per fish)")
    ax.legend(fontsize=8)
    _stamp(fig, note)
    p = out_dir / "fig_encounters_vs_captures.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    made.append(p)

    _export(
        p,
        {
            "per_fish": metrics[
                ["seed", "fish_id", "encounters", "captures", "capture_attempts", "prey_capture"]
            ],
        },
        caption="§2.1 denominator (encounters, pre-size-gate) vs captures, per fish",
        sources={"per_fish": "metrics.csv；注意分母右偏（见 diagnostics.md）"},
        provenance={"note": note},
    )
    return made


def main() -> None:
    parser = argparse.ArgumentParser(description="Make figures for an Arena/experiment run.")
    parser.add_argument(
        "--experiment-id",
        default=None,
        help="默认取 results/tables 下最近修改的那份 *_summary.json",
    )
    args = parser.parse_args()

    ids = discovery()
    if args.experiment_id is None:
        if not ids:
            raise SystemExit("results/tables 下没有任何 *_summary.json；先跑 scripts/run_arena.py")
        cands = sorted(TABLES.glob("*_summary.json"), key=lambda p: p.stat().st_mtime)
        experiment_id = cands[-1].name[: -len("_summary.json")]
        print(f"（未指定 --experiment-id，取最近修改的：{experiment_id}；可选 {ids}）")
    else:
        experiment_id = args.experiment_id

    metrics, pop, eps, summary = load(experiment_id)
    note = provenance(experiment_id)

    made = []
    for d in sorted(RUNS.glob(f"{experiment_id}-s*")):
        seed = int(d.name.split("-s")[-1])
        made += per_seed_figs(d, metrics[metrics["seed"] == seed], pop[pop["seed"] == seed], note)
    made += report_figs(FIGS / experiment_id, metrics, eps, summary, note)

    print(f"图已生成 {len(made)} 张（脚注 {note}）：")
    for p in made:
        print(f"  {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
