"""薄 CLI：Experiment D 三臂消融对照（`实验与评价体系.md` §3.4）。

业务逻辑全在 `evogenesis.experiment.ablation_run`；本脚本只解析参数、建 run 目录、调用与写盘。

用法：
    uv run python scripts/run_ablations.py --experiment-id expD --seed 1103 --n 12
    uv run python scripts/run_ablations.py --experiment-id expD \\
        --seeds 1103,2207,3301 --trajectories-dir results/runs/<collect>/trajectories
"""

from __future__ import annotations

import argparse
from pathlib import Path

from evogenesis.arena.config import load_arena_config
from evogenesis.evolution.config import load_evolution_config
from evogenesis.experiment import runlayout
from evogenesis.experiment.ablation_run import (
    run_ablation_comparison,
    table_path,
    write_comparison_table,
)
from evogenesis.experiment.config import load_formal_seeds
from evogenesis.experiment.learning_run import load_learning_config

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "configs" / "default_model.yaml"
DEFAULT_ARENA = ROOT / "configs" / "default_arena.yaml"
DEFAULT_EVOLUTION = ROOT / "configs" / "evolution.yaml"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment D 三臂消融对照")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--seed", type=int, default=1103)
    parser.add_argument(
        "--seeds",
        default=None,
        help="逗号分隔多 seed；缺省取 configs/experiment_seeds.yaml（--seed 仅单跑回退）",
    )
    parser.add_argument("--n", type=int, default=12, help="当代个体数（取首个 viable）")
    parser.add_argument(
        "--tau", type=float, default=5.5, help="homogeneous τ 臂的 τ*（默认中值 5.5）"
    )
    parser.add_argument("--steps", type=int, default=None, help="缺省取 world.episode_steps")
    parser.add_argument("--model-config", default=str(DEFAULT_MODEL))
    parser.add_argument("--arena-config", default=str(DEFAULT_ARENA))
    parser.add_argument("--evolution-config", default=str(DEFAULT_EVOLUTION))
    parser.add_argument(
        "--trajectories-dir",
        default=None,
        help="BC 臂的专家轨迹目录；缺省跳过 BC 臂（仅架构臂）",
    )
    parser.add_argument("--out-root", default=str(ROOT / "results" / "runs"))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.seeds:
        seeds = tuple(int(s) for s in args.seeds.split(",") if s.strip())
    else:
        seeds = tuple(load_formal_seeds().seeds)
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

    result = run_ablation_comparison(
        experiment_id=args.experiment_id,
        seeds=seeds,
        model_config_path=args.model_config,
        arena_config=arena_config,
        learning_config=learning_config,
        evolution_config=evolution_config,
        trajectories_dir=args.trajectories_dir,
        tau=args.tau,
        n=args.n,
        steps=args.steps,
        run_dir_of=lambda seed: run_dirs[seed],
    )
    for run_dir in run_dirs.values():
        runlayout.update_run_status(run_dir, "completed")

    out = write_comparison_table(result, table_path(args.experiment_id, ROOT / "results"))
    print(f"Experiment D 对照表（{len(seeds)} seeds，τ*={args.tau}）→ {out.relative_to(ROOT)}")
    for arm in result.arms:
        metrics = arm["metrics"]
        if metrics is None:
            print(f"  {arm['arm']:16s} —（{arm['note']}）")
            continue
        line = f"  {arm['arm']:16s} capture_rate={metrics['capture_rate']['mean']:.6g}"
        if "flip_rate" in metrics:
            line += f"｜flip_rate={metrics['flip_rate']['mean']:.4g}"
        print(line)


if __name__ == "__main__":
    main()
