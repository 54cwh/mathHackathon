"""F6「发育 viability 通过率」：把 `RGCD数学模型.md` §7 判定的通过率变成**可复现**的一等公民。

背景：`paper/报告-骨架.md` §2.1 写「发育通过率（随机 q）：**2/14 ≈ 14%**」，但该数字此前
只有结论、没有可重跑的出处（原 probe 未落盘、未记 seed、未记抽样方式）。本脚本用**固定
master seed** 重算同一件事，并把「seed / 尝试次数 / 通过数 / 每次的判因 / 每次的 ρ(W⁰)」
全部写进配套 `.xlsx` 的 `_manifest` 与各 sheet，使该数字**可复现、可追溯、可反驳**。

关键诚实点（**脚本不迁就结论**）：实算结果显示 2/14 是**小样本读法**——同一 seed、同一
随机流的前 14 次恰好通过 2 次（14.3%），而把同一流拉到 1000 次后系统率 ≈ 7.1%。
两者的调和方式**不是**「全样本 CI 覆盖 14%」（实测不覆盖：[5.7%, 8.9%]），而是
**n=14 自己的 Wilson 区间宽到 [4.0%, 39.9%]**，宽到足以容纳 7.1% —— 也就是
2/14 这个点估计偏高约 2×，但它携带的信息量本来就只能定到「个位数百分比」。
本脚本照实输出两者，不为了对上 14% 而挑 seed 或挑次数。

数据从哪来（**未落盘 -> 固定 seed 现算**）：

- ``uniform_q``：``q ~ U[0,1]^8``，取自 ``SeedManager(master).rng("initial_population")``
  （命名空间 id=7，`core §3`）。q 的随机流与发育的随机流**相互独立** ——
  发育走 ``torch_generator("development", index)``（id=2），二者是不同 spawn 子树。
  **probe 约定**（非 pipeline 契约）：pipeline 里 q 由 ``q(G)`` 派生，不直接抽；
  这里直抽 q 是为了对齐「随机 q」这一原始口径。
- ``genome_q``：真实 pipeline 口径 ``q = q(G)`` —— ``random_genome``
  （``initial_population`` 命名空间）→ ``genome_affinity``。用来对照：pipeline 的
  ``q(G)`` 实测落在 [0.64, 0.83]，比 ``U[0,1]^8`` 窄得多，故**两者通过率不可互换**。

图的文字一律用英文：matplotlib 默认字体不含 CJK，中文会渲染成方框（同 `make_figs.py`）。
图脚注带 ``dev_viability @ git_commit`` 可回溯标识。

输出：

    results/figs/dev_viability/fig_viability.png
    results/figs/dev_viability/data/fig_viability.xlsx   （首 sheet 为 `_manifest`）

用法：

    .venv/Scripts/python.exe scripts/make_fig_viability.py
    .venv/Scripts/python.exe scripts/make_fig_viability.py --master-seed 2207 --n-attempts 500
"""

from __future__ import annotations

import argparse
import math
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无显示环境

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from evogenesis.core.seed import SeedManager  # noqa: E402
from evogenesis.development.config import DEFAULT_CONFIG  # noqa: E402
from evogenesis.development.grn import spectral_radius  # noqa: E402
from evogenesis.development.rgcd import ConnectomePhenotype, develop  # noqa: E402
from evogenesis.experiment.console import force_utf8_stdout  # noqa: E402
from evogenesis.experiment.figdata import export_workbook  # noqa: E402
from evogenesis.genome.config import DEFAULT_LAYOUT  # noqa: E402
from evogenesis.genome.genome import genome_affinity, random_genome  # noqa: E402
from evogenesis.genome.motifs import motif_catalog_for  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "figs" / "dev_viability"

#: 六类 fate 顺序（`configs/default_model.yaml → development.domains`，RGCD §3）。
DOMAINS: tuple[str, ...] = tuple(DEFAULT_CONFIG.domains)

