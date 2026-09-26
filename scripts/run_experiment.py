"""薄 CLI：创建 EvoGenesis experiment run（run 目录布局由 `experiment/runlayout.py` 实现）。

用法：
    uv run python scripts/run_experiment.py --config configs/default_arena.yaml \
        --seed 1 --experiment-id exp-0001
"""

import argparse
from pathlib import Path

from evogenesis.experiment.runlayout import create_run_dir

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an EvoGenesis experiment run.")
    parser.add_argument("--config", required=True, help="configs/ 下的 yaml 路径")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument(
        "--experiment-id",
        required=True,
        help="稳定实验 ID，run 目录名为 <experiment_id>-s<seed>（核心契约，调用方给定）",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path

    try:
        run_dir = create_run_dir(
            experiment_id=args.experiment_id, seed=args.seed, config_path=config_path
        )
    except FileNotFoundError as exc:
        parser.error(str(exc))
    except FileExistsError as exc:
        parser.error(str(exc))
    print(f"已创建 run 目录: {run_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
