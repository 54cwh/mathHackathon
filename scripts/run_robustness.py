"""Experiment E（删边退化）CLI（薄壳；业务 owner：`experiment/robustness_run.py`）。

口径 `experiment §3.5`。用法::

    uv run python scripts/run_robustness.py --experiment-id expE-0001

读 `configs/default_model.yaml` 与 `configs/default_arena.yaml`，seeds 缺省取
`configs/experiment_seeds.yaml`；写 `results/tables/<experiment_id>_robustness.json`
（schema `schemas/robustness.schema.json`）。产物 `status=草案待确认`，不得进正式结果。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:  # 允许未 editable 安装时 `python scripts/...`
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from evogenesis.arena.config import load_arena_config  # noqa: E402
from evogenesis.experiment import robustness_run as R  # noqa: E402
from evogenesis.experiment.config import load_formal_seeds  # noqa: E402
from evogenesis.experiment.console import force_utf8_stdout  # noqa: E402
from evogenesis.pipeline import load_model_chain_config  # noqa: E402

DEFAULT_MODEL = _REPO_ROOT / "configs" / "default_model.yaml"
DEFAULT_ARENA = _REPO_ROOT / "configs" / "default_arena.yaml"


def _parse_seeds(value: str | None) -> tuple[int, ...]:
    if value is None:
        return tuple(load_formal_seeds().seeds)
    seeds = tuple(int(token) for token in value.split(",") if token.strip())
    if not seeds:
        raise argparse.ArgumentTypeError("seeds 不能为空")
    return seeds


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdout()
    parser = argparse.ArgumentParser(description="Experiment E 删边退化（experiment §3.5）")
    parser.add_argument("--experiment-id", required=True, help="实验 id（产物文件名）")
    parser.add_argument("--model-config", default=str(DEFAULT_MODEL))
    parser.add_argument("--arena-config", default=str(DEFAULT_ARENA))
    parser.add_argument("--seeds", default=None, help="逗号分隔 master seed（缺省取配置种子）")
    parser.add_argument("--n-danio", type=int, default=R.DEFAULT_N_DANIO, help="每 seed 候选个体数")
    parser.add_argument(
        "--steps", type=int, default=None, help="episode 步数（缺省取 Arena config）"
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--json", default=None, help="产物路径（缺省 results/tables/<id>_robustness.json）"
    )
    args = parser.parse_args(argv)

    chain = load_model_chain_config(args.model_config)
    arena_config = load_arena_config(args.arena_config)
    payload = R.run_robustness(
        experiment_id=args.experiment_id,
        seeds=_parse_seeds(args.seeds),
        chain=chain,
        arena_config=arena_config,
        n_danio=args.n_danio,
        steps=args.steps,
        device=args.device,
    )

    out = Path(args.json) if args.json else R.table_path(args.experiment_id, _REPO_ROOT / "results")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    shown = out.relative_to(_REPO_ROOT) if out.is_relative_to(_REPO_ROOT) else out
    print(f"Experiment E → {shown}  status={payload['status']}")
    for fraction in payload["fractions"]:
        key = f"{fraction:g}"
        agg = payload["aggregate"].get(key, {}).get("composite_fitness", {})
        deg = payload["degradation"].get(key, {}).get("composite_fitness", {})
        delta = deg.get("mean_abs") if fraction != 0.0 else 0.0
        print(f"  f={fraction:.2f}  composite={agg.get('mean')}  Δ={delta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