#: 报告 §2.1 引用的口径：本机 probe 的「14 次随机 q」（`paper/报告-骨架.md` §2.1）。
HEADLINE_N = 14
#: 主 seed 取正式种子表之首（`configs/experiment_seeds.yaml:1` 的 `seeds:`）。
DEFAULT_MASTER_SEED = 1103
#: 三个正式 seed（`configs/experiment_seeds.yaml:1` `seeds: [1103, 2207, 3301]`；
#: 文档里以概念名 `formal_seeds` 引用，见 `core §` 「正式实验固定 3 个随机种子」）。
#: 用于展示 2/14 的 seed 依赖。
FORMAL_SEEDS = (1103, 2207, 3301)
DEFAULT_N_ATTEMPTS = 1000
DEFAULT_N_GENOME_ATTEMPTS = 200

#: §7 判据的失因词表（owner：`development/rgcd.py::viability_check`）。
#: ``missing_fate`` 的取值来自 ``DEFAULT_CONFIG.domains``，不在此硬编码，避免与配置漂移。
CRITERIA: tuple[str, ...] = (
    "no_active_neurons",
    "weight_spectral_radius_not_contractive",
    "motor_side_empty",
    "no_sensory_to_motor_path",
    "nonfinite_activation",
    "activation_bound_violated",
    "persistent_saturation",
)
VIABLE_LABEL = "ok"
MISSING_FATE_PREFIX = "missing_fate:"

#: 图的 caption（进 `.xlsx` 的 `_manifest`）。
CAPTION = (
    "F6 developmental viability (RGCD §7): per-attempt outcome, running rate with Wilson CI, "
    "failure-criteria breakdown, rho(W0) distribution, and uniform-q vs pipeline q(G) scope check"
)

#: 逐 sheet 的口径说明（进 `.xlsx` 的 `_manifest`）。
SOURCES: dict[str, str] = {
    "attempts_uniform_q": (
        "scripts/make_fig_viability.py；q ~ U[0,1]^8 (initial_population 命名空间) -> "
        "development.rgcd.develop，逐次记录 viable/reason/rho(W0)/fate 计数"
    ),
    "attempts_genome_q": "同脚本；q = q(G)（random_genome -> genome_affinity，真实 pipeline 口径）",
    "headline_14": "主 seed 随机流的前 14 次（对齐 paper/报告-骨架.md §2.1 的 2/14 口径）",
    "running_rate": "attempts_uniform_q 的累计通过率 + Wilson 95% 区间",
    "criteria_failure": "按 reason 字符串拆解；一次尝试可同时命中多个判据，故计数和 > 失败次数",
    "rho_w0": "活跃子矩阵 W^(0) 的谱半径（development.grn.spectral_radius，§7 判据 iv，阈值 1.0）",
    "q_source_compare": "两种 q 口径的通过率与 q 取值范围对照 —— 不可互相换算",
    "formal_seeds_n14": (
        "configs/experiment_seeds.yaml 的三个 formal seed 各跑 n=14（展示 2/14 的 seed 依赖）"
    ),
}


def _commit() -> str:
    """图脚注用的 git 短 hash；非 git 环境退回 ``unknown``。"""
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


def uniform_q_stream(master_seed: int, n: int) -> np.ndarray:
    """``q ~ U[0,1]^8`` 的 ``(n, 8)`` 矩阵（``initial_population`` 命名空间，`core §3`）。"""
    rng = SeedManager(master_seed).rng("initial_population")
    return rng.random((n, DEFAULT_CONFIG.grn_dim), dtype=np.float32)


def genome_q_stream(master_seed: int, n: int) -> np.ndarray:
    """真实 pipeline 口径的 ``q(G)``：``random_genome`` → ``genome_affinity``。

    个体 ``index`` 用稳定序号（`core §3`：不得用调用顺序）；同一个 ``index`` 同时喂给
    ``develop``，与 pipeline 的 ``phenotype_of`` 一致。
    """
    manager = SeedManager(master_seed)
    motifs = motif_catalog_for(master_seed)
    rows = [
        genome_affinity(
            random_genome(
                DEFAULT_LAYOUT, rng=manager.spawn_rng("initial_population", index), genome_id=""
            ),
            motifs,
        )
        for index in range(n)
    ]
    return np.stack(rows).astype(np.float32)


