"""F7 连接矩阵落盘：从**发育产物**直接导出 48x48 的 ``W^0`` / 支撑掩码 / ``Theta``。

为什么需要本脚本（阻塞可自上拆掉）
----------------------------------

``paper/图表-数据对照表.md`` §4 把 F7「连接矩阵 / 拓扑可视化」的阻塞写成
「需 48x48 矩阵落盘」+「与 api 边界一起定」。**该阻塞不必等下游**：48x48 张量不是
WS / api 侧的私产，而是 `DanioNet` 对发育产物做 batch 内补零后的缓冲区
（`connectome/danionet.py` 的 ``weights0`` / ``support`` / ``theta``，形状
``(batch, max_nodes, max_nodes)``，``max_nodes = development.max_neurons = 48``）。
把它写成仓库内的可追溯产物，F7 就与 api 落盘解耦。

与 `scripts/probe_architecture.py` 的关系（**口径同源，不重复实现**）
------------------------------------------------------------------

架构尺寸（``N`` / 支撑边数 / 密度 / 可训练元素数）一律由
``probe_architecture.probe_architecture`` 产出，并原样嵌进本产物（``architecture_probe``
块）；本脚本只在其上追加「把张量本身落盘」这一层。故 F7 图上的尺寸数字与其它图
引用的是**同一个函数**的输出，不会长出第二套口径。每个代表个体另存
``probe_record``（该个体在 probe 里的原始记录行），供第三方交叉核对。

三条口径提示（引用数字前必读）
------------------------------

1. **容量 48 != 实际 N**：``max_nodes = 48`` 是张量的补零容量；实测 ``N`` 中位 36、
   范围 26--44（见 ``architecture_probe.pooled``）。张量里 ``N .. 47`` 的行列恒 0，
   即 ``neuron_mask`` 为假处``weights0`` / ``support`` / ``theta`` 全为 0。
2. **支撑 != 全张量**：``Theta`` 有 ``48 x 48 = 2304`` 个元素，但只有支撑 ``A`` 之内
   才可训练（``support`` 掩码，``Theta`` 初值 = ``softplus^{-1}(|W^0|)``）；
   ``allow_self_loops = false``，故对角恒 0。
3. **支撑边数 == 可训练元素数**：两者同源（``DanioNet.support`` 的元素和）。本脚本对
   每个代表个体断言一次；不等即说明支撑口径漂了，宁可报错也不落盘一个自相矛盾的数字。

Dale 符号（`RGCD §10`，`development/rgcd.py::apply_dale_sign`）
---------------------------------------------------------------

符号由**突触前**（行 ``i``）的类型定：``cell_type[i] == inhibitory`` 时整行取负，
否则取正。故 ``W^0`` 的行结构是自洽的 —— 抑制性行全部 ``<= 0``，其余行全部 ``>= 0``。
``support_edges_by_pre_type`` / ``by_post_type`` 把这一结构量化落盘（E / I 边数），
供 F7 的 (b) 面板与后续 E-I 平衡讨论直接引用。

确定性
------

产物不含任何时间戳；同一 ``(master_seeds, n_individuals, representatives_per_seed,
config)`` 两次运行**逐字节相同**（``digest`` 给内容 sha256，口径与
`probe_architecture.content_digest` 完全一致）。``develop`` 的随机流按
``(master_seed, index)`` 派生（`core §3`），与「一次发育几个个体」无关 —— 这正是本
脚本只重发育代表个体的前提；`tests/test_dump_connectome_matrix.py` 对此有守护断言。

输出
----

    results/tables/connectome_matrix.json   机器可读（48x48 数值 + 支撑坐标 + Theta 量）
    results/tables/connectome_matrix.csv    人类可读扁平长表（row, col, w0, support_bool, sign）

用法::

    .venv/Scripts/python.exe scripts/dump_connectome_matrix.py
    .venv/Scripts/python.exe scripts/dump_connectome_matrix.py --seeds 1103 --n-individuals 14
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import statistics
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

from evogenesis.connectome.danionet import DanioNet
from evogenesis.experiment.console import force_utf8_stdout
from evogenesis.pipeline.model_chain import (
    initial_population,
    load_model_chain_config,
    motif_catalog,
    phenotype_of,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "default_model.yaml"
DEFAULT_JSON = ROOT / "results" / "tables" / "connectome_matrix.json"
DEFAULT_CSV = ROOT / "results" / "tables" / "connectome_matrix.csv"
PROBE_SCRIPT = ROOT / "scripts" / "probe_architecture.py"

#: 正式 seed 轴（`configs/experiment_seeds.yaml` 的 ``seeds: [1103, 2207, 3301]``）。
DEFAULT_SEEDS = "1103,2207,3301"
#: 每个 seed 发育的个体数（与 `probe_architecture` / F6 的 14 同量级，口径可比）。
DEFAULT_N_INDIVIDUALS = 14
#: 每个 seed 落盘几个代表个体的完整张量（1 = 中位 N 那个）。
DEFAULT_REPRESENTATIVES_PER_SEED = 1
#: 本产物的 `experiment_id`（只进 `mint_id` 的 ID 字符串，**不参与任何数值**）。
EXPERIMENT_ID = "connectome-matrix"

#: CSV / Excel `matrix` 长表的列（顺序即落盘顺序）。
LONG_COLUMNS: tuple[str, ...] = (
    "master_seed",
    "individual_index",
    "row",
    "col",
    "w0",
    "support_bool",
    "sign",
    "pre_cell_type",
    "post_cell_type",
)

#: 支撑掩码之外的占位标签（padding 行的 `cell_type` 数值上是 0，与 sensory 撞号，故显式区分）。
PADDING_LABEL = "padding"


def load_probe_module(script: Path = PROBE_SCRIPT) -> ModuleType:
    """按路径载入 `scripts/probe_architecture.py`（`scripts/` 不是包）。

    先查 `sys.modules`：pytest 里 `tests/test_probe_architecture.py` 可能已经载入过它，
    重复 ``exec_module`` 会得到两个互不相干的模块对象（`isinstance` / 缓存全乱）。
    """
    name = "probe_architecture"
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


def _as_float_matrix(tensor: Any) -> list[list[float]]:
    """``float32`` 张量 -> 嵌套 ``float`` 列表。

    ``float32 -> float64`` 是**精确**提升（无舍入），故落盘值与张量逐位相同，
    不需要也不应该再round。
    """
    return np.asarray(tensor.detach().cpu().numpy(), dtype=np.float64).tolist()


def select_representatives(
    records: list[dict[str, Any]],
    master_seeds: list[int],
    per_seed: int,
) -> dict[int, list[int]]:
    """每个 seed 选 ``per_seed`` 个代表个体（只在**可构造** `DanioNet` 的个体里选）。

    规则（确定性、与输入顺序无关）：取该 seed 下 ``danionet_built`` 的个体，按
    ``(master_seed, index)`` 排定后，以 ``|N - median(N)|`` 升序、``index`` 升序取前
    ``per_seed`` 个。中位数取在**可构造子集**上。

    口径提示：`probe_architecture` 的 ``median_individual`` 是在**全部**个体（含构造
    失败者）上取中位数，本函数是在**可构造**子集上取 —— 因为下游要的是 `DanioNet`
    的 48x48 张量。两者可能不是同一个个体，需要对齐时以 ``probe_record`` 为准。
    """
    if per_seed < 1:
        raise ValueError("per_seed 必须 >= 1")
    chosen: dict[int, list[int]] = {}
    for seed in master_seeds:
        rows = [r for r in records if r["master_seed"] == seed and r["danionet_built"]]
        if not rows:
            continue
        target = statistics.median([r["n_neurons"] for r in rows])
        ranked = sorted(rows, key=lambda r: (abs(r["n_neurons"] - target), r["index"]))
        chosen[seed] = [r["index"] for r in ranked[:per_seed]]
    return chosen


def _edge_counts_by_type(
    support: np.ndarray, cell_type: np.ndarray, n: int, domains: tuple[str, ...]
) -> tuple[dict[str, int], dict[str, int]]:
    """按突触前 / 突触后类型拆支撑边数（只在 ``[0, n)`` 的真实槽位上统计）。

    padding 槽位的 ``cell_type`` 数值上等于 0（= sensory），若不切到 ``[0, n)`` 会把
    padding 误记成 sensory 的边 —— 这个坑在长表里用 ``pre_cell_type == "padding"``
    显式标出，在这里则直接不统计。
    """
    block = support[:n, :n]
    types = np.asarray(cell_type[:n], dtype=int)
    by_pre = {name: int((block & (types[:, None] == k)).sum()) for k, name in enumerate(domains)}
    by_post = {name: int((block & (types[None, :] == k)).sum()) for k, name in enumerate(domains)}
    return by_pre, by_post


def dump_representative(
    phenotype: Any,
    *,
    chain: Any,
    master_seed: int,
    index: int,
    genome_id: str,
    fish_id: str,
    domains: tuple[str, ...],
    probe_record: dict[str, Any] | None,
) -> dict[str, Any]:
    """单个代表个体：`DanioNet` 的 48x48 张量 + 支撑坐标 + Theta 相关量。

    落盘的是 **`DanioNet` 补零后的 48x48**（不是发育产物的 NxN）—— 因为论文里
    「48-node 的含义」讲的正是这个补零张量，F7 的 (a) 面板要展示的就是补零区。
    """
    net = DanioNet([phenotype], master_seed=master_seed, config=chain.network)
    n = int(phenotype.adjacency.shape[0])

    w0 = np.asarray(net.weights0[0].detach().cpu().numpy(), dtype=np.float64)
    support = np.asarray(net.support[0].cpu().numpy(), dtype=bool)
    theta = np.asarray(net.theta.detach()[0].cpu().numpy(), dtype=np.float64)
    cell_type = [int(v) for v in net.cell_type[0].cpu().tolist()]
    neuron_mask = [bool(v) for v in net.neuron_mask[0].cpu().tolist()]

    rows, cols = np.nonzero(support)
    coordinates = [[int(r), int(c)] for r, c in zip(rows, cols, strict=True)]

    support_edges = int(support.sum())
    by_pre, by_post = _edge_counts_by_type(support, cell_type, n, domains)
    inhibitory_index = domains.index("inhibitory")
    inhibitory_edges = by_pre[domains[inhibitory_index]]

    record: dict[str, Any] = {
        "master_seed": master_seed,
        "index": index,
        "genome_id": genome_id,
        "fish_id": fish_id,
        "n_neurons": n,
        "max_nodes": int(chain.network.max_nodes),
        "theta_shape": [1, int(chain.network.max_nodes), int(chain.network.max_nodes)],
        "support_edges": support_edges,
        "trainable_elements": support_edges,
        "support_density": round(support_edges / (n * (n - 1)), 6) if n > 1 else 0.0,
        "tensor_elements": int(chain.network.max_nodes) ** 2,
        "support_share_of_tensor": round(
            support_edges / (int(chain.network.max_nodes) ** 2), 6
        ),
        "excitatory_edges": support_edges - inhibitory_edges,
        "inhibitory_edges": inhibitory_edges,
        "support_edges_by_pre_type": by_pre,
        "support_edges_by_post_type": by_post,
        "inhibitory_index": inhibitory_index,
        "cell_type": cell_type,
        "neuron_mask": neuron_mask,
        "tau": [float(v) for v in net.tau[0].cpu().tolist()],
        "positions": [
            [float(x), float(y)] for x, y in net.positions[0].cpu().numpy().tolist()
        ],
        "w0": _as_float_matrix(net.weights0[0]),
        "support": [[int(v) for v in row] for row in support.astype(int).tolist()],
        "sign": [
            [int(v) for v in row] for row in np.sign(w0).astype(int).tolist()
        ],
        "theta": _as_float_matrix(net.theta[0]),
        "support_coordinates": coordinates,
        "probe_record": probe_record,
    }
    return record


def long_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """把代表个体的 48x48 摊成**长表**记录（CSV 与 Excel `matrix` sheet 同源）。

    长表而非宽表：2304 行 x 9 列在 Excel 里可筛可排序；2304 列或 2304 行的宽表不可读。
    """
    domains = payload["domains"]
    max_nodes = payload["max_nodes"]
    out: list[dict[str, Any]] = []
    for rep in payload["representatives"]:
        n = rep["n_neurons"]
        for row in range(max_nodes):
            pre = domains[rep["cell_type"][row]] if row < n else PADDING_LABEL
            for col in range(max_nodes):
                post = domains[rep["cell_type"][col]] if col < n else PADDING_LABEL
                out.append(
                    {
                        "master_seed": rep["master_seed"],
                        "individual_index": rep["index"],
                        "row": row,
                        "col": col,
                        "w0": rep["w0"][row][col],
                        "support_bool": int(rep["support"][row][col]),
                        "sign": rep["sign"][row][col],
                        "pre_cell_type": pre,
                        "post_cell_type": post,
                    }
                )
    return out


def summary_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """逐个体标量摘要（全种群，含构造失败者），并标出哪些是代表个体。"""
    reps = {(r["master_seed"], r["index"]) for r in payload["representatives"]}
    rows: list[dict[str, Any]] = []
    for record in payload["architecture_probe"]["per_individual"]:
        key = (record["master_seed"], record["index"])
        rows.append(
            {
                "master_seed": record["master_seed"],
                "individual_index": record["index"],
                "n_neurons": record["n_neurons"],
                "active_neurons": record["active_neurons"],
                "support_edges": record["support_edges"],
                "support_density": record["support_density"],
                "trainable_elements": record["trainable_elements"],
                "phenotype_viable": record["phenotype_viable"],
                "danionet_built": record["danionet_built"],
                "is_representative": key in reps,
            }
        )
    return rows


def cell_type_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """逐个体 x 六类 cell type 的计数（长表；缺失类记 0，不插补）。"""
    domains = payload["domains"]
    rows: list[dict[str, Any]] = []
    for record in payload["architecture_probe"]["per_individual"]:
        counts = record["cell_type_counts"]
        total = record["n_neurons"]
        for name in domains:
            rows.append(
                {
                    "master_seed": record["master_seed"],
                    "individual_index": record["index"],
                    "cell_type": name,
                    "n_cells": counts[name],
                    "share": round(counts[name] / total, 6) if total else 0.0,
                }
            )
    return rows


def population_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """汇总块转长表：三个 scope（全种群 / 可构造 / viable）x 各统计量。"""
    probe = payload["architecture_probe"]
    rows: list[dict[str, Any]] = []
    for scope, block in (
        ("all_individuals", probe["pooled"]),
        ("danionet_built", probe["pooled_danionet_built"]),
        ("viable", probe["pooled_viable"]),
    ):
        for quantity in ("n_neurons", "support_edges", "support_density"):
            stats = block[quantity]
            rows.append({"scope": scope, "quantity": quantity, **stats})
        rows.append(
            {
                "scope": scope,
                "quantity": "trainable_elements",
                **probe["theta"]["trainable_elements"],
            }
        )
    rows.append(
        {
            "scope": "all_individuals",
            "quantity": "tensor_elements_per_individual",
            "n": len(probe["per_individual"]),
            "min": probe["theta"]["elements_per_individual"],
            "median": probe["theta"]["elements_per_individual"],
            "mean": probe["theta"]["elements_per_individual"],
            "max": probe["theta"]["elements_per_individual"],
        }
    )
    return rows


def build_payload(
    master_seeds: list[int],
    *,
    n_individuals: int = DEFAULT_N_INDIVIDUALS,
    config_path: Path = DEFAULT_CONFIG_PATH,
    representatives_per_seed: int = DEFAULT_REPRESENTATIVES_PER_SEED,
) -> dict[str, Any]:
    """跑完整落盘并返回 payload（纯函数：同一入参恒得同一 payload）。"""
    if n_individuals < 1:
        raise ValueError("n_individuals 必须 >= 1")
    if not master_seeds:
        raise ValueError("master_seeds 不能为空")
    if representatives_per_seed < 1:
        raise ValueError("representatives_per_seed 必须 >= 1")

    probe = load_probe_module()
    probe_payload = probe.probe_architecture(
        list(master_seeds), n_individuals=n_individuals, config_path=config_path
    )
    chain = load_model_chain_config(config_path)
    domains = tuple(chain.network.domains)

    probe_index = {
        (r["master_seed"], r["index"]): r for r in probe_payload["per_individual"]
    }
    selected = select_representatives(
        probe_payload["per_individual"], list(master_seeds), representatives_per_seed
    )

    representatives: list[dict[str, Any]] = []
    for master_seed in master_seeds:
        indices = selected.get(master_seed)
        if not indices:
            continue
        population = initial_population(
            master_seed=master_seed,
            experiment_id=EXPERIMENT_ID,
            n=n_individuals,
            layout=chain.layout,
        )
        motifs = motif_catalog(master_seed, chain.layout)
        for index in indices:
            individual = population[index]
            phenotype = phenotype_of(
                individual.genome, motifs, master_seed=master_seed, index=index, config=chain.rgcd
            )
            record = dump_representative(
                phenotype,
                chain=chain,
                master_seed=master_seed,
                index=index,
                genome_id=individual.genome_id,
                fish_id=individual.fish_id,
                domains=domains,
                probe_record=probe_index.get((master_seed, index)),
            )
            # 口径自洽：DanioNet 的支撑元素和必须等于 probe 的支撑边数。
            # 不等说明支撑口径漂了 —— 直接报错，不落盘一个自相矛盾的数字。
            expected = (record["probe_record"] or {}).get("support_edges")
            if expected is not None and record["support_edges"] != expected:
                raise AssertionError(
                    f"seed {master_seed} 个体 {index}：本脚本支撑边数 "
                    f"{record['support_edges']} != probe_architecture 的 {expected}"
                )
            record["is_primary"] = not representatives
            representatives.append(record)

    payload: dict[str, Any] = {
        "probe": "connectome_matrix",
        "generated_by": "scripts/dump_connectome_matrix.py",
        "source": (
            "pipeline.model_chain（config -> motif -> 初始种群 -> q(G) -> RGCD -> DanioNet）；"
            "尺寸口径由 probe_architecture.probe_architecture 产出并整体嵌入 architecture_probe"
        ),
        "master_seeds": list(master_seeds),
        "n_individuals_per_seed": n_individuals,
        "representatives_per_seed": representatives_per_seed,
        "experiment_id": EXPERIMENT_ID,
        "config_path": probe_payload["config_path"],
        "config_sha256": probe_payload["config_sha256"],
        "domains": list(domains),
        "max_nodes": int(chain.network.max_nodes),
        "target_density": float(chain.rgcd.target_density),
        "allow_self_loops": bool(chain.rgcd.allow_self_loops),
        "representative_rule": (
            "每 seed 在 danionet_built 个体里取 |N - median(N)| 最小者（并列按 index 升序）"
        ),
        "caliber_note": (
            "support_edges == trainable_elements == DanioNet.support 元素和；"
            "支撑为 off-diagonal（allow_self_loops=false），故对角恒 0"
        ),
        "architecture_probe": probe_payload,
        "representatives": representatives,
    }
    payload["digest"] = probe.content_digest(payload)
    return payload


def write_csv(payload: dict[str, Any], path: Path) -> Path:
    """长表落盘。``lineterminator="\\n"`` + ``newline=""``：换行符不随平台漂。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(LONG_COLUMNS)
        for record in long_records(payload):
            writer.writerow([record[column] for column in LONG_COLUMNS])
    return path


