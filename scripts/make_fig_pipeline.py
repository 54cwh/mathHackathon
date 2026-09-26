"""F12 数据流总览图：把 `core §2 数据流水线总览` 画成一张可回溯的图。

为什么这张图存在
----------------
`paper/latex/sections/02-method.tex` 的 `\\todo`（\\S\\ref{method:pipeline}）要求一张
「数据流总览图」（DNA -> GRN -> 发育 -> connectome -> Arena -> 三条分支 -> fitness ->
selection -> 下一代 genome）。该图此前被写成「F12」，而 `paper/图表-数据对照表.md` §2
的图清单只到 F11 —— **leader 裁决：这张图就是 F12**，本脚本负责产出并登记。

内容权威性
----------
逐节点、逐边可追溯到 `src/evogenesis/core/核心机制与数据流.md` **§2 数据流水线总览**
（必要时补 core §3 / §4.4 / §5 / §7 与 `experiment/实验与评价体系.md` §5.1）。
本脚本**不新造**任何环节：节点表 `nodes` 与边表 `edges` 的 `source` 列就是出处。

两处需要声明的口径（诚实标注，不藏在代码里）：

1. **三条分支自 Arena 分出**。`core §2` 的 ASCII 图把三条分支画在 `development` 的缩进
   之下，但同一小节的正文与 core §4.1 / §5 都写「Arena 之后」「ExpertPolicy 在 Arena
   正常 episode 中驱动鱼」「事件日志……全部实验指标的原始来源」，故本图按 **Arena**
   作为三条分支的起点（ASCII 的缩进是排版，不是契约）。
2. **`results/runs/` 与 `artifacts/` 的入边**。`core §2` 把这两个 sink 画在管线竖轴的
   末端；但其内容的生产者按 core §4.5（`trajectories/`）与 §7（`metrics` /
   `population` / `events`）归属 **Arena 阶段**。本图按 producer 归属连
   `arena -> results/runs`，而 sink 仍落在图的底部（`artifacts/` 由 run 目录提升，
   core §7「仅 Demo 所需子集」）。

图的文字**一律英文**：matplotlib 默认字体不含 CJK，中文会渲染成方框
（同 `scripts/make_figs.py` 的 docstring）。中文只出现在配套 `.xlsx` 的 `note` 列里。

配套 Excel（用户长期硬要求：图必须有同名数据表）
------------------------------------------------
同图同名 `.xlsx` 落在同级 `data/`，首 sheet 固定为 `_manifest`。流程图没有「数值」，
故这里的**底层数据 = 节点表 + 边表**（`nodes` / `edges` 两个 sheet）——这样换配色、
换排版都不必重推结构（「改样式不改数据」）。

输出：
    results/figs/pipeline/fig_pipeline.png
    results/figs/pipeline/data/fig_pipeline.xlsx   （首 sheet 为 `_manifest`）

用法：
    .venv/Scripts/python.exe scripts/make_fig_pipeline.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无显示环境

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

from evogenesis.experiment.console import force_utf8_stdout  # noqa: E402
from evogenesis.experiment.figdata import export_workbook  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "figs" / "pipeline"

#: 图号（`paper/报告-骨架.md` §6 / `paper/图表-数据对照表.md` §2 的报告位）。
FIGURE_ID = "F12"

#: 权威出处：`core §2` 的小节号（逐节点/逐边在 `source` 列里逐条给出）。
CORE_SECTION = "core §2"

#: 图的唯一权威文档指针（进 `_manifest` 的 provenance，供不看代码的人复核）。
AUTHORITATIVE_SOURCE = "src/evogenesis/core/核心机制与数据流.md §2 数据流水线总览"

#: 三处配色（语义固定，不随美化漂移）。
_C_INPUT = ("#E8F1FA", "#2C6E9B")
_C_MODEL = ("#EAF4EC", "#3D7A4E")
_C_SIM = ("#FDF0E3", "#B2651A")
_C_BRANCH = ("#F3EDF7", "#6A3D8F")
_C_FLOW = ("#EDEFF2", "#4A5568")
_C_STORE = ("#FFF6D9", "#8A6D0B")
_C_BLOCK = ("#FBE9E9", "#B23A3A")


# ---------------------------------------------------------------------------
# 权威节点表 / 边表（`core §2`）。列名保持英文（`figdata.py` 约定：便于再加工），
# 说明与出处用中文 —— 中文只在 `.xlsx` 里，绝不进图。
# ---------------------------------------------------------------------------

#: (id, label, kind, note, source)。`label` 是**图上的文字**，必须英文。
PIPELINE_NODES: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "configs",
        "configs/*.yaml\n(incl. seed)",
        "input",
        "运行期取值的唯一来源；master seed 在此给定（configs/experiment_seeds.yaml）",
        "core §2; core §7",
    ),
    (
        "seed_manager",
        "Seed Manager",
        "mechanism",
        "master seed 派生一切子种子（NumPy SeedSequence 命名空间派生）",
        "core §2; core §3",
    ),
    (
        "genome",
        "genome\n(DNA + motif)",
        "model",
        "二倍体 DNA + 一次性抽样的 motif 目录；唯一进入下一代的遗传物",
        "core §2; 注 (DNA+motif)",
    ),
    (
        "development",
        "development\n(GRN / RGCD)",
        "model",
        "调控网络 + RGCD 发育：q(G) -> 细胞命运 -> 结构",
        "core §2; 注 (GRN/RGCD 发育)",
    ),
    (
        "connectome",
        "connectome\n(DanioNet, 48-node)",
        "model",
        "发育产物落到 DanioNet（48 节点槽位）",
        "core §2; 注 (DanioNet 48-node)",
    ),
    (
        "arena",
        "Arena simulation  (20 Hz x 600 steps / episode)",
        "simulation",
        "每 episode 30 s；一律跑满 600 步（A9，terminated/truncated 均为 False）",
        "core §2; 注 (20 Hz x 600 steps)",
    ),
    (
        "expert_trajectory",
        "expert trajectories\n(ExpertPolicy)",
        "branch",
        "分支 (i)：ExpertPolicy 在正常 episode 中驱动鱼，逐 step 采样本",
        "core §2; core §4.1",
    ),
    (
        "bc_training",
        "BC training",
        "branch",
        "行为克隆（Stage 1）；唯一的「训练」环节",
        "core §2; core §4",
    ),
    (
        "delta_w",
        "Delta W\n(contemporary, NOT inherited)",
        "branch",
        "当代学习增量；只影响当代表现型，绝不进入繁殖通路",
        "core §2; core §4.4",
    ),
    (
        "event_log",
        "event log",
        "branch",
        "分支 (ii)：Arena 事件日志；全部实验指标的原始来源",
        "core §2; core §5",
    ),
    (
        "metrics",
        "experiment metrics",
        "branch",
        "由事件日志算出实验指标",
        "core §2",
    ),
    (
        "frame_snapshot",
        "frame snapshots\n(position / heading / energy)",
        "branch",
        "分支 (iii)：帧快照",
        "core §2",
    ),
    (
        "ws_push",
        "WS real-time push\n(demo only, no disk)",
        "branch",
        "仅现场演示、不落盘；磁盘日志是它的超集（单向同源）",
        "core §2; 注 关键原则",
    ),
    ("fitness", "fitness", "flow", "适应度 F", "core §2"),
    ("selection", "selection / drift", "flow", "选择与漂变", "core §2"),
    (
        "next_genome",
        "next-generation\ngenome",
        "flow",
        "下一代 genome；回到 genome 形成闭环",
        "core §2",
    ),
    (
        "results_runs",
        "results/runs/<experiment_id>-s<seed>/   (NOT committed)",
        "storage",
        "run 目录：metadata / config_snapshot / metrics / population / events / trajectories / plots",
        "core §2; core §7; 实验与评价体系.md §5.1",
    ),
    (
        "artifacts",
        "artifacts/   (committed: fixed seed, demo population, small checkpoints)",
        "storage",
        "入库的 Demo 子集（仅 Demo 所需子集由 run 目录提升）",
        "core §2; core §7",
    ),
)

#: (from, to, kind, note)。`kind == "blocked"` 的边**只作图示**，不表示数据流动。
PIPELINE_EDGES: tuple[tuple[str, str, str, str], ...] = (
    ("configs", "seed_manager", "config", "配置 + master seed 进入 Seed Manager"),
    ("seed_manager", "genome", "seed", "子种子驱动基因组生成"),
    ("genome", "development", "data", "DNA + motif -> GRN / RGCD 发育"),
    ("development", "connectome", "data", "发育产物 -> DanioNet"),
    ("connectome", "arena", "data", "DanioNet -> Arena 仿真"),
    ("arena", "expert_trajectory", "branch", "分支 (i) 起点"),
    ("expert_trajectory", "bc_training", "branch", "专家轨迹 -> BC 训练"),
    ("bc_training", "delta_w", "branch", "BC 产出 Delta W"),
    ("arena", "event_log", "branch", "分支 (ii) 起点"),
    ("event_log", "metrics", "branch", "事件日志 -> 实验指标"),
    ("arena", "frame_snapshot", "branch", "分支 (iii) 起点"),
    ("frame_snapshot", "ws_push", "branch", "帧快照 -> WS 实时推送"),
    ("arena", "fitness", "flow", "仿真结果 -> 适应度 F"),
    ("fitness", "selection", "flow", "适应度 -> 选择 / 漂变"),
    ("selection", "next_genome", "flow", "选择 -> 下一代 genome"),
    ("next_genome", "genome", "loop", "闭回：下一代 genome 回到 genome"),
    (
        "delta_w",
        "next_genome",
        "blocked",
        "遗传边界（NOT inherited）：Delta W 当代有效、不遗传 —— 后代只继承 DNA 并从发育重来，"
        "Delta W 绝不进入繁殖通路。本边只作图示（图上标 NOT inherited），不表示存在数据流动",
    ),
    (
        "arena",
        "results_runs",
        "storage",
        "仿真期产物写入 run 目录（不入库；trajectories/ 亦落此处）",
    ),
    ("results_runs", "artifacts", "subset", "仅 Demo 所需子集入库"),
)

#: 图中必须出现的「关键节点」（`core §2` 管线骨架）—— 守护测试按此集合校验。
KEY_NODES: frozenset[str] = frozenset(
    {
        "configs",
        "seed_manager",
        "genome",
        "development",
        "connectome",
        "arena",
        "fitness",
        "selection",
        "next_genome",
        "results_runs",
        "artifacts",
    }
)

#: 三条并行分支的首节点（`core §2` 的 `├──►` / `└──►` 三条）。
BRANCH_HEADS: tuple[str, ...] = ("expert_trajectory", "event_log", "frame_snapshot")

CAPTION = (
    f"{FIGURE_ID} Data-flow overview: configs -> Seed Manager -> genome -> development -> "
    "connectome -> Arena -> three parallel branches (expert trajectories -> BC -> Delta W; "
    "event log -> metrics; frame snapshots -> WS push) -> fitness -> selection/drift -> "
    "next-generation genome, with the genetic boundary (Delta W is NOT inherited) and the "
    "two storage sinks (results/runs not committed; artifacts committed)"
)

SOURCES: dict[str, str] = {
    "nodes": (
        "scripts/make_fig_pipeline.py 的 PIPELINE_NODES 常量；逐节点的出处在 source 列，"
        "权威来源 = src/evogenesis/core/核心机制与数据流.md §2 数据流水线总览"
    ),
    "edges": (
        "scripts/make_fig_pipeline.py 的 PIPELINE_EDGES 常量；kind=blocked 的边（Delta W -> "
        "下一代 genome）只作图示，表示遗传边界不成立的数据通路，非数据流"
    ),
}


def _commit() -> str:
    """图脚注用的 git 短 hash；非 git 环境退回 ``unknown``（同 make_figs.py 的做法）。"""
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


def nodes_frame() -> pd.DataFrame:
    """节点表（流程图的「底层数据」之一）。"""
    return pd.DataFrame(
        [
            {"id": nid, "label": label, "kind": kind, "note": note, "source": source}
            for nid, label, kind, note, source in PIPELINE_NODES
        ]
    )


def edges_frame() -> pd.DataFrame:
    """边表（流程图的「底层数据」之二）。"""
    return pd.DataFrame(
        [
            {"from": src, "to": dst, "kind": kind, "note": note}
            for src, dst, kind, note in PIPELINE_EDGES
        ]
    )


# ---------------------------------------------------------------------------
# 绘制
# ---------------------------------------------------------------------------


def _box(
    ax,
    cx: float,
    cy: float,
    w: float,
    h: float,
    label: str,
    *,
    colors: tuple[str, str],
    fontsize: float = 8.5,
    linestyle: str = "-",
    linewidth: float = 1.3,
) -> tuple[float, float, float, float]:
    """画一个圆角方框 + 居中英文标签；返回 ``(x0, y0, x1, y1)`` 供锚点计算。"""
    x0, y0 = cx - w / 2, cy - h / 2
    patch = FancyBboxPatch(
        (x0, y0),
        w,
        h,
        boxstyle="round,pad=0,rounding_size=0.012",
        linewidth=linewidth,
        facecolor=colors[0],
        edgecolor=colors[1],
        linestyle=linestyle,
        transform=ax.transAxes,
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(
        cx,
        cy,
        label,
        ha="center",
        va="center",
        fontsize=fontsize,
        color="#1A202C",
        transform=ax.transAxes,
        zorder=3,
        linespacing=1.35,
    )
    return (x0, y0, cx + w / 2, cy + h / 2)


def _mid(r: tuple[float, float, float, float]) -> tuple[float, float]:
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def _top(r: tuple[float, float, float, float]) -> tuple[float, float]:
    return ((r[0] + r[2]) / 2, r[3])


def _bottom(r: tuple[float, float, float, float]) -> tuple[float, float]:
    return ((r[0] + r[2]) / 2, r[1])


def _left(r: tuple[float, float, float, float]) -> tuple[float, float]:
    return (r[0], (r[1] + r[3]) / 2)


def _right(r: tuple[float, float, float, float]) -> tuple[float, float]:
    return (r[2], (r[1] + r[3]) / 2)


def _arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = "#4A5568",
    linewidth: float = 1.3,
    linestyle: str = "-",
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            transform=ax.transAxes,
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=linewidth,
            color=color,
            linestyle=linestyle,
            shrinkA=0,
            shrinkB=0,
            clip_on=False,
            zorder=1,
        )
    )


def _polyline_arrow(
    ax,
    points: list[tuple[float, float]],
    *,
    color: str,
    linewidth: float = 1.3,
    linestyle: str = "-",
) -> None:
    """折线 + 末端箭头（用于绕行：闭回边）。"""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ax.plot(
        xs[:-1],
        ys[:-1],
        color=color,
        linewidth=linewidth,
        linestyle=linestyle,
        transform=ax.transAxes,
        solid_capstyle="round",
        clip_on=False,
        zorder=1,
    )
    ax.annotate(
        "",
        xy=points[-1],
        xytext=points[-2],
        xycoords=ax.transAxes,
        textcoords=ax.transAxes,
        arrowprops={
            "arrowstyle": "-|>",
            "color": color,
            "linewidth": linewidth,
            "linestyle": linestyle,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        annotation_clip=False,
        zorder=1,
    )


def draw_pipeline(ax, note: str) -> None:
    """把 `core §2` 的管线画到 ``ax``（所有坐标均为 axes fraction）。"""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    spine_cx, spine_w, spine_h = 0.14, 0.20, 0.052
    lane_cx = (0.42, 0.69, 0.895)
    lane_w = (0.22, 0.22, 0.17)
    lane_h = 0.052
    row1_y, row2_y, row3_y = 0.520, 0.430, 0.340

    # --- 主轴（generative chain）------------------------------------------
    configs = _box(ax, spine_cx, 0.962, spine_w, spine_h, "configs/*.yaml\n(incl. seed)", colors=_C_INPUT)
    seed = _box(ax, spine_cx, 0.892, spine_w, spine_h, "Seed Manager", colors=_C_INPUT)
    genome = _box(ax, spine_cx, 0.822, spine_w, spine_h, "genome\n(DNA + motif)", colors=_C_MODEL)
    dev = _box(
        ax, spine_cx, 0.752, spine_w, spine_h, "development\n(GRN / RGCD)", colors=_C_MODEL
    )
    conn = _box(
        ax, spine_cx, 0.682, spine_w, spine_h, "connectome\n(DanioNet, 48-node)", colors=_C_MODEL
    )
    # Arena 画成一条宽箱：它是三条分支的**扇出点**（core §2 的 `├──► / ├──► / └──►`）。
    arena = _box(
        ax,
        0.50,
        0.600,
        0.93,
        0.060,
        "Arena simulation  (20 Hz x 600 steps / episode)",
        colors=_C_SIM,
        fontsize=9.5,
    )

    # --- 三条并行分支 ------------------------------------------------------
    traj = _box(
        ax, lane_cx[0], row1_y, lane_w[0], lane_h, "expert trajectories\n(ExpertPolicy)", colors=_C_BRANCH
    )
    evlog = _box(ax, lane_cx[1], row1_y, lane_w[1], lane_h, "event log", colors=_C_BRANCH)
    snap = _box(
        ax,
        lane_cx[2],
        row1_y,
        lane_w[2],
        lane_h,
        "frame snapshots\n(position / heading / energy)",
        colors=_C_BRANCH,
        fontsize=7.6,
    )
    bc = _box(ax, lane_cx[0], row2_y, lane_w[0], lane_h, "BC training", colors=_C_BRANCH)
    met = _box(ax, lane_cx[1], row2_y, lane_w[1], lane_h, "experiment metrics", colors=_C_BRANCH)
    ws = _box(
        ax,
        lane_cx[2],
        row2_y,
        lane_w[2],
        lane_h,
        "WS real-time push\n(demo only, no disk)",
        colors=_C_BRANCH,
        fontsize=7.6,
    )
    dw = _box(
        ax,
        lane_cx[0],
        row3_y,
        lane_w[0],
        lane_h,
        "Delta W\n(contemporary, NOT inherited)",
        colors=_C_BLOCK,
        fontsize=8.0,
    )

    # --- 演化闭环 ----------------------------------------------------------
    fit = _box(ax, spine_cx, 0.470, spine_w, spine_h, "fitness", colors=_C_FLOW)
    sel = _box(ax, spine_cx, 0.380, spine_w, spine_h, "selection / drift", colors=_C_FLOW)
    nxt = _box(ax, spine_cx, 0.290, spine_w, spine_h, "next-generation\ngenome", colors=_C_FLOW)

    # --- 两个去向（storage sinks）-----------------------------------------
    runs = _box(
        ax,
        0.68,
        0.105,
        0.52,
        spine_h,
        "results/runs/<experiment_id>-s<seed>/   (NOT committed)",
        colors=_C_STORE,
        fontsize=8.2,
    )
    art = _box(
        ax,
        0.68,
        0.032,
        0.52,
        spine_h,
        "artifacts/   (committed: fixed seed, demo population, small checkpoints)",
        colors=_C_STORE,
        fontsize=8.2,
    )

    # --- 主轴箭头 ----------------------------------------------------------
    for a, b in ((configs, seed), (seed, genome), (genome, dev), (dev, conn)):
        _arrow(ax, _bottom(a), _top(b))
    _arrow(ax, _bottom(conn), (spine_cx, arena[3]))
    _arrow(ax, (spine_cx, arena[1]), _top(fit))
    _arrow(ax, _bottom(fit), _top(sel))
    _arrow(ax, _bottom(sel), _top(nxt))

    # 闭回：下一代 genome -> genome（绕左行，避开主轴上的箱体）
    _polyline_arrow(
        ax,
        [_left(nxt), (-0.040, _left(nxt)[1]), (-0.040, _left(genome)[1]), _left(genome)],
        color="#3D7A4E",
        linewidth=1.3,
    )

    # --- 三条分支的扇出 + 竖直推进 -----------------------------------------
    for cx, head in zip(lane_cx, (traj, evlog, snap), strict=True):
        _arrow(ax, (cx, arena[1]), _top(head), color="#6A3D8F")
    for head, tail in ((traj, bc), (bc, dw), (evlog, met), (snap, ws)):
        _arrow(ax, _bottom(head), _top(tail), color="#6A3D8F")

    # --- 遗传边界（不遗传）：红色虚线 + 只作图示的 blocked 边 ---------------
    ax.add_patch(
        FancyBboxPatch(
            (dw[0] - 0.012, dw[1] - 0.012),
            (dw[2] - dw[0]) + 0.024,
            (dw[3] - dw[1]) + 0.024,
            boxstyle="round,pad=0,rounding_size=0.014",
            linewidth=1.4,
            facecolor="none",
            edgecolor="#B23A3A",
            linestyle=(0, (4, 3)),
            transform=ax.transAxes,
            zorder=4,
        )
    )
    _arrow(
        ax,
        _left(dw),
        _right(nxt),
        color="#B23A3A",
        linewidth=1.6,
        linestyle=(0, (4, 3)),
    )
    ax.text(
        0.305,
        0.285,
        "NOT inherited",
        ha="center",
        va="center",
        fontsize=7.6,
        color="#B23A3A",
        fontweight="bold",
        transform=ax.transAxes,
        zorder=5,
    )
    ax.text(
        0.22,
        0.163,
        "GENETIC BOUNDARY (core §2 / §4.4)\n"
        "Delta W is contemporary and NOT inherited: offspring\n"
        "inherit DNA only and re-develop from scratch, so Delta W\n"
        "never enters the reproduction path.",
        ha="center",
        va="center",
        fontsize=7.4,
        color="#8C2F2F",
        transform=ax.transAxes,
        linespacing=1.45,
        bbox={
            "boxstyle": "round,pad=0.5",
            "facecolor": "#FBE9E9",
            "edgecolor": "#B23A3A",
            "linestyle": (0, (4, 3)),
            "linewidth": 1.0,
            "alpha": 0.95,
        },
        zorder=5,
    )

    # --- 两个去向 ----------------------------------------------------------
    # 走 x=0.56 这条竖直通道：它夹在 lane 1（右缘 0.53）与 lane 2（左缘 0.58）之间，
    # 不穿任何箱体（斜连会切过 `experiment metrics`）。
    _arrow(ax, (0.56, arena[1]), (0.56, runs[3]), color="#8A6D0B", linewidth=1.4)
    _arrow(ax, _bottom(runs), _top(art), color="#8A6D0B", linewidth=1.4)

    # --- 图例 --------------------------------------------------------------
    ax.text(
        0.955,
        0.800,
        "solid arrow: data / control flow\n"
        "red dashed arrow: genetic boundary (blocked path)\n"
        "red dashed box: lifetime-only phenotype, not inherited",
        ha="right",
        va="top",
        fontsize=7.2,
        color="#4A5568",
        transform=ax.transAxes,
        linespacing=1.5,
        bbox={
            "boxstyle": "round,pad=0.45",
            "facecolor": "white",
            "edgecolor": "#CBD5E0",
            "linewidth": 0.8,
            "alpha": 0.95,
        },
        zorder=5,
    )

    ax.set_title(
        "EvoGenesis data pipeline (authoritative: core §2 Data Pipeline Overview)",
        fontsize=12,
        pad=12,
    )
    _stamp(ax.figure, note)


def _stamp(fig, note: str) -> None:
    """图脚注：可回溯标识（同 `make_figs.py` 的 `_stamp` / `provenance` 做法）。"""
    fig.text(0.995, 0.006, note, ha="right", va="bottom", fontsize=6.5, color="0.45")


def build_figure(note: str) -> tuple[Path, Path, dict[str, pd.DataFrame], dict[str, str]]:
    """画 F12 **并**写配套 xlsx；返回 ``(图路径, Excel 路径, sheets, provenance)``。

    一个调用 = 一张图 + 一份同名数据表（长期要求：改样式不改数据，
    见 `paper/图表-数据对照表.md` §1）。
    """
    fig = plt.figure(figsize=(15.5, 12.5))
    ax = fig.add_axes((0.06, 0.05, 0.93, 0.90))
    draw_pipeline(ax, note)

    OUT.mkdir(parents=True, exist_ok=True)
    fig_path = OUT / "fig_pipeline.png"
    fig.savefig(fig_path, dpi=150, facecolor="white")
    plt.close(fig)

    sheets = {"nodes": nodes_frame(), "edges": edges_frame()}
    provenance = {
        "figure": f"{FIGURE_ID} data-flow overview",
        "authoritative_source": AUTHORITATIVE_SOURCE,
        "core_section": CORE_SECTION,
        "related_sections": "core §3 (seed) / §4.4 (genetic boundary) / §5 (event log) / §7 (storage)",
        "n_nodes": str(len(PIPELINE_NODES)),
        "n_edges": str(len(PIPELINE_EDGES)),
        "genetic_boundary": "delta_w -> next_genome is a blocked (dashed) edge: Delta W is NOT inherited",
        "branch_origin": "three branches fan out from arena (core §2 prose + core §4.1 / §5)",
        "storage_attribution": "arena -> results/runs by producer ownership (core §4.5 / §7)",
        "reproduce": "python scripts/make_fig_pipeline.py",
        "note": note,
    }
    workbook = export_workbook(
        fig_path, sheets, caption=CAPTION, sources=SOURCES, provenance=provenance
    )
    return fig_path, workbook, sheets, provenance


def main() -> None:
    force_utf8_stdout()  # 被管道/重定向时不因中文而崩（`experiment/console.py`）
    note = f"pipeline @ {_commit()} (source: core §2; figure {FIGURE_ID})"
    fig_path, workbook, _sheets, _provenance = build_figure(note)

    print(f"图：{fig_path.relative_to(ROOT)}")
    print(f"数据：{workbook.relative_to(ROOT)}")
    print()
    print(f"节点 {len(PIPELINE_NODES)} 个 / 边 {len(PIPELINE_EDGES)} 条（出处 {CORE_SECTION}）：")
    for nid, label, kind, _note, source in PIPELINE_NODES:
        print(f"  {nid:<18}{kind:<11}{label.splitlines()[0]:<48}{source}")
    print()
    print("边（kind=blocked 即遗传边界）：")
    for src, dst, kind, _note in PIPELINE_EDGES:
        print(f"  {src:<18}-> {dst:<18}{kind}")


if __name__ == "__main__":
    main()
