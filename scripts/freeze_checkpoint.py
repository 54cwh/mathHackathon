"""薄 CLI：冻结 Demo checkpoint（`pipeline/模型链装配.md` §6）。

用法：
    uv run python scripts/freeze_checkpoint.py --out artifacts/demo
    uv run python scripts/freeze_checkpoint.py --out /tmp/ckpt --no-train   # 快速路径
"""

from __future__ import annotations

import argparse
from pathlib import Path

from evogenesis.core.config import read_yaml
from evogenesis.experiment.freeze_run import freeze_demo_checkpoint

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "configs" / "default_model.yaml"
DEFAULT_ARENA = ROOT / "configs" / "default_arena.yaml"
DEFAULT_DEMO_SEED = ROOT / "configs" / "demo_seed.yaml"


def _default_master_seed() -> int:
    data = read_yaml(DEFAULT_DEMO_SEED) or {}
    seed = data.get("master_seed")
    if not isinstance(seed, int):
        raise ValueError(f"demo_seed.yaml 缺 master_seed：{DEFAULT_DEMO_SEED}")
    return seed


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="冻结 Demo checkpoint（§6）")
    parser.add_argument("--out", default=str(ROOT / "artifacts" / "demo"))
    parser.add_argument("--experiment-id", default="demo")
    parser.add_argument(
        "--master-seed", type=int, default=None, help="缺省取 configs/demo_seed.yaml"
    )
    parser.add_argument("--n", type=int, default=12)
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--environment", default="default")
    parser.add_argument("--model-config", default=str(DEFAULT_MODEL))
    parser.add_argument("--arena-config", default=str(DEFAULT_ARENA))
    parser.add_argument(
        "--train", action=argparse.BooleanOptionalAction, default=True, help="是否跑 BC 训练"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    seed = args.master_seed if args.master_seed is not None else _default_master_seed()
    path = freeze_demo_checkpoint(
        out_dir=args.out,
        model_config_path=args.model_config,
        arena_config_path=args.arena_config,
        experiment_id=args.experiment_id,
        master_seed=seed,
        n=args.n,
        train=args.train,
        steps=args.steps,
        environment=args.environment,
    )
    print(f"checkpoint: {path}（master_seed={seed}, trained={args.train}）")


if __name__ == "__main__":
    main()
