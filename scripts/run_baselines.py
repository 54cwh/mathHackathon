"""薄 CLI：Experiment C baseline 对照（`实验与评价体系.md` §3.3）。

业务逻辑全在 `evogenesis.experiment.baseline_run`；本脚本只解析参数、建 run 目录、调用与写盘。

用法：
    uv run python scripts/run_baselines.py --experiment-id expC \\
        --trajectories-dir results/runs/<collect_run>/trajectories
    uv run python scripts/run_baselines.py --experiment-id expC \\
        --trajectories-dir <dir> --seeds 1103,2207,3301
"""

from __future__ import annotations

import argparse
from pathlib import Path

from evogenesis.arena.config import load_arena_config
from evogenesis.evolution.config import load_evolution_config
from evogenesis.experiment import runlayout
from evogenesis.experiment.baseline_run import (
    comparison_payload,
    run_baseline_comparison,
    table_path,
)
from evogenesis.experiment.config import load_formal_seeds
from evogenesis.experiment.learning_run import load_learning_config
from evogenesis.experiment.run_artifacts import dump_json
from evogenesis.pipeline import load_model_chain_config

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "configs" / "default_model.yaml"
DEFAULT_ARENA = ROOT / "configs" / "default_arena.yaml"
DEFAULT_EVOLUTION = ROOT / "configs" / "evolution.yaml"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment C baseline 对照")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument(
        "--trajectories-dir",
        required=True,
        help="Stage-1 专家轨迹目录（episode_*.jsonl；与 BC 同数据）",
    )
    parser.add_argument(
        "--seeds",
        default=",".join(str(s) for s in load_formal_seeds().seeds),
        help="逗号分隔；缺省取 configs/experiment_seeds.yaml",
    )
    parser.add_argument(
        "--n-danio", type=int, default=12, help="DanioNet 候选个体数（取首个 viable）"
    )
    parser.add_argument("--steps", type=int, default=None, help="缺省取 world.episode_steps")
    parser.add_argument("--model-config", default=str(DEFAULT_MODEL))
    parser.add_argument("--arena-config", default=str(DEFAULT_ARENA))
    parser.add_argument("--evolution-config", default=str(DEFAULT_EVOLUTION))
    parser.add_argument("--out-root", default=str(ROOT / "results" / "runs"))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    seeds = tuple(int(s) for s in args.seeds.split(",") if s.strip())
    chain = load_model_chain_config(args.model_config)
    arena_config = load_arena_config(args.arena_config)
    evolution_config = load_evolution_config(args.evolution_config)
    learning_config = load_learning_config(args.model_config)

    run_dirs: dict[int, Path] = {}
    for seed in seeds:
        run_dirs[seed] = runlayout.create_run_dir(
            experiment_id=args.experiment_id,
            seed=seed,
            config_path=args.arena_config,
            out_root=args.out_root,
            extra_configs=(args.model_config, args.evolution_config),
        )

    result = run_baseline_comparison(
        experiment_id=args.experiment_id,
        seeds=seeds,
        chain=chain,
        arena_config=arena_config,
        learning_config=learning_config,
        evolution_config=evolution_config,
        trajectories_dir=args.trajectories_dir,
        run_dir_of=lambda seed: run_dirs[seed],
        n_danio=args.n_danio,
        steps=args.steps,
    )
    for run_dir in run_dirs.values():
        runlayout.update_run_status(run_dir, "completed")

    tables = ROOT / "results" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    out = table_path(args.experiment_id, ROOT / "results")
    dump_json(out, comparison_payload(result, n_agents=1), indent=2)
    print(f"Experiment C 对照表（{len(seeds)} seeds）→ {out.relative_to(ROOT)}")
    for model in result.models:
        metrics = model["metrics"]
        headline = "—" if metrics is None else f"capture_rate={metrics['capture_rate']['mean']:.6g}"
        print(f"  {model['model']:16s} {headline}")


if __name__ == "__main__":
    main()
