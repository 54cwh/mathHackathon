"""薄 CLI：跑「评估 → 回填 F → advance_generation → 下一代」代循环。

owner：`experiment/代循环编排.md`。

业务逻辑在 `evogenesis.experiment.evolution_run`；本脚本只做参数解析、建 run 目录与调用。
逐代产物落 `<run>/generations/g<gen:04d>/`，汇总落 `<run>/evolution.jsonl`。

用法：
    uv run python scripts/run_evolution.py --experiment-id exp-evo --seed 1103 --generations 5
"""

from __future__ import annotations

import argparse
from pathlib import Path

from evogenesis.arena.config import load_arena_config
from evogenesis.evolution.config import load_evolution_config
from evogenesis.experiment import runlayout
from evogenesis.experiment.config import DEFAULT_EXPERIMENT_CONFIG_PATH, load_experiment_config
from evogenesis.experiment.environments import load_environment
from evogenesis.experiment.evolution_run import run_evolution
from evogenesis.experiment.tracking_run import track_run
from evogenesis.pipeline import load_model_chain_config

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "configs" / "default_model.yaml"
DEFAULT_ARENA = ROOT / "configs" / "default_arena.yaml"
DEFAULT_EVOLUTION = ROOT / "configs" / "evolution.yaml"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the evolution generation loop.")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--seed", type=int, default=1103)
    parser.add_argument(
        "--generations", type=int, default=None, help="缺省取 configs/experiment.yaml::generations"
    )
    parser.add_argument(
        "--environment", default=None, help="环境对照组 ID（缺省=基线；取值见 experiment §4）"
    )
    parser.add_argument("--model-config", default=str(DEFAULT_MODEL))
    parser.add_argument("--arena-config", default=str(DEFAULT_ARENA))
    parser.add_argument("--evolution-config", default=str(DEFAULT_EVOLUTION))
    parser.add_argument("--steps", type=int, default=None, help="缺省取 world.episode_steps")
    parser.add_argument(
        "--fitness-mode",
        default="minmax",
        choices=("minmax", "drop_degenerate", "drift"),
        help="选择用 F 的口径（实验臂）：minmax=evolution §6 现状；"
        "drop_degenerate=剔除代内退化分量并重分权重；drift=漂变对照",
    )
    parser.add_argument(
        "--fitness-floor",
        type=float,
        default=1e-3,
        help="drop_degenerate 的分量跨度下限（代内 min-max 之前）",
    )
    parser.add_argument(
        "--episodes-per-generation",
        type=int,
        default=1,
        help="每代用于折算 F 的独立 episode 数（默认 1）。单次实现的排序可靠性实测仅 0.069；"
        "按 Spearman-Brown，K=14 / 32 / 50 可把可靠性抬到约 0.53 / 0.69 / 0.79。",
    )
    parser.add_argument("--out-root", default=str(ROOT / "results" / "runs"))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    chain = load_model_chain_config(args.model_config)
    try:
        overrides = load_environment(args.environment) if args.environment else None
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    arena_config = load_arena_config(args.arena_config, overrides=overrides)
    evolution_config = load_evolution_config(args.evolution_config)
    generations = (
        load_experiment_config().generations if args.generations is None else args.generations
    )

    run_dir = runlayout.create_run_dir(
        experiment_id=args.experiment_id,
        seed=args.seed,
        config_path=args.arena_config,
        overrides=overrides,
        out_root=args.out_root,
        extra_configs=(
            args.model_config,
            args.evolution_config,
            DEFAULT_EXPERIMENT_CONFIG_PATH,
        ),
    )
    result = run_evolution(
        experiment_id=args.experiment_id,
        master_seed=args.seed,
        generations=generations,
        chain=chain,
        arena_config=arena_config,
        evolution_config=evolution_config,
        run_dir=run_dir,
        environment_id=args.environment or "default",
        steps=args.steps,
        fitness_mode=args.fitness_mode,
        fitness_floor=args.fitness_floor,
        episodes_per_generation=args.episodes_per_generation,
    )
    status = "bottleneck" if result.bottleneck else "completed"
    last = result.summaries[-1] if result.summaries else None
    metrics = (
        {
            "fitness_mean": last.fitness_mean,
            "fitness_std": last.fitness_std,
            "n_viable": last.n_viable,
        }
        if last is not None
        else {}
    )
    track_run(
        run_dir,
        status=status,
        metrics={k: v for k, v in metrics.items() if v is not None},
        tags={"generations_run": result.generations_run},
    )
    print(
        f"evolution run: {run_dir}｜generations {result.generations_run}/{generations}"
        f"｜bottleneck {result.bottleneck}｜final pop {len(result.final_population)}"
    )


if __name__ == "__main__":
    main()
