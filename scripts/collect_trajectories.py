"""薄 CLI：调用 `evogenesis.experiment.collect` 采集 Stage-1 专家轨迹。

业务逻辑（episode 子种子、Arena 采集、header/step 落盘）owner 为
`src/evogenesis/experiment/collect.py`（依据 `core §4.5` 产出方 = `experiment`/`scripts` 编排、
`experiment/实验与评价体系.md` §5.1）；本脚本只做 argparse、路径解析、调用与打印
（AGENTS：`scripts/` 为薄 CLI 入口，不放业务逻辑）。

产出：`results/runs/<experiment_id>-s<seed>/trajectories/episode_<episode_id>.jsonl`。

用法：

    uv run python scripts/collect_trajectories.py \\
        --experiment-id exp-0001 --seed 1103 --environment-id <env> \\
        --schema-version <semver>
"""

from __future__ import annotations

import argparse
from pathlib import Path

from evogenesis.arena.config import load_arena_config
from evogenesis.experiment.collect import (
    collect_trajectories,
    default_trajectories,
)
from evogenesis.experiment.console import force_utf8_stdout

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARENA_CONFIG = "configs/default_arena.yaml"
DEFAULT_MODEL_CONFIG = "configs/default_model.yaml"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Stage-1 expert trajectories.")
    parser.add_argument("--experiment-id", required=True, help="稳定实验 ID（run 目录前缀）")
    parser.add_argument("--seed", type=int, required=True, help="master seed（core §3）")
    parser.add_argument(
        "--environment-id", required=True, help="环境对照组 ID（取值集合待定，见文档缺口）"
    )
    parser.add_argument(
        "--schema-version",
        required=True,
        help="轨迹 schema 版本 SemVer（schemas/trajectory.schema.json，取值来源待定，见文档缺口）",
    )
    parser.add_argument(
        "--trajectories",
        type=int,
        default=None,
        help="episode 条数；默认取 configs/default_model.yaml::learning.trajectories",
    )
    parser.add_argument("--generation", type=int, required=True, help="演化代数（进入 header）")
    parser.add_argument(
        "--arena-config", default=DEFAULT_ARENA_CONFIG, help="Arena 配置路径（取 episode_steps 等）"
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="输出目录；默认 results/runs/<experiment_id>-s<seed>/trajectories/（core §4.5）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    # 打印含“→”；被重定向时 stdout 回落 GBK，先切 UTF-8 以免崩溃。
    force_utf8_stdout()
    args = _parse_args(argv)

    arena_config_path = Path(args.arena_config)
    if not arena_config_path.is_absolute():
        arena_config_path = ROOT / arena_config_path
    config = load_arena_config(arena_config_path)

    trajectories = (
        args.trajectories
        if args.trajectories is not None
        else default_trajectories(ROOT / DEFAULT_MODEL_CONFIG)
    )
    out_dir = (
        Path(args.out_dir)
        if args.out_dir is not None
        else ROOT / "results" / "runs" / f"{args.experiment_id}-s{args.seed}" / "trajectories"
    )

    written = collect_trajectories(
        config,
        experiment_id=args.experiment_id,
        environment_id=args.environment_id,
        generation=args.generation,
        schema_version=args.schema_version,
        seed=args.seed,
        trajectories=trajectories,
        out_dir=out_dir,
    )
    print(f"已写入 {len(written)} 条 episode 轨迹 → {out_dir}")


if __name__ == "__main__":
    main()
