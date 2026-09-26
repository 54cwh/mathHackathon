"""F7「连接矩阵 / 拓扑」：把 48x48 的 ``W^0`` / 支撑 / Dale 符号结构画成可投稿图。

数据源**只有一处**：``results/tables/connectome_matrix.json``
（由 `scripts/dump_connectome_matrix.py` 从发育产物落盘）。本脚本**不重新发育**、不
重算任何尺寸数字 —— 图与落盘产物因此逐字对应，改样式不会改数据
（`paper/图表-数据对照表.md` §1 的长期约定）。

四个面板，各自回答一个「易混对比」：

- (a) ``W^0`` 的 48x48 热图：**补零容量 48 与实际活跃 N 的差别**（``N .. 47`` 行列恒 0），
      并给出「张量元素 / 活跃块 / 支撑边」三级数量阶梯 —— 即**支撑 vs 全张量 2304**。
- (b) 按 cell type 分块的**符号结构**：Dale 约束（`RGCD §10`，符号由突触前类型定）
      使抑制性行整行 ``<= 0``、其余行 ``=> 0``，块状结构肉眼可验。
- (c) 全种群的 ``N`` 分布 vs **容量上界 48**（与 ``initial_precursors`` 给出的下界 24）。
- (d) 全种群的**支撑边数分布**，并标出它只占 ``Theta`` 张量元素的一小部分。

图的文字**一律用英文**：matplotlib 默认字体不含 CJK，中文会渲染成方框（同
`make_figs.py` / `make_fig_viability.py`）；中文叙述进配套 Excel 的 `_manifest`。
图脚注带 ``fig_connectome @ git_commit`` 可回溯标识。

输出：

    results/figs/connectome/fig_connectome.png
    results/figs/connectome/data/fig_connectome.xlsx   （首 sheet 为 `_manifest`）

用法：

    .venv/Scripts/python.exe scripts/dump_connectome_matrix.py
    .venv/Scripts/python.exe scripts/make_fig_connectome.py
    .venv/Scripts/python.exe scripts/make_fig_connectome.py --json <path> --out-dir <dir>
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import matplotlib

matplotlib.use("Agg")  # 无显示环境

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from evogenesis.experiment.console import force_utf8_stdout  # noqa: E402
from evogenesis.experiment.figdata import export_workbook  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "results" / "tables" / "connectome_matrix.json"
DEFAULT_OUT = ROOT / "results" / "figs" / "connectome"
DUMP_SCRIPT = ROOT / "scripts" / "dump_connectome_matrix.py"

#: 图的 caption（进 `.xlsx` 的 `_manifest`）。
CAPTION = (
    "F7 connectome: 48x48 padded W0 with the active N x N block, cell-type-blocked Dale sign "
    "structure, and the population distributions of N and of support-edge count"
)

#: 逐 sheet 的口径说明（进 `.xlsx` 的 `_manifest`）。
SOURCES: dict[str, str] = {
    "matrix": (
        "代表个体的 48x48 张量摊平成长表（2304 行/个体）；w0/support_bool/sign 取自 "
        "DanioNet 的 weights0 / support / sign0，pre/post_cell_type 为 padding 显式标出"
    ),
    "w0_wide": "primary 代表个体的 48x48 W0 宽表（48 行 x 48 列 + 行号列），padding 行列恒 0",
    "support_wide": "同上的支撑掩码宽表（1 = 支撑内、可训练；0 = 掩码外）",
    "summary": (
        "probe_architecture.per_individual 原样搬运（含 danionet_built=false 的个体，"
        "不静默丢）；is_representative 标出被落盘张量的个体"
    ),
    "cell_types": "逐个体 x 六类 cell type 的计数与占比（来自发育产物 cell_type 的计数）",
    "representatives": (
        "代表个体的尺寸与 E/I 边数；probe_support_edges 一列是该个体在 probe_architecture "
        "里的原始读数，用于交叉核对支撑口径"
    ),
    "population": (
        "probe_architecture 的 pooled / pooled_danionet_built / pooled_viable 三块 + Theta 量"
    ),
}


def _load_dump_module(script: Path = DUMP_SCRIPT) -> ModuleType:
    """按路径载入 `scripts/dump_connectome_matrix.py`（`scripts/` 不是包）。

    图脚本复用 dump 脚本的**成形函数**（长表 / 摘要 / 六类计数），从而与 CSV
    保证同一份长表，不会出现「图一套、Excel 另一套」。
    """
    name = "dump_connectome_matrix"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, script)
    if spec is None or spec.loader is None:  # pragma: no cover - 仅在脚本被删时触发
        raise ImportError(f"无法载入 {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


def _stamp(fig, note: str) -> None:
    fig.text(0.995, 0.005, note, ha="right", va="bottom", fontsize=6.5, color="0.45")


def _display_path(path: Path) -> str:
    """仓库内路径记成相对（正斜杠，跨平台一致）；仓库外退化为绝对路径（不因 relative_to 崩）。"""
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def load_matrix_payload(path: Path) -> dict[str, Any]:
    """读回落盘产物；缺件或格式不对时给出**能照着做**的报错。"""
    if not path.is_file():
        raise FileNotFoundError(
            f"缺少 {path}；先跑 `.venv/Scripts/python.exe scripts/dump_connectome_matrix.py`"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key in ("domains", "max_nodes", "representatives", "architecture_probe"):
        if key not in payload:
            raise ValueError(f"{path} 不是 connectome_matrix 产物：缺字段 {key}")
    if not payload["representatives"]:
        raise ValueError(f"{path} 里没有任何代表个体（本次样本无可构造 DanioNet 的个体），无法出图")
    return payload


def primary_representative(payload: dict[str, Any]) -> dict[str, Any]:
    """primary 代表个体（落盘时按 ``master_seeds`` 顺序的第一个）。"""
    for rep in payload["representatives"]:
        if rep.get("is_primary"):
            return rep
    return payload["representatives"][0]


def _individuals(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return payload["architecture_probe"]["per_individual"]


def _representative_frame(payload: dict[str, Any]) -> pd.DataFrame:
    """代表个体一行：尺寸 + E/I 边数 + 与 probe 的交叉核对列。"""
    rows = []
    for rep in payload["representatives"]:
        probe_record = rep.get("probe_record") or {}
        rows.append(
            {
                "master_seed": rep["master_seed"],
                "individual_index": rep["index"],
                "is_primary": bool(rep.get("is_primary")),
                "n_neurons": rep["n_neurons"],
                "support_edges": rep["support_edges"],
                "trainable_elements": rep["trainable_elements"],
                "support_density": rep["support_density"],
                "tensor_elements": rep["tensor_elements"],
                "support_share_of_tensor": rep["support_share_of_tensor"],
                "excitatory_edges": rep["excitatory_edges"],
                "inhibitory_edges": rep["inhibitory_edges"],
                "probe_n_neurons": probe_record.get("n_neurons"),
                "probe_support_edges": probe_record.get("support_edges"),
                "probe_trainable_elements": probe_record.get("trainable_elements"),
                "probe_phenotype_viable": probe_record.get("phenotype_viable"),
            }
        )
    return pd.DataFrame(rows)


def _wide(matrix: list[list[float]]) -> pd.DataFrame:
    """48x48 嵌套列表 -> 带行号列的宽表（48 行 x 49 列，Excel 里可读）。"""
    frame = pd.DataFrame(matrix, dtype=float)
    frame.columns = [f"col_{c}" for c in range(frame.shape[1])]
    frame.insert(0, "row", list(range(frame.shape[0])))
    return frame


def build_figure(
    payload: dict[str, Any],
    out_dir: Path,
    note: str,
    *,
    source_json: Path | None = None,
) -> tuple[Path, Path, dict[str, pd.DataFrame], dict[str, str]]:
    """画 2x2 面板**并**写配套 xlsx；返回 (图路径, Excel 路径, sheets, provenance)。

    一个调用 = 一张图 + 一份同名数据表（长期要求：改样式不改数据，
    见 `paper/图表-数据对照表.md` §1）。``source_json`` 进 provenance，
    使 manifest 能指回**确切**的输入文件（不是只写个脚本名）。
    """
    dump = _load_dump_module()
    domains: tuple[str, ...] = tuple(payload["domains"])
    max_nodes = int(payload["max_nodes"])
    probe = payload["architecture_probe"]
    rep = primary_representative(payload)

    n = int(rep["n_neurons"])
    w0 = np.asarray(rep["w0"], dtype=float)
    support = np.asarray(rep["support"], dtype=bool)
    cell_type = np.asarray(rep["cell_type"], dtype=int)[:n]
    edges = int(rep["support_edges"])
    tensor_cells = max_nodes * max_nodes
    inhibitory_index = int(rep["inhibitory_index"])

    ns = np.asarray([r["n_neurons"] for r in _individuals(payload)], dtype=int)
    edge_counts = np.asarray([r["support_edges"] for r in _individuals(payload)], dtype=int)
    n_seeds = len(payload["master_seeds"])
    n_per_seed = int(payload["n_individuals_per_seed"])

    # 版式 = **左 / 中 / 右** 三栏（与 `paper/latex/sections/02-method.tex` 的 fig:connectome
    # 图注措辞一一对应）：左 = 48x48 张量热图，中 = 按 cell type 分块的符号结构，
    # 右 = 群体分布（上：N， 下：支撑边数）。右栏内部上下分格，使「分布」两问同栏并列。
    fig = plt.figure(figsize=(17.0, 6.4))
    grid = fig.add_gridspec(
        2,
        3,
        left=0.055,
        right=0.985,
        top=0.90,
        bottom=0.135,
        width_ratios=(1.0, 1.0, 1.15),
        height_ratios=(1.0, 1.0),
        wspace=0.48,
        hspace=0.60,
    )
    ax_left = fig.add_subplot(grid[:, 0])
    ax_mid = fig.add_subplot(grid[:, 1])
    ax_right_top = fig.add_subplot(grid[0, 2])
    ax_right_bottom = fig.add_subplot(grid[1, 2])

    # (A) W^0 的 48x48：补零容量 48 与活跃 N 的差别一眼可见（padding 行列恒 0）。
    ax = ax_left
    masked = np.ma.masked_where(~support, w0)
    limit = float(np.abs(w0).max()) or 1.0
    cmap = plt.get_cmap("RdBu_r").copy().with_extremes(bad="#f0f0f0")
    ax.imshow(masked, cmap=cmap, vmin=-limit, vmax=limit, interpolation="nearest")
    ax.add_patch(Rectangle((-0.5, -0.5), n, n, fill=False, ec="black", lw=1.5))
    tick_step = 8
    ax.set_xticks(range(0, max_nodes, tick_step))
    ax.set_yticks(range(0, max_nodes, tick_step))
    ax.set_xlabel("postsynaptic neuron index (padded slot)", fontsize=8.5)
    ax.set_ylabel("presynaptic neuron index (padded slot)", fontsize=8.5)
    ax.set_title(
        f"(A) $W^0$ on the ${max_nodes}\\times{max_nodes}$ tensor", fontsize=9.5, loc="left"
    )
    ladder = (
        f"seed {rep['master_seed']} / individual {rep['index']}\n"
        f"capacity     {max_nodes}x{max_nodes} = {tensor_cells} cells\n"
        f"active block {n}x{n} = {n * n} cells\n"
        f"support      {edges} edges = {edges / tensor_cells:.1%} of tensor\n"
        f"padding rows/cols {n}..{max_nodes - 1} = 0"
    )
    # 阶梯框放在**右下角的补零区**上：那里恒为 0，压住不丢信息，也正好把「容量 vs 实际」
    # 与「支撑 vs 全张量」两组对比并排写在读者眼睛会落到的那块空白上。
    ax.text(
        0.985,
        0.02,
        ladder,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.8,
        family="monospace",
        bbox={"boxstyle": "round,pad=0.35", "fc": "white", "ec": "0.7", "alpha": 0.92},
    )
    # 色标标题放**上方**而不是右侧：三栏版式里 (A) 与 (B) 之间只剩一条窄缝，
    # 右侧标签会和 (B) 的 y 轴标签叠在一起。
    colorbar = fig.colorbar(
        plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=-limit, vmax=limit)),
        ax=ax,
        fraction=0.045,
        pad=0.025,
    )
    colorbar.ax.set_title("$W^0$", fontsize=8, pad=6)

    # (B) 按 cell type 分块的符号结构：Dale 约束（符号由突触前类型定）肉眼可验。
    ax = ax_mid
    # 稳定排序：同类神经元保持原索引顺序，块的边界即可用累计计数定位。
    order = np.argsort(cell_type, kind="stable")
    sign_block = np.sign(w0[:n, :n])[np.ix_(order, order)].astype(int)
    sign_cmap = ListedColormap(["#c0392b", "#f0f0f0", "#2c7fb8"])
    ax.imshow(sign_block + 1, cmap=sign_cmap, vmin=-0.5, vmax=2.5, interpolation="nearest")
    counts = [int((cell_type == k).sum()) for k in range(len(domains))]
    centers = np.cumsum(counts) - np.asarray(counts) / 2.0 - 0.5
    for boundary in (np.cumsum(counts) - 0.5)[:-1]:
        ax.axhline(boundary, color="black", lw=0.7)
        ax.axvline(boundary, color="black", lw=0.7)
    ax.set_xticks(centers)
    ax.set_xticklabels(list(domains), rotation=40, ha="right", fontsize=7.5)
    ax.set_yticks(centers)
    ax.set_yticklabels(list(domains), fontsize=7.5)
    # 三栏版式下 (B) 右侧没有空位，故 Dale 口径写进 x 轴标签（不压住任何数据格），
    # E / I 边数进标题。
    ax.set_xlabel(
        "cell type of the postsynaptic neuron\n"
        f"Dale sign (RGCD 10) is set by the PRESYNAPTIC type: "
        f"{domains[inhibitory_index]} -> -1, all others -> +1",
        fontsize=8,
    )
    ax.set_ylabel("cell type of the presynaptic neuron", fontsize=8.5)
    ax.set_title(
        f"(B) Dale sign by cell type (E {rep['excitatory_edges']} / I {rep['inhibitory_edges']})",
        fontsize=9.5,
        loc="left",
    )
    ax.legend(
        handles=[
            Line2D([], [], marker="s", ls="", ms=8, color="#2c7fb8", label="excitatory edge (+1)"),
            Line2D([], [], marker="s", ls="", ms=8, color="#c0392b", label="inhibitory edge (-1)"),
            Line2D([], [], marker="s", ls="", ms=8, color="#f0f0f0", label="no edge"),
        ],
        fontsize=7.5,
        loc="lower right",
        framealpha=0.92,
    )

    # (C) N 的分布 vs 容量上界 48：48 是容量，不是某个基因型的规模。
    ax = ax_right_top
    ax.hist(ns, bins=range(int(ns.min()), int(ns.max()) + 2), color="tab:blue", alpha=0.85)
    ax.axvline(max_nodes, color="tab:red", ls="--", lw=1.6, label=f"capacity {max_nodes}")
    ax.axvline(
        int(probe["initial_precursors"]),
        color="tab:green",
        ls=":",
        lw=1.6,
        label=f"lower bound {probe['initial_precursors']}",
    )
    ax.set_xlabel("realized active neuron count N (per genotype)", fontsize=8.5)
    ax.set_ylabel("genotypes", fontsize=8.5)
    ax.set_title(f"(C) Capacity {max_nodes} vs realized N", fontsize=9.5, loc="left")
    ax.text(
        0.03,
        0.95,
        f"n = {ns.size} = {n_seeds} seeds x {n_per_seed}\n"
        f"median = {int(np.median(ns))}   range = {int(ns.min())}--{int(ns.max())}\n"
        f"at capacity: {int((ns == max_nodes).sum())}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.5,
        family="monospace",
        bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    ax.legend(fontsize=7.5, loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    # (D) 支撑边数的分布：它只是 Theta 张量元素的一小部分。
    ax = ax_right_bottom
    ax.hist(edge_counts, bins=18, color="tab:purple", alpha=0.8)
    ax.axvline(
        float(np.median(edge_counts)),
        color="tab:orange",
        ls="--",
        lw=1.6,
        label=f"median = {int(np.median(edge_counts))}",
    )
    ax.set_xlabel("support edges per genotype (= trainable Theta elements)", fontsize=8.5)
    ax.set_ylabel("genotypes", fontsize=8.5)
    ax.set_title(f"(D) Support edges vs the {tensor_cells}-cell tensor", fontsize=9.5, loc="left")
    ax.text(
        0.03,
        0.95,
        f"n = {edge_counts.size}   median = {int(np.median(edge_counts))}\n"
        f"range = {int(edge_counts.min())}--{int(edge_counts.max())}   "
        f"tensor = {tensor_cells} -> share {np.median(edge_counts) / tensor_cells:.1%}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.5,
        family="monospace",
        bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    ax.legend(fontsize=7.5, loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle(
        "F7  Connectome: 48-node capacity, realized N, and the supported sub-tensor", fontsize=12
    )
    _stamp(fig, note)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_path = out_dir / "fig_connectome.png"
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)

    matrix_frame = pd.DataFrame(dump.long_records(payload))
    sheets: dict[str, pd.DataFrame] = {
        "matrix": matrix_frame,
        "w0_wide": _wide(rep["w0"]),
        "support_wide": _wide(rep["support"]),
        "summary": pd.DataFrame(dump.summary_records(payload)),
        "cell_types": pd.DataFrame(dump.cell_type_records(payload)),
        "representatives": _representative_frame(payload),
        "population": pd.DataFrame(dump.population_records(payload)),
    }
    provenance = {
        "figure": "F7 连接矩阵 / 拓扑",
        "matrix_json": _display_path(source_json if source_json is not None else DEFAULT_JSON),
        "matrix_json_generated_by": str(payload.get("generated_by", "")),
        "matrix_json_digest": str(payload.get("digest", "")),
        "config_sha256": str(payload.get("config_sha256", "")),
        "master_seeds": ", ".join(str(s) for s in payload["master_seeds"]),
        "n_individuals_per_seed": str(payload["n_individuals_per_seed"]),
        "primary_representative": f"seed {rep['master_seed']} index {rep['index']}",
        "primary_n_neurons": str(n),
        "primary_support_edges": str(edges),
        "primary_excitatory_edges": str(rep["excitatory_edges"]),
        "primary_inhibitory_edges": str(rep["inhibitory_edges"]),
        "tensor_cells_per_individual": str(tensor_cells),
        "gene_to_column_caveat": (
            "w0_wide/support_wide 只含 primary 代表个体；全部代表个体的 48x48 见 matrix 长表"
        ),
        "reproduce": (
            "python scripts/dump_connectome_matrix.py && python scripts/make_fig_connectome.py"
        ),
        "note": note,
    }
    workbook = export_workbook(
        fig_path, sheets, caption=CAPTION, sources=SOURCES, provenance=provenance
    )
    return fig_path, workbook, sheets, provenance


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdout()  # 被管道/重定向时不因中文而崩（`experiment/console.py`）
    parser = argparse.ArgumentParser(description="F7: 48x48 connectome matrix / topology figure.")
    parser.add_argument("--json", default=str(DEFAULT_JSON), help="dump_connectome_matrix 的产物")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT), help="图与 data/ 的输出目录")
    args = parser.parse_args(argv)

    json_path = Path(args.json)
    payload = load_matrix_payload(json_path)
    rep = primary_representative(payload)
    note = (
        f"fig_connectome @ {_commit()} "
        f"(seeds {payload['master_seeds']}, n={payload['n_individuals_per_seed']}/seed, "
        f"primary = seed {rep['master_seed']} idx {rep['index']})"
    )
    fig_path, workbook, sheets, _provenance = build_figure(
        payload, Path(args.out_dir), note, source_json=json_path
    )

    print(f"图：{_display_path(fig_path)}")
    print(f"数据：{_display_path(workbook)}")
    print(f"来源：{_display_path(json_path)}  digest={payload.get('digest')}")
    print()
    print(
        f"primary 代表个体：seed {rep['master_seed']} idx {rep['index']}"
        f"  N={rep['n_neurons']}  支撑边={rep['support_edges']}"
        f"  E/I={rep['excitatory_edges']}/{rep['inhibitory_edges']}"
        f"  密度={rep['support_density']}"
    )
    print(
        "sheets："
        + "  ".join(f"{name}({frame.shape[0]}x{frame.shape[1]})" for name, frame in sheets.items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
