"""架构尺寸 probe：`paper/报告-骨架.md` §2.1 / §6 那组「实测结构规模」数字的可重放凭证。

固定 master seed 跑一次**模型链前半段**
（`configs/default_model.yaml` -> motif 目录 -> 初始种群 -> ``q(G)`` -> RGCD 发育 -> `DanioNet`），
把论文引用的架构尺寸落盘成机器可读 JSON：

- 神经元数 ``N``、支撑边数、支撑密度 ``edges / (N(N-1))``；
- ``Theta`` 张量形状（batch 内 padding 到 ``development.max_neurons`` = 48，故 48x48 = 2304）
  与**支撑内有效可训练元素数**（`DanioNet.support` 的元素和，与支撑边数同源）；
- 六类 cell type 的计数、左右 motor 池大小。

只做**编排**：不新造数值、不复算发育算法，全部走 `pipeline.model_chain`（与生产同一条路径）。

**确定性**：产物不含任何时间戳，同一 ``(seeds, n_individuals, config)`` 两次运行逐字节相同
（``digest`` 字段给内容 sha256）；见 `tests/test_probe_architecture.py`。

用法::

    .venv/Scripts/python.exe scripts/probe_architecture.py
    .venv/Scripts/python.exe scripts/probe_architecture.py --seeds 1103 --n-individuals 36
    .venv/Scripts/python.exe scripts/probe_architecture.py --json out.json

口径说明（引用本文件的数字前必读）：

- 统计单位是**个体**（generation-0 种群里的一个 genome），不是 seed。
  ``N`` / 边数 / cell type 计数在个体间**方差很大**（2026-09-26 §7 修复前另有若干个体 motor
  池为空或缺失 fate、无法构造 `DanioNet`；修复后本档已无此类个体，字段与守护仍保留）；
  引用时**必须并列分布**（``pooled`` 块给 min/median/mean/max），
  只报一个数会把读者引到「架构是固定的」这一错误印象。
- ``phenotype_viable`` 是本次 probe 的**副产品**（`develop` 本就返回该字段）。
  发育通过率的**正式交付物**是 ``scripts/make_fig_viability.py``（F6），两者口径不同、不互相替代。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from evogenesis.connectome.danionet import DanioNet, motor_sides
from evogenesis.development.config import RGCDConfig
from evogenesis.development.rgcd import ConnectomePhenotype
from evogenesis.experiment.console import force_utf8_stdout
from evogenesis.pipeline.model_chain import (
    ModelChainConfig,
    initial_population,
    load_model_chain_config,
    motif_catalog,
    phenotypes_of,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "default_model.yaml"
DEFAULT_JSON = ROOT / "results" / "tables" / "architecture_probe.json"

#: 正式 seed 轴（镜像 `configs/experiment_seeds.yaml` 的 ``seeds: [1103, 2207, 3301]``）。
DEFAULT_SEEDS = "1103,2207,3301"
#: 每个 seed 的 probe 种群规模（与 F6 发育 viability probe 的 14 个个体同量级）。
DEFAULT_N_INDIVIDUALS = 14
#: probe 专用的 ``experiment_id``（`mint_id` 的命名空间，不影响数值）。
PROBE_EXPERIMENT_ID = "arch-probe"


def content_digest(payload: dict[str, Any]) -> str:
    """payload 内容的 sha256（**忽略 ``digest`` 字段本身**），用于比对两次运行。

    规范化：``sort_keys=True`` + 紧凑分隔符 + ``ensure_ascii=False`` —— 与落盘缩进无关，
    故「改缩进」不会改 digest，「改任一数字」一定改 digest。
    """
    body = {key: value for key, value in payload.items() if key != "digest"}
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _stats(values: list[int] | list[float]) -> dict[str, Any]:
    """min / median / mean / max；整数输入保持整数（只在 ``mean`` 上取整到 6 位）。

    **空子集返回 ``None`` 而非抛异常**：小样本下 ``pooled_viable`` /
    ``pooled_danionet_built`` 完全可能一个个体都没有 —— 历史成因是发育通过率低（约 1/10）
    且 motor 池为空的个体无法构造 `DanioNet`；2026-09-26 §7 修复后真实数据已不产出空子集，
    但该降级路径仍须成立（`tests/test_probe_architecture.py` 以显式注入守护）。
    此时 ``n = 0`` 就是结论本身，不该让整个 probe 崩掉。
    """
    if not values:
        return {"n": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "mean": round(statistics.fmean(values), 6),
        "max": max(values),
    }


def _display_path(path: Path) -> str:
    """仓库内路径记成相对（正斜杠，跨平台一致）；仓库外退化为绝对路径。"""
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _support_edges(adjacency: Any) -> int:
    """支撑边数 = ``A`` 的非零**非对角**元素数（``allow_self_loops=false``，对角恒 0）。"""
    nonzero = int((adjacency != 0).sum().item())
    diagonal = int((adjacency.diagonal() != 0).sum().item())
    return nonzero - diagonal


def _cell_type_counts(phenotype: ConnectomePhenotype, domains: tuple[str, ...]) -> dict[str, int]:
    """按 ``development.domains`` 顺序统计六类 cell type（缺失的类记 0，不做隐式补位）。"""
    counter = Counter(phenotype.cell_type.tolist())
    return {name: counter.get(index, 0) for index, name in enumerate(domains)}


def _motor_pools(phenotype: ConnectomePhenotype, domains: tuple[str, ...]) -> tuple[int, int]:
    """左右 motor 池大小：复用 `DanioNet` §5 的 x 中位数二分（`danionet.motor_sides`）。"""
    motor_index = domains.index("motor")
    motor_local = (phenotype.cell_type == motor_index).nonzero(as_tuple=False).squeeze(-1)
    if motor_local.numel() == 0:
        return 0, 0
    left, right = motor_sides(
        phenotype.positions[motor_local], phenotype.cell_type[motor_local], motor_index
    )
    return int(left.numel()), int(right.numel())


def _probe_individual(
    phenotype: ConnectomePhenotype,
    *,
    master_seed: int,
    index: int,
    genome_id: str,
    fish_id: str,
    chain: ModelChainConfig,
) -> dict[str, Any]:
    """单个体：发育产物层面的尺寸 + 构造 `DanioNet` 取 ``Theta`` 形状与可训练元素数。

    motor 池为空 / 缺失 fate 的个体会被 `DanioNet.__init__` 拒绝（§5 / RGCD §7）；
    此时 ``danionet_built=false`` 并记下 ``danionet_error``，不中断整个 probe。
    """
    domains = chain.network.domains
    n_neurons = int(phenotype.adjacency.shape[0])
    edges = _support_edges(phenotype.adjacency)
    left, right = _motor_pools(phenotype, domains)

    record: dict[str, Any] = {
        "master_seed": master_seed,
        "index": index,
        "genome_id": genome_id,
        "fish_id": fish_id,
        "n_neurons": n_neurons,
        "active_neurons": int(phenotype.active_mask.sum().item()),
        "support_edges": edges,
        # N < 2 时无 off-diagonal，密度定义为 0（发育不会产出 N=0，此处仅作防御）
        "support_density": round(edges / (n_neurons * (n_neurons - 1)), 6)
        if n_neurons > 1
        else 0.0,
        "cell_type_counts": _cell_type_counts(phenotype, domains),
        "motor_left": left,
        "motor_right": right,
        "phenotype_viable": bool(phenotype.viable),
        "viability_reason": phenotype.viability_reason,
    }

    try:
        net = DanioNet([phenotype], master_seed=master_seed, config=chain.network)
    except (ValueError, NotImplementedError) as exc:
        record["danionet_built"] = False
        record["danionet_error"] = str(exc)
        record["theta_shape"] = None
        record["trainable_elements"] = None
        return record

    record["danionet_built"] = True
    record["danionet_error"] = None
    record["theta_shape"] = list(net.theta.shape)
    record["trainable_elements"] = int(net.support.sum().item())
    return record


def _aggregate(rows: list[dict[str, Any]], domains: tuple[str, ...]) -> dict[str, Any]:
    """给定个体子集的分组统计（缺口一律用 ``n`` 显式暴露，不做插补）。"""
    return {
        "n_individuals": len(rows),
        "n_neurons": _stats([r["n_neurons"] for r in rows]),
        "support_edges": _stats([r["support_edges"] for r in rows]),
        "support_density": _stats([r["support_density"] for r in rows]),
        "cell_type_counts": {
            name: _stats([r["cell_type_counts"][name] for r in rows]) for name in domains
        },
        "motor_left": _stats([r["motor_left"] for r in rows]),
        "motor_right": _stats([r["motor_right"] for r in rows]),
        "n_viable": sum(1 for r in rows if r["phenotype_viable"]),
        "n_danionet_built": sum(1 for r in rows if r["danionet_built"]),
    }


def _median_individual(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """``N`` **最接近** pooled 中位数的那个个体 —— 一个可直引的样例。

    个体数为偶数时中位数是两值之半（如 37.5），没有个体取到该值，故取「最近」而非「相等」；
    并列时按 ``(master_seed, index)`` 破平，保证结果唯一且可复现。
    """
    target = statistics.median([r["n_neurons"] for r in rows])
    return min(rows, key=lambda r: (abs(r["n_neurons"] - target), r["master_seed"], r["index"]))


def probe_architecture(
    master_seeds: list[int],
    *,
    n_individuals: int = DEFAULT_N_INDIVIDUALS,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> dict[str, Any]:
    """跑完整 probe 并返回 payload（纯函数：同一入参恒得同一 payload）。"""
    if n_individuals < 1:
        raise ValueError("n_individuals 必须 ≥ 1")
    if not master_seeds:
        raise ValueError("master_seeds 不能为空")
    if not config_path.is_file():
        raise FileNotFoundError(f"缺少配置 {config_path}")

    chain = load_model_chain_config(config_path)
    domains = chain.network.domains
    rgcd: RGCDConfig = chain.rgcd

    rows: list[dict[str, Any]] = []
    per_seed: dict[str, dict[str, Any]] = {}
    for master_seed in master_seeds:
        motifs = motif_catalog(master_seed, chain.layout)
        population = initial_population(
            master_seed=master_seed,
            experiment_id=PROBE_EXPERIMENT_ID,
            n=n_individuals,
            layout=chain.layout,
        )
        phenotypes = phenotypes_of(population, motifs, master_seed=master_seed, config=rgcd)
        seed_rows = [
            _probe_individual(
                phenotype,
                master_seed=master_seed,
                index=index,
                genome_id=individual.genome_id,
                fish_id=individual.fish_id,
                chain=chain,
            )
            for index, (individual, phenotype) in enumerate(
                zip(population, phenotypes, strict=True)
            )
        ]
        rows.extend(seed_rows)
        per_seed[str(master_seed)] = _aggregate(seed_rows, domains)

    built = [r for r in rows if r["danionet_built"]]
    viable = [r for r in rows if r["phenotype_viable"]]
    theta_shapes = {tuple(r["theta_shape"]) for r in built}

    payload: dict[str, Any] = {
        "probe": "architecture",
        "generated_by": "scripts/probe_architecture.py",
        "source": "pipeline.model_chain（config -> motif -> 初始种群 -> q(G) -> RGCD -> DanioNet）",
        "master_seeds": list(master_seeds),
        "n_individuals_per_seed": n_individuals,
        "experiment_id": PROBE_EXPERIMENT_ID,
        # 仓库内记相对路径（可读、跨机器稳定）；仓库外退化为绝对路径（不因 relative_to 崩）
        "config_path": _display_path(config_path),
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "domains": list(domains),
        "max_nodes": int(chain.network.max_nodes),
        "target_density": float(rgcd.target_density),
        "initial_precursors": int(rgcd.initial_precursors),
        "precursors_per_domain": int(rgcd.precursors_per_domain),
        "max_divisions_per_precursor": int(rgcd.max_divisions_per_precursor),
        "per_individual": rows,
        "per_seed": per_seed,
        "pooled": _aggregate(rows, domains),
        "pooled_viable": _aggregate(viable, domains),
        "pooled_danionet_built": _aggregate(built, domains),
        "theta": {
            "shape_per_individual": sorted(list(s) for s in theta_shapes),
            "max_nodes": int(chain.network.max_nodes),
            "elements_per_individual": int(chain.network.max_nodes) ** 2,
            "trainable_elements": _stats([r["trainable_elements"] for r in built]),
            "note": (
                "Theta 与 W^0 同形（batch 内 padding 到 max_nodes=48），"
                "但仅在支撑 A 上非零；trainable_elements 取自 DanioNet.support 的元素和"
            ),
        },
        "median_individual": _median_individual(rows),
    }

    payload["digest"] = content_digest(payload)
    return payload


def _print_summary(payload: dict[str, Any]) -> None:
    pooled = payload["pooled"]
    theta = payload["theta"]
    print("架构尺寸 probe（管道：config -> motif -> 种群 -> q(G) -> RGCD -> DanioNet）")
    print(
        f"  seeds           : {payload['master_seeds']}  x {payload['n_individuals_per_seed']} 个体"
    )
    print(f"  配置            : {payload['config_path']}  sha256={payload['config_sha256'][:12]}")
    print(
        f"  个体总数        : {pooled['n_individuals']}"
        f"（可构造 DanioNet {pooled['n_danionet_built']}，viable {pooled['n_viable']}）"
    )
    for key, label in (
        ("n_neurons", "N 神经元数"),
        ("support_edges", "支撑边数"),
        ("support_density", "支撑密度"),
    ):
        s = pooled[key]
        print(f"  {label}: min={s['min']} median={s['median']} mean={s['mean']} max={s['max']}")
    print(
        f"  Theta 张量      : shape={theta['shape_per_individual']} "
        f"= {theta['elements_per_individual']} 元素/个体，"
        f"支撑内可训练 median={theta['trainable_elements']['median']}"
    )
    counts = "  ".join(
        f"{name}={pooled['cell_type_counts'][name]['median']}" for name in payload["domains"]
    )
    print(f"  cell type 中位  : {counts}")
    print(
        f"  motor 池中位    : L={pooled['motor_left']['median']}"
        f"  R={pooled['motor_right']['median']}"
    )
    print(f"  digest          : {payload['digest']}")


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdout()
    parser = argparse.ArgumentParser(description="架构尺寸 probe（见 paper/报告-骨架.md §2.1）")
    parser.add_argument("--seeds", default=DEFAULT_SEEDS, help="逗号分隔的 master seed 列表")
    parser.add_argument(
        "--n-individuals", type=int, default=DEFAULT_N_INDIVIDUALS, help="每个 seed 的 probe 个体数"
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="模型链配置 yaml")
    parser.add_argument("--json", default=str(DEFAULT_JSON), help="落盘路径（机器可读）")
    args = parser.parse_args(argv)

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    payload = probe_architecture(
        seeds, n_individuals=args.n_individuals, config_path=Path(args.config)
    )

    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _print_summary(payload)
    print(f"  写出            : {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
