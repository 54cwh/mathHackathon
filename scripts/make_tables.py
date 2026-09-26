"""表生成：把 run 目录的数据汇成报告用表（`实验与评价体系.md` §1.4 正式结果原则 / §5.1 目录布局）。

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
    """口径诊断：分母（`encounters`）的健康度、不变式核对、以及诊断列 `capture_attempts`。

    公式（`实验与评价体系.md` §2.1，2026-09-26 裁决）：
    `prey_capture = captures / max(encounters, 1)`。
    `encounters` = 进入 `capture_radius` 的猎物数（尺寸门**之前**，纯距离口径，`arena` S6）。
    """
    n = len(metrics)
    encounters = metrics["encounters"]
    captures = metrics["captures"]
    attempts = metrics["capture_attempts"]
    zero_enc = int((encounters == 0).sum())
    no_catch = int((captures == 0).sum())

    # 不变式（§2.1 声明）：captures <= capture_attempts <= encounters。违反即为真 bug。
    bad = int(((attempts > encounters) | (captures > attempts)).sum())
    # `encounters` 严重右偏（少数「蹲守」个体刷高）⇒ 任何引用都必须并列偏态。
    enc_med = float(encounters.median())
    enc_max = int(encounters.max())
    enc_total = int(encounters.sum())
    top = encounters.sort_values(ascending=False).head(3).sum()
    top_share = (float(top) / enc_total) if enc_total else 0.0
    # 个体比值均值 != 汇总比值（实测差 ~7x）=> 两个都必须报，且须标明是哪一个。
    cap_total = int(captures.sum())
    per_fish_mean = float(metrics["prey_capture"].mean())
    pooled = (cap_total / enc_total) if enc_total else 0.0
    ratio_gap = (per_fish_mean / pooled) if pooled else float("nan")
    gap = attempts - captures
    eq = int((gap == 0).sum())

    lines = [
        "# 指标口径诊断（自动生成）",
        "",
        "- 公式：`prey_capture = captures / max(encounters, 1)`（§2.1；"
        "分母 = **尺寸门之前**的纯距离接触数，S6）",
        f"- 个体总数：{n}",
        f"- `encounters == 0` 的个体：{zero_enc}（分母被 `max(·,1)` 兜底"
        " ⇒ 记 0.0，**不等于**捕食失败）",
        f"- `captures == 0` 的个体：{no_catch}",
        f"- 不变式 `captures <= capture_attempts <= encounters`："
        f"{'✅ 全部满足' if bad == 0 else f'❌ {bad} 个个体违反（**实现缺陷**）'}",
        f"- 诊断列 `capture_attempts − captures`（「进过口但吃不下」次数）："
        f"mean={gap.mean():.3f}, max={int(gap.max())}, 其中为 0 的个体 {eq}/{n}",
        f"- 分母偏态：`encounters` 中位数={enc_med:.0f}、最大={enc_max}、合计={enc_total}；"
        f"**前 3 位个体占 {top_share:.1%}** —— 引用该均值时必须并列偏态尾，",
        "否则会被少数「蹲守」个体主导。",
        f"- **捕获率有两个口径，必须标明**：个体比值均值={per_fish_mean:.4f}；"
        f"汇总比值={pooled:.4f}（{cap_total} / {enc_total}）；"
        f"绝对量 captures/episode={cap_total}",
        f"- 两者相差 {ratio_gap:.1f}x —— 前者是「典型个体的得手率」，"
        "后者是「全部接触中的得手比例」，**不可互换**。",
        "",
    ]
    if bad:
        lines += [
            "> ❌ **不变式被破坏**：`captures / capture_attempts / encounters`"
            " 三者的大小关系不成立。",
            "> 这是计数器实现缺陷（不是口径问题），须先修 `arena/env.py` 再解释任何指标。",
            "",
        ]
    if eq == n:
        gap_note = f"本 run 中 {eq}/{n} 个体的差额为 0 —— **无**「进过口但吃不下」判定发生。"
    else:
        gap_note = (
            f"本 run 中 {n - eq} 个个体的差额 > 0，来自「判定为太小（`arena.capture_attempt`）」。",
        )
    lines += [
        "> ℹ️ **常数捕获（知会，非警告）**：`P_capture_success = 1.0` 为占位"
        "（`arena` §8 待裁决项 a），故 `capture_attempts == captures` 普遍成立。",
        f"> {gap_note}",
        "> 该事实**不影响** `prey_capture` —— 其分母已是尺寸门之前的 `encounters`；"
        "若未来引入 `P_capture_success < 1`，公式不变，该指标自动成为标准成功率。",
        "",
    ]
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