def _diagnostics(phenotype: ConnectomePhenotype) -> dict[str, float | int]:
    """对已判定的发育产物**复算**诊断量（只读，不重写判定）。

    - ``rho_w0``：活跃子矩阵 ``W^{(0)}`` 的谱半径，判定阈值 1.0（§7 判据 iv）；
      用的是模块自己的 ``spectral_radius``，不另写一版。
    - 六类 fate 计数：来自 ``cell_type`` + ``active_mask``（§7 developmental）。
    """
    idx = np.flatnonzero(phenotype.active_mask.numpy())
    cell_type = phenotype.cell_type.numpy()
    counts = {f"n_{name}": int((cell_type[idx] == k).sum()) for k, name in enumerate(DOMAINS)}
    idx_list = idx.tolist()
    sub = phenotype.weights0[idx_list][:, idx_list]
    return {"n_active": int(idx.size), "rho_w0": spectral_radius(sub), **counts}


def statuses(reason: str) -> set[str]:
    """把 ``viability_reason`` 拆成判据集合（``;`` 分隔；``missing_fate:a,b`` 展开）。"""
    out: set[str] = set()
    for token in reason.split(";"):
        token = token.strip()
        if not token or token == VIABLE_LABEL:
            continue
        if token.startswith(MISSING_FATE_PREFIX):
            out.update(
                f"{MISSING_FATE_PREFIX}{fate.strip()}"
                for fate in token[len(MISSING_FATE_PREFIX) :].split(",")
                if fate.strip()
            )
        else:
            out.add(token)
    return out


def run_variant(master_seed: int, q_matrix: np.ndarray, variant: str) -> pd.DataFrame:
    """对 ``q_matrix`` 每行跑一次 ``develop``，返回逐次记录（含判因与诊断量）。"""
    rows = []
    for index, q in enumerate(q_matrix):
        phenotype = develop(q, master_seed=master_seed, index=index)
        rows.append(
            {
                "variant": variant,
                "master_seed": master_seed,
                "attempt_index": index,
                **{f"q_{k}": float(v) for k, v in enumerate(q)},
                "viable": bool(phenotype.viable),
                "reason": phenotype.viability_reason,
                **_diagnostics(phenotype),
            }
        )
    return pd.DataFrame(rows)


