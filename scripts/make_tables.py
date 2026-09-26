"""表生成：把 run 目录的数据汇成报告用表（`实验与评价体系.md` §10 / §11）。

输入（只读）：

    results/runs/<experiment_id>-s<seed>/{metrics.csv, episodes.jsonl}
    results/tables/<experiment_id>_summary.json

输出：`results/tables/<experiment_id>/`

    summary.md        跨 seed 的 mean ± std（含逐 seed 值）
    diagnostics.md    **口径诊断**：零机会个体数、attempts 与 captures 是否恒等
    by_fish.csv       全部个体行（可直接进附录）
    episodes.csv      逐 episode 事件计数

用法：

    .venv/Scripts/python.exe scripts/make_tables.py
    .venv/Scripts/python.exe scripts/make_tables.py --experiment-id exp_arena_expert_ref
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "results" / "runs"
TABLES = ROOT / "results" / "tables"

#: (列名, 展示名, 单位)。energy_efficiency 是**率**（每步），其余是比值。
ROWS = (
    ("survival", "survival", "ratio"),
    ("prey_capture", "prey capture", "ratio"),
    ("escape_success", "escape success", "ratio"),
    ("energy_efficiency", "energy efficiency", "per step"),
    ("composite_fitness", "composite fitness", "ratio"),
)


def discover() -> list[str]:
    return sorted(p.name[: -len("_summary.json")] for p in TABLES.glob("*_summary.json"))


def load(experiment_id: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    dirs = sorted(RUNS.glob(f"{experiment_id}-s*"))
    if not dirs:
        raise SystemExit(f"找不到 run 目录：{RUNS}/{experiment_id}-s*")
    metrics = pd.concat([pd.read_csv(d / "metrics.csv") for d in dirs], ignore_index=True)
    eps_frames = [pd.read_json(d / "episodes.jsonl", lines=True) for d in dirs]
    eps = pd.concat(eps_frames, ignore_index=True)
    sp = TABLES / f"{experiment_id}_summary.json"
    if not sp.is_file():
        raise SystemExit(f"缺跨 seed 汇总：{sp}")
    return metrics, eps, json.loads(sp.read_text(encoding="utf-8"))


def provenance_note(experiment_id: str) -> str:
    for d in sorted(RUNS.glob(f"{experiment_id}-s*")):
        f = d / "git_commit.txt"
        if f.is_file():
            return f"（数据来源：{experiment_id} @ {f.read_text(encoding='utf-8').strip()}）"
    return f"（数据来源：{experiment_id}）"


NL = chr(10)


def md_table(metrics: pd.DataFrame, summary: dict) -> str:
    per = summary["per_metric"]
    seeds = summary["seeds"]
    head = f"| 指标 | 单位 | mean ± std（n={len(seeds)} 个 seed） | "
    head += " | ".join(f"seed {s}" for s in seeds) + " |"
    lines = [head, "|---|---|---|" + "---|" * len(seeds)]
    for col, label, unit in ROWS:
        st = per[col]
        mean = "—" if st["mean"] is None else format(st["mean"], ".6g")
        std = "—" if st["std"] is None else format(st["std"], ".3g")
        cells = [format(float(metrics[metrics["seed"] == s][col].mean()), ".4g") for s in seeds]
        lines.append(f"| {label} | {unit} | {mean} ± {std} | " + " | ".join(cells) + " |")
    return NL.join(lines) + NL


def diagnostics(metrics: pd.DataFrame) -> str:
    """口径诊断：讲明「零机会个体」与「attempts 恒等于 captures」这类退化。"""
    n = len(metrics)
    zero = int((metrics["capture_attempts"] == 0).sum())
    eq = int((metrics["capture_attempts"] == metrics["captures"]).sum())
    lines = [
        "# 指标口径诊断（自动生成）",
        "",
        f"- 个体总数：{n}",
        f"- `capture_attempts == 0` 的个体：{zero}（其 `prey_capture` 按 §4 的 max(·,1) 记 0.0，"
        "**不等于**尝试失败）",
        f"- `capture_attempts == captures` 的个体：{eq} / {n}",
        "",
    ]
    if eq == n:
        lines += [
            "> ⚠️ **退化警告**：全部个体的 `attempts` 与 `captures` **恒等**。原因是捕获确定性",
            "> （`P_capture_success = 1.0`，参数总表占位）且每鱼每步至多一次判定（§17 S5）。",
            "> 此时 `prey_capture` 只能取 1.0（有机会且吃到）或 0.0（从未有机会），均值实际含义是",
            "> 「**有过至少一次机会的个体占比**」，而**不是**吃到成功率。",
            "> 要让它成为成功率，需裁决：",
            "> (a) 引入 `P_capture_success < 1`；或 (b) 分母改为「进入 `capture_radius` 的猎物数」",
            "> （尺寸门之前）；或 (c) 保留公式但并列报告 `n_with_opportunity`。",
            "> **未裁决前不得把该均值解释为成功率。**",
            "",
        ]
    else:
        lines += [f"- `attempts > captures` 的个体：{n - eq}（比例口径可用）", ""]
    return NL.join(lines) + NL


def main() -> None:
    parser = argparse.ArgumentParser(description="Make tables for an Arena/experiment run.")
    parser.add_argument("--experiment-id", default=None)
    args = parser.parse_args()
    ids = discover()
    if args.experiment_id is None:
        if not ids:
            raise SystemExit("results/tables 下没有 *_summary.json；先跑 scripts/run_arena.py")
        cands = sorted(TABLES.glob("*_summary.json"), key=lambda p: p.stat().st_mtime)
        experiment_id = cands[-1].name[: -len("_summary.json")]
        print(f"（未指定 --experiment-id，取最近修改的：{experiment_id}；可选 {ids}）")
    else:
        experiment_id = args.experiment_id

    metrics, eps, summary = load(experiment_id)
    out = TABLES / experiment_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.md").write_text(
        md_table(metrics, summary) + NL + provenance_note(experiment_id) + NL, encoding="utf-8"
    )
    (out / "diagnostics.md").write_text(diagnostics(metrics), encoding="utf-8")
    metrics.to_csv(out / "by_fish.csv", index=False)
    eps.to_csv(out / "episodes.csv", index=False)
    print("表已生成：")
    for f in sorted(out.iterdir()):
        print(f"  {f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
