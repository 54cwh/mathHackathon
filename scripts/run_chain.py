"""薄 CLI：DanioNet 驱动 Arena 跑一代评估（**模型评估入口**）。

链路：genome → 发育 → connectome → Arena。驱动方分工（`experiment §3.3`、`learning §5`）：
本脚本为 **DanioNet 驱动**；`ExpertPolicy` 基线 / 环境 pre-check 见 `scripts/run_arena.py`。
规模：默认 `--n` 取 `configs/evolution.yaml::population_size`（48）。

上游链路的**生产入口**（`pipeline/模型链装配.md` §4）：业务逻辑全在 `evogenesis.pipeline`，
落盘格式 owner 为 `experiment`（`metrics.csv` / `events.jsonl` / `seed_summary.json`，
run 目录布局见 `experiment/实验与评价体系.md` §5.1）。本脚本只解析参数、调用与写盘。

用法：
    uv run python scripts/run_chain.py --experiment-id exp-chain --seed 1103
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from evogenesis.arena.config import load_arena_config
from evogenesis.core.config import read_yaml
from evogenesis.experiment import runlayout
from evogenesis.experiment.events import episode_event_header, write_event_log
from evogenesis.experiment.metrics import aggregate_by_seed, episode_metrics
from evogenesis.pipeline import (
    arena_seeds_for,
    initial_population,
    load_model_chain_config,
    run_arena_episode,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "configs" / "default_model.yaml"
DEFAULT_ARENA = ROOT / "configs" / "default_arena.yaml"


def _default_population_size() -> int:
    """默认取 `configs/evolution.yaml::population_size`（`evolution §5`）。"""
    path = ROOT / "configs" / "evolution.yaml"
    if path.is_file():
        value = read_yaml(path).get("population_size")
        if value:
            return int(value)
    return 48


def _write_metrics_csv(path: Path, rows: list[dict]) -> None:
    fields = list(rows[0]) if rows else ["seed", "fish_id"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DanioNet 驱动 Arena 跑一代评估")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--seed", type=int, default=1103)
    parser.add_argument("--generation", type=int, default=0)
    parser.add_argument("--n", type=int, default=None, help="种群规模；缺省取 evolution.yaml")
    parser.add_argument("--steps", type=int, default=None, help="缺省取 world.episode_steps")
    parser.add_argument("--model-config", default=str(DEFAULT_MODEL))
    parser.add_argument("--arena-config", default=str(DEFAULT_ARENA))
    parser.add_argument("--out-root", default=str(ROOT / "results" / "runs"))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    chain = load_model_chain_config(args.model_config)
    arena_config = load_arena_config(args.arena_config)
    steps = arena_config.world.episode_steps if args.steps is None else args.steps
    n = _default_population_size() if args.n is None else args.n

    population = initial_population(
        master_seed=args.seed,
        experiment_id=args.experiment_id,
        n=n,
        layout=chain.layout,
    )
    result = run_arena_episode(
        population,
        master_seed=args.seed,
        chain=chain,
        arena_config=arena_config,
        steps=steps,
        generation=args.generation,
    )

    run_dir = runlayout.create_run_dir(
        experiment_id=args.experiment_id,
        seed=args.seed,
        config_path=args.arena_config,
        out_root=args.out_root,
    )
    spawn_seed, _ = arena_seeds_for(args.seed)
    write_event_log(
        run_dir / "events.jsonl",
        episode_event_header(
            experiment_id=args.experiment_id,
            episode_id="ep0001",
            environment_id="default",
            generation=args.generation,
            episode_seed=spawn_seed,
            n_events=len(result.events),
        ),
        result.events,
    )
    rows = [
        {
            "seed": args.seed,
            "fish_id": fish_id,
            **episode_metrics(rec, episode_steps=steps, e_max=arena_config.energy.e_max),
        }
        for fish_id, rec in sorted(result.per_fish.items())
    ]
    _write_metrics_csv(run_dir / "metrics.csv", rows)
    (run_dir / "seed_summary.json").write_text(
        json.dumps(aggregate_by_seed(rows), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"chain run: {run_dir}｜viable {result.evaluated_individuals}/{n}"
        f"｜steps {result.steps}｜events {len(result.events)}"
    )


if __name__ == "__main__":
    main()