def wilson(passed: int, total: int, z: float = 1.959963985) -> tuple[float, float]:
    """Wilson score 区间（小 n 下比 Wald 稳；n=14 时 Wald 会给出上下界越界的假区间）。"""
    if total <= 0:
        return (0.0, 1.0)
    phat = passed / total
    denom = 1.0 + z * z / total
    center = (phat + z * z / (2 * total)) / denom
    half = z * math.sqrt(phat * (1.0 - phat) / total + z * z / (4.0 * total * total)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def running_rate(df: pd.DataFrame) -> pd.DataFrame:
    """逐次累计通过率 + Wilson 区间（第 k 行 = 「前 k 次」的口径）。"""
    cumulative = df["viable"].to_numpy().cumsum()
    total = np.arange(1, len(df) + 1)
    bounds = [wilson(int(c), int(t)) for c, t in zip(cumulative, total, strict=True)]
    return pd.DataFrame(
        {
            "n_attempts": total,
            "n_passed": cumulative.astype(int),
            "pass_rate": cumulative / total,
            "wilson_lo": [b[0] for b in bounds],
            "wilson_hi": [b[1] for b in bounds],
        }
    )


def criteria_table(df: pd.DataFrame) -> pd.DataFrame:
    """每个 §7 判据**各自**失败了多少次（一次可同时命中多判据，故计数可超过失败次数）。"""
    labels = [*CRITERIA, *(f"{MISSING_FATE_PREFIX}{f}" for f in DEFAULT_CONFIG.domains)]
    counters = dict.fromkeys(labels, 0)
    for reason in df["reason"]:
        for label in statuses(reason):
            if label in counters:
                counters[label] += 1
    total = len(df)
    return pd.DataFrame(
        [
            {
                "criterion": label,
                "n_failed": counters[label],
                "frac_of_attempts": counters[label] / total if total else 0.0,
            }
            for label in labels
        ]
    )


def head_line(df: pd.DataFrame) -> dict[str, float | int]:
    """一次口径的汇总：n / 通过数 / 点估计 / Wilson 区间。"""
    total = len(df)
    passed = int(df["viable"].sum())
    lo, hi = wilson(passed, total)
    return {
        "n_attempts": total,
        "n_passed": passed,
        "pass_rate": passed / total if total else 0.0,
        "wilson_lo": lo,
        "wilson_hi": hi,
    }


def _stamp(fig, note: str) -> None:
    fig.text(0.995, 0.005, note, ha="right", va="bottom", fontsize=6.5, color="0.45")


def _wrap(label: str, width: int = 40) -> str:
    """把长判因 token 折成多行（**只插换行、不改字符**，故与代码词表不脱钩）。

    宽度取 40：最长判因 ``weight_spectral_radius_not_contractive``（39 字符）也保持单行，
    避免多行标签把 2x2 网格压到 ``tight_layout`` 放弃。
    """
    if len(label) <= width:
        return label
    return "\n".join(label[i : i + width] for i in range(0, len(label), width))


def build_figure(
    uniform: pd.DataFrame,
    genome: pd.DataFrame,
    formal: pd.DataFrame,
    criteria: pd.DataFrame,
    note: str,
) -> tuple[Path, Path, dict[str, pd.DataFrame], dict[str, str]]:
    """画 2x2 面板**并**写配套 xlsx；返回 (图路径, Excel 路径, sheets, provenance)。

    一个调用 = 一张图 + 一份同名数据表（长期要求：改样式不改数据，
    见 `paper/图表-数据对照表.md` §1）。
    """
    q_cols = [f"q_{k}" for k in range(DEFAULT_CONFIG.grn_dim)]
    run = running_rate(uniform)
    uniform_head = head_line(uniform)
    genome_head = head_line(genome)
    headline = head_line(uniform.iloc[:HEADLINE_N])
    primary_seed = int(uniform["master_seed"].iloc[0])

    fig, axes = plt.subplots(2, 2, figsize=(13.0, 9.4))

    # (A) 累计通过率：为什么 2/14 与 ~7% 不矛盾 —— n=14 的区间宽到 ±10pp。
    ax = axes[0][0]
    ax.plot(
        run["n_attempts"], run["pass_rate"], color="tab:blue", lw=1.6, label="running pass rate"
    )
    ax.fill_between(
        run["n_attempts"],
        run["wilson_lo"],
        run["wilson_hi"],
        color="tab:blue",
        alpha=0.18,
        label="Wilson 95% interval",
    )
    ax.axhline(
        uniform_head["pass_rate"],
        ls="--",
        color="0.35",
        lw=1.0,
        label=f"full-sample rate {uniform_head['pass_rate']:.3f} (n={uniform_head['n_attempts']})",
    )
    ax.axvline(HEADLINE_N, ls=":", color="tab:red", lw=1.2)
    ax.plot(
        [HEADLINE_N],
        [headline["pass_rate"]],
        "o",
        color="tab:red",
        ms=6,
        label=(
            f"n={HEADLINE_N} probe: {headline['n_passed']}/{HEADLINE_N}"
            f" = {headline['pass_rate']:.3f}"
        ),
    )
    ax.set_xscale("log")
    ax.set_xlabel(f"random-q development attempts (log scale, master seed {primary_seed})")
    ax.set_ylabel("cumulative viability pass rate")
    ax.set_title("(A) The n=14 probe reads high; the running rate settles near 7%", fontsize=10)
    ax.set_ylim(0.0, 0.55)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7.5, loc="upper right")

    # (B) 哪个 §7 判据在筛人：ρ(W⁰)<1 是唯一的绑定约束。
    ax = axes[0][1]
    plot = criteria[criteria["n_failed"] > 0].sort_values("n_failed")
    # 判因 token 直接取代码字符串（可能很长）——只折行不改字，避免与 `viability_check`
    # 的词表脱钩；精确字符串见 xlsx 的 `criteria_failure`。
    ax.barh([_wrap(label) for label in plot["criterion"]], plot["n_failed"], color="tab:orange")
    for y, (count, frac) in enumerate(zip(plot["n_failed"], plot["frac_of_attempts"], strict=True)):
        ax.text(count * 1.15, y, f"{count} ({frac:.1%})", va="center", fontsize=7)
    ax.set_xscale("log")
    ax.set_xlim(0.7, max(1.0, float(plot["n_failed"].max())) * 6.0)
    ax.set_xlabel("attempts failing this §7 criterion (log; one attempt may fail several)")
    ax.set_title("(B) Failure criteria: weight spectral radius dominates", fontsize=10)
    ax.tick_params(axis="y", labelsize=7.5)
    ax.grid(axis="x", alpha=0.3)

    # (C) 绑定约束的分布：ρ(W⁰) 的典型值就在阈值 1.0 之上。
    ax = axes[1][0]
    rho = uniform["rho_w0"].to_numpy()
    hi = float(np.percentile(rho, 99.5))
    ax.hist(rho, bins=40, range=(float(rho.min()), hi), color="tab:purple", alpha=0.75)
    ax.axvline(1.0, color="tab:red", lw=1.6, ls="--", label=r"§7 threshold $\rho(W^{(0)})<1$")
    ax.axvspan(float(rho.min()), 1.0, color="tab:green", alpha=0.18)
    ax.set_xlim(float(rho.min()) - 0.1, hi + 0.35)
    ax.set_ylim(0.0, ax.get_ylim()[1] * 1.28)
    ax.text(
        0.97,
        0.94,
        f"{float((rho < 1.0).mean()):.1%} of attempts below threshold\n"
        f"median $\\rho$ = {float(np.median(rho)):.2f}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        color="0.2",
        bbox={"boxstyle": "round,pad=0.35", "fc": "white", "ec": "0.75", "alpha": 0.9},
    )
    ax.set_xlabel(r"$\rho_{\mathrm{spec}}(W^{(0)})$ on the active submatrix")
    ax.set_ylabel("attempts")
    ax.set_title("(C) Why: the contractivity criterion binds by construction", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # (D) 口径警告：pipeline 的 q(G) 不是 U[0,1]^8，两者通过率不可互换。
    ax = axes[1][1]
    labels = [
        f"uniform\n$q\\sim U[0,1]^8$\n(n={uniform_head['n_attempts']})",
        f"pipeline\n$q=q(G)$\n(n={genome_head['n_attempts']})",
    ]
    rates = [uniform_head["pass_rate"], genome_head["pass_rate"]]
    err_lo = [
        uniform_head["pass_rate"] - uniform_head["wilson_lo"],
        genome_head["pass_rate"] - genome_head["wilson_lo"],
    ]
    err_hi = [
        uniform_head["wilson_hi"] - uniform_head["pass_rate"],
        genome_head["wilson_hi"] - genome_head["pass_rate"],
    ]
    ax.bar(labels, rates, yerr=[err_lo, err_hi], capsize=5, color=["tab:blue", "tab:green"])
    for x, (rate, head) in enumerate(zip(rates, (uniform_head, genome_head), strict=True)):
        ax.text(
            x,
            head["wilson_hi"] + 0.006,
            f"{rate:.3f}\n({head['n_passed']}/{head['n_attempts']})",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.set_ylabel("viability pass rate (Wilson 95% error bars)")
    ax.set_ylim(0.0, max(rates) * 1.9)
    ax.set_title("(D) Scope caveat: 'random q' is not the pipeline's q(G)", fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle(
        "F6  Developmental viability (RGCD §7): reproducible pass rate under random q",
        fontsize=12,
    )
    _stamp(fig, note)
    OUT.mkdir(parents=True, exist_ok=True)
    fig_path = OUT / "fig_viability.png"
    fig.tight_layout(rect=(0, 0.015, 1, 0.985))
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)

    sheets = {
        "attempts_uniform_q": uniform,
        "attempts_genome_q": genome,
        "headline_14": uniform.iloc[:HEADLINE_N],
        "running_rate": run,
        "criteria_failure": criteria,
        "rho_w0": uniform[["attempt_index", "rho_w0", "n_active", "viable", "reason"]],
        "q_source_compare": pd.DataFrame(
            [
                {
                    "q_source": "uniform_q",
                    "definition": "q ~ U[0,1]^8, SeedManager(master).rng('initial_population')",
                    **uniform_head,
                    "q_min": float(uniform[q_cols].to_numpy().min()),
                    "q_max": float(uniform[q_cols].to_numpy().max()),
                },
                {
                    "q_source": "genome_q",
                    "definition": "q = q(G): random_genome -> genome_affinity (pipeline 口径)",
                    **genome_head,
                    "q_min": float(genome[q_cols].to_numpy().min()),
                    "q_max": float(genome[q_cols].to_numpy().max()),
                },
            ]
        ),
        "formal_seeds_n14": pd.DataFrame(
            [
                {
                    "master_seed": seed,
                    "q_source": "uniform_q",
                    **head_line(formal[formal["master_seed"] == seed]),
                }
                for seed in FORMAL_SEEDS
            ]
        ),
    }
    provenance = {
        "figure": "F6 发育 viability 通过率",
        "master_seed": str(primary_seed),
        "formal_seeds": ", ".join(str(s) for s in FORMAL_SEEDS),
        "n_attempts_uniform_q": str(uniform_head["n_attempts"]),
        "n_passed_uniform_q": str(uniform_head["n_passed"]),
        "pass_rate_uniform_q": f"{uniform_head['pass_rate']:.4f}",
        "n_attempts_genome_q": str(genome_head["n_attempts"]),
        "n_passed_genome_q": str(genome_head["n_passed"]),
        "headline_n": str(HEADLINE_N),
        "headline_passed": str(headline["n_passed"]),
        "headline_rate": f"{headline['pass_rate']:.4f}",
        "q_sampling": "uniform_q: q ~ U[0,1]^8 from SeedManager(master).rng('initial_population')",
        "reproduce": "python scripts/make_fig_viability.py --master-seed 1103 --n-attempts 1000",
        "note": note,
    }
    workbook = export_workbook(
        fig_path, sheets, caption=CAPTION, sources=SOURCES, provenance=provenance
    )
    return fig_path, workbook, sheets, provenance


def main() -> None:
    force_utf8_stdout()  # 被管道/重定向时不因中文而崩（`experiment/console.py`）
    parser = argparse.ArgumentParser(
        description="F6: developmental viability pass rate under random q."
    )
    parser.add_argument("--master-seed", type=int, default=DEFAULT_MASTER_SEED)
    parser.add_argument("--n-attempts", type=int, default=DEFAULT_N_ATTEMPTS)
    parser.add_argument("--n-genome-attempts", type=int, default=DEFAULT_N_GENOME_ATTEMPTS)
    args = parser.parse_args()

    uniform = run_variant(
        args.master_seed, uniform_q_stream(args.master_seed, args.n_attempts), "uniform_q"
    )
    genome = run_variant(
        args.master_seed,
        genome_q_stream(args.master_seed, args.n_genome_attempts),
        "genome_q",
    )
    formal = pd.concat(
        [
            run_variant(seed, uniform_q_stream(seed, HEADLINE_N), "uniform_q")
            for seed in FORMAL_SEEDS
        ],
        ignore_index=True,
    )
    criteria = criteria_table(uniform)
    note = (
        f"dev_viability @ {_commit()} "
        f"(seed {args.master_seed}, n={args.n_attempts} uniform-q attempts)"
    )

    fig_path, workbook, _sheets, _provenance = build_figure(uniform, genome, formal, criteria, note)

    print(f"图：{fig_path.relative_to(ROOT)}")
    print(f"数据：{workbook.relative_to(ROOT)}")
    print()
    print(f"{'口径':<28}{'n':>6}{'passed':>8}{'rate':>9}   Wilson 95%")
    for name, head in (
        (f"uniform_q seed={args.master_seed}", head_line(uniform)),
        (f"headline n={HEADLINE_N}", head_line(uniform.iloc[:HEADLINE_N])),
        ("genome_q (pipeline)", head_line(genome)),
    ):
        print(
            f"{name:<28}{head['n_attempts']:>6}{head['n_passed']:>8}"
            f"{head['pass_rate']:>9.4f}   [{head['wilson_lo']:.4f}, {head['wilson_hi']:.4f}]"
        )
    print()
    print("formal seeds n=14（uniform_q）：")
    for seed in FORMAL_SEEDS:
        head = head_line(formal[formal["master_seed"] == seed])
        print(f"  seed {seed}: {head['n_passed']}/{HEADLINE_N}")
    print()
    print("失败判据（uniform_q）：")
    for row in criteria[criteria["n_failed"] > 0].itertuples():
        print(f"  {row.criterion:<48}{row.n_failed:>5}  ({row.frac_of_attempts:.1%})")


if __name__ == "__main__":
    main()