def write_json(payload: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path


def load_payload(path: Path) -> dict[str, Any]:
    """读回产物并校验 digest（防止手工改过 JSON 却仍被当成凭证）。"""
    payload = json.loads(path.read_text(encoding="utf-8"))
    digest = payload.get("digest")
    expected = load_probe_module().content_digest(payload)
    if digest != expected:
        raise ValueError(f"{path} 的 digest 不自洽：{digest} != {expected}")
    return payload


def _print_summary(payload: dict[str, Any], json_path: Path, csv_path: Path) -> None:
    pooled = payload["architecture_probe"]["pooled"]
    print("F7 连接矩阵落盘（管道：config -> motif -> 种群 -> q(G) -> RGCD -> DanioNet）")
    print(
        f"  seeds           : {payload['master_seeds']}"
        f"  x {payload['n_individuals_per_seed']} 个体"
        f"（代表个体 {len(payload['representatives'])} 个）"
    )
    print(f"  配置            : {payload['config_path']}  sha256={payload['config_sha256'][:12]}")
    neurons = pooled["n_neurons"]
    edges = pooled["support_edges"]
    print(
        f"  容量 vs 实际 N  : 张量 {payload['max_nodes']}x{payload['max_nodes']}"
        f" = {payload['max_nodes'] ** 2} 元素/个体；"
        f"N 中位 {neurons['median']}（{neurons['min']}--{neurons['max']}）"
    )
    print(
        f"  支撑 vs 全张量  : 支撑边中位 {edges['median']}"
        f"（{edges['min']}--{edges['max']}）= 张量元素的"
        f" {edges['median'] / payload['max_nodes'] ** 2:.1%}"
    )
    for rep in payload["representatives"]:
        print(
            f"  代表个体        : seed {rep['master_seed']} idx {rep['index']}"
            f"  N={rep['n_neurons']}  边={rep['support_edges']}"
            f"（E/I = {rep['excitatory_edges']}/{rep['inhibitory_edges']}）"
            f"  密度={rep['support_density']:.6f}"
            f"  可训练={rep['trainable_elements']}"
            + ("  <- primary" if rep["is_primary"] else "")
        )
    print(f"  digest          : {payload['digest']}")
    print(f"  写出            : {json_path}")
    print(f"  写出            : {csv_path}")


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdout()
    parser = argparse.ArgumentParser(description="F7 连接矩阵落盘（48x48 W^0 / 支撑 / Theta）")
    parser.add_argument("--seeds", default=DEFAULT_SEEDS, help="逗号分隔的 master seed 列表")
    parser.add_argument(
        "--n-individuals", type=int, default=DEFAULT_N_INDIVIDUALS, help="每个 seed 的个体数"
    )
    parser.add_argument(
        "--representatives-per-seed",
        type=int,
        default=DEFAULT_REPRESENTATIVES_PER_SEED,
        help="每个 seed 落盘几个代表个体的完整张量",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="模型链配置 yaml")
    parser.add_argument("--json", default=str(DEFAULT_JSON), help="机器可读落盘路径")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="扁平长表落盘路径")
    args = parser.parse_args(argv)

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    payload = build_payload(
        seeds,
        n_individuals=args.n_individuals,
        config_path=Path(args.config),
        representatives_per_seed=args.representatives_per_seed,
    )

    json_path = write_json(payload, Path(args.json))
    csv_path = write_csv(payload, Path(args.csv))
    if not payload["representatives"]:
        print("警告：本次样本里没有任何可构造 DanioNet 的个体，未落盘任何 48x48 张量", file=sys.stderr)

    _print_summary(payload, json_path, csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
