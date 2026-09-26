"""薄 CLI：从已落盘的 `metrics.csv` **离线重建** Experiment C 对照表（`experiment §3.3`）。

**为什么存在**：一次全规模 run 中途结束时，已完成 seed 的 `metrics.csv` 仍在盘上。本脚本把这些
seed 恢复成与在线路径**同形**的 `results/tables/<id>_baselines.json`，而不必重训。
业务逻辑全在 `evogenesis.experiment.baseline_run.rebuild_from_metrics_csv`。

**忠实性边界**（见该函数 docstring）：汇总（`_summarise_models`）与结构量都与在线路径**逐位
一致**；**唯一**不可复现的是 `latency` —— 它是 wall-clock 量（`experiment §2.4`），在线路径
自己两次跑也不同，故本脚本的产物**不是**在线路径的逐字节复制品，而是「已在盘的 seed 的合法汇总」。

**权威 producer 仍是在线路径** `scripts/run_baselines.py`。本脚本是**恢复**路径：默认**拒绝覆盖**
已存在的表（加 `--force` 才覆盖），避免把在线路径的 3-seed 权威表降级成 1-seed 表。

用法：
    uv run --frozen python scripts/rebuild_baselines_table.py --experiment-id expC \
        --csv 1103=results/runs/expC-s1103/metrics.csv
    uv run --frozen python scripts/rebuild_baselines_table.py --experiment-id expC \
        --csv 1103=results/runs/expC-s1103/metrics.csv \
        --out results/tables/expC_seed1103_baselines.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from evogenesis.arena.config import load_arena_config
from evogenesis.experiment.baseline_run import (
    comparison_payload,
    rebuild_from_metrics_csv,
    table_path,
)
from evogenesis.experiment.config import load_experiment_config
from evogenesis.experiment.run_artifacts import dump_json
from evogenesis.pipeline import load_model_chain_config

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "configs" / "default_model.yaml"
DEFAULT_ARENA = ROOT / "configs" / "default_arena.yaml"


def _parse_csv_arg(text: str) -> tuple[int, Path]:
    seed_text, sep, path_text = text.partition("=")
    if not sep or not seed_text.strip() or not path_text.strip():
        raise argparse.ArgumentTypeError(f"--csv 需为 SEED=PATH，得到 {text!r}")
    return int(seed_text), Path(path_text)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment C 对照表离线重建（不训练）")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument(
        "--csv",
        action="append",
        type=_parse_csv_arg,
        required=True,
        metavar="SEED=PATH",
        help="已完成 seed 的 metrics.csv；可重复（每个 seed 一次）",
    )
    parser.add_argument("--n-agents", type=int, default=None, help="缺省取 configs/experiment.yaml")
    parser.add_argument(
        "--n-episodes", type=int, default=None, help="缺省取 configs/experiment.yaml"
    )
    parser.add_argument("--n-danio", type=int, default=None, help="缺省取 configs/experiment.yaml")
    parser.add_argument("--steps", type=int, default=None, help="缺省取 world.episode_steps")
    parser.add_argument("--model-config", default=str(DEFAULT_MODEL))
    parser.add_argument("--arena-config", default=str(DEFAULT_ARENA))
    parser.add_argument(
        "--out",
        default=None,
        help="输出路径；缺省 results/tables/<experiment_id>_baselines.json",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="允许覆盖已存在的表（缺省拒绝，以免覆盖在线路径的权威产物）",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    csv_of = dict(args.csv)
    seeds = tuple(sorted(csv_of))

    out = Path(args.out) if args.out else table_path(args.experiment_id, ROOT / "results")
    if out.exists() and not args.force:
        raise SystemExit(
            f"拒绝覆盖已存在的 {out.relative_to(ROOT)} —— 它可能是在线路径（"
            "scripts/run_baselines.py）的权威产物。若确实要用重建结果替换，加 --force；"
            "若想并存，用 --out 指定别的文件名。"
        )

    chain = load_model_chain_config(args.model_config)
    arena_config = load_arena_config(args.arena_config)
    exp_config = load_experiment_config()
    n_agents = exp_config.n_agents if args.n_agents is None else args.n_agents
    n_episodes = exp_config.n_episodes if args.n_episodes is None else args.n_episodes
    n_danio = exp_config.n_danio if args.n_danio is None else args.n_danio

    result = rebuild_from_metrics_csv(
        experiment_id=args.experiment_id,
        seeds=seeds,
        metrics_csv_of=lambda seed: csv_of[seed],
        chain=chain,
        arena_config=arena_config,
        n_agents=n_agents,
        n_episodes=n_episodes,
        n_danio=n_danio,
        steps=args.steps,
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    dump_json(out, comparison_payload(result), indent=2)
    print(
        f"[REBUILD 路径产物] seeds={list(seeds)} × {n_agents} agent × {n_episodes} episode"
        f"（未训练、未跑 Arena）→ {out.relative_to(ROOT)}"
    )
    print(
        "  权威 producer 仍是在线路径 scripts/run_baselines.py；"
        "latency 为本次测量值，非在线那次数"
    )
    for model in result.models:
        metrics = model["metrics"]
        if metrics is None or metrics["capture_rate"]["mean"] is None:
            headline = "—"
        else:
            headline = f"capture_rate={metrics['capture_rate']['mean']:.6g}"
        print(f"  {model['model']:16s} n_agents={model['n_agents']:<3d} {headline}")


if __name__ == "__main__":
    main()
