"""薄 CLI：BC 生命周期学习端到端 run（**Stage 1 采集 → Stage 2 训练 → 前/后对照**）。

链路（`experiment/实验与评价体系.md` §3.8）：`config → 种群 → 发育 → viable →
collect（专家轨迹）→ 逐个体 BC 训练 → 训练前后同一局 DanioNet 驱动评估 → 非遗传证据`。
业务逻辑在 `evogenesis.experiment.learning_run`；本脚本只解析参数、调用与写盘
（AGENTS：`scripts/` 不放业务逻辑）。run 目录布局 owner = `experiment §5.1`。

用法：
    uv run python scripts/run_bc.py --experiment-id exp-bc --seed 1103 --n 12
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from evogenesis.arena.config import load_arena_config
from evogenesis.core.config import ModelConfig, load_config
from evogenesis.experiment import collect, learning_run, runlayout
from evogenesis.experiment.environments import BASELINE, load_environment
from evogenesis.experiment.metrics import aggregate_by_seed
from evogenesis.experiment.overrides import parse_overrides
from evogenesis.experiment.run_artifacts import write_metrics_csv
from evogenesis.pipeline import load_model_chain_config

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "configs" / "default_model.yaml"
DEFAULT_ARENA = ROOT / "configs" / "default_arena.yaml"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BC 生命周期学习端到端 run")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--seed", type=int, default=1103)
    parser.add_argument("--generation", type=int, default=0)
    parser.add_argument("--n", type=int, default=12, help="当代个体数（默认 12）")
    parser.add_argument("--steps", type=int, default=None, help="缺省取 world.episode_steps")
    parser.add_argument("--model-config", default=str(DEFAULT_MODEL))
    parser.add_argument("--arena-config", default=str(DEFAULT_ARENA))
    parser.add_argument(
        "--environment", default=BASELINE, help="环境对照组 ID（缺省 default；见 experiment §4）"
    )
    parser.add_argument(
        "--trajectories",
        type=int,
        default=None,
        help="Stage-1 轨迹条数；缺省取 model config 的 learning.trajectories",
    )
    parser.add_argument(
        "--trajectories-dir",
        default=None,
        help="复用已有轨迹目录；缺省 <run>/trajectories/（不存在则按 learning.trajectories 采集）",
    )
    parser.add_argument(
        "--sign-constrained",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Dale 符号约束（默认开；--no-sign-constrained 为消融对照，learning §4）",
    )
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        help="段级覆盖 section.key=value（可重复）；Experiment D 消融臂，见 experiment §3.4",
    )
    parser.add_argument("--out-root", default=str(ROOT / "results" / "runs"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    model_config = Path(args.model_config)
    arena_config_path = Path(args.arena_config)
    learning_cfg = load_config(model_config, model=ModelConfig).learning
    # 两类覆盖正交：`--override` 只进 model chain，`--environment` 只进 Arena 配置。
    cli_overrides = parse_overrides(args.override) or None
    env_overrides = None if args.environment == BASELINE else load_environment(args.environment)
    arena_config = load_arena_config(arena_config_path, overrides=env_overrides)
    chain = load_model_chain_config(model_config, overrides=cli_overrides)

    run_dir = runlayout.create_run_dir(
        experiment_id=args.experiment_id,
        seed=args.seed,
        config_path=arena_config_path,
        overrides=env_overrides,
        out_root=args.out_root,
    )

    trajectories_dir = (
        Path(args.trajectories_dir) if args.trajectories_dir else run_dir / "trajectories"
    )
    if not list(trajectories_dir.glob(learning_run.TRAJECTORY_GLOB)):
        count = args.trajectories or collect.default_trajectories(model_config)
        collect_config = (
            arena_config
            if args.steps is None
            else replace(arena_config, world=replace(arena_config.world, episode_steps=args.steps))
        )
        collect.collect_trajectories(
            collect_config,
            experiment_id=args.experiment_id,
            environment_id=args.environment,
            generation=args.generation,
            seed=args.seed,
            trajectories=count,
            out_dir=trajectories_dir,
        )
    n_trajectories = len(list(trajectories_dir.glob(learning_run.TRAJECTORY_GLOB)))

    result = learning_run.run_lifetime_learning(
        experiment_id=args.experiment_id,
        master_seed=args.seed,
        chain=chain,
        arena_config=arena_config,
        learning_config=learning_cfg,
        trajectories_dir=trajectories_dir,
        generation=args.generation,
        n=args.n,
        steps=args.steps,
        sign_constrained=args.sign_constrained,
    )

    steps = arena_config.world.episode_steps if args.steps is None else args.steps
    rows = learning_run.metric_rows(
        result,
        seed=args.seed,
        episode_steps=steps,
        arena_config=arena_config,
        generation=args.generation,
    )
    write_metrics_csv(run_dir, rows)
    with (run_dir / "learning.jsonl").open("w", encoding="utf-8") as handle:
        for record in learning_run.learning_records(result):
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    post_rows = [row for row in rows if row["phase"] == "post"]
    (run_dir / "seed_summary.json").write_text(
        json.dumps(aggregate_by_seed(post_rows), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (run_dir / "learning_summary.json").write_text(
        json.dumps(
            learning_run.learning_summary(result, seed=args.seed), indent=2, ensure_ascii=False
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"bc run: {run_dir}｜trajectories {n_trajectories}｜viable {result.n_viable}/{args.n}"
        f"｜sign_constrained {args.sign_constrained}"
        f"｜mean final loss {result.mean_final_loss:.4f}"
    )


if __name__ == "__main__":
    main()
